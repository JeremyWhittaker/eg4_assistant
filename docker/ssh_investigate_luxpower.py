#!/usr/bin/env python3
import paramiko
import time

def run_ssh_command(ssh, command, use_sudo=False):
    """Run command via SSH and return output"""
    if use_sudo:
        command = f"echo 'solar123' | sudo -S {command}"
    
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    if error and not error.startswith('[sudo]'):
        print(f"Error: {error}")
    
    return output

def investigate_luxpower_config():
    """SSH into Solar Assistant and investigate Luxpower configuration"""
    
    # SSH connection details
    host = "172.16.109.214"
    username = "solar-assistant"
    password = "solar123"
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=username, password=password)
        print("Connected successfully!\n")
        
        # Check the influx-bridge process details
        print("=== Influx-Bridge Process Details ===")
        output = run_ssh_command(ssh, "ps aux | grep 583")
        print(output)
        
        # Check the application directory
        print("\n=== Application Directory ===")
        output = run_ssh_command(ssh, "ls -la /dev/shm/grafana-sync/", use_sudo=True)
        print(output)
        
        # Look for configuration files
        print("\n=== Configuration Files in /dev/shm ===")
        output = run_ssh_command(ssh, "find /dev/shm -name '*.conf' -o -name '*.config' -o -name '*.json' 2>/dev/null | head -20", use_sudo=True)
        print(output)
        
        # Check systemd service file
        print("\n=== Solar Assistant Service File ===")
        output = run_ssh_command(ssh, "cat /etc/systemd/system/solar-assistant.service", use_sudo=True)
        print(output)
        
        # Check for config in app directory
        print("\n=== App Config Directory ===")
        output = run_ssh_command(ssh, "ls -la /dev/shm/grafana-sync/*/releases/*/", use_sudo=True)
        print(output)
        
        # Check environment variables for the process
        print("\n=== Process Environment ===")
        output = run_ssh_command(ssh, "cat /proc/583/environ | tr '\\0' '\\n' | grep -E '(HOST|PORT|INVERTER|MODBUS|CONFIG)'", use_sudo=True)
        print(output)
        
        # Check for database content
        print("\n=== InfluxDB Databases ===")
        output = run_ssh_command(ssh, "influx -execute 'SHOW DATABASES'", use_sudo=True)
        print(output)
        
        # Check recent measurements
        print("\n=== Recent InfluxDB Measurements ===")
        output = run_ssh_command(ssh, "influx -database solar_assistant -execute 'SHOW MEASUREMENTS' 2>/dev/null", use_sudo=True)
        print(output)
        
        # Check for MQTT topics
        print("\n=== MQTT Topics (if available) ===")
        output = run_ssh_command(ssh, "timeout 5 mosquitto_sub -h localhost -t '#' -v 2>/dev/null | head -20", use_sudo=True)
        print(output)
        
        # Look for the actual config file
        print("\n=== Looking for inverter config ===")
        output = run_ssh_command(ssh, "find /var /etc /opt /home -name '*inverter*' -o -name '*luxpower*' -o -name '*eg4*' 2>/dev/null | grep -v '/proc' | head -20", use_sudo=True)
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    investigate_luxpower_config()