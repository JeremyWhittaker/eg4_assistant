# Solar Assistant Linux Image Analysis Report

## Summary

Solar Assistant is a sophisticated monitoring system for solar inverters that runs on Raspberry Pi. Based on my analysis of the Linux image, it uses a modern tech stack with Elixir/Phoenix for the backend, Grafana for data visualization, MQTT for real-time communication, and Modbus for inverter communication.

## Architecture Overview

### 1. Core Technology Stack

- **Backend Framework**: Elixir/Phoenix (Erlang BEAM VM)
- **Data Visualization**: Grafana with custom dashboards
- **Message Broker**: Mosquitto MQTT broker
- **Communication Protocol**: Modbus (RS485/TCP)
- **Web Server**: Likely Phoenix serving on port 80/443
- **Operating System**: Debian-based Linux for ARM64 (Raspberry Pi)

### 2. System Configuration

- **Main User**: `solar-assistant` (UID 1000)
- **Home Directory**: `/home/solar-assistant`
- **System Service**: `solar-assistant.service`
- **Hostname**: `solar-assistant.local`
- **IP Configuration**: 10.0.0.5
- **Default Password Hash**: `$y$j9T$lCmZ0wn/LxORwnbmF4Cvv1$A4xhU5sVHyGt7DDa5YI1.ZDVBQO.hD.wvngWkZ5zvEB`

### 3. Key Services

1. **solar-assistant** - Main application service
2. **grafana-server** - Data visualization
3. **mosquitto** - MQTT broker for real-time data

### 4. Grafana Configuration

- **Dashboard Path**: `/etc/grafana/solar-assistant/dashboards/charts.json`
- **Provisioning**: `/etc/grafana/solar-assistant/dashboards/`
- **URL Configuration**: Served under `/grafana` path
- **Dashboard Folder**: "SolarAssistant"

### 5. Communication Protocols

#### MQTT Configuration
- Default Mosquitto installation
- Likely publishes inverter data to MQTT topics
- InfluxDB uses MQTT data (based on the presence of Paho MQTT library references)

#### Modbus
- libmodbus library for RS485/TCP communication
- Used to communicate with solar inverters

### 6. Web Interface

- **API Endpoint Found**: `http://127.0.0.1/api/v1/network`
- **Static Assets**: JavaScript bundles, CSS files
- **Frontend Framework**: Appears to use modern JavaScript with webpack bundling
- **Icon Library**: Unicons icon library detected

## Data Flow Architecture

```
Inverters → Modbus → Solar Assistant → MQTT → Grafana/InfluxDB
                           ↓
                      Web Interface
                           ↓
                    User Dashboard
```

## Key Findings for Replication

### 1. Data Collection
- Modbus communication to read inverter data
- Real-time data publishing via MQTT
- Time-series data storage (likely InfluxDB)

### 2. Web Interface Components
- Phoenix LiveView or standard Phoenix controllers
- Grafana embedded dashboards
- Custom JavaScript for real-time updates

### 3. MQTT Topics (Inferred)
Based on the architecture, likely topics include:
- `solar_assistant/inverter/power`
- `solar_assistant/inverter/voltage`
- `solar_assistant/inverter/current`
- `solar_assistant/battery/soc`
- `solar_assistant/battery/voltage`
- `solar_assistant/grid/status`
- `solar_assistant/load/power`

## Next Steps for Cloning

1. **Mount the Image**: To access actual configuration files
   ```bash
   sudo mount -o loop,offset=$((512*532480)) linux_partition.img /mnt/solar
   ```

2. **Extract Key Files**:
   - `/etc/grafana/solar-assistant/`
   - `/home/solar-assistant/`
   - Phoenix application files
   - MQTT configuration

3. **Reverse Engineer**:
   - Grafana dashboard JSON
   - MQTT topic structure
   - Modbus register mappings
   - API endpoints

4. **Build Clone**:
   - Set up Elixir/Phoenix app
   - Configure Modbus communication
   - Set up MQTT broker
   - Create Grafana dashboards
   - Implement web interface

## Security Notes

- SSH access is available (mentioned in EULA)
- Default user has sudo access
- Web interface likely has authentication

## Legal Considerations

The system includes EULA and copyright notices:
- `https://solar-assistant.io/register/eula`
- `https://solar-assistant.io/help/ssh`

Any cloning should be for educational purposes only and respect the original software's licensing terms.