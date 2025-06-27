#!/usr/bin/env python3
"""
Service Monitor - Watches for service crashes and attempts recovery
"""

import subprocess
import time
import logging
import logging.handlers
import json
import os
import sys
import signal
import threading
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import docker
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/service_monitor.log'),
        logging.handlers.RotatingFileHandler(
            '/var/log/service_monitor_detailed.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

class ServiceMonitor:
    def __init__(self, config_file='monitor_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.docker_client = docker.from_env()
        self.running = True
        self.recovery_attempts = {}
        self.incident_log = []
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "check_interval": 30,  # seconds
            "max_recovery_attempts": 3,
            "recovery_cooldown": 300,  # 5 minutes
            "services": {
                "docker_containers": [
                    {
                        "name": "eg4-web-monitor",
                        "health_check": {
                            "type": "http",
                            "url": "http://localhost:8282",
                            "timeout": 10,
                            "expected_status": 200
                        },
                        "recovery_actions": [
                            "restart_container",
                            "check_logs",
                            "rebuild_if_needed"
                        ],
                        "alerts": {
                            "email": False,
                            "webhook": None
                        }
                    },
                    {
                        "name": "influxdb",
                        "health_check": {
                            "type": "port",
                            "port": 8086,
                            "timeout": 5
                        },
                        "recovery_actions": [
                            "restart_container"
                        ]
                    },
                    {
                        "name": "grafana",
                        "health_check": {
                            "type": "http",
                            "url": "http://localhost:3000",
                            "timeout": 10,
                            "expected_status": 200
                        },
                        "recovery_actions": [
                            "restart_container"
                        ]
                    }
                ],
                "system_processes": [
                    {
                        "name": "mosquitto",
                        "process_name": "mosquitto",
                        "recovery_actions": [
                            "restart_systemd_service"
                        ]
                    }
                ]
            },
            "alerts": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "from_email": "",
                    "to_email": "",
                    "password": ""
                },
                "log_retention_days": 30
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    default_config.update(loaded_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def check_docker_container(self, container_config):
        """Check health of a Docker container"""
        try:
            container = self.docker_client.containers.get(container_config['name'])
            
            # Check if container is running
            if container.status != 'running':
                return False, f"Container {container_config['name']} is not running (status: {container.status})"
            
            # Perform health check based on type
            health_check = container_config.get('health_check', {})
            check_type = health_check.get('type')
            
            if check_type == 'http':
                import requests
                try:
                    response = requests.get(
                        health_check['url'],
                        timeout=health_check.get('timeout', 10)
                    )
                    if response.status_code != health_check.get('expected_status', 200):
                        return False, f"HTTP check failed: status {response.status_code}"
                except Exception as e:
                    return False, f"HTTP check failed: {e}"
            
            elif check_type == 'port':
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(health_check.get('timeout', 5))
                try:
                    result = sock.connect_ex(('localhost', health_check['port']))
                    sock.close()
                    if result != 0:
                        return False, f"Port {health_check['port']} is not accessible"
                except Exception as e:
                    return False, f"Port check failed: {e}"
            
            # Check container health status if available
            if hasattr(container, 'health'):
                health = container.attrs.get('State', {}).get('Health', {})
                if health.get('Status') == 'unhealthy':
                    return False, "Container health check reports unhealthy"
            
            return True, "Healthy"
            
        except docker.errors.NotFound:
            return False, f"Container {container_config['name']} not found"
        except Exception as e:
            return False, f"Error checking container: {e}"
    
    def check_system_process(self, process_config):
        """Check if a system process is running"""
        process_name = process_config['process_name']
        
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == process_name:
                return True, f"Process {process_name} is running (PID: {proc.info['pid']})"
        
        return False, f"Process {process_name} is not running"
    
    def restart_container(self, container_name):
        """Restart a Docker container"""
        try:
            container = self.docker_client.containers.get(container_name)
            logger.info(f"Restarting container {container_name}")
            container.restart(timeout=30)
            time.sleep(10)  # Give container time to start
            return True, "Container restarted successfully"
        except Exception as e:
            return False, f"Failed to restart container: {e}"
    
    def check_container_logs(self, container_name, lines=100):
        """Check container logs for errors"""
        try:
            container = self.docker_client.containers.get(container_name)
            logs = container.logs(tail=lines, stream=False).decode('utf-8')
            
            # Look for common error patterns
            error_patterns = [
                'FATAL', 'CRITICAL', 'panic', 'segfault',
                'out of memory', 'Cannot allocate memory',
                'Page crashed', 'Connection refused'
            ]
            
            errors_found = []
            for pattern in error_patterns:
                if pattern.lower() in logs.lower():
                    errors_found.append(pattern)
            
            if errors_found:
                logger.warning(f"Found errors in {container_name} logs: {errors_found}")
                return False, f"Errors found: {', '.join(errors_found)}"
            
            return True, "No critical errors in logs"
            
        except Exception as e:
            return False, f"Failed to check logs: {e}"
    
    def rebuild_container(self, container_name):
        """Rebuild and restart a container"""
        try:
            # Find the compose file
            compose_files = [
                'docker-compose.yml',
                'docker-compose.eg4.yml',
                'docker-compose-grafana.yml'
            ]
            
            for compose_file in compose_files:
                if os.path.exists(compose_file):
                    # Check if container is defined in this compose file
                    result = subprocess.run(
                        ['docker', 'compose', '-f', compose_file, 'ps', container_name],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Rebuilding container {container_name} using {compose_file}")
                        
                        # Stop and remove
                        subprocess.run(
                            ['docker', 'compose', '-f', compose_file, 'stop', container_name],
                            check=True
                        )
                        subprocess.run(
                            ['docker', 'compose', '-f', compose_file, 'rm', '-f', container_name],
                            check=True
                        )
                        
                        # Rebuild and start
                        subprocess.run(
                            ['docker', 'compose', '-f', compose_file, 'build', '--no-cache', container_name],
                            check=True
                        )
                        subprocess.run(
                            ['docker', 'compose', '-f', compose_file, 'up', '-d', container_name],
                            check=True
                        )
                        
                        time.sleep(15)  # Give container time to start
                        return True, f"Container rebuilt using {compose_file}"
            
            return False, "Could not find compose file for container"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to rebuild container: {e}"
        except Exception as e:
            return False, f"Error during rebuild: {e}"
    
    def restart_systemd_service(self, service_name):
        """Restart a systemd service"""
        try:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', service_name],
                check=True
            )
            time.sleep(5)
            return True, f"Service {service_name} restarted"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to restart service: {e}"
    
    def execute_recovery_action(self, service_type, service_config, action):
        """Execute a recovery action"""
        service_name = service_config['name']
        
        if action == 'restart_container':
            return self.restart_container(service_name)
        elif action == 'check_logs':
            return self.check_container_logs(service_name)
        elif action == 'rebuild_if_needed':
            log_check = self.check_container_logs(service_name)
            if not log_check[0] and 'Page crashed' in log_check[1]:
                return self.rebuild_container(service_name)
            return True, "Rebuild not needed"
        elif action == 'restart_systemd_service':
            return self.restart_systemd_service(service_name)
        else:
            return False, f"Unknown recovery action: {action}"
    
    def send_alert(self, subject, message, service_config=None):
        """Send alert notification"""
        try:
            # Log the alert
            logger.warning(f"ALERT: {subject} - {message}")
            
            # Send email if configured
            if self.config['alerts']['email']['enabled']:
                self.send_email_alert(subject, message)
            
            # Send to webhook if configured
            if service_config and service_config.get('alerts', {}).get('webhook'):
                self.send_webhook_alert(
                    service_config['alerts']['webhook'],
                    subject,
                    message
                )
                
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def send_email_alert(self, subject, message):
        """Send email alert"""
        email_config = self.config['alerts']['email']
        
        if not all([email_config['from_email'], email_config['to_email'], email_config['password']]):
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = email_config['to_email']
            msg['Subject'] = f"Service Monitor Alert: {subject}"
            
            body = f"""
Service Monitor Alert

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Subject: {subject}

Details:
{message}

--
Service Monitor
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['from_email'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    def send_webhook_alert(self, webhook_url, subject, message):
        """Send webhook alert"""
        try:
            import requests
            payload = {
                'subject': subject,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'service': 'service_monitor'
            }
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
    
    def check_service(self, service_type, service_config):
        """Check a service and perform recovery if needed"""
        service_name = service_config['name']
        
        # Check if service is healthy
        if service_type == 'docker_container':
            is_healthy, status_message = self.check_docker_container(service_config)
        elif service_type == 'system_process':
            is_healthy, status_message = self.check_system_process(service_config)
        else:
            logger.error(f"Unknown service type: {service_type}")
            return
        
        # Log status
        if is_healthy:
            logger.debug(f"{service_name}: {status_message}")
            # Reset recovery attempts on successful check
            if service_name in self.recovery_attempts:
                del self.recovery_attempts[service_name]
        else:
            logger.warning(f"{service_name} UNHEALTHY: {status_message}")
            
            # Check recovery attempts
            if service_name not in self.recovery_attempts:
                self.recovery_attempts[service_name] = {
                    'count': 0,
                    'last_attempt': None
                }
            
            recovery_info = self.recovery_attempts[service_name]
            
            # Check cooldown period
            if recovery_info['last_attempt']:
                time_since_last = datetime.now() - recovery_info['last_attempt']
                if time_since_last.total_seconds() < self.config['recovery_cooldown']:
                    logger.info(f"Skipping recovery for {service_name} - in cooldown period")
                    return
            
            # Check max attempts
            if recovery_info['count'] >= self.config['max_recovery_attempts']:
                logger.error(f"Max recovery attempts reached for {service_name}")
                self.send_alert(
                    f"{service_name} Recovery Failed",
                    f"Service {service_name} has failed {recovery_info['count']} recovery attempts.\n"
                    f"Status: {status_message}\n"
                    f"Manual intervention required."
                )
                return
            
            # Attempt recovery
            recovery_info['count'] += 1
            recovery_info['last_attempt'] = datetime.now()
            
            logger.info(f"Attempting recovery for {service_name} (attempt {recovery_info['count']})")
            
            # Execute recovery actions
            for action in service_config.get('recovery_actions', []):
                success, action_message = self.execute_recovery_action(
                    service_type,
                    service_config,
                    action
                )
                
                logger.info(f"Recovery action '{action}': {action_message}")
                
                if success and action in ['restart_container', 'rebuild_if_needed', 'restart_systemd_service']:
                    # Wait and recheck
                    time.sleep(10)
                    is_healthy_after, status_after = self.check_docker_container(service_config) \
                        if service_type == 'docker_container' \
                        else self.check_system_process(service_config)
                    
                    if is_healthy_after:
                        logger.info(f"Recovery successful for {service_name}")
                        self.send_alert(
                            f"{service_name} Recovered",
                            f"Service {service_name} has been successfully recovered.\n"
                            f"Action: {action}\n"
                            f"Status: {status_after}"
                        )
                        del self.recovery_attempts[service_name]
                        return
            
            # Log incident
            self.incident_log.append({
                'timestamp': datetime.now().isoformat(),
                'service': service_name,
                'status': status_message,
                'recovery_attempts': recovery_info['count'],
                'actions_taken': service_config.get('recovery_actions', [])
            })
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Service Monitor started")
        
        while self.running:
            try:
                # Check Docker containers
                for container_config in self.config['services']['docker_containers']:
                    self.check_service('docker_container', container_config)
                
                # Check system processes
                for process_config in self.config['services']['system_processes']:
                    self.check_service('system_process', process_config)
                
                # Clean up old incident logs
                self.cleanup_incident_log()
                
                # Wait for next check
                time.sleep(self.config['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(10)
    
    def cleanup_incident_log(self):
        """Remove old incidents from log"""
        retention_days = self.config['alerts']['log_retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        self.incident_log = [
            incident for incident in self.incident_log
            if datetime.fromisoformat(incident['timestamp']) > cutoff_date
        ]
    
    def get_status(self):
        """Get current status of all services"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        # Check Docker containers
        for container_config in self.config['services']['docker_containers']:
            is_healthy, message = self.check_docker_container(container_config)
            status['services'][container_config['name']] = {
                'type': 'docker_container',
                'healthy': is_healthy,
                'message': message,
                'recovery_attempts': self.recovery_attempts.get(
                    container_config['name'], {}
                ).get('count', 0)
            }
        
        # Check system processes
        for process_config in self.config['services']['system_processes']:
            is_healthy, message = self.check_system_process(process_config)
            status['services'][process_config['name']] = {
                'type': 'system_process',
                'healthy': is_healthy,
                'message': message,
                'recovery_attempts': self.recovery_attempts.get(
                    process_config['name'], {}
                ).get('count', 0)
            }
        
        return status
    
    def stop(self):
        """Stop the monitor"""
        logger.info("Stopping Service Monitor")
        self.running = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if hasattr(signal_handler, 'monitor'):
        signal_handler.monitor.stop()
    sys.exit(0)


if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start monitor
    monitor = ServiceMonitor()
    signal_handler.monitor = monitor
    
    # Start monitoring in a thread
    monitor_thread = threading.Thread(target=monitor.monitor_loop)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Start a simple HTTP server for status checks
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    class StatusHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/status':
                status = monitor.get_status()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(status, indent=2).encode())
            elif self.path == '/incidents':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(monitor.incident_log, indent=2).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            # Suppress default HTTP logs
            pass
    
    # Start HTTP server
    server = HTTPServer(('0.0.0.0', 9090), StatusHandler)
    logger.info("Status server listening on http://0.0.0.0:9090")
    logger.info("  - GET /status - Current service status")
    logger.info("  - GET /incidents - Incident log")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()
        server.shutdown()