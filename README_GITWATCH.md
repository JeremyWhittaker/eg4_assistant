# Gitwatch Configuration

This repository is automatically monitored by gitwatch.

## Service Information
- **Service Name**: gitwatch-eg4-srp-monitor
- **Project Path**: /mnt/data/src/eg4-srp-monitor
- **Auto-commit**: Enabled
- **Auto-push**: Enabled (via SSH)
- **Init System**: systemd

## Management Commands

### SystemD Commands
```bash
# Check status
systemctl --user status ${SERVICE_NAME}

# View logs
journalctl --user -u ${SERVICE_NAME} -f

# Restart service
systemctl --user restart ${SERVICE_NAME}

# Stop service
systemctl --user stop ${SERVICE_NAME}

# Disable service
systemctl --user disable ${SERVICE_NAME}
```

## Troubleshooting
If pushes fail, check:
1. SSH key is added to GitHub
2. SSH agent is running
3. Service logs (see commands above)

Configured on: Fri Jul 25 11:44:27 AM MST 2025
