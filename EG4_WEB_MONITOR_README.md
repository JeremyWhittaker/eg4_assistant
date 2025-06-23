# EG4 Web Monitor

A web-based monitoring interface for EG4 inverters with real-time data display, configurable alerts, and built-in configuration file editor.

## Features

### Real-time Monitoring
- **Automatic monitoring** - No manual start/stop needed
- Live data updates every 30 seconds via WebSocket
- Visual battery state indicator with animated charge/discharge status
- Comprehensive display of:
  - Battery status (SOC, voltage, current, power)
  - Solar production (PV1, PV2, total)
  - Grid status (power, voltage, frequency)
  - Load consumption with percentage
  - Daily energy statistics
  - System status and temperature

### Configuration Tab

#### Credentials Management
- Easy setup of EG4 cloud credentials
- **Automatic credential verification** before saving
- Option to save unverified credentials if needed
- Credentials stored securely in .env file
- Auto-reloads environment when .env is saved

#### Built-in File Editor
- **Visual file browser** showing all configuration files
- Supported file types: `.env`, `.yaml`, `.yml`, `.json`, `.txt`, `.conf`, `.ini`
- **Live editing** with syntax-appropriate monospace font
- **Save functionality** with success notifications
- **Unsaved changes warning** when switching files or leaving
- File size and icons for easy identification
- Supports files in main directory and `config/` subdirectory

### Alert System

#### 1. Battery SOC Alert
- Check battery state of charge at a specific time daily
- Configure minimum acceptable SOC percentage
- Example: Alert if battery is below 80% at 6:00 AM

#### 2. Peak Demand Alert
- Monitor load during peak hours
- Set maximum load threshold (watts)
- Configure monitoring time window
- Alert if load exceeds threshold for X consecutive minutes
- Example: Alert if load > 5000W for 5+ minutes between 4-9 PM

#### 3. Cloud Connectivity Alert
- Monitor connection to EG4 cloud service
- Alert if connection fails for 3+ consecutive attempts
- Helps identify internet or service issues

### Visual Notifications
- Color-coded alerts (warning/critical/success)
- Pop-up notifications in browser
- Real-time alert delivery via WebSocket
- Connection status indicator (green when connected)

## Installation

1. Install requirements:
```bash
pip install -r requirements_web.txt
playwright install chromium
```

2. Configure credentials:
   - Option 1: Use the web interface Configuration tab (recommended)
   - Option 2: Create .env file:
   ```
   EG4_MONITOR_USERNAME=your_username
   EG4_MONITOR_PASSWORD=your_password
   ```

## Usage

### Start the Web Monitor

```bash
# Using the startup script
./start_web_monitor.sh

# Or manually
python3 eg4_web_monitor.py

# Run in background
nohup python3 eg4_web_monitor.py > web_monitor.log 2>&1 &
```

The web interface will be available at: `http://localhost:8282`

### Initial Setup

1. Open web browser to `http://localhost:8282`
2. Click on "Configuration" tab
3. Enter your EG4 cloud credentials
4. Click "Save Configuration"
   - Credentials will be verified automatically
   - If verification fails, you'll be prompted to save anyway
5. Once verified, monitoring starts automatically

### Using the File Editor

1. Go to "Configuration" tab
2. In the "Configuration Files" section:
   - Click any file in the left panel to open it
   - Edit the content in the main editor
   - Click "Save" to persist changes
   - Warning appears if you have unsaved changes

### Setting Up Alerts

1. Go to "Monitoring" tab
2. Scroll down to "Alert Configuration"
3. Configure each alert type:
   - **Battery SOC**: Set check time and minimum SOC
   - **Peak Demand**: Set time range, max load, and duration
   - **Cloud Connectivity**: Simply enable/disable
4. Click "Save Alert Configuration"

### Alert Examples

#### Battery SOC Alert
- Check Time: 06:00
- Minimum SOC: 80%
- Alert: "Battery SOC Alert: 75% is below minimum 80% at 06:00"

#### Peak Demand Alert
- Time Range: 16:00 - 21:00
- Max Load: 5000W
- Duration: 5 minutes
- Alert: "Peak Demand Alert: Load 5500W exceeded 5000W for 5 minutes"

#### Cloud Connectivity Alert
- Triggers after 3 consecutive connection failures
- Alert: "Cloud Connectivity Alert: Failed to connect to EG4 cloud"

## Technical Details

### Architecture
- **Backend**: Flask with SocketIO for real-time communication
- **Frontend**: Vanilla JavaScript with Socket.IO client
- **Data Collection**: Playwright browser automation
- **File Management**: Python pathlib with security checks
- **Update Interval**: 30 seconds (configurable in code)

### Port Configuration
- Default port: 8282
- Change in `eg4_web_monitor.py` if needed

### Data Flow
1. Backend verifies and saves credentials
2. Automatically starts monitoring when credentials are valid
3. Connects to EG4 cloud using Playwright (headless Chrome)
4. Extracts data every 30 seconds
5. Checks configured alerts
6. Sends updates to all connected clients via WebSocket
7. Frontend updates display in real-time

### File Editor Security
- Path traversal protection (no `..` or absolute paths)
- Limited to specific file extensions
- Files must be in application directory or config subdirectory
- Automatic .env reload when saved

### Alert Logic

#### Battery SOC
- Checks once per day at configured time
- Compares current SOC with minimum threshold
- Prevents duplicate alerts on same day

#### Peak Demand
- Active only during configured time window
- Tracks violations in sliding window
- Alerts only for consecutive violations
- Resets after alert to prevent spam

#### Cloud Connectivity
- Counts consecutive connection failures
- Alerts after 3 failures
- Resets counter on successful connection

## Troubleshooting

### Web Interface Not Loading
- Check if port 8282 is available
- Verify Flask is installed: `pip install flask flask-socketio`
- Check console for error messages
- Try `lsof -i :8282` to see if port is in use

### No Data Showing
- Verify credentials in Configuration tab
- Monitoring starts automatically when credentials are verified
- Look for connection status indicator (green = connected)
- Check browser console for errors
- Check server logs: `tail -f web_monitor.log`

### Credential Verification Issues
- Ensure username and password are correct
- Check internet connection to EG4 cloud
- Try saving credentials even if verification fails
- Check for quotes in .env file (should not have quotes)

### File Editor Issues
- Ensure file has proper permissions
- Check that file extension is allowed
- Verify file is in application directory
- Look for save confirmation message

### Alerts Not Working
- Ensure monitoring is active (check status indicator)
- Verify alert configuration is saved
- Check browser allows notifications
- Monitor browser console for alert events
- Verify time settings match your timezone

### High CPU Usage
- Normal during initial page load
- Consider increasing update interval in code
- Ensure headless mode is enabled (default)
- Check for browser memory leaks after long runtime

## Customization

### Change Update Interval
In `eg4_web_monitor.py`, modify:
```python
await asyncio.sleep(30)  # Change 30 to desired seconds
```

### Add Custom Alerts
1. Add configuration in `alert_config` dictionary
2. Implement check logic in `check_alerts()` function
3. Add UI controls in `index.html`

### Add New File Types
In `eg4_web_monitor.py`, modify:
```python
ALLOWED_EXTENSIONS = ['.env', '.yaml', '.yml', '.json', '.txt', '.conf', '.ini', '.yourext']
```

### Modify UI Theme
Edit styles in `templates/index.html` `<style>` section

### Change Editor Settings
Modify the `.editor-textarea` CSS class for font, size, colors

## Security Notes

- Credentials stored locally in .env file
- No quotes needed in .env file (automatically stripped)
- WebSocket runs on same host (no external access by default)
- File editor has path traversal protection
- Use reverse proxy with SSL for internet access
- Consider firewall rules for port 8282
- Regular backups recommended for configuration files

## Browser Compatibility

- Chrome/Chromium: Fully supported
- Firefox: Fully supported
- Safari: Fully supported
- Edge: Fully supported
- Mobile browsers: Responsive design included

## Known Limitations

- File editor limited to text files
- No syntax highlighting in editor
- Single user interface (no multi-user support)
- Requires persistent browser connection for alerts
- Maximum file size limited by browser memory