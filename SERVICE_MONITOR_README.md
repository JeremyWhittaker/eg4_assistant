# Service Monitor

A comprehensive service monitoring and auto-recovery system for Docker containers and system processes.

## Features

- **Automatic Health Checks**: Monitors Docker containers and system processes
- **Auto-Recovery**: Attempts to restart or rebuild failed services
- **Smart Recovery Logic**: Includes cooldown periods and max attempt limits
- **Multiple Check Types**:
  - HTTP endpoint checks
  - Port availability checks
  - Container health status
  - Process existence checks
- **Incident Logging**: Tracks all service failures and recovery attempts
- **Web Dashboard**: Real-time status visualization
- **Alert System**: Email and webhook notifications (configurable)
- **Log Analysis**: Checks container logs for common error patterns

## Quick Start

### 1. Start the Service Monitor

```bash
# Build and start the monitor
docker compose -f docker-compose.monitor.yml up -d

# Check logs
docker logs service-monitor -f
```

### 2. Access the Dashboard

- **Status API**: http://localhost:9090/status
- **Incidents API**: http://localhost:9090/incidents
- **Web Dashboard**: http://localhost:9091 (if running monitor_dashboard.py)

### 3. Install as System Service (Optional)

```bash
# Copy systemd service file
sudo cp service-monitor.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable service-monitor
sudo systemctl start service-monitor

# Check status
sudo systemctl status service-monitor
```

## Configuration

Edit `monitor_config.json` to configure services and alerts:

```json
{
  "check_interval": 30,          // How often to check services (seconds)
  "max_recovery_attempts": 3,    // Max recovery attempts before giving up
  "recovery_cooldown": 300,      // Cooldown between recovery attempts (seconds)
  "services": {
    "docker_containers": [
      {
        "name": "container-name",
        "health_check": {
          "type": "http",        // or "port"
          "url": "http://localhost:8080",
          "timeout": 10,
          "expected_status": 200
        },
        "recovery_actions": [
          "check_logs",          // Check logs for errors
          "restart_container",   // Restart the container
          "rebuild_if_needed"    // Rebuild if specific errors found
        ]
      }
    ]
  }
}
```

## Recovery Actions

1. **check_logs**: Analyzes container logs for error patterns
2. **restart_container**: Performs a container restart
3. **rebuild_if_needed**: Rebuilds container if specific errors are found (e.g., "Page crashed")
4. **restart_systemd_service**: Restarts a systemd service (for system processes)

## Error Patterns Detected

The monitor checks for these error patterns in logs:
- FATAL, CRITICAL
- panic, segfault
- out of memory, Cannot allocate memory
- Page crashed, Connection refused

## API Endpoints

### GET /status
Returns current status of all monitored services:
```json
{
  "timestamp": "2025-06-26T22:30:00",
  "services": {
    "eg4-web-monitor": {
      "type": "docker_container",
      "healthy": true,
      "message": "Healthy",
      "recovery_attempts": 0
    }
  }
}
```

### GET /incidents
Returns recent incident log:
```json
[
  {
    "timestamp": "2025-06-26T22:25:00",
    "service": "eg4-web-monitor",
    "status": "Container not running",
    "recovery_attempts": 1,
    "actions_taken": ["restart_container"]
  }
]
```

## Email Alerts

To enable email alerts, update the configuration:

```json
"alerts": {
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "from_email": "your-email@gmail.com",
    "to_email": "alert-recipient@gmail.com",
    "password": "your-app-password"
  }
}
```

## Troubleshooting

### Monitor Not Starting
- Check Docker socket is accessible: `ls -la /var/run/docker.sock`
- Verify network connectivity between monitor and services
- Check logs: `docker logs service-monitor`

### Services Not Being Detected
- Ensure container names match exactly in config
- Verify containers are on the same Docker network
- Check health check URLs are accessible from monitor container

### Recovery Not Working
- Check recovery cooldown period hasn't been exceeded
- Verify max attempts haven't been reached
- Look for specific errors in monitor logs

## Adding New Services

1. Edit `monitor_config.json`
2. Add service definition with appropriate health check
3. Restart monitor: `docker compose -f docker-compose.monitor.yml restart`

## Log Files

- Service monitor logs: `./monitor_logs/service_monitor.log`
- Detailed logs: `./monitor_logs/service_monitor_detailed.log`
- Container logs: Available via `docker logs <container-name>`

## Security Considerations

- The monitor requires Docker socket access to manage containers
- Use appropriate firewall rules for status endpoints
- Store email credentials securely
- Consider using webhook authentication for external alerts