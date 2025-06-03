# EG4 18kPV Integration Summary

## Overview
This document summarizes the findings from analyzing EG4 18kPV inverter communication protocols.

## Key Findings

### 1. System Requirements
- **OS**: Linux system with Python 3.8+
- **Network**: Access to EG4 inverter on local network
- **Ports**: 8000 (IoTOS), 5000 (Web interface)

### 2. EG4 18kPV Communication
- **Dongle**: Micro/IoTOS TCP dongle
- **Local Port**: 8000 (IoTOS protocol)
- **Cloud Server**: 3.101.7.137 port 4346
- **Web Interface**: http://172.16.107.53/index_en.html (requires auth)

### 3. IoTOS Protocol Details
The IoTOS protocol on port 8000 uses a binary format:
- **Header**: Starts with 0xA1
- **Serial Number**: Found at offset 8 (e.g., "BA32401949a")
- **Device ID**: Found around offset 24 (e.g., "3352670252")
- **Command Format**: 4 bytes minimum (e.g., `\xa1\x1a\x05\x00`)

### 4. Working Commands
These commands successfully retrieve data from the EG4:
- `\xa1\x00\x00\x00` - Basic query
- `\xa1\x1a\x00\x00` - Status query
- `\xa1\x1a\x05\x00` - Extended status
- `\xa1\x01\x00\x00` - Command 01
- `\xa1\x02\x00\x00` - Command 02
- `\xa1\x03\x00\x00` - Command 03

## Implementation

### 1. Basic Connection
```python
import socket

# Connect to EG4
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('172.16.107.53', 8000))

# Send query
sock.send(b'\xa1\x1a\x05\x00')

# Receive response
response = sock.recv(4096)
```

### 2. Files Created
1. **eg4_iotos_client.py** - Full client implementation with protocol discovery
2. **eg4_monitor_alerts.py** - Monitoring system with email alerts
3. **decode_iotos_protocol.py** - Protocol analysis tool
4. **test_eg4_connection.py** - Connection testing utility

### 3. Email Alert Configuration
Add these to your `.env` file:
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=recipient@example.com
```

## Alert Types
The monitoring system can send alerts for:
- Connection lost
- Power outage
- Battery low (< 20%)
- High temperature (> 50°C)
- Inverter faults
- Daily summary (8 PM)

## Next Steps
1. **Protocol Documentation**: The IoTOS protocol needs proper documentation to decode all values
2. **Data Parsing**: Current parsing is based on common patterns; actual offsets may vary
3. **Integration**: Could integrate with other monitoring systems
4. **Testing**: Long-term testing needed to verify stability

## Running the Monitor
```bash
# Basic monitoring
python eg4_monitor_alerts.py

# Protocol analysis
python eg4_iotos_client.py

# Connection test
python test_eg4_connection.py
```

## Notes
- The EG4 responds to various command headers but always starts responses with 0xA1
- Data appears to be big-endian encoded
- The protocol seems to support both status queries and control commands
- Web interface on port 80 requires HTTP basic auth