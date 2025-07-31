# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the EG4-SRP Monitor system.

## Quick Diagnostics

### System Health Check

Run these commands to quickly assess system status:

```bash
# Check service status
sudo systemctl status eg4-srp-monitor

# Check if application is running
ps aux | grep -v grep | grep app.py

# Check port availability
ss -tulpn | grep :5002

# Check recent logs
tail -20 logs/eg4_srp_monitor.log

# Test web interface
curl -I http://localhost:5002
```

### Log Analysis Commands

```bash
# View live logs
tail -f logs/eg4_srp_monitor.log

# Search for errors
grep -i error logs/eg4_srp_monitor.log

# Search for specific system
grep -i "eg4\|srp\|enphase" logs/eg4_srp_monitor.log

# View systemd service logs
sudo journalctl -u eg4-srp-monitor -f
```

## Common Issues and Solutions

### 1. Service Won't Start

**Symptoms:**
- `sudo systemctl start eg4-srp-monitor` fails
- Service shows "failed" status
- Application not accessible at http://localhost:5002

**Diagnosis:**
```bash
# Check service status
sudo systemctl status eg4-srp-monitor

# View detailed logs
sudo journalctl -u eg4-srp-monitor -n 50

# Check file permissions
ls -la /home/$(whoami)/eg4-srp-monitor/
```

**Common Causes and Solutions:**

**a) File Permission Issues:**
```bash
# Fix ownership
sudo chown -R $(whoami):$(whoami) /path/to/eg4-srp-monitor/

# Fix permissions
chmod +x install.sh
chmod 755 logs/ config/ downloads/
chmod 600 config/config.json ~/.gmail_send/.env
```

**b) Python Environment Issues:**
```bash
# Recreate virtual environment
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

**c) Missing Dependencies:**
```bash
# Install system dependencies
sudo apt update
sudo apt install python3-venv python3-pip curl wget git

# Reinstall Python dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Web Interface Not Accessible

**Symptoms:**
- Browser shows "connection refused" or "site can't be reached"
- Curl returns connection errors

**Diagnosis:**
```bash
# Check if process is running
ps aux | grep app.py

# Check port binding
ss -tulpn | grep 5002

# Test local connection
curl -v http://localhost:5002

# Check firewall
sudo ufw status
```

**Solutions:**

**a) Port Already in Use:**
```bash
# Find process using port 5002
sudo lsof -i :5002

# Kill conflicting process
sudo kill -9 <PID>

# Restart service
sudo systemctl restart eg4-srp-monitor
```

**b) Firewall Blocking Access:**
```bash
# Allow local access
sudo ufw allow from 127.0.0.1 to any port 5002

# Allow LAN access (adjust IP range)
sudo ufw allow from 192.168.1.0/24 to any port 5002
```

**c) Application Crash on Startup:**
```bash
# Check for Python errors
python app.py
# Look for import errors, missing dependencies, etc.
```

### 3. Gmail Authentication Fails

**Symptoms:**
- "Configuration saved but test failed" message
- Email alerts not being sent
- Gmail-related errors in logs

**Diagnosis:**
```bash
# Test Gmail configuration
source venv/bin/activate
send-gmail --to test@example.com --subject "Test" --body "Test message"

# Check Gmail config file
ls -la ~/.gmail_send/.env
cat ~/.gmail_send/.env
```

**Solutions:**

**a) App Password Issues:**
1. Verify you're using an App Password, NOT your regular Gmail password
2. Create new App Password at: https://myaccount.google.com/apppasswords
3. Update credentials through web interface

**b) Configuration File Issues:**
```bash
# Check file exists and has correct permissions
ls -la ~/.gmail_send/.env
chmod 600 ~/.gmail_send/.env

# Verify format (should contain):
# GMAIL_ADDRESS=your-email@gmail.com
# GMAIL_APP_PASSWORD=your-app-password
```

**c) Network/SMTP Issues:**
```bash
# Test SMTP connectivity
telnet smtp.gmail.com 587

# Check if port 587 is blocked
sudo netstat -tulpn | grep 587
```

### 4. Data Not Updating

**Symptoms:**
- Dashboard shows stale data
- "Last updated" timestamp not changing
- No new entries in logs

**Diagnosis:**
```bash
# Check if monitoring threads are active
grep -i "monitor\|thread" logs/eg4_srp_monitor.log

# Check for authentication errors
grep -i "login\|auth" logs/eg4_srp_monitor.log

# Test network connectivity
curl -I https://eg4cloud.com
curl -I https://myaccount.srpnet.com
curl -I https://enlighten.enphaseenergy.com
```

**Solutions:**

**a) Credential Issues:**
1. Update credentials through web interface
2. Verify account access by logging in manually
3. Check for account lockouts or security blocks

**b) Network Connectivity:**
```bash
# Check internet connection
ping google.com

# Check DNS resolution
nslookup eg4cloud.com
nslookup myaccount.srpnet.com
```

**c) Session Expiry:**
- Service automatically handles session refresh
- If persistent issues, restart service: `sudo systemctl restart eg4-srp-monitor`

### 5. High Resource Usage

**Symptoms:**
- High CPU usage (>10% consistently)
- High memory usage (>300MB)
- System slowdown

**Diagnosis:**
```bash
# Check resource usage
top -p $(pgrep -f app.py)
ps aux | grep app.py

# Check memory usage
free -h
cat /proc/meminfo

# Check disk usage
df -h
du -sh logs/ downloads/ data/
```

**Solutions:**

**a) Memory Leaks:**
```bash
# Restart service
sudo systemctl restart eg4-srp-monitor

# Monitor memory usage over time
watch -n 5 'ps aux | grep app.py'
```

**b) Log File Size:**
```bash
# Check log file size
ls -lh logs/eg4_srp_monitor.log*

# Manually rotate if needed
mv logs/eg4_srp_monitor.log logs/eg4_srp_monitor.log.old
sudo systemctl restart eg4-srp-monitor
```

**c) Browser Process Buildup:**
```bash
# Check for zombie browser processes
ps aux | grep chromium

# Kill stuck browser processes
pkill -f chromium
sudo systemctl restart eg4-srp-monitor
```

### 6. SSL/TLS Certificate Errors

**Symptoms:**
- "SSL certificate verification failed" in logs
- Connection timeouts to external services

**Diagnosis:**
```bash
# Test SSL connectivity
openssl s_client -connect eg4cloud.com:443
openssl s_client -connect myaccount.srpnet.com:443

# Check system time
date
timedatectl status
```

**Solutions:**

**a) System Time Issues:**
```bash
# Synchronize system time
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
```

**b) Certificate Issues:**
```bash
# Update CA certificates
sudo apt update
sudo apt install ca-certificates
sudo update-ca-certificates
```

### 7. Database Issues

**Symptoms:**
- "Database locked" errors
- Historical data not saving
- SQLite-related errors in logs

**Diagnosis:**
```bash
# Check database file
ls -la data/eg4_srp_monitor.db

# Test database access
sqlite3 data/eg4_srp_monitor.db ".tables"

# Check for locks
lsof data/eg4_srp_monitor.db
```

**Solutions:**

**a) Database Corruption:**
```bash
# Backup existing database
cp data/eg4_srp_monitor.db data/eg4_srp_monitor.db.backup

# Check integrity
sqlite3 data/eg4_srp_monitor.db "PRAGMA integrity_check;"

# Recreate if corrupted
rm data/eg4_srp_monitor.db
sudo systemctl restart eg4-srp-monitor
```

**b) Permission Issues:**
```bash
# Fix permissions
chmod 664 data/eg4_srp_monitor.db
chown $(whoami):$(whoami) data/eg4_srp_monitor.db
```

## System Maintenance

### Regular Maintenance Tasks

**Weekly:**
```bash
# Check service status
sudo systemctl status eg4-srp-monitor

# Review log files for errors
grep -i error logs/eg4_srp_monitor.log | tail -20

# Check disk space
df -h
```

**Monthly:**
```bash
# Backup configuration and data
mkdir -p ~/backups/eg4-monitor/$(date +%Y%m%d)
cp -r config/ data/ ~/backups/eg4-monitor/$(date +%Y%m%d)/

# Clean old CSV files (if needed)
find downloads/ -name "*.csv" -mtime +30 -delete

# Update dependencies
source venv/bin/activate
pip list --outdated
```

**Quarterly:**
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Review and update credentials
# Check through web interface Configuration tab

# Performance review
# Check resource usage trends
```

### Emergency Recovery

**If System Completely Fails:**

1. **Stop the service:**
   ```bash
   sudo systemctl stop eg4-srp-monitor
   ```

2. **Backup current state:**
   ```bash
   mkdir -p ~/emergency-backup/$(date +%Y%m%d-%H%M%S)
   cp -r logs/ config/ data/ ~/emergency-backup/$(date +%Y%m%d-%H%M%S)/
   ```

3. **Reinstall from scratch:**
   ```bash
   # Clean installation
   rm -rf venv/
   ./install.sh
   ```

4. **Restore configuration:**
   ```bash
   cp ~/emergency-backup/latest/config/config.json config/
   # Reconfigure credentials through web interface
   ```

5. **Restart service:**
   ```bash
   sudo systemctl start eg4-srp-monitor
   ```

## Getting Help

### Information to Collect

When reporting issues, please provide:

1. **System Information:**
   ```bash
   uname -a
   python3 --version
   sudo systemctl --version
   ```

2. **Service Status:**
   ```bash
   sudo systemctl status eg4-srp-monitor
   sudo journalctl -u eg4-srp-monitor -n 100
   ```

3. **Application Logs:**
   ```bash
   tail -100 logs/eg4_srp_monitor.log
   ```

4. **Configuration (sanitized):**
   ```bash
   # Remove sensitive data before sharing
   cat config/config.json | jq 'del(.credentials)'
   ```

### Support Channels

- **GitHub Issues**: https://github.com/JeremyWhittaker/eg4-srp-monitor/issues
- **Discussions**: https://github.com/JeremyWhittaker/eg4-srp-monitor/discussions
- **Documentation**: README.md and CLAUDE.md in repository

### Before Asking for Help

1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Try the emergency recovery steps
4. Collect all relevant information listed above

Remember: The more information you provide, the faster we can help resolve your issue!