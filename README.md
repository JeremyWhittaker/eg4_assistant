# EG4-SRP Monitor

A real-time monitoring and alerting system for EG4 inverters and SRP (Salt River Project) peak demand tracking.

## Overview

This application provides automated monitoring of solar energy systems using EG4 inverters and tracks peak demand from SRP utility accounts. It features a web-based dashboard with real-time updates and configurable email alerts.

**Current Status (July 2025):**
- ✅ Running in production at port 8085
- ✅ Email alerts via gmail-send integration
- ✅ All features tested and working
- 📊 Real-time monitoring data example:
  ```
  Battery: 23% SOC | 51.6V | 0W
  Grid: 17,810W import | 238.9V
  Load: 17,810W consumption
  SRP Peak: Updates every 5 minutes
  ```

## System Requirements

- Docker and Docker Compose
- 2GB+ RAM (for Playwright browser automation)
- Network access to EG4 and SRP portals
- Linux/macOS/Windows with Docker support

## Features

### Currently Implemented

- **Real-time EG4 Inverter Monitoring**
  - Battery state of charge (SOC) and power flow
  - Solar PV generation
  - Grid import/export
  - Load consumption
  - Battery voltage monitoring
  - Grid voltage monitoring
  - Manual refresh button (30-second cooldown)
  - Last update timestamp display

- **SRP Peak Demand Tracking**
  - Automated peak demand monitoring
  - Updates every 5 minutes during monitoring
  - Current billing cycle peak display

- **Alert System**
  - Configurable thresholds for all monitored values
  - Email notifications when thresholds are exceeded
  - Real-time alerts in web interface
  - Battery low/high alerts
  - Peak demand alerts
  - Grid import alerts

- **Web Dashboard**
  - Live data updates via WebSocket
  - Dark theme optimized for monitoring
  - Mobile-responsive design
  - Configuration interface for alerts

- **Automatic Recovery**
  - Retry logic for login failures (3 attempts)
  - Connection recovery with exponential backoff
  - Handles data fetch failures gracefully
  - Maximum 5 retry attempts before giving up

### Planned Features

- Historical data storage (database integration)
- Data export functionality (CSV/JSON)
- Support for multiple inverters
- API authentication and multi-user support
- Mobile app with push notifications
- Grafana integration for advanced visualization

## Project Structure

```
eg4-srp-monitor/
├── app.py              # Main Flask application with monitoring logic
├── templates/
│   └── index.html      # Web dashboard interface
├── requirements.txt    # Python dependencies
├── requirements-dev.txt # Development dependencies (testing, linting)
├── Dockerfile         # Container configuration
├── docker-compose.yml # Docker Compose setup
├── .env.example       # Environment variable template
├── .gitignore         # Git ignore rules
├── CLAUDE.md          # Development guide
└── README.md          # This file
```

## Prerequisites

- Docker and Docker Compose
- EG4 monitoring account credentials
- SRP account credentials
- Google account (Gmail or Google Workspace) with App Password for email alerts

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd eg4-srp-monitor
   ```

2. **Create environment file**
   Copy the example and add your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   Required variables:
   ```env
   EG4_USERNAME=your_eg4_username
   EG4_PASSWORD=your_eg4_password
   SRP_USERNAME=your_srp_username
   SRP_PASSWORD=your_srp_password
   ```

3. **Setup Gmail integration and build**
   ```bash
   # Setup gmail integration for Docker
   ./setup-gmail.sh
   
   # Build and run with Docker
   docker compose build
   docker compose up -d
   ```

4. **Access the web interface**
   Open http://localhost:8085 in your browser

   Note: The port is configurable in docker-compose.yml (default: 8085)

## Configuration

### Alert Thresholds

Configure alerts through the web interface:

- **Battery Low**: Alert when battery SOC drops below threshold at specified check time
  - Default threshold: 20%
  - Default check time: 6:00 AM UTC
  - Checked once daily at the configured time
- **Peak Demand**: Alert when SRP peak demand exceeds threshold
  - Default threshold: 5.0 kW
  - Check time is configurable (default: 6:00 AM UTC)
  - Checked once daily at the configured time
- **Grid Import**: Alert when importing more than threshold from grid during specified hours
  - Default threshold: 10,000W
  - Default hours: 14:00-20:00 (2 PM - 8 PM)
  - Only alerts during the configured time window
  - Note: Times are in 24-hour format and use the container's timezone (typically UTC)

**Configuration Persistence**: All email and alert settings are now saved to disk and automatically loaded when the container restarts. Settings are stored in the `./config` directory on the host.

### Time Zone Considerations

The container runs in UTC time by default. When configuring time-based alerts:
- Convert your local time to UTC
- Example: 2 PM PST = 10 PM UTC (22:00)
- Check container time: `docker compose exec eg4-srp-monitor date`

### Email Configuration

Email alerts can be configured directly through the web interface - no command line required!

1. **Access the Web Interface**
   Open http://localhost:8085 in your browser

2. **Check Gmail Status**
   Look for the "Gmail Status" indicator in the Email Settings section:
   - ✗ Not configured (red) - Click "Configure" to set up
   - ✓ Configured (green) - Gmail is ready to send alerts

3. **Configure Gmail (if needed)**
   - Click the "Configure" button next to Gmail Status
   - Enter your email address (Gmail or Google Workspace custom domain)
   - Enter a Google App Password (16 characters)
   
   **To create an App Password:**
   - Go to https://myaccount.google.com/apppasswords
   - Enable 2-Step Verification if not already enabled
   - Generate an App Password for "Mail"
   - Copy the 16-character password (without spaces)

4. **Set Email Recipients**
   - Enable email alerts with the checkbox
   - Add recipient email addresses (comma-separated)
   - Click "Save Configuration"
   - Use "Test Email" button to verify everything works

**Technical Details:**
- Works with both @gmail.com and Google Workspace custom domains
- Credentials are stored securely on the host system
- The container uses the host's gmail-send command via subprocess
- Configuration persists across container restarts
- No need to install anything on the host manually

**Troubleshooting:**
- If configuration fails, check that the app password is correct
- Ensure you're using a Google App Password, not your regular password
- Custom domain users: make sure you have Google Workspace with 2FA enabled
- Check container logs for detailed error messages
- The test email will confirm if everything is working

### Data Collection Intervals

- EG4 data: Updates every 60 seconds
- SRP peak demand: Updates every 5 minutes
- WebSocket updates: Real-time when data changes

## Development

### Run Locally Without Docker

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Gmail integration
pip install -e ../gmail_integration

# Install Playwright browsers
playwright install chromium

# Set environment variables
export EG4_USERNAME=your_username
export EG4_PASSWORD=your_password
export SRP_USERNAME=your_username
export SRP_PASSWORD=your_password

# Run the application
python app.py
```

### Docker Installation with Gmail Integration

Since the gmail-send integration is installed locally, you'll need to either:

1. **Option 1: Install on Host** (Recommended)
   - Install gmail-send on the host system
   - The container will use the host's email sending capability via the command line

2. **Option 2: Build Custom Image**
   - Modify the Dockerfile to include the gmail_integration directory
   - Build a custom image with the integration included

### Dependencies

- **Flask**: Web framework and API
- **Flask-SocketIO**: Real-time WebSocket communication
- **Playwright**: Browser automation for data collection
- **python-dotenv**: Environment variable management
- **email-validator**: Email validation for alerts

## Architecture

### Backend (app.py)

- **Flask Application**: Serves web interface and API endpoints
- **WebSocket Server**: Provides real-time updates to connected clients (no authentication)
- **Monitor Classes**:
  - `EG4Monitor`: Handles EG4 inverter data collection via web scraping
  - `SRPMonitor`: Collects SRP peak demand data
- **Background Thread**: Runs continuous monitoring loop
- **Alert System**: Checks thresholds and sends email notifications

### Frontend (index.html)

- **Single Page Application**: Pure JavaScript with Socket.IO client
- **Real-time Updates**: WebSocket connection for live data
- **Configuration Interface**: Save alert settings without restart
- **Responsive Design**: Works on desktop and mobile devices

### Data Flow

1. Background thread starts monitor instances
2. Monitors login to respective services using Playwright
3. Data is scraped at configured intervals
4. Updates are broadcast via WebSocket to all connected clients
5. Thresholds are checked and alerts sent if needed
6. Web interface updates in real-time

## Troubleshooting

### Container Health Checks

The Docker container includes health checks that verify the API is responding:
```bash
docker compose ps  # Check container status
docker compose logs -f eg4-srp-monitor  # View logs
```

### Common Issues

1. **Login Failures**: 
   - Check credentials in `.env` file
   - Ensure variable names are exact: `EG4_USERNAME` not `EG4_MONITOR_USERNAME`
   - The app will retry login 3 times before failing

2. **No Data Updates**: 
   - Verify network connectivity and site availability
   - Check logs for specific error messages
   - EG4 updates every 60 seconds, SRP every 5 minutes

3. **Email Alerts Not Sending**: 
   - Check "Gmail Status" indicator in web interface
   - If "Not configured", run `gmail-auth-setup` on the host system
   - Ensure gmail-send is installed on host: `pip install gmail-send`
   - Test using the "Test Email" button in the web interface
   - Check container logs for detailed error messages
   - Verify recipient email addresses are valid

4. **High Memory Usage**: 
   - Playwright requires ~2GB RAM (configured in docker-compose.yml)
   - Container runs browsers in single-process mode for stability

5. **Port Conflicts**:
   - Default port is 8085, change in docker-compose.yml if needed
   - Ensure no other service is using the configured port

### Logs

Logs are stored in:
- Container: `/tmp/eg4_srp_monitor.log`
- Host (when using docker-compose): `./logs/`
- View logs: `docker compose exec eg4-srp-monitor cat /tmp/eg4_srp_monitor.log`

## Security Notes

- Credentials are stored in environment variables
- SMTP passwords are masked in the web interface
- WebSocket connections have no authentication (localhost only recommended)
- Container runs with limited privileges
- Configuration is not persisted between restarts (stored in memory only)

## API Endpoints

- `GET /` - Web dashboard interface
- `GET /api/status` - Get current monitoring data
- `GET /api/config` - Get current configuration (passwords masked)
- `POST /api/config` - Update configuration
- `GET /api/test-email` - Send a test email

## Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Running Tests

```bash
pytest
pytest --cov=app  # With coverage
```

### Code Quality

```bash
black app.py       # Format code
pylint app.py      # Lint code
mypy app.py        # Type checking
flake8 app.py      # Style guide enforcement
```

## Project Structure

For detailed information about each file in the project, see [FILE_STRUCTURE.md](FILE_STRUCTURE.md).

### Key Files
- `app.py` - Main application (457 lines)
- `templates/index.html` - Web dashboard (391 lines)
- `setup-gmail.sh` - Gmail integration setup
- `docker-compose.yml` - Container configuration
- `requirements.txt` - Python dependencies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pip install -r requirements-dev.txt && pytest`
5. Submit a pull request

## Repository

This project is maintained at: https://github.com/JeremyWhittaker/eg4_assistant
- Branch: `eg4-srp-monitor`
- Status: Production ready

## License

This project is for personal use. Please ensure you comply with the terms of service for EG4 and SRP when using their monitoring services.