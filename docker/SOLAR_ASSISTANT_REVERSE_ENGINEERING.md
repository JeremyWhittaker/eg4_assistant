# Solar Assistant Reverse Engineering Results

## Key Findings

### 1. Architecture
- **Framework**: Phoenix LiveView (Elixir)
- **Real-time Updates**: WebSocket at `/live/websocket?vsn=2.0.0`
- **Data Storage**: InfluxDB (local, port 8086 blocked externally)
- **Process**: Running as `influx-bridge` (beam.smp Erlang VM)
- **Config Issue**: Inverter configured as "luxpower" type, not EG4

### 2. Why Data Shows as Fake
- The logs show: `[inverter:luxpower] [error] Not connected. Retrying...`
- The inverter is misconfigured as "luxpower" type instead of EG4
- Solar Assistant is showing demo/fake data because it can't connect to the actual inverter

### 3. Data Flow
```
EG4 Inverter (172.16.107.129)
    ↓ (Expected: Modbus TCP)
Solar Assistant (can't connect - wrong protocol)
    ↓ (Fake/Demo data)
InfluxDB (stores fake data)
    ↓
Phoenix LiveView WebSocket (sends fake data)
    ↓
Web Browser (displays fake data)
```

### 4. Actual Data on Main Page (from HTML)
- Grid Voltage: 235.3 V
- Battery Power: 557 W (21% SOC)
- Solar PV: 7083 W
- Grid Power: 0 W
- Load Power: 7702 W

### 5. WebSocket Protocol
Phoenix LiveView uses a specific protocol:
- Message format: `[join_ref, ref, topic, event, payload]`
- Topics: "phoenix" for heartbeat, "lvu:session_id" for LiveView updates
- Events: "phx_join", "heartbeat", "phx_reply", etc.

## Solution

To fix the real Solar Assistant:
1. Change inverter type from "luxpower" to the correct EG4 protocol
2. Configure the correct Modbus registers for EG4 18kPV
3. Ensure port 502 is accessible on the inverter

For our implementation, we'll create a simpler solution that directly connects to the inverter.