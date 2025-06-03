# EG4 Assistant - Solar Assistant Clone for EG4 18kPV

A web-based monitoring system for EG4 18kPV inverters that clones the functionality of Solar Assistant.

## Features

- **Real-time Monitoring**: Live data updates via WebSocket
- **Dashboard**: Overview of all system parameters
- **Power Flow Visualization**: Animated diagram showing energy flow
- **Charts**: Real-time charts for power, battery, voltage, and temperature
- **Energy Totals**: Daily, monthly, yearly, and lifetime statistics
- **Configuration**: System settings and network status

## Installation

1. Install dependencies:
```bash
cd eg4_assistant
pip install -r requirements.txt
```

2. Configure your EG4 inverter details in `.env`:
```env
EG4_IP=172.16.107.53
EG4_WEB_IP=172.16.107.3
EG4_WEB_URL=http://172.16.107.53/index_en.html
EG4_USERNAME=admin
EG4_PASSWORD=admin
```

3. Run the application:
```bash
python app.py
```

4. Access the web interface at: http://localhost:5000

## Architecture

```
┌─────────────┐     IoTOS      ┌──────────────┐     WebSocket    ┌─────────────┐
│ EG4 18kPV   │ ◄─────────────► │ EG4 Assistant │ ◄──────────────► │ Web Browser │
│ 172.16.107.53│     Port 8000  │ Flask Server │                   │             │
└─────────────┘                 └──────────────┘                   └─────────────┘
```

## IoTOS Protocol

The EG4 18kPV uses the IoTOS protocol on port 8000:
- Binary protocol with 0xA1 header
- Contains serial number and device ID
- Real-time inverter data embedded in responses

## API Endpoints

- `/` - Dashboard
- `/charts` - Real-time charts
- `/totals` - Energy statistics
- `/power` - Power flow visualization
- `/configuration` - System settings
- `/api/current` - Current inverter data (JSON)
- `/api/history` - Historical data (JSON)
- `/api/totals` - Energy totals (JSON)
- `/api/configuration` - Configuration (JSON)

## WebSocket Events

- `connect` - Client connected
- `disconnect` - Client disconnected
- `inverter_update` - Real-time data update
- `request_update` - Manual update request

## Development

The system consists of:
- `app.py` - Main Flask application
- `eg4_iotos_client.py` - EG4 communication client
- `templates/` - HTML templates
- `static/` - CSS and JavaScript files

## Testing

Test scripts included:
- `test_eg4_connection.py` - Test inverter connectivity
- `eg4_iotos_client.py` - Protocol discovery
- `eg4_monitor_alerts.py` - Monitoring with email alerts

## License

MIT License