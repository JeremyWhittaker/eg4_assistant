# Solar Assistant Installation Guide

This guide covers all installation methods for Solar Assistant, from simple Docker deployment to advanced configurations.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Install (Docker)](#quick-install-docker)
- [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### For Docker Installation
- Docker Engine 20.10+ and Docker Compose 2.0+
- 2GB RAM minimum (4GB recommended)
- 10GB disk space
- Linux, macOS, or Windows with WSL2

### For Manual Installation
- Python 3.8+
- Git
- SQLite3
- Network access to inverters

## Quick Install (Docker)

### 1. Clone the Repository
```bash
git clone git@github.com:JeremyWhittaker/solar_assistant.git
cd solar_assistant
```

### 2. Navigate to Docker Directory
```bash
cd docker
```

### 3. Setup Environment
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### 4. Configure Inverters
```bash
# Edit configuration
nano ../config/config.yaml
```

Add your inverter(s):
```yaml
inverters:
  - name: "My EG4 Inverter"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.100"  # Your inverter IP
    port: 8000
    enabled: true
```

### 5. Start the System
```bash
# Using Make (recommended)
make up

# Or using docker-compose directly
docker-compose up -d
```

### 6. Access the Interface
Open http://localhost in your browser

## Manual Installation

### Option A: Standalone Python (Development)

#### 1. Clone and Setup
```bash
git clone git@github.com:JeremyWhittaker/solar_assistant.git
cd solar_assistant/eg4_assistant
```

#### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment
```bash
cp .env.example .env
nano .env
```

#### 5. Run the Application
```bash
# V1 (Single Inverter)
python app.py

# V2 (Multi-Inverter)
python app_v2.py
```

### Option B: System Service (Production)

#### 1. Create Service User
```bash
sudo useradd -r -s /bin/false solar-assistant
```

#### 2. Install to System Location
```bash
sudo mkdir -p /opt/solar-assistant
sudo cp -r * /opt/solar-assistant/
sudo chown -R solar-assistant:solar-assistant /opt/solar-assistant
```

#### 3. Create Systemd Service
```bash
sudo nano /etc/systemd/system/solar-assistant.service
```

Add:
```ini
[Unit]
Description=Solar Assistant Monitoring Service
After=network.target

[Service]
Type=simple
User=solar-assistant
WorkingDirectory=/opt/solar-assistant
ExecStart=/usr/bin/python3 /opt/solar-assistant/solar_assistant_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4. Enable and Start
```bash
sudo systemctl daemon-reload
sudo systemctl enable solar-assistant
sudo systemctl start solar-assistant
```

## Configuration

### Basic Configuration

The main configuration file is `config/config.yaml`:

```yaml
system:
  name: "My Solar System"
  timezone: "America/New_York"
  update_interval: 5  # seconds

inverters:
  - name: "Primary Inverter"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.100"
    port: 8000
    enabled: true
```

### Advanced Configuration

#### Multiple Inverters
```yaml
inverters:
  - name: "EG4 Primary"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.100"
    port: 8000
    enabled: true
    
  - name: "EG4 Secondary"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.101"
    port: 8000
    enabled: true
    
  - name: "Modbus Inverter"
    type: "generic"
    protocol: "modbus_tcp"
    host: "192.168.1.102"
    port: 502
    unit_id: 1
    enabled: true
```

#### MQTT Configuration
```yaml
mqtt:
  enabled: true
  host: "192.168.1.50"
  port: 1883
  username: "solar"
  password: "secret"
  topics:
    prefix: "solar-assistant"
    publish_interval: 10
```

#### Alert Configuration
```yaml
alerts:
  enabled: true
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_user: "your-email@gmail.com"
    smtp_password: "app-specific-password"
    from_address: "solar@yourdomain.com"
    to_addresses: ["admin@yourdomain.com"]
  
  rules:
    - name: "Battery Critical"
      condition: "battery_soc < 10"
      severity: "critical"
      cooldown: 1800
```

### Network Configuration

#### Firewall Rules
Allow these ports:
- 80 (Web Interface)
- 5000 (API)
- 1883 (MQTT)
- 8000 (IoTOS)
- 502 (Modbus)

Example for UFW:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 1883/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 502/tcp
```

#### Reverse Proxy (nginx)
```nginx
server {
    listen 80;
    server_name solar.yourdomain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Verification

### 1. Check Services
```bash
# Docker
docker-compose ps

# Systemd
sudo systemctl status solar-assistant
```

### 2. Test Inverter Connection
```bash
cd test_scripts
python test_inverter_connection.py
```

### 3. Check Logs
```bash
# Docker
docker-compose logs -f

# Standalone
tail -f logs/solar_assistant.log
```

### 4. API Test
```bash
curl http://localhost/api/status
```

## Troubleshooting

### Common Issues

#### 1. Cannot Connect to Inverter
- Verify inverter IP is correct
- Check network connectivity: `ping <inverter-ip>`
- Ensure firewall allows connection
- Verify protocol settings match inverter

#### 2. No Data Displayed
- Check logs for errors
- Verify inverter configuration
- Test with single inverter first
- Enable debug logging

#### 3. High CPU Usage
- Increase update interval
- Reduce number of active inverters
- Check for connection timeouts

#### 4. Database Errors
- Check disk space
- Verify write permissions
- Run database cleanup

### Debug Mode

Enable debug logging:
```yaml
logging:
  level: "DEBUG"
```

### Reset Database
```bash
# Docker
docker-compose down
docker volume rm solar-assistant_data
docker-compose up -d

# Standalone
rm data/solar_assistant.db
python init_database.py
```

### Support

For additional help:
- Check logs first
- Review configuration
- Open an issue on GitHub
- Include error messages and configuration (remove passwords)

## Next Steps

After successful installation:
1. Configure all inverters
2. Set up alerts
3. Enable MQTT if needed
4. Configure backups
5. Set up monitoring

See the [User Guide](USER_GUIDE.md) for detailed usage instructions.