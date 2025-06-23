# Solar Assistant Web Interface Analysis

## Overview
Solar Assistant is a Phoenix/Elixir-based web application that provides real-time monitoring and control of solar inverters. Based on my analysis of http://172.16.109.214/, here are the key findings:

## 1. Web Technology Stack
- **Framework**: Phoenix LiveView (Elixir web framework)
- **Real-time Updates**: Uses Phoenix LiveView WebSocket connections for real-time data updates
- **Session Management**: Cookie-based authentication with CSRF tokens
- **Charts**: Integrated Grafana dashboards for data visualization

## 2. API Endpoints and Data Format

### Phoenix LiveView WebSocket
- Solar Assistant uses Phoenix LiveView for real-time updates
- WebSocket endpoint: `/live/websocket` (standard Phoenix LiveView)
- Data format: Phoenix LiveView protocol (binary or JSON messages)
- Session-based authentication required

### Key Pages/Routes
- `/` - Dashboard with real-time data
- `/power` - Power management
- `/configuration` - System configuration
- `/inverter/status` - Inverter status
- `/inverter/settings` - Inverter settings
- `/battery/status` - Battery status
- `/grid/status` - Grid status
- `/totals` - Energy totals

### Data Available on Dashboard
```
- Inverter Mode: "Solar/Grid mode"
- Grid Voltage: 240.6 V
- Battery SOC: 62%
- Battery Change Rate: 25%/hr
- Load: 1261 W
- Solar PV: 12.7 kW
- Grid: -3421 W (feeding back to grid)
- Battery: 7587 W (charging)
```

## 3. MQTT Integration
- MQTT broker is available on port 1883
- Configuration available at `/configuration/mqtt`
- Topic structure likely follows: `solar_assistant/[device]/[metric]`

## 4. EG4 Inverter Communication

### Connection Details
- **Inverter IP**: 172.16.107.129
- **Device ID**: BA32401949
- **Interface**: Local network
- **Current Status**: "Timeout. Retrying..." (communication issues)

### Protocol Analysis
Based on the configuration options found, Solar Assistant supports multiple protocols:
- Modbus RS232/485
- Serial RS232/485
- CAN bus
- Various BMS protocols (Daly, JBD, JK, etc.)

For the EG4 inverter connected via network:
- **HTTP Interface**: Available on port 80 (requires authentication - admin:admin)
- **Web Interface**: Chinese language interface, appears to be IoT/monitoring system
- **Modbus TCP**: Port 502 is closed (not available)
- The device ID "BA32401949" appears to be the inverter's serial number
- Solar Assistant is experiencing communication timeouts with the inverter

## 5. Authentication
- Cookie-based sessions
- CSRF protection enabled
- Session cookie: `_solar_assistant_key`

## 6. Data Flow Architecture
```
EG4 Inverter (172.16.107.129)
    ↓ (Modbus TCP)
Solar Assistant (172.16.109.214)
    ↓ (Phoenix LiveView WebSocket)
Web Browser (Real-time updates)
    ↓ (MQTT - optional)
External systems
```

## 7. How to Access the Data

### Option 1: MQTT (Recommended)
1. Connect to MQTT broker at 172.16.109.214:1883
2. Subscribe to topics (need to determine exact topic structure)
3. Parse JSON messages for real-time data

### Option 2: WebSocket (Phoenix LiveView)
1. Authenticate and get session cookie
2. Connect to Phoenix LiveView WebSocket
3. Handle Phoenix protocol messages

### Option 3: Direct Modbus Connection
1. Connect directly to EG4 inverter at 172.16.107.129:502
2. Use Modbus TCP protocol
3. Query standard Modbus registers for inverter data

## 8. Recommended Approach for Integration

For your Solar Assistant server implementation, I recommend:

1. **Use MQTT as the primary data source**
   - Solar Assistant already publishes data to MQTT
   - Standard protocol, easy to integrate
   - Real-time updates

2. **Direct Modbus as backup**
   - Connect directly to the EG4 inverter
   - Use when Solar Assistant is unavailable
   - More control over polling frequency

3. **Data points to collect**:
   - Grid voltage/current/power
   - Solar PV voltage/current/power
   - Battery voltage/current/power/SOC
   - Load power
   - Inverter mode/status
   - Temperature readings
   - Daily/monthly energy totals

## Next Steps

1. Configure MQTT in Solar Assistant web interface
2. Determine exact MQTT topic structure
3. Implement MQTT client in your server
4. Add Modbus TCP client as backup data source
5. Store data in InfluxDB with proper tags and fields