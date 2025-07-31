# Configuration Guide

This document provides detailed information about configuring the EG4-SRP Monitor system.

## Configuration Files

### 1. Application Configuration (`config/config.json`)

The main configuration file stores all application settings in JSON format:

```json
{
    "timezone": "America/Phoenix",
    "email_alerts_enabled": true,
    "email_to": "me@jeremywhittaker.com",
    "thresholds": {
        "battery_low": 90,
        "battery_check_hour": 14,
        "battery_check_minute": 0,
        "peak_demand": 1.0,
        "peak_demand_check_hour": 6,
        "peak_demand_check_minute": 0,
        "grid_import": 1000,
        "grid_import_start_hour": 14,
        "grid_import_end_hour": 20
    }
}
```

**Configuration Options:**

- `timezone`: Selected timezone for alert scheduling
- `email_alerts_enabled`: Global email alert toggle
- `email_to`: Comma-separated list of email recipients
- `thresholds`: Alert threshold settings
  - `battery_low`: SOC percentage threshold (default: 90%)
  - `battery_check_hour/minute`: Daily battery check time (24h format)
  - `peak_demand`: Peak demand threshold in kW (default: 1.0)
  - `peak_demand_check_hour/minute`: Daily peak demand check time
  - `grid_import`: Grid import threshold in watts (default: 1000W)
  - `grid_import_start_hour/end_hour`: Time window for grid import alerts

### 2. Gmail Configuration (`~/.gmail_send/.env`)

Gmail SMTP credentials for email alerts:

```bash
GMAIL_ADDRESS=bot@jeremywhittaker.com
GMAIL_APP_PASSWORD=ssvg wsgf rsma vilo
```

**Important Notes:**
- Use Gmail App Passwords, not regular passwords
- Create App Password at: https://myaccount.google.com/apppasswords
- File permissions should be 600 (read/write for owner only)

### 3. System Credentials (Web Interface Only)

Credentials for EG4, SRP, and Enphase systems are managed through the web interface and stored securely. These are not stored in plain text files but are encrypted and managed by the application.

## Environment Variables

The application can also use environment variables (optional):

```bash
# Flask configuration
FLASK_ENV=production
FLASK_DEBUG=false

# Application settings
EG4_SRP_MONITOR_PORT=5002
EG4_SRP_MONITOR_HOST=127.0.0.1

# Database location (optional)
DATABASE_PATH=./data/eg4_srp_monitor.db
```

## Timezone Configuration

### Supported Timezones

The application supports 6 US timezones:

1. **UTC** - Coordinated Universal Time
2. **America/Phoenix** - Mountain Standard Time (no DST)
3. **America/Los_Angeles** - Pacific Standard/Daylight Time
4. **America/Denver** - Mountain Standard/Daylight Time
5. **America/Chicago** - Central Standard/Daylight Time
6. **America/New_York** - Eastern Standard/Daylight Time

### Timezone Impact

All alert scheduling uses the selected timezone:
- Battery checks occur at the specified time in your timezone
- Peak demand checks occur at the specified time in your timezone
- Grid import alerts only trigger during the configured hours in your timezone

## Alert Configuration

### Battery Alerts

- **Purpose**: Monitor battery state of charge
- **Default**: Check daily at 2:00 PM, alert if SOC < 90%
- **Cooldown**: Once per day maximum
- **Configuration**: Battery threshold percentage and check time

### Peak Demand Alerts

- **Purpose**: Monitor SRP peak demand charges
- **Default**: Check daily at 6:00 AM, alert if demand > 1.0 kW
- **Cooldown**: Once per day maximum
- **Configuration**: Demand threshold in kW and check time

### Grid Import Alerts

- **Purpose**: Monitor grid power import during peak hours
- **Default**: Monitor 2:00-8:00 PM, alert if import > 1000W
- **Cooldown**: 1 hour between alerts
- **Configuration**: Import threshold in watts and time window

## Web Interface Configuration

### Credential Management

All system credentials are managed through the web interface:

1. **Access**: Navigate to http://localhost:5002 → Configuration tab
2. **EG4 Cloud**: Username and password for inverter access
3. **SRP Account**: Username and password for utility data
4. **Enphase Account**: Username and password for solar monitoring
5. **Gmail SMTP**: Email address and App Password for alerts

### Settings Persistence

- Configuration changes are saved immediately to `config/config.json`
- Settings persist across application restarts
- Credentials are stored securely and encrypted
- Backup configuration files are created automatically

### Real-time Updates

Configuration changes take effect immediately for:
- Alert thresholds
- Email settings
- Timezone selection

Changes requiring restart:
- Credential modifications
- Service-level configuration changes

## Advanced Configuration

### Logging Configuration

The application uses a 5-level logging system:

- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning messages for attention
- **ERROR**: Error conditions that don't stop the application
- **CRITICAL**: Serious errors that may stop the application

**Log Configuration:**
- Log file: `logs/eg4_srp_monitor.log`
- Max size: 10MB with 3 rotations
- In-memory buffer: 1000 recent entries for web interface
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Database Configuration

The application uses SQLite for data storage:

- **Location**: `data/eg4_srp_monitor.db` (auto-created)
- **Tables**: Metrics for EG4, SRP, and Enphase data
- **Retention**: No automatic cleanup (manual management required)
- **Backup**: Regular SQLite backup recommended

### Network Configuration

**Default Settings:**
- Host: 127.0.0.1 (localhost only)
- Port: 5002
- Protocol: HTTP with WebSocket upgrades

**Production Considerations:**
- Use reverse proxy (nginx/Apache) for HTTPS
- Configure firewall rules for remote access
- Consider authentication for multi-user environments

### Performance Tuning

**Memory Usage:**
- Typical: ~100MB
- Maximum: 512MB (systemd limit)
- Monitoring: View through systemd or web interface logs

**CPU Usage:**
- Typical: <1%
- Spikes: During data collection (every 60 seconds)
- Monitoring: `top -p $(pgrep -f app.py)`

**Disk Usage:**
- Logs: Rotated at 10MB
- Database: Grows with historical data
- CSV files: Cleaned periodically

## Security Configuration

### File Permissions

```bash
# Application files
chmod 755 app.py install.sh
chmod 644 requirements.txt *.md
chmod 700 config/ logs/ downloads/

# Configuration files
chmod 600 config/config.json
chmod 600 ~/.gmail_send/.env

# Service file
chmod 644 /etc/systemd/system/eg4-srp-monitor.service
```

### Network Security

**Recommended Settings:**
- Bind to localhost only for local access
- Use reverse proxy with SSL/TLS for remote access
- Implement authentication for multi-user access
- Configure firewall rules appropriately

**Firewall Configuration (ufw example):**
```bash
# Allow local access only
sudo ufw deny 5002

# Allow from specific IP range (adjust as needed)
sudo ufw allow from 192.168.1.0/24 to any port 5002

# Allow from specific IP
sudo ufw allow from 192.168.1.100 to any port 5002
```

## Backup and Restore

### Configuration Backup

```bash
# Backup configuration
cp config/config.json config/config.json.backup
cp ~/.gmail_send/.env ~/.gmail_send/.env.backup

# Backup database
cp data/eg4_srp_monitor.db data/eg4_srp_monitor.db.backup
```

### Full System Backup

```bash
# Create backup directory
mkdir -p ~/eg4-monitor-backup/$(date +%Y%m%d)

# Backup all important files
cp -r config/ logs/ data/ ~/.gmail_send/ ~/eg4-monitor-backup/$(date +%Y%m%d)/
```

### Restore Configuration

```bash
# Restore configuration
cp config/config.json.backup config/config.json
cp ~/.gmail_send/.env.backup ~/.gmail_send/.env

# Restart service to apply changes
sudo systemctl restart eg4-srp-monitor
```

## Troubleshooting Configuration Issues

### Configuration Not Loading

1. Check file permissions:
   ```bash
   ls -la config/config.json
   ls -la ~/.gmail_send/.env
   ```

2. Validate JSON syntax:
   ```bash
   python3 -m json.tool config/config.json
   ```

3. Check application logs:
   ```bash
   tail -f logs/eg4_srp_monitor.log
   ```

### Credential Issues

1. Verify credentials through web interface
2. Test Gmail configuration:
   ```bash
   source venv/bin/activate
   send-gmail --to test@example.com --subject "Test" --body "Test message"
   ```

3. Check system access:
   ```bash
   curl -I https://eg4cloud.com
   curl -I https://myaccount.srpnet.com
   ```

### Service Configuration Issues

1. Check service status:
   ```bash
   sudo systemctl status eg4-srp-monitor
   ```

2. View service logs:
   ```bash
   sudo journalctl -u eg4-srp-monitor -n 50
   ```

3. Verify service file:
   ```bash
   sudo systemctl cat eg4-srp-monitor
   ```

For additional troubleshooting, see the main [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide.