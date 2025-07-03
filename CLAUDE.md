# EG4-SRP Monitor - Claude Development Guide

## Project Overview

This is a monitoring application for EG4 solar inverters and SRP (Salt River Project) peak demand tracking. It uses web scraping to collect data and provides real-time monitoring with email alerts.

**Latest Update (July 2025):** The application is fully functional with:
- Automatic retry logic and error recovery
- Gmail integration for email alerts (no SMTP configuration needed)
- Port 8085 by default
- Battery and grid voltage monitoring added
- Time-based grid import alerts (only during configured hours)
- Battery high alert removed (unnecessary)
- Configuration persistence to disk (survives container restarts)
- Time-based battery checks (once daily at configured time)
- Peak demand checks once daily at 6 AM
- All features tested and working in production

## Key Components

### Main Application (app.py)
- Flask web server with Socket.IO for real-time updates
- Two monitor classes: `EG4Monitor` and `SRPMonitor` 
- Background thread runs continuous monitoring loop
- Email alert system using gmail-send integration
- Simplified email configuration (recipients only, no SMTP settings)

### Web Interface (templates/index.html)
- Single-page application with real-time WebSocket updates
- Dark theme dashboard showing inverter and utility data
- Configuration interface for alert thresholds and email settings

### Docker Setup
- Dockerfile installs Playwright and Chrome dependencies
- docker-compose.yml configures the service with health checks
- Requires environment variables for EG4 and SRP credentials
- Default port mapping: 8085:5000 (external:internal)
- 2GB shared memory allocation for browser stability

## Development Commands

### Running Tests
```bash
# Install development dependencies first
pip install -r requirements-dev.txt

# Run tests
pytest
pytest --cov=app  # With coverage
```

### Linting and Type Checking
```bash
# Development tools are in requirements-dev.txt
black app.py       # Format code
pylint app.py      # Lint code  
mypy app.py        # Type checking
flake8 app.py      # Style guide enforcement
```

### Building and Running
```bash
# Build Docker image
docker compose build

# Start container
docker compose up -d

# View logs
docker compose logs -f eg4-srp-monitor

# Stop container
docker compose down
```

## Gmail Integration

### Prerequisites
- gmail-send must be installed on the HOST system: `pip install gmail-send`
- Run `gmail-auth-setup` on the HOST to configure Gmail credentials
- The container accesses the host's gmail-send via subprocess

### Setup Process
1. Run `./setup-gmail.sh` to copy gmail_integration for Docker build
2. The Dockerfile will automatically include and install the integration
3. Gmail credentials are managed by the gmail-send tool on the host, not in the container

### How It Works
- Uses `send-gmail` command via subprocess
- Sends HTML-formatted emails with system status
- Supports multiple recipients (comma-separated)
- No SMTP configuration needed in the app
- Requires gmail-send to be installed on host system

### Email Alert Configuration
- Only requires recipient email addresses
- Gmail sender credentials managed externally on host
- Test email button to verify setup
- Web interface shows Gmail configuration status
- Detailed error messages guide setup process

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
  - Added helpful notes about UTC time and alert behavior
- Improved alert messages to include time window information
- Added configuration persistence:
  - Settings saved to `./config/config.json`
  - Automatically loaded on container restart
  - Includes email settings and all alert thresholds
- Enhanced alert logic:
  - Battery SOC checked once daily at configured time
  - Peak demand checked once daily at 6 AM
  - Grid import checked continuously but only alerts during configured hours
  - Prevents duplicate alerts with cooldown periods
- Gmail integration improvements:
  - Added configuration status check endpoint
  - Web UI shows Gmail configuration status
  - Better error messages with setup instructions
  - Detects if gmail-send is not installed or configured

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

## Current Implementation Status

### Working Features ✅
- EG4 inverter data collection with all metrics (SOC, power, voltage)
- SRP peak demand monitoring (updates every 5 minutes)
- Real-time WebSocket updates to web dashboard
- Email alerts via gmail-send integration
- Configurable alert thresholds:
  - Battery low warnings (checked at specified time daily)
  - Peak demand alerts (checked at 6 AM daily)
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
- `app.py` (457 lines) - Main Flask application
- `templates/index.html` (391 lines) - Web dashboard UI
- `requirements.txt` (8 lines) - Python dependencies
- `requirements-dev.txt` (8 lines) - Development dependencies

### Docker Configuration
- `Dockerfile` (59 lines) - Container image definition
- `docker-compose.yml` (20 lines) - Service orchestration
- `setup-gmail.sh` (23 lines) - Gmail integration setup script

### Configuration Files
- `.env` - Environment variables (gitignored)
- `.env.example` (15 lines) - Template for credentials
- `.gitignore` (7 lines) - Git exclusions

### Documentation
- `README.md` - User documentation
- `CLAUDE.md` - This development guide
- `FILE_STRUCTURE.md` - Detailed file documentation

### Runtime Directories
- `logs/` - Container log volume mount
- `gmail_integration_temp/` - Temporary build directory (gitignored)

## Future Enhancements
- Add historical data storage (SQLite/PostgreSQL)
- Implement data export functionality (CSV/JSON)
- Add support for multiple inverters
- Create mobile app with push notifications
- Add Grafana integration for visualization
- Implement API authentication
- Add configuration persistence
- Add timezone configuration option