# CLAUDE.md - Development Guide for EG4-SRP Monitor

## Project Overview
EG4-SRP Monitor is a comprehensive real-time monitoring system for EG4 inverters with Salt River Project (SRP) utility integration. Built with Flask, Socket.IO, and Playwright for reliable web automation.

**Latest Update (July 2025):** Complete rewrite with enhanced features:
- **Multi-MPPT PV Monitoring**: Individual string tracking with automatic totaling
- **Complete SRP Integration**: All 4 chart types (Net Energy, Generation, Usage, Demand)
- **Smart Alert Protection**: Prevents false alerts when systems are offline  
- **Enhanced Error Recovery**: Robust connection validation and retry logic
- **Real-time Dashboard**: Live WebSocket updates with detailed system status
- **Comprehensive Documentation**: Full user and developer guides

## Architecture

### Core Components
1. **Flask Application** (`app.py`) - Main server with 1,400+ lines
2. **Web Interface** (`templates/index.html`) - Real-time dashboard with 700+ lines
3. **Docker Environment** - Containerized deployment with volume persistence
4. **Playwright Automation** - Headless browser for EG4 and SRP data extraction

### Key Technologies
- **Backend**: Flask + Socket.IO for real-time WebSocket communication
- **Automation**: Playwright for reliable web scraping with retry logic
- **Containerization**: Docker with health checks and auto-restart
- **Data Processing**: CSV parsing for SRP energy usage analytics
- **Alerting**: Gmail integration using gmail-send package

## Development Setup

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run locally
python app.py
```

### Docker Development
```bash
# Build and run
docker-compose up -d

# View logs
docker logs eg4-srp-monitor -f

# Rebuild after changes
docker-compose build
```

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

## File Structure & Responsibilities

```
eg4-srp-monitor/
├── app.py                 # Main Flask application
│   ├── Data extraction functions (EG4/SRP)
│   ├── Alert logic and email integration
│   ├── API endpoints for configuration
│   ├── WebSocket handlers for real-time updates
│   └── Background monitoring threads
│
├── templates/index.html   # Web dashboard
│   ├── Real-time data display with Socket.IO
│   ├── Interactive SRP charts with Chart.js
│   ├── Configuration forms and validation
│   └── PV string breakdown display
│
├── docker-compose.yml     # Container orchestration
├── Dockerfile            # Container build instructions
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (credentials)
└── README.md             # User documentation
```

## Common Development Tasks

### Adding New Alerts
1. **Define threshold** in `alert_config['thresholds']`
2. **Add check logic** in `check_alerts()` function
3. **Update configuration form** in `index.html`
4. **Test with test email** endpoint

### Modifying Data Extraction
1. **EG4 changes**: Update `extract_eg4_data()` JavaScript execution
2. **SRP changes**: Modify `fetch_srp_chart_data()` or `fetch_srp_peak_demand()`
3. **Test thoroughly** with real accounts in development
4. **Add error handling** for new failure modes

### Updating Web Interface
1. **Real-time updates**: Modify Socket.IO emit in monitoring thread
2. **Static elements**: Update `index.html` template
3. **Charts**: Modify Chart.js configuration in JavaScript section
4. **Styling**: Update CSS in `<style>` section

## Important Patterns

### Data Collection
- Uses Playwright for browser automation
- Logs into EG4 and SRP websites
- Scrapes data using CSS selectors
- Handles login failures with 3 retry attempts
- Automatic reconnection with exponential backoff
- Maximum 5 connection retries before giving up
- EG4 updates every 60 seconds
- SRP updates every 5 minutes (at :00, :05, :10, etc.)

### Real-time Updates
- Socket.IO broadcasts updates to all connected clients
- Separate events for EG4 and SRP data
- Alert events sent when thresholds exceeded
- No authentication on WebSocket connections

### Configuration Storage
- Alert configuration persisted to disk in ./config/config.json
- Settings survive container restarts
- Email recipients and all thresholds are saved
- Alert state tracking prevents duplicate notifications

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
- Docker containerization with health checks
- HTML formatted alert emails with full system status
- Multiple email recipient support (comma-separated)

### Known Limitations ⚠️
- No historical data persistence between restarts (only configuration is saved)
- No authentication for API or WebSocket
- Single inverter support only
- No historical data storage
- No data export functionality

### Production Ready ✅
The application has been thoroughly tested and is running in production:
- Container stable with automatic restarts
- Email alerts confirmed working
- All monitoring features operational
- GitHub repository maintained at: JeremyWhittaker/eg4_assistant (branch: eg4-srp-monitor)

## Complete File Inventory

### Core Application Files
- `app.py` (952 lines) - Main Flask application with monitoring, logging, and timezone support
- `templates/index.html` (972 lines) - Web dashboard UI with auto-refresh and logs viewer
- `srp_csv_downloader.py` (142 lines) - Standalone script for SRP CSV export
- `requirements.txt` (8 lines) - Python dependencies including pytz
- `requirements-dev.txt` (7 lines) - Development dependencies

### Docker Configuration
- `Dockerfile` (61 lines) - Container image with tzdata support
- `docker-compose.yml` (33 lines) - Service orchestration with volume mounts
- `setup-gmail.sh` (23 lines) - Gmail integration setup script
- `update_timezone.sh` (19 lines) - Helper script for timezone updates

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