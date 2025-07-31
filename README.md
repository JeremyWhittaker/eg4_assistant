# EG4-SRP Monitor 🔋⚡

A comprehensive real-time energy monitoring system that integrates EG4 solar inverters with Salt River Project (SRP) utility data and Enphase solar systems. Built with Flask, Socket.IO, and Playwright for reliable web automation and professional dashboard presentation.

![EG4-SRP Monitor Dashboard](https://img.shields.io/badge/Status-Production%20Ready-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

### 🎨 Professional Web Interface
- **Modern Design**: Glassmorphism interface with integrated header and logo-only branding
- **Real-time Updates**: Live WebSocket dashboard with 60-second refresh intervals
- **Mobile Responsive**: Optimized for all screen sizes with touch-friendly controls
- **Dark Theme**: Professional color scheme with blue accent highlights

### 📊 Multi-System Energy Monitoring
- **EG4 Inverter Integration**:
  - Real-time battery SOC, power flow, and voltage monitoring
  - Individual PV string tracking (PV1, PV2, PV3) with automatic totaling
  - Grid import/export tracking with directional power flow
  - Load consumption monitoring with connection validation

- **SRP Utility Integration**:
  - Daily peak demand tracking with threshold alerts
  - Historical energy data with 4 chart types (Net Energy, Generation, Usage, Demand)
  - Automatic CSV download and parsing with temperature correlation

- **Enphase Solar Integration**:
  - Current power production monitoring
  - Daily and lifetime energy statistics with microinverter health status

### 🚨 Smart Alert System
- **Timezone-aware Notifications**: Supports 6 US timezones with configurable scheduling
- **Anti-spam Protection**: Cooldown periods prevent duplicate alerts
- **Gmail Integration**: Custom SMTP with App Password support and HTML formatting
- **Multiple Alert Types**: Battery low, peak demand, and time-based grid import alerts

### ⚙️ Configuration Management
- **Web-based Setup**: Complete credential management for all systems through web interface
- **Settings Persistence**: JSON configuration with automatic backup and restore
- **Live Monitoring**: System log viewer with filtering and download capabilities
- **Service Integration**: Systemd service support for automatic startup

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Ubuntu/Debian Linux (recommended) or similar systemd-based system
- Active accounts with EG4 Cloud, SRP, and Enphase (as applicable)
- Gmail account with App Password for alerts

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/JeremyWhittaker/eg4-srp-monitor.git
cd eg4-srp-monitor
```

2. **Run the automated installation**:
```bash
chmod +x install.sh
./install.sh
```

3. **Configure credentials through web interface**:
```bash
# Start the application
python app.py

# Navigate to http://localhost:5002
# Go to Configuration tab and enter your credentials
```

4. **Install as system service** (optional but recommended):
```bash
sudo systemctl enable eg4-srp-monitor
sudo systemctl start eg4-srp-monitor
```

### Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Create required directories
mkdir -p logs config downloads

# Start application
python app.py
```

## 📱 Usage

### Web Interface
Access the dashboard at `http://localhost:5002`

- **Monitoring Tab**: Real-time energy data with interactive charts
- **Configuration Tab**: System credentials, alert settings, and logs

### System Service Management
```bash
# Service status and control
sudo systemctl status eg4-srp-monitor    # Check status
sudo systemctl restart eg4-srp-monitor   # Restart service
sudo journalctl -u eg4-srp-monitor -f    # View live logs

# Configuration changes
# Edit settings through web interface, then restart service
sudo systemctl restart eg4-srp-monitor
```

## 🔧 Configuration

### Credential Setup
Configure through the web interface at `http://localhost:5002` → Configuration tab:

1. **EG4 Cloud Account**: Username and password for inverter access
2. **SRP Account**: Username and password for utility data
3. **Enphase Account**: Username and password for solar monitoring
4. **Gmail SMTP**: Email address and App Password for alerts

### Alert Configuration
- **Battery Alerts**: Daily SOC check at configurable time (default: 2:00 PM)
- **Peak Demand Alerts**: Daily demand check at configurable time (default: 6:00 AM)
- **Grid Import Alerts**: Time-window based monitoring (default: 2:00-8:00 PM)
- **Email Recipients**: Comma-separated list for notifications

### Timezone Settings
Select from 6 supported US timezones:
- UTC
- Phoenix (MST)
- Los Angeles (PST/PDT)
- Denver (MST/MDT)
- Chicago (CST/CDT)
- New York (EST/EDT)

## 📊 Monitoring Data

### Real-time Metrics
- **Battery**: State of charge, power flow, voltage
- **Solar**: Individual PV string power and voltage
- **Grid**: Import/export power and voltage
- **Load**: Current consumption

### Historical Data
- **SRP Charts**: Net energy, generation, usage, and demand
- **Data Export**: CSV files with timestamp naming
- **Temperature Correlation**: High/low temperature data

## 🛠️ Architecture

### System Design
- **Monolithic Flask Application**: Single-file architecture for simplicity
- **Real-time Communication**: WebSocket updates with auto-reconnection
- **Background Processing**: Threaded monitoring with intelligent retry logic
- **Data Persistence**: SQLite storage with JSON configuration

### File Structure
```
eg4-srp-monitor/
├── app.py                          # Main Flask application (1,800+ lines)
├── templates/index.html            # Web interface (2,100+ lines)
├── requirements.txt                # Python dependencies
├── install.sh                      # Automated installation script
├── eg4-srp-monitor.service        # Systemd service definition
├── venv/bin/send-gmail            # Custom Gmail SMTP script
├── config/config.json             # Persistent settings
├── logs/eg4_srp_monitor.log       # Application logs (rotated)
├── downloads/                     # SRP CSV files
└── README.md                      # This file
```

## 🔒 Security

### Credential Protection
- All credentials stored locally with restricted permissions (600)
- Gmail App Passwords required (not regular passwords)
- No hardcoded secrets in source code
- HTTPS recommended for remote access

### Network Security
- Application binds to localhost by default
- No authentication required (designed for trusted networks)
- Consider reverse proxy with authentication for internet exposure

## 📋 Requirements

### System Requirements
- **Operating System**: Linux with systemd (Ubuntu 20.04+ recommended)
- **Python**: 3.8 or higher
- **Memory**: ~100MB typical usage
- **CPU**: <1% typical load
- **Network**: Outbound HTTPS for data collection and SMTP

### Account Requirements
- **EG4 Cloud**: Active account with inverter registered
- **SRP**: Active utility account with online access
- **Enphase**: Solar system account (if applicable)
- **Gmail**: Account with App Password enabled

## 🐛 Troubleshooting

### Common Issues

**Service won't start**:
```bash
# Check service status
sudo systemctl status eg4-srp-monitor

# View detailed logs
sudo journalctl -u eg4-srp-monitor -n 50

# Check file permissions
ls -la /home/$(whoami)/eg4-srp-monitor/
```

**Gmail authentication fails**:
- Ensure you're using an App Password, not your regular Gmail password
- Create App Password at: https://myaccount.google.com/apppasswords
- Verify credentials in Configuration tab

**Data not updating**:
```bash
# Check if all threads are running
tail -f logs/eg4_srp_monitor.log

# Verify network connectivity
curl -I https://eg4cloud.com
curl -I https://myaccount.srpnet.com
```

**Web interface not accessible**:
```bash
# Check if application is running
ps aux | grep app.py

# Verify port availability
ss -tulpn | grep :5002

# Check firewall settings
sudo ufw status
```

### Log Analysis
Access logs through:
- **Web Interface**: Configuration tab → System Logs
- **Command Line**: `tail -f logs/eg4_srp_monitor.log`
- **Service Logs**: `sudo journalctl -u eg4-srp-monitor -f`

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Commit with descriptive messages: `git commit -m 'Add amazing feature'`
5. Push to your branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for new functions
- Test all changes with real credentials in development

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **EG4 Electronics** for their solar inverter technology
- **Salt River Project** for utility data access
- **Enphase Energy** for solar monitoring systems
- **Flask** and **Socket.IO** communities for excellent frameworks
- **Playwright** team for reliable browser automation

## 📞 Support

- **Issues**: Report bugs via [GitHub Issues](https://github.com/JeremyWhittaker/eg4-srp-monitor/issues)
- **Documentation**: See [CLAUDE.md](CLAUDE.md) for development details
- **Discussions**: Use [GitHub Discussions](https://github.com/JeremyWhittaker/eg4-srp-monitor/discussions) for questions

## 🗺️ Roadmap

### Planned Features
- [ ] HTTPS/TLS support for production deployments
- [ ] User authentication for multi-user access
- [ ] Data export functionality (CSV, JSON)
- [ ] Historical data retention policies
- [ ] REST API documentation
- [ ] Docker containerization option
- [ ] Grafana integration for advanced analytics
- [ ] Mobile app with push notifications

### Recent Updates

**July 30, 2025 - Major UI and Gmail Integration Update**
- 🎨 Complete UI redesign with glassmorphism interface
- 🖼️ Logo-only branding with 250% larger EG4 icon
- 📧 Fixed Gmail two-factor authentication with custom SMTP
- ✅ All systems tested and production-ready

**July 25, 2025 - Native Python Migration**
- 🚀 Removed Docker dependency for simpler deployment
- ⚙️ Web-based credential management
- 📊 Enhanced multi-MPPT PV monitoring
- 🔔 Smart timezone-aware alert system

---

**⭐ Star this repository if you find it useful!**

Built with ❤️ for the solar energy community