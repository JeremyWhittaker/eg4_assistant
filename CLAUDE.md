# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# EG4-SRP Monitor Development Guide

## Project Overview
EG4-SRP Monitor is a comprehensive real-time monitoring system for EG4 inverters with Salt River Project (SRP) utility integration. Built with Flask, Socket.IO, and Playwright for reliable web automation.

**Latest Update (July 25, 2025):** Native Python deployment with enhanced features:
- **Docker Migration Complete**: Removed all Docker components, native Python virtual environment
- **Web-based Credential Management**: Complete credential setup through Configuration tab
- **Multi-MPPT PV Monitoring**: Individual string tracking with automatic totaling
- **Complete SRP Integration**: All 4 chart types (Net Energy, Generation, Usage, Demand)
- **Smart Alert Protection**: Prevents false alerts when systems are offline  
- **Enhanced Error Recovery**: Robust connection validation and retry logic
- **Real-time Dashboard**: Live WebSocket updates with detailed system status
- **Comprehensive Logging**: 5-level logging system with web interface

## Architecture Overview

This is a **monolithic Flask application** with real-time web scraping and WebSocket communication running on port 5001.

### Core Components
- **`app.py` (1,496 lines)**: Main Flask server containing all business logic
  - EG4/SRP data extraction using Playwright browser automation
  - Socket.IO WebSocket handlers for real-time updates  
  - Background monitoring threads with retry logic
  - Gmail alert system with smart scheduling
  - API endpoints for configuration management

- **`templates/index.html` (1,479 lines)**: Single-page web dashboard
  - Real-time updates via Socket.IO client
  - Chart.js visualizations for SRP energy data
  - Configuration forms and system status display
  - Dark theme responsive design

### Key Architectural Patterns
- **Browser Automation**: Playwright handles EG4/SRP login and data scraping
- **Real-time Communication**: Socket.IO broadcasts live data updates to web clients
- **Background Processing**: Separate threads for EG4 (60s) and SRP (daily) monitoring
- **Configuration Persistence**: JSON config stored in `./config/config.json`
- **Session Management**: EG4 browser sessions persist for ~1 hour to reduce login overhead

## Essential Commands

### Development Workflow
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ./gmail_integration_temp
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Start the application
python app.py
```

### Testing & Debugging
```bash
# View application logs
tail -f logs/eg4_srp_monitor.log

# Access web interface
curl http://localhost:5000/api/status

# Stop the application
Ctrl+C
```

### No Build/Lint/Test Commands
This is a simple Python Flask application - changes are reflected immediately when you restart the app.

## Key Features & Implementation

### 1. Multi-MPPT PV Monitoring
**Location**: `app.py:extract_eg4_data()` function
**Enhancement**: Individual PV string tracking with automatic totaling

```javascript
// Enhanced PV extraction (in extract_eg4_data)
const pv1Power = parseInt(cleanText(rawPv1Power)) || 0;
const pv2Power = parseInt(cleanText(rawPv2Power)) || 0;
const pv3Power = parseInt(cleanText(rawPv3Power)) || 0;
const totalPvPower = pv1Power + pv2Power + pv3Power;

return {
    pv_power: totalPvPower,
    pv1_power: pv1Power,
    pv1_voltage: parseFloat(cleanText(rawPv1Voltage)) || 0,
    // ... similar for PV2, PV3
};
```

### 2. Connection Validation System
**Location**: `app.py:is_valid_eg4_data()` function
**Purpose**: Prevents false alerts when EG4 system is offline

```python
def is_valid_eg4_data(data):
    """Validate that EG4 data represents a real connection"""
    if not data:
        return False
    
    # Check for all-zero condition (system offline)
    critical_values = [
        data.get('battery_soc', 0),
        data.get('battery_power', 0),
        data.get('pv_power', 0),
        data.get('grid_power', 0)
    ]
    
    # If all critical values are zero, system is likely offline
    return any(abs(value) > 0.1 for value in critical_values)
```

### 3. SRP Chart Data Processing
**Location**: `app.py:fetch_srp_chart_data()` function
**Enhancement**: Support for all 4 SRP chart types with different CSV structures

```python
# Chart type specific column mapping
if chart_type == 'generation':
    # Generation CSV: Off-peak kWh + On-peak kWh columns
    off_peak = float(row.get('Off-peak kWh', 0) or 0)
    on_peak = float(row.get('On-peak kWh', 0) or 0)
    
elif chart_type == 'demand':
    # Demand CSV: On-peak kW column for peak demand
    demand_value = float(row.get('On-peak kW', 0) or 0)
```

### 4. Smart Alert System
**Location**: `app.py:check_alerts()` function
**Features**: Time-based scheduling, anti-spam, connection-aware

```python
def should_send_alert(alert_type, current_time):
    """Determine if alert should be sent based on timing and cooldowns"""
    last_sent = last_alerts.get(alert_type)
    
    if alert_type == 'battery':
        # Daily check at configured hour
        target_hour = alert_config['thresholds']['battery_check_hour']
        return (current_time.hour == target_hour and 
                current_time.minute < 5 and
                (not last_sent or last_sent.date() < current_time.date()))
```

## Critical File Locations

### Core Application
- `app.py`: Main Flask server - all Python logic lives here
- `templates/index.html`: Complete web interface - HTML, CSS, JavaScript in one file

### Key Functions in app.py
- `extract_eg4_data()` (~line 400): Playwright script for EG4 data scraping  
- `fetch_srp_chart_data()` (~line 800): SRP CSV processing and chart data
- `check_alerts()` (~line 1200): Alert logic with timezone-aware scheduling
- `monitor_eg4()` (~line 1400): Background thread for EG4 monitoring
- `is_valid_eg4_data()` (~line 300): Connection validation to prevent false alerts

### Configuration & Data
- `.env`: EG4_USERNAME, EG4_PASSWORD, SRP_USERNAME, SRP_PASSWORD
- `config/config.json`: Persistent alert settings, email recipients, thresholds
- `downloads/`: SRP CSV files (YYYYMMDD_HHMMSS format)
- `logs/eg4_srp_monitor.log`: Application logs accessible via web interface

## Development Guidelines

### Using AI Agents
When working on this project, always check for available local and global AI agents that can assist with specific tasks. Use the appropriate specialized agents for:
- **Testing and validation**: Look for agents that can test web interfaces, validate functionality, or check system health
- **Code organization**: Utilize agents that help with file cleanup, documentation updates, or project structure improvements
- **Data and storage**: Employ agents that can advise on data persistence, storage optimization, or database design
- **UX and design**: Use agents that can review and improve user interface design and user experience
- **Monitoring and troubleshooting**: Deploy agents that can analyze logs, diagnose issues, or monitor system health

Always invoke relevant agents proactively when their capabilities match the task at hand. This ensures thorough analysis, better code quality, and comprehensive testing.

### Data Extraction Changes
- **EG4 modifications**: Update JavaScript in `extract_eg4_data()` function - uses CSS selectors
- **SRP modifications**: Update CSV parsing in `fetch_srp_chart_data()` - handles different column structures
- **Always test with real credentials** in development environment
- **Add robust error handling** - connection failures are common

### Adding New Features
1. **Backend changes**: All logic goes in `app.py` 
2. **Frontend changes**: Update `templates/index.html` (single file contains HTML/CSS/JS)
3. **Real-time updates**: Use `socketio.emit()` to broadcast changes to web clients
4. **Configuration**: Add settings to `alert_config` dict and persist to `config.json`

## Critical Patterns & Data Flow

### Monitoring Loop Architecture
- **EG4 Thread**: Continuous 60-second polling with persistent browser sessions
- **SRP Thread**: Daily updates at configured time (default 6 AM)
- **Alert Thread**: Runs every 5 minutes, checks thresholds based on timezone
- **WebSocket Broadcasting**: Live data pushed to all connected web clients

### Session Management
- EG4 browser sessions persist ~1 hour to reduce login overhead
- Login retry logic: 3 attempts with exponential backoff
- Connection validation prevents false alerts when systems offline

### Alert Logic
- **Time-based scheduling**: Battery/peak demand checked daily at specific hours
- **Grid import alerts**: Only during configured time windows (e.g., 2 PM - 8 PM)
- **Anti-spam protection**: Cooldown periods prevent duplicate notifications
- **HTML email formatting**: Rich emails with full system status

## Common Tasks

### Adding New Metrics
1. Update data extraction in monitor class `get_data()` method
2. Add metric to web interface display (both HTML and JavaScript)
3. Update alert threshold logic if needed
4. Example: Battery and grid voltage were added in latest update

### Debugging Data Collection
1. Check logs in `/tmp/eg4_srp_monitor.log` inside container
2. View logs with `docker compose logs -f eg4-srp-monitor`
3. Run Playwright in headed mode by setting `headless=False`
4. Add debug logging around CSS selectors
5. Monitor retry attempts in logs for connection issues
6. Access container logs: `docker compose exec eg4-srp-monitor cat /tmp/eg4_srp_monitor.log`

### Modifying Alert Logic
1. Update `check_thresholds()` function in app.py
2. Add new threshold fields to configuration interface
3. Update email template with new alert details

### Recent Changes (July 2025)
- Removed battery high alert (unnecessary)
- Added time-based grid import alerts
  - Only triggers during configured hours
  - Uses container timezone (typically UTC)
  - Default: 14:00-20:00 (2 PM - 8 PM UTC)
  - Configure start/end hours in web interface
- Updated web interface:
  - Removed battery high threshold field
  - Added grid import time window configuration
  - Added battery check time configuration (hour:minute)
  - Added timezone selector with 6 US timezones
  - Shows current time in selected timezone
  - Alert times now display with timezone name
- Improved alert messages to include time window information
- Added configuration persistence:
  - Settings saved to `./config/config.json`
  - Automatically loaded on container restart
  - Includes email settings and all alert thresholds
- Enhanced alert logic:
  - Battery SOC checked once daily at configured time
  - Peak demand checked once daily at configured time (default 6 AM)
  - Grid import checked continuously but only alerts during configured hours
  - Prevents duplicate alerts with cooldown periods
- Gmail integration improvements:
  - Added configuration status check endpoint
  - Web UI shows Gmail configuration status
  - Better error messages with setup instructions
  - Detects if gmail-send is not installed or configured
  - **NEW: Web-based Gmail configuration**
    - Added modal dialog for Gmail setup
    - Users can configure Gmail entirely through the web interface
    - No command line access required
    - Automatic credential file creation
    - Test email sent on successful configuration
- **Timezone Support (July 2025)**:
  - Added timezone selector defaulting to America/Phoenix
  - Supports UTC, Phoenix, Los Angeles, Denver, Chicago, New York
  - All alert checks use selected timezone
  - Container restarts automatically when timezone changes
  - Timezone setting persists across container restarts
  - Added pytz library for proper timezone handling
  - Current time display updates every second
- **Live Code Updates (July 2025)**:
  - Volume mounts for app.py and templates directory
  - Flask development mode with auto-reload
  - No container rebuild needed for code changes
  - FLASK_ENV=development for auto-reload
  - Changes reflect immediately on save
- **Logging System (July 2025)**:
  - Dual output to Docker logs and file
  - Rotating file handler (10MB max, 3 rotations)
  - In-memory buffer for web interface
  - Log viewer with level filtering
  - Download full log functionality
  - Auto-refresh every 5 seconds
- **SRP Improvements (July 2025)**:
  - Daily update only (once at configured time)
  - Shows next update time in UI
  - Manual refresh endpoint for testing
  - CSV export functionality (srp_csv_downloader.py)
- **EG4 Auto-Refresh (July 2025)**:
  - Toggle for auto-refresh on/off
  - Configurable intervals (30s, 60s, 2m, 5m)
  - Default 60 seconds with checkbox checked
  - Manual refresh still available

### Changing Default Port
1. Edit `docker-compose.yml` ports section
2. Change from `"8085:5000"` to `"YOUR_PORT:5000"`
3. Restart container with `docker compose down && docker compose up -d`

## Security Considerations
- Credentials stored as environment variables
- Configuration persisted to disk in JSON format
- WebSocket has no authentication (localhost only recommended)
- Consider adding API key for production use
- Email recipients stored in plain text in config file

## Latest Bug Fixes (July 15, 2025)

### 1. Persistent EG4 Browser Sessions ✅ NEW
- **Problem**: EG4 system logging in every 60 seconds, causing unnecessary overhead
- **Solution**: Implemented session persistence with smart re-login detection
- **Benefits**: 
  - Login frequency reduced from ~1,440/day to ~24/day
  - Faster data collection using page refresh instead of full navigation
  - Automatic session recovery on timeout or errors
- **Implementation**: `is_logged_in()` method, 1-hour session timeout, graceful error handling

### 2. Docker Volume Timestamp Issue ✅ FIXED
- **Problem**: SRP charts showing old data despite new CSV files being downloaded
- **Root Cause**: Docker volumes reset file creation times, causing `os.path.getctime()` to return same time for all files
- **Solution**: Changed to lexicographic max on filenames (which contain YYYYMMDD_HHMMSS timestamps)
- **Result**: Charts now always show the most recent data available
- **Location**: `app.py` line ~1326 in get_srp_chart_data()

### Previous Fixes (July 11, 2025)

### 3. SRP Data Update Issues ✅ FIXED
- **Problem**: Dashboard showing yesterday's data wasn't updating, peak demand stuck at 0
- **Root Cause**: SRP CSV files from July 10th not refreshing daily
- **Solution**: Fixed daily SRP refresh mechanism and CSV download automation
- **Result**: Peak demand now shows correct values, charts include current data

### 4. Timezone Datetime Errors ✅ FIXED  
- **Problem**: "can't subtract offset-naive and offset-aware datetimes"
- **Root Cause**: Mixed timezone-aware and naive datetime objects
- **Solution**: Enhanced timezone handling for consistent datetime awareness
- **Impact**: Eliminated timezone comparison crashes

### 5. False Grid Import Alerts ✅ FIXED
- **Problem**: Receiving alerts when exporting power TO grid instead of importing FROM grid  
- **Solution**: Changed to `grid_power < 0 and abs(grid_power) > threshold`
- **Logic**: Positive = export to grid, Negative = import from grid

### 6. Production Deployment Warnings ✅ FIXED
- **Problem**: Werkzeug development server warnings in production logs
- **Solution**: Set FLASK_ENV=production and suppressed Werkzeug logger warnings
- **Result**: Clean production logs without development warnings

## Current Implementation Status

### Working Features ✅
- EG4 inverter data collection with all metrics (SOC, power, voltage)
- SRP peak demand monitoring (updates every 5 minutes)
- Real-time WebSocket updates to web dashboard
- Email alerts via gmail-send integration
- Configurable alert thresholds:
  - Battery low warnings (checked at specified time daily)
  - Peak demand alerts (checked at configurable time daily)
  - Time-based grid import alerts (with hour configuration)
- Automatic retry logic (3 login attempts, 5 reconnection attempts)
- Battery and grid voltage display in UI
- Native Python virtual environment deployment
- HTML formatted alert emails with full system status
- Multiple email recipient support (comma-separated)
- Web-based credential management (EG4, SRP, Gmail)
- Comprehensive system logs with web interface

### Known Limitations ⚠️
- No historical data persistence between restarts (only configuration is saved)
- No authentication for API or WebSocket
- Single inverter support only
- No historical data storage
- No data export functionality

### Production Ready ✅
The application has been thoroughly tested and is running in production:
- Native Python deployment with virtual environment
- Email alerts confirmed working
- All monitoring features operational
- Web-based credential management functional
- Comprehensive logging system with 5 levels
- GitHub repository maintained at: JeremyWhittaker/eg4_assistant (branch: eg4-srp-monitor)

## Complete File Inventory

### Core Application Files (Active)
- `app.py` (1,496 lines) - Main Flask application with monitoring, logging, and credential management
- `templates/index.html` (1,479 lines) - Web dashboard UI with real-time updates and credential management
- `requirements.txt` (8 lines) - Python dependencies including pytz
- `PROJECT_STRUCTURE.md` - Comprehensive project documentation
- `CLAUDE.md` - This development guide

### Archived Files (Deprecated)
- `archive/deprecated-docs/srp_csv_downloader.py` - Standalone CSV export (integrated into main app)
- `archive/deprecated-docs/requirements-dev.txt` - Development dependencies (no longer needed)
- `archive/deprecated-docs/send-gmail` - Standalone email script (integrated into main app)
- `archive/deprecated-docs/FILE_STRUCTURE.md` - Old Docker-based documentation
- `archive/deprecated-docs/README_GITWATCH.md` - Gitwatch automation docs

### Docker Configuration (Removed in v2.3)
**Note**: All Docker components have been removed and archived. The application now runs natively with Python virtual environment.

### Configuration Files
- `.env` - Environment variables (gitignored)
- `.env.example` (15 lines) - Template for credentials
- `.gitignore` (9 lines) - Git exclusions

### Documentation
- `README.md` (415 lines) - User documentation
- `CLAUDE.md` (342 lines) - This development guide
- `FILE_STRUCTURE.md` (239 lines) - Detailed file documentation

### Runtime Directories
- `logs/` - Container log volume mount
- `config/` - Persistent configuration storage
- `gmail_config/` - Gmail credentials persistence
- `downloads/` - SRP CSV downloads
- `gmail_integration_temp/` - Temporary build directory (gitignored)

## Recent Updates (July 18, 2025)

### Gmail Integration Fix
- **Problem**: Alert emails failing with "send-gmail command not found" error
- **Solution**: Created custom `send-gmail` utility script that:
  - Reads configuration from `~/.gmail_send/.env` file
  - Supports both plain text and HTML email formats (with `--html` flag)
  - Compatible with the app's existing Gmail integration
- **Location**: `/usr/local/bin/send-gmail` in container

### SRP CSV Download Timeout Fix
- **Problem**: SRP CSV downloads failing with "Timeout 30000ms exceeded" at 6:00 AM scheduled downloads
- **Root Cause**: Default Playwright page timeout of 30 seconds was too short for SRP's slow export process
- **Solution**: 
  - Set page default timeout to 120000ms (2 minutes) for both EG4 and SRP monitors
  - Added manual CSV download endpoint `/api/download-srp-csv` for testing
- **Impact**: Daily SRP data downloads should now complete successfully

### New API Endpoints
- `GET /api/download-srp-csv` - Manually trigger SRP CSV downloads
  - Useful for testing or recovering from failed scheduled downloads
  - Returns status of download request

## Future Enhancements
- Add historical data storage (SQLite/PostgreSQL)
- Implement data export functionality (CSV/JSON)
- Add support for multiple inverters
- Create mobile app with push notifications
- Add Grafana integration for visualization
- Implement API authentication
- Add timezone configuration option
- Implement OAuth authentication for enhanced security
- Add support for multiple alert profiles