# EG4-SRP Monitor - Project Structure

## Version 2.3 (Native Python Deployment)
**Date**: July 25, 2025  
**Migration**: Complete removal of Docker containerization to native Python virtual environment

## 📁 Active Project Files

### Core Application
```
eg4-srp-monitor/
├── app.py                     # Main Flask application (1,496 lines)
├── templates/
│   └── index.html            # Web interface template (1,479 lines)
├── requirements.txt          # Python dependencies
└── venv/                     # Python virtual environment
```

### Configuration & Data
```
├── config/
│   └── config.json          # Persistent configuration storage
├── gmail_config/            # Gmail authentication credentials
├── logs/
│   └── eg4_srp_monitor.log  # Application logs (rotated at 10MB)
└── downloads/               # SRP CSV data files
    ├── srp_net_*.csv
    ├── srp_generation_*.csv
    ├── srp_usage_*.csv
    └── srp_demand_*.csv
```

### Gmail Integration
```
├── gmail_integration_temp/   # Gmail send functionality
    ├── setup.py
    ├── requirements.txt
    ├── send_email_simple.py
    └── setup_auth.py
```

### Documentation
```
├── README.md                # User documentation and setup guide
└── CLAUDE.md               # Development guide and architecture
```

### Archive
```
└── archive/
    ├── deprecated-docs/     # Old documentation and scripts
    │   ├── FILE_STRUCTURE.md
    │   ├── README_GITWATCH.md
    │   ├── srp_csv_downloader.py
    │   ├── requirements-dev.txt
    │   └── send-gmail
    └── docker-components/   # Future Docker-related files
```

## 🚀 Quick Start Commands

### Initial Setup
```bash
# Clone repository
git clone <repository-url> eg4-srp-monitor
cd eg4-srp-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ./gmail_integration_temp
playwright install chromium
```

### Running the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Start application
python app.py

# Access web interface
# http://localhost:5000
```

### Log Management
```bash
# View real-time logs
tail -f logs/eg4_srp_monitor.log

# View recent errors
grep -i error logs/eg4_srp_monitor.log | tail -20
```

## 📋 File Descriptions

### `app.py` (Main Application)
- **Purpose**: Flask web server with real-time monitoring
- **Features**: 
  - EG4 inverter data collection via Playwright
  - SRP utility data integration
  - Email alerts via Gmail integration
  - WebSocket real-time updates
  - Configuration management API
  - System logging with web interface

### `templates/index.html` (Web Interface)
- **Purpose**: Single-page web application
- **Features**:
  - Real-time dashboard with Socket.IO
  - Interactive SRP usage charts (Chart.js)
  - Credential management interface
  - Alert configuration forms
  - System logs viewer with filtering

### `requirements.txt` (Dependencies)
- **Core**: Flask, Socket.IO, Playwright
- **Charts**: Data processing libraries
- **Email**: Gmail integration components
- **Utilities**: Python-dotenv, asyncio support

### Configuration Files

#### `config/config.json`
- Persistent application settings
- Alert thresholds and schedules
- Email configuration
- System credentials (encrypted)
- Timezone settings

#### `gmail_config/`
- Gmail OAuth credentials
- Authentication tokens
- Email service configuration

### Data Directories

#### `logs/`
- **eg4_srp_monitor.log**: Main application log
- Rotating file handler (10MB max, 3 backups)
- Web-accessible via logs API

#### `downloads/`
- SRP CSV data files with timestamps
- Automatically downloaded energy usage data
- Chart data source for web interface

## 🔧 Development Notes

### Architecture Changes (v2.3)
- **Removed**: Docker containerization
- **Added**: Native Python virtual environment
- **Updated**: All hard-coded paths from `/app/` to `./`
- **Enhanced**: Web-based credential management

### Logging System
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Handlers**: Console, File (rotating), Web (in-memory buffer)
- **Web Interface**: Real-time log viewer with filtering

### Credential Management
- **Primary**: Web interface (Configuration tab)
- **Fallback**: Environment variables (.env file)
- **Storage**: Encrypted JSON configuration
- **Scope**: EG4 Cloud, SRP Account, Gmail settings

## 🗂️ Archived Components

### `archive/deprecated-docs/`
- **FILE_STRUCTURE.md**: Old Docker-based structure docs
- **README_GITWATCH.md**: Gitwatch automation documentation
- **srp_csv_downloader.py**: Standalone CSV downloader (integrated into main app)
- **requirements-dev.txt**: Development dependencies (no longer needed)
- **send-gmail**: Standalone email script (integrated into main app)

### Why These Were Archived
1. **Docker references**: No longer applicable after migration
2. **Standalone scripts**: Functionality integrated into main application
3. **Development files**: Not needed for production deployment
4. **Gitwatch**: External monitoring system, not core to application

## 📊 Dependencies Summary

### Production Dependencies (requirements.txt)
- **Flask>=2.3.3**: Web framework
- **flask-socketio>=5.3.6**: Real-time communication
- **playwright>=1.39.0**: Browser automation
- **python-dotenv>=1.0.0**: Environment management
- **pytz>=2023.3**: Timezone handling

### Gmail Integration (gmail_integration_temp/)
- **google-auth>=2.23.4**: Gmail authentication
- **google-auth-httplib2>=0.2.0**: HTTP library
- **google-api-python-client>=2.108.0**: Gmail API client

## 🔄 Migration History

### v2.3 (July 25, 2025) - Docker Removal
- Migrated from Docker containers to native Python
- Added web-based credential management
- Fixed all hard-coded Docker paths
- Integrated system logs into Configuration tab

### v2.2 (July 15, 2025) - Performance Improvements
- Persistent EG4 browser sessions
- Fixed Docker volume timestamp issues
- Enhanced session management

### v2.1 (July 11, 2025) - Bug Fixes
- Fixed SRP data update issues
- Improved grid import/export logic
- Enhanced timezone handling

---

**Note**: This structure reflects the current native Python deployment. All Docker-related components have been archived for reference but are no longer required for operation.