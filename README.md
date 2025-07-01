# Solar Assistant - Open Source Solar Monitoring System

A comprehensive, Docker-based solar monitoring system that provides real-time monitoring, data visualization, and management capabilities for solar inverters. Originally designed for EG4 inverters but supports multiple protocols and brands.

## 🚀 Quick Start

### EG4 Web Monitor (Docker)
```bash
# Clone the repository
git clone git@github.com:JeremyWhittaker/solar_assistant.git
cd solar_assistant

# Start the EG4 web monitor
docker compose -f docker-compose.eg4.yml up -d

# Access at http://localhost:8282
```

### Full Solar Assistant (Docker)
```bash
cd solar_assistant/docker

# Initial setup
make install

# Start the system
make up

# Access at http://localhost
```

## 🌟 Features

### Core Features
- **Multi-Inverter Support**: Monitor unlimited inverters simultaneously
- **Multi-Protocol Support**: IoTOS (EG4), Modbus TCP/RTU, expandable
- **Real-time Monitoring**: 5-second update intervals via WebSocket
- **Data Persistence**: SQLite with automatic backups
- **Time Series Storage**: InfluxDB for long-term data analysis
- **MQTT Integration**: Publish data and receive commands
- **Alert System**: Configurable alerts with multiple notification methods
- **Data Export**: CSV, JSON, Excel formats
- **RESTful API**: Full API for third-party integration
- **Mobile Responsive**: Works on all devices

### Advanced Features
- **Docker Containerized**: Easy deployment and scaling
- **Microservices Architecture**: Modular and maintainable
- **Automatic Backups**: Scheduled database backups with retention
- **Energy Reports**: Daily/monthly/yearly statistics
- **EG4 Cloud Monitor**: Remote monitoring via monitor.eg4electronics.com
- **SRP Integration**: Salt River Project utility data with peak/off-peak visualization
- **Service Auto-Recovery**: Automatic restart on crashes
- **Persistent Credentials**: Secure credential storage that survives restarts
- **Weather Integration**: (Coming soon)
- **Energy Prediction**: (Coming soon)

## 📦 Installation Options

### Option 1: Docker (Recommended)
The Docker implementation provides a complete, production-ready system with all dependencies managed.

```bash
cd docker
cp .env.example .env
# Edit .env with your settings
make up
```

### Option 2: Standalone Python
For development or testing on a single machine.

```bash
cd eg4_assistant
pip install -r requirements.txt
python app_v2.py
```

### Option 3: EG4 Cloud Monitor
For remote monitoring through EG4's cloud service.

```bash
pip install playwright python-dotenv
playwright install chromium
python3 eg4_monitor.py
```

See [docs/EG4_CLOUD_MONITOR.md](docs/EG4_CLOUD_MONITOR.md) for detailed setup.

## 🏗️ Architecture

### Docker Architecture
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Web Browser   │────▶│  Nginx (80)  │────▶│ Flask App   │
└─────────────────┘     └──────────────┘     └─────────────┘
                                                     │
                              ┌──────────────────────┴───────────────────┐
                              │                                          │
                        ┌─────▼─────┐  ┌──────────┐  ┌────────┐  ┌─────▼────┐
                        │  SQLite   │  │ InfluxDB │  │  MQTT  │  │  Redis   │
                        └───────────┘  └──────────┘  └────────┘  └──────────┘
```

### Communication Flow
```
┌─────────────┐     Protocol      ┌──────────────┐     WebSocket    ┌─────────────┐
│  Inverters  │ ◄─────────────► │ Solar Assistant│ ◄──────────────► │ Web Browser │
│             │   IoTOS/Modbus   │     Server     │                   │             │
└─────────────┘                  └──────────────┘                   └─────────────┘
```

## ⚙️ Configuration

### Inverter Configuration
Edit `config/config.yaml` to add your inverters:

```yaml
inverters:
  - name: "EG4 18kPV Primary"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.100"
    port: 8000
    enabled: true
    
  - name: "Generic Modbus Inverter"
    type: "generic"
    protocol: "modbus_tcp"
    host: "192.168.1.101"
    port: 502
    unit_id: 1
    enabled: true
```

### System Configuration
- **Update Interval**: How often to poll inverters (default: 5 seconds)
- **Data Retention**: How long to keep historical data (default: 30 days)
- **MQTT Settings**: Broker connection and topics
- **Alert Rules**: Define conditions for notifications

## 📊 API Documentation

### RESTful Endpoints
- `GET /api/status` - System status and totals
- `GET /api/inverters` - List all inverters
- `GET /api/data/<inverter>/<period>` - Historical data
- `GET /api/config` - Current configuration
- `POST /api/config` - Update configuration
- `GET /api/export/<format>` - Export data

### WebSocket Events
- `system_update` - Real-time system status
- `inverter_update` - Individual inverter data
- `alert` - System alerts

### MQTT Topics
Publishing:
- `solar-assistant/system/status` - System totals
- `solar-assistant/inverter/<name>` - Individual inverter data

Subscribing:
- `solar-assistant/command/+` - System commands
- `solar-assistant/set/+` - Configuration changes

## 🔧 Development

### Project Structure
```
solar_assistant/
├── docker/                 # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── config/                 # Configuration files
│   └── config.yaml
├── eg4_assistant/         # Standalone version
│   ├── app.py            # V1 (single inverter)
│   └── app_v2.py         # V2 (multi-inverter)
├── solar_assistant_server.py  # Docker main app
├── mqtt_bridge.py         # MQTT service
├── data_collector.py      # Background tasks
└── database.py            # Database models
```

### Adding Protocol Support
1. Create a new client in `protocol_clients/`
2. Implement the standard interface
3. Add to `solar_assistant_server.py`
4. Update configuration schema

### Running Tests
```bash
make test
```

## 🚀 Deployment

### Production Deployment
1. Use a reverse proxy with SSL (nginx, Traefik)
2. Set strong passwords in `.env`
3. Configure firewall rules
4. Enable automatic backups
5. Set up monitoring

### Scaling
- Run multiple instances behind a load balancer
- Use external PostgreSQL for larger deployments
- Implement Redis for session storage

## 🔄 Migration Guide

### From EG4 Assistant V1/V2
1. Export your data: `python export_data.py`
2. Stop the old service
3. Start Docker version
4. Import data: `make restore file=backup.db`

### From Other Systems
Use the API to import historical data or configure MQTT bridging.

## 🛠️ Troubleshooting

### Common Issues
1. **Connection Failed**: Check inverter IP and firewall
2. **No Data**: Verify protocol settings match inverter
3. **High CPU**: Reduce update interval or inverter count

### Debug Commands
```bash
# View logs
make logs

# Access container
make shell

# Check service status
make status
```

## 📈 Roadmap

- [ ] Mobile app (PWA)
- [ ] Cloud connectivity
- [ ] Machine learning predictions
- [ ] Voice control integration
- [ ] Advanced battery management
- [ ] Grid trading automation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Inspired by Solar Assistant commercial product
- Built on the shoulders of open source giants
- Community contributions and feedback

## 📞 Support

- GitHub Issues: [Report bugs or request features](https://github.com/JeremyWhittaker/solar_assistant/issues)
- Documentation: See `/docker/README.md` for detailed Docker setup
- Wiki: Coming soon

---

Made with ❤️ for the solar community