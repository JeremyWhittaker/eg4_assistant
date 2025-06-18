# Solar Assistant Docker Container

This is a complete Docker-based implementation of a Solar Assistant monitoring system, reverse-engineered to provide all the functionality of the original Raspberry Pi image.

## Features

- **Multi-Protocol Support**: IoTOS, Modbus TCP/RTU
- **Multi-Inverter Support**: Monitor unlimited inverters
- **Real-time Monitoring**: 5-second update intervals via WebSocket
- **Data Persistence**: SQLite with automatic backups
- **Time Series Data**: InfluxDB integration for long-term storage
- **MQTT Integration**: Publish data and receive commands
- **Alert System**: Configurable alerts with email notifications
- **Data Export**: CSV, JSON, Excel formats
- **RESTful API**: Full API for integration
- **Web Interface**: Responsive dashboard with real-time updates

## Quick Start

1. **Configure your inverters** in `config/config.yaml`:
```yaml
inverters:
  - name: "My EG4 Inverter"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.100"
    port: 8000
    enabled: true
```

2. **Start the containers**:
```bash
docker-compose up -d
```

3. **Access the web interface** at http://localhost

## Architecture

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

## Services

### Main Application (`solar-assistant`)
- Web interface on port 80
- API on port 5000
- WebSocket for real-time updates
- IoTOS protocol on port 8000
- Modbus TCP on port 502

### MQTT Broker (`mqtt`)
- MQTT on port 1883
- WebSocket on port 9001

### Time Series Database (`influxdb`)
- HTTP API on port 8086
- Long-term data storage

### Cache (`redis`)
- Redis on port 6379
- Session storage and caching

## Configuration

All configuration is done through `config/config.yaml`:

- **System Settings**: Name, timezone, update intervals
- **Database**: Backup settings, retention policies
- **Inverters**: Add/modify inverter connections
- **MQTT**: Broker settings and topics
- **Alerts**: Define alert conditions and notifications
- **API**: Authentication and rate limiting

## Data Persistence

All data is stored in Docker volumes:
- `/data/db`: SQLite database
- `/data/logs`: Application logs
- `/data/reports`: Daily reports
- `/data/backups`: Database backups
- `/data/exports`: Exported data files

## API Endpoints

- `GET /api/status` - System status
- `GET /api/inverters` - List all inverters
- `GET /api/data/<inverter>/<period>` - Historical data
- `GET /api/config` - Current configuration
- `POST /api/config` - Update configuration
- `GET /api/export/<format>` - Export data

## MQTT Topics

Publishing:
- `solar-assistant/system/status` - System status
- `solar-assistant/inverter/<name>` - Inverter data

Subscribing:
- `solar-assistant/command/+` - Commands
- `solar-assistant/set/+` - Settings

## Environment Variables

- `TZ` - Timezone (default: UTC)
- `DATABASE_PATH` - Database location
- `LOG_PATH` - Log directory
- `CONFIG_PATH` - Configuration file path

## Monitoring

Access monitoring endpoints:
- `/health` - Health check
- `/metrics` - Prometheus metrics

## Backup and Restore

Automatic backups run daily at 3 AM. To manually backup:
```bash
docker exec solar-assistant python -c "from data_collector import DataCollector; DataCollector().backup_database()"
```

To restore:
```bash
docker cp backup.db solar-assistant:/data/db/solar_assistant.db
docker restart solar-assistant
```

## Development

To modify the application:
1. Edit source files
2. Rebuild: `docker-compose build`
3. Restart: `docker-compose restart`

## Troubleshooting

Check logs:
```bash
docker-compose logs -f solar-assistant
```

Access container:
```bash
docker exec -it solar-assistant /bin/bash
```

## Security

- Change default passwords in `docker-compose.yml`
- Update `secret_key` in `config.yaml`
- Use SSL/TLS for production deployments
- Configure firewall rules appropriately

## License

This is a reverse-engineered implementation for educational and personal use.