# EG4-SRP Monitor File Structure Documentation

This document provides a detailed explanation of each file in the project directory.

## Root Directory Files

### `app.py` (766 lines)
The main application file containing the Flask web server and monitoring logic.

**Key Components:**
- Flask application setup with Socket.IO for real-time WebSocket communication
- `EG4Monitor` class: Handles EG4 inverter data collection via web scraping
  - Uses Playwright to automate browser interactions
  - Logs into EG4 monitoring portal
  - Extracts battery SOC, power, voltage, PV generation, grid status, and load data
- `SRPMonitor` class: Collects Salt River Project peak demand data
  - Similar browser automation approach
  - Updates every 5 minutes during peak hours
- Background monitoring thread with automatic retry logic
- Email alert system using gmail-send integration (subprocess calls)
- RESTful API endpoints for configuration and status
- Alert thresholds:
  - Battery low warning with configurable check time
  - SRP peak demand alerts with configurable check time
  - Time-based grid import alerts (only during configured hours)
- Web-based Gmail configuration endpoint
- Manual refresh endpoint for immediate data updates
- Timezone configuration endpoint with container restart

### `docker-compose.yml` (25 lines)
Docker Compose configuration for container orchestration.

**Features:**
- Port mapping: 8085:5000 (external:internal)
- Environment variable injection from .env file
- Volume mounts for logs, .env file, config directory, and timezone data
- Default timezone set to America/Phoenix
- Health check configuration
- 2GB shared memory for Playwright browser operations
- Automatic restart policy

### `Dockerfile` (61 lines)
Container image definition for the application.

**Build Steps:**
1. Base image: Python 3.9-slim
2. Installs system dependencies for Playwright/Chromium and tzdata for timezone support
3. Installs Python dependencies
4. Copies and installs gmail integration
5. Installs Chromium browser for web scraping
6. Copies application files
7. Exposes port 5000

### `requirements.txt` (9 lines)
Python package dependencies:
- `flask==3.0.0` - Web framework
- `flask-socketio==5.3.5` - WebSocket support
- `python-socketio==5.10.0` - Socket.IO implementation
- `python-dotenv==1.0.0` - Environment variable management
- `playwright==1.40.0` - Browser automation
- `email-validator==2.1.0` - Email validation
- `pytz==2023.3` - Timezone handling
- Comment about gmail-integration installation from local path

### `requirements-dev.txt` (8 lines)
Development dependencies for testing and code quality:
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Code coverage
- `black>=23.0.0` - Code formatting
- `pylint>=2.17.0` - Code linting
- `mypy>=1.0.0` - Type checking
- `flake8>=6.0.0` - Style guide enforcement

### `.env` (4 lines)
Environment configuration file containing credentials:
- `EG4_USERNAME` - EG4 portal username
- `EG4_PASSWORD` - EG4 portal password
- `SRP_USERNAME` - SRP account username
- `SRP_PASSWORD` - SRP account password

**Note:** This file is gitignored for security.

### `.env.example` (15 lines)
Template for environment variables with placeholders.
Shows required credentials and optional email configuration.

### `.gitignore` (8 lines)
Specifies files to exclude from version control:
- `.env` - Credentials file
- `*.pyc` - Compiled Python files
- `__pycache__/` - Python cache directory
- `logs/` - Log directory
- `*.log` - Log files
- `.DS_Store` - macOS metadata
- `gmail_integration_temp/` - Temporary build directory
- `config/` - Configuration directory

### `README.md` (409 lines)
Main project documentation including:
- Project overview and features
- Quick start guide
- Configuration instructions
- API documentation
- Development guidelines
- Security notes
- Troubleshooting

### `CLAUDE.md` (318 lines)
AI development guide containing:
- Project patterns and conventions
- Development commands
- Common tasks and workflows
- Implementation status
- Known limitations
- Future enhancements

### `FILE_STRUCTURE.md` (This file - 240 lines)
Detailed documentation of all project files and their purposes.

### `setup-gmail.sh` (23 lines, Executable script)
Setup script for Gmail integration:
- Checks for gmail_integration directory in ../gmail_integration
- Validates .env file exists with Gmail credentials
- Copies gmail_integration to temporary location for Docker build
- Ensures gmail-send is available in container
- Must be run before `docker compose build`

### `update_timezone.sh` (20 lines, Executable script)
Helper script for updating container timezone:
- Takes timezone as command line argument
- Updates docker-compose.yml with new timezone
- Restarts container to apply changes
- Example usage: `./update_timezone.sh America/Phoenix`
- Note: Timezone can also be changed through web interface

## Subdirectories

### `templates/` Directory
Contains HTML templates for the web interface.

#### `templates/index.html` (762 lines)
Single-page web dashboard application.

**Features:**
- Dark theme optimized for monitoring
- Real-time data display via WebSocket
- Responsive grid layout
- Configuration interface for alerts
- JavaScript Socket.IO client
- Dynamic status indicators
- Alert threshold configuration
- Email settings management

**Key Sections:**
1. EG4 Inverter Status card
   - Battery SOC, power, voltage
   - PV generation
   - Grid import/export with voltage
   - Load consumption
   - Battery and grid voltage displays
   - Manual refresh button
   - Last update timestamp
2. SRP Peak Demand card
   - Current peak display
   - Last update timestamp
3. Alert Configuration section
   - Email recipients with Gmail status indicator
   - Battery alerts section with threshold and check time
   - Peak demand alerts with threshold and configurable check time
   - Grid import alerts with threshold and time window
   - Gmail configuration modal for web-based setup
   - Save/test functionality with error handling
   - Timezone selector with 6 US timezones (Phoenix default)
   - Live current time display

### `logs/` Directory (Created at runtime)
Volume mount point for application logs.
- Contains `eg4_srp_monitor.log` when running

### `config/` Directory (Created at runtime)
Volume mount point for persistent configuration.
- Contains `config.json` with email and alert settings
- Automatically created on first save
- Survives container restarts

## Data Flow

1. **Startup**: Docker container starts → Flask app initializes → Monitoring thread launches
2. **Data Collection**: Playwright browsers → Login to portals → Scrape data → Parse values
3. **Distribution**: Backend collects data → Socket.IO broadcast → Web clients update
4. **Persistence**: Environment variables (credentials) persist, configuration saved to disk
5. **Alerts**: Threshold checks → Email notifications → Web UI alerts

## Port Configuration

- Internal Flask app: Port 5000
- External access: Port 8085 (configurable in docker-compose.yml)
- WebSocket: Same port as HTTP (8085)

## Security Considerations

- Credentials stored in `.env` file (gitignored)
- No authentication on web interface (localhost recommended)
- Gmail credentials managed externally by gmail-send
- Container runs with limited privileges
- Single-process mode for container stability

## Alert System Details

### Current Alert Types
1. **Battery Low** - Checked once daily at configured time
   - Default check time: 6:00 AM UTC
   - Triggers when SOC drops below threshold (default: 20%)
   - Configurable check hour and minute
2. **Peak Demand** - Checked once daily at configured time
   - Default check time: 6:00 AM UTC (configurable)
   - Triggers when SRP demand exceeds threshold (default: 5.0 kW)
   - Only checks/alerts once per day to avoid spam
3. **Grid Import** - Continuously monitored during operation
   - Time-based: Only alerts during configured hours
   - Default window: 14:00-20:00 UTC (2 PM - 8 PM)
   - Threshold: 10,000W default
   - 15-minute cooldown between alerts

### Alert State Tracking
- Battery and peak demand checks tracked by date
- Grid import alerts tracked by timestamp
- State persisted in config.json to survive restarts

### Removed Features
- Battery high alerts (removed as unnecessary)

## Time Zone Handling
- Container defaults to America/Phoenix timezone
- Timezone is configurable through web interface
- Available timezones: UTC, Phoenix, Los Angeles, Denver, Chicago, New York
- Changing timezone restarts container to apply system-wide
- All alert times are displayed in selected timezone
- Use `docker compose exec eg4-srp-monitor date` to check container time