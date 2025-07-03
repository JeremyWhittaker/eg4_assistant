# EG4-SRP Monitor File Structure Documentation

This document provides a detailed explanation of each file in the project directory.

## Root Directory Files

### `app.py` (406 lines)
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
- Email alert system with configurable thresholds
- RESTful API endpoints for configuration and status

### `docker-compose.yml` (21 lines)
Docker Compose configuration for container orchestration.

**Features:**
- Port mapping: 8085:5000 (external:internal)
- Environment variable injection from .env file
- Volume mounts for logs and .env file
- Health check configuration
- 2GB shared memory for Playwright browser operations
- Automatic restart policy

### `Dockerfile` (54 lines)
Container image definition for the application.

**Build Steps:**
1. Base image: Python 3.9-slim
2. Installs system dependencies for Playwright/Chromium
3. Installs Python dependencies
4. Installs Chromium browser for web scraping
5. Copies application files
6. Exposes port 5000

### `requirements.txt` (6 lines)
Python package dependencies:
- `Flask==2.3.2` - Web framework
- `Flask-SocketIO==5.3.4` - WebSocket support
- `playwright==1.37.0` - Browser automation
- `python-dotenv==1.0.0` - Environment variable management
- `email-validator==2.0.0` - Email validation
- `python-engineio==4.5.1` - Socket.IO engine

### `requirements-dev.txt` (8 lines)
Development dependencies for testing and code quality:
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Code coverage
- `black>=23.0.0` - Code formatting
- `pylint>=2.17.0` - Code linting
- `mypy>=1.0.0` - Type checking
- `flake8>=6.0.0` - Style guide enforcement

### `.env` (5 lines)
Environment configuration file containing credentials:
- `EG4_USERNAME` - EG4 portal username
- `EG4_PASSWORD` - EG4 portal password
- `SRP_USERNAME` - SRP account username
- `SRP_PASSWORD` - SRP account password

**Note:** This file is gitignored for security.

### `.env.example` (15 lines)
Template for environment variables with placeholders.
Shows required credentials and optional email configuration.

### `.gitignore` (6 lines)
Specifies files to exclude from version control:
- `.env` - Credentials file
- `*.pyc` - Compiled Python files
- `__pycache__/` - Python cache directory
- `logs/` - Log directory
- `*.log` - Log files
- `.DS_Store` - macOS metadata

### `README.md` (220+ lines)
Main project documentation including:
- Project overview and features
- Quick start guide
- Configuration instructions
- API documentation
- Development guidelines
- Security notes
- Troubleshooting

### `CLAUDE.md` (130+ lines)
AI development guide containing:
- Project patterns and conventions
- Development commands
- Common tasks and workflows
- Implementation status
- Known limitations
- Future enhancements

### `FILE_STRUCTURE.md` (This file)
Detailed documentation of all project files and their purposes.

## Subdirectories

### `templates/` Directory
Contains HTML templates for the web interface.

#### `templates/index.html` (389 lines)
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
   - Grid import/export
   - Load consumption
2. SRP Peak Demand card
   - Current peak display
   - Last update timestamp
3. Alert Configuration section
   - Email settings
   - Threshold configuration
   - Save/test functionality

### `logs/` Directory (Created at runtime)
Volume mount point for application logs.
- Contains `eg4_srp_monitor.log` when running

## Data Flow

1. **Startup**: Docker container starts → Flask app initializes → Monitoring thread launches
2. **Data Collection**: Playwright browsers → Login to portals → Scrape data → Parse values
3. **Distribution**: Backend collects data → Socket.IO broadcast → Web clients update
4. **Persistence**: Environment variables (credentials) persist, configuration is in-memory only
5. **Alerts**: Threshold checks → Email notifications → Web UI alerts

## Port Configuration

- Internal Flask app: Port 5000
- External access: Port 8085 (configurable in docker-compose.yml)
- WebSocket: Same port as HTTP (8085)

## Security Considerations

- Credentials stored in `.env` file (gitignored)
- No authentication on web interface (localhost recommended)
- SMTP passwords masked in API responses
- Container runs with limited privileges
- Single-process mode for container stability