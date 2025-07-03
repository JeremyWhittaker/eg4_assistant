# EG4-SRP Monitor - Claude Development Guide

## Project Overview

This is a monitoring application for EG4 solar inverters and SRP (Salt River Project) peak demand tracking. It uses web scraping to collect data and provides real-time monitoring with email alerts.

**Latest Update:** The application is fully functional with automatic retry logic, proper error handling, and runs on port 8085 by default.

## Key Components

### Main Application (app.py)
- Flask web server with Socket.IO for real-time updates
- Two monitor classes: `EG4Monitor` and `SRPMonitor` 
- Background thread runs continuous monitoring loop
- Email alert system with configurable thresholds

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
- Alert configuration stored in memory (not persisted)
- Configuration is lost on container restart
- Could be enhanced to use SQLite or JSON file for persistence

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

### Changing Default Port
1. Edit `docker-compose.yml` ports section
2. Change from `"8085:5000"` to `"YOUR_PORT:5000"`
3. Restart container with `docker compose down && docker compose up -d`

## Security Considerations
- Credentials stored as environment variables
- No database - all state is in-memory
- WebSocket has no authentication (localhost only recommended)
- Configuration not persisted between restarts
- Consider adding API key for production use
- SMTP passwords masked in web interface but stored in plain text in memory

## Current Implementation Status

### Working Features
- EG4 inverter data collection with all advertised metrics
- SRP peak demand monitoring
- Real-time WebSocket updates
- Email alerts with configurable thresholds
- Automatic retry and recovery logic
- Battery and grid voltage display
- Docker containerization

### Known Limitations
- No data persistence between restarts
- No authentication for API or WebSocket
- Single inverter support only
- No historical data storage
- No data export functionality

## Future Enhancements
- Add historical data storage (SQLite/PostgreSQL)
- Implement data export functionality (CSV/JSON)
- Add support for multiple inverters
- Create mobile app with push notifications
- Add Grafana integration for visualization
- Implement API authentication
- Add configuration persistence