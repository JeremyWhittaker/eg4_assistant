# EG4-SRP Monitor

A comprehensive monitoring and alerting system for EG4 inverters with Salt River Project (SRP) utility integration. Features real-time monitoring, intelligent alerting, and detailed energy usage analytics.

## 🌟 Features

### Real-time EG4 Monitoring
- **Multi-MPPT Support**: Individual PV string monitoring (PV1, PV2, PV3) with automatic totaling
- **Battery Management**: SOC, power, voltage monitoring with intelligent alert protection
- **Grid & Load Tracking**: Real-time power flow monitoring with import/export detection
- **Connection Validation**: Prevents false alerts when system is offline

### SRP Integration
- **Peak Demand Tracking**: Daily peak demand monitoring with configurable update times
- **Energy Usage Analytics**: Complete chart suite with Net Energy, Generation, Usage, and Demand
- **CSV Data Export**: Automatic download and processing of SRP usage data
- **Historical Analysis**: 30+ days of detailed energy usage trends

### Smart Alert System
- **Gmail Integration**: Seamless email alerts using gmail-send
- **Time-based Scheduling**: Configurable alert times (e.g., 6:00 AM battery check)
- **Anti-spam Protection**: Prevents duplicate alerts and false positives
- **Connection-aware**: Only sends alerts when systems are properly connected

### Web Interface
- **Real-time Dashboard**: Live updates via WebSocket for instant feedback
- **Interactive Charts**: Four chart types with dynamic switching
- **Configuration Management**: Easy setup through web interface
- **Mobile Responsive**: Works on desktop and mobile devices

## 🚀 Quick Start

1. **Clone and Setup**:
   ```bash
   cd /path/to/your/projects
   git clone <repository-url> eg4-srp-monitor
   cd eg4-srp-monitor
   cp .env.example .env
   ```

2. **Configure Credentials** (edit `.env`):
   ```bash
   # EG4 IoTOS Cloud Credentials
   EG4_USERNAME=your_eg4_username
   EG4_PASSWORD=your_eg4_password
   
   # SRP Account Credentials  
   SRP_USERNAME=your_srp_username
   SRP_PASSWORD=your_srp_password
   ```

3. **Create Virtual Environment and Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -e ./gmail_integration_temp
   playwright install chromium
   ```

4. **Start the Application**:
   ```bash
   python app.py
   ```

5. **Access Dashboard**: Open http://localhost:5000

## 📊 Dashboard Overview

### EG4 Inverter Status
- **Battery**: SOC percentage, power flow, voltage
- **PV Generation**: Total power with individual string breakdown
  ```
  PV Power: 11,120W
  
  PV1: 6483W    PV2: 2302W    PV3: 2335W
       346.3V        355.9V        359.8V
  ```
- **Grid**: Import/export power and voltage
- **Load**: Current consumption
- **Connection Status**: Real-time connectivity indicator

### SRP Peak Demand
- **Current Peak**: Today's maximum demand
- **Next Update**: Scheduled update time (default: 6:00 AM)
- **Manual Refresh**: On-demand data updates
- **Historical Tracking**: Daily peak demand progression

### SRP Energy Usage Charts
- **Net Energy**: Grid import vs export balance
- **Generation**: Solar production over time  
- **Usage**: Off-peak vs on-peak consumption breakdown
- **Demand**: Peak demand trends

## ⚙️ Configuration

### Alert Thresholds
Configure in the web interface under "Alert Configuration":

- **Battery SOC Alerts**:
  - Low battery threshold (default: 20%)
  - High battery threshold (default: 95%)
  - Check time (default: 6:00 AM daily)

- **Peak Demand Alerts**:
  - Maximum demand threshold (default: 5.0 kW)
  - Check time (default: 6:00 AM daily)

- **Grid Import Alerts**:
  - Import threshold (default: 10,000W)
  - Active hours (default: 2:00 PM - 8:00 PM)
  - 15-minute cooldown between alerts

### Email Configuration
Set up Gmail alerts through the web interface:
1. Use Gmail app-specific password (not regular password)
2. Configure sender and recipient addresses
3. Test with the "Test Email" button
4. Credentials are securely stored and persist across restarts

### Timezone Settings
- Default: America/Phoenix (Arizona time)
- Configurable via web interface
- Affects alert scheduling and data timestamps

## 🔧 API Endpoints

### Status & Data
- `GET /api/status` - Current system status and data
- `GET /api/config` - Alert configuration  
- `POST /api/config` - Update alert settings

### SRP Integration  
- `GET /api/refresh-srp` - Manual SRP data refresh
- `GET /api/srp-chart-data?type={net|generation|usage|demand}` - Chart data

### Email & Testing
- `GET /api/test-email` - Send test alert email
- `GET /api/gmail-status` - Check Gmail configuration

## 💻 Local Development

### Running the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
python app.py

# View logs
tail -f logs/eg4_srp_monitor.log
```

## 📁 Project Structure

```
eg4-srp-monitor/
├── app.py                 # Main Flask application (1,400+ lines)
├── templates/
│   └── index.html        # Web interface template (700+ lines)
├── requirements.txt      # Python dependencies
├── downloads/           # SRP CSV data storage
├── config/             # Configuration persistence
├── logs/               # Application logs
├── .env                # Environment variables (credentials)
├── .env.example        # Example environment file
└── README.md           # This documentation
```

## 🔍 Troubleshooting

### Common Issues

1. **EG4 Shows All Zeros**:
   - Check EG4 credentials in `.env`
   - Verify EG4 cloud service is accessible
   - Check application logs: `tail -f logs/eg4_srp_monitor.log`

2. **SRP Data Not Loading**:
   - Verify SRP credentials in web interface
   - Check if it's past 6:00 AM update time
   - Use manual refresh button
   - Ensure SRP website is accessible

3. **Email Alerts Not Working**:
   - Use Gmail app-specific password (not regular password)
   - Check Gmail configuration in web interface
   - Test with "Test Email" button
   - Verify recipient email is correct

4. **Application Won't Start**:
   - Check port 5000 isn't in use: `netstat -an | grep 5000`
   - Verify virtual environment is activated
   - Check application logs for specific errors

### Viewing Logs
```bash
# Real-time logs
tail -f logs/eg4_srp_monitor.log

# Recent logs only
tail -50 logs/eg4_srp_monitor.log

# Filter for specific issues
grep -i error logs/eg4_srp_monitor.log
```

### Manual Refresh
```bash
# Trigger SRP data refresh
curl http://localhost:8085/api/refresh-srp

# Check current status
curl http://localhost:8085/api/status | python3 -m json.tool
```

## 🔄 Monitoring Schedule

- **EG4 Data**: Updates every 60 seconds
- **SRP Peak Demand**: Daily at 6:00 AM (configurable)
- **SRP CSV Downloads**: Daily with peak demand update
- **Alert Checks**: Continuous with time-based triggers
- **Connection Validation**: Every update cycle

## 🛡️ Security & Privacy

- **Credential Storage**: Environment variables and secure file storage
- **Network Access**: Only connects to EG4 and SRP official websites
- **Local Data**: All data stored locally, no cloud services
- **Gmail Integration**: Uses official Gmail API via gmail-send package

## 📈 Performance

- **Memory Usage**: ~200-300MB
- **CPU Usage**: Low (1-2% on modern systems)
- **Storage**: ~50MB for application + CSV data
- **Network**: Minimal (only during scheduled updates)

## 🔧 Recent Improvements

### Version 2.2 (July 15, 2025)
- **Persistent EG4 Sessions**: Reduced login frequency from every minute to once per hour
- **Docker Volume Fix**: Resolved SRP charts showing old data due to file timestamp issues
- **Session Management**: Smart detection of expired sessions with automatic re-login
- **Performance Boost**: Page refresh instead of full navigation for faster updates

### Version 2.1 (July 11, 2025)
- **Fixed SRP Data Updates**: Resolved issue where yesterday's data wasn't appearing in charts
- **Peak Demand Accuracy**: Fixed peak demand display showing 0 instead of actual values
- **Daily CSV Refresh**: Automated daily SRP CSV downloads now working reliably
- **Grid Alert Logic**: Fixed false grid import alerts when exporting power to grid
- **Production Deployment**: Eliminated Werkzeug development warnings in production
- **Timezone Handling**: Enhanced timezone-aware datetime processing for alerts

### Version 2.0 (July 2025)
- **Enhanced PV Monitoring**: Multi-MPPT string support with individual power/voltage display
- **Improved SRP Integration**: All 4 chart types (Net Energy, Generation, Usage, Demand)
- **Smart Alert Protection**: Prevents false alerts when systems are offline
- **Better Error Handling**: Robust connection validation and retry logic
- **Real-time Charts**: Interactive SRP usage charts with historical data

### Key Bug Fixes (July 15, 2025)
- **SRP File Selection**: Fixed Docker volume timestamp issue causing old CSV files to be used
- **Persistent Sessions**: EG4 browser stays logged in, reducing authentication overhead
- **Chart Data Currency**: All SRP charts now show the most recent data available
- **Session Recovery**: Graceful handling of session timeouts with automatic re-authentication

## 🤝 Contributing

1. **Bug Reports**: Include logs and system information
2. **Feature Requests**: Describe use case and expected behavior
3. **Pull Requests**: Follow existing code style and add tests
4. **Documentation**: Help improve setup and troubleshooting guides

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **EG4 Electronics**: For providing IoTOS cloud monitoring platform
- **Salt River Project**: For comprehensive energy usage data access
- **Playwright Team**: For reliable web automation framework
- **Flask & Socket.IO**: For real-time web interface capabilities