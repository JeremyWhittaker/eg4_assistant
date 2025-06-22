# EG4 Cloud Monitor Documentation

The EG4 Cloud Monitor provides comprehensive monitoring of EG4 inverters through the official cloud portal at monitor.eg4electronics.com.

## Features

- **Real-time Monitoring**: Live data updates every 30 seconds
- **Comprehensive Data**: All available inverter parameters and statistics
- **Multiple Display Modes**: Real-time compact view or detailed statistics
- **Historical Data**: Today's and lifetime energy statistics
- **Weather Integration**: Solar prediction and weather conditions
- **Command Line Interface**: Full control via command-line options
- **JSON Export**: Save data for analysis or integration

## Installation

### Prerequisites

```bash
# Install Python dependencies
pip install playwright python-dotenv

# Install Chromium browser
playwright install chromium
```

### Configuration

1. Create a `.env` file in the project root:
```env
EG4_MONITOR_USERNAME=your_username
EG4_MONITOR_PASSWORD=your_password
```

2. Ensure you have an account at monitor.eg4electronics.com with your inverter registered.

## Usage

### Basic Usage

The unified monitor script `eg4_monitor.py` provides all monitoring functionality:

```bash
# Run continuous real-time monitoring (default)
python3 eg4_monitor.py

# Run once and exit
python3 eg4_monitor.py --mode once

# Show detailed statistics
python3 eg4_monitor.py --display detailed

# Custom update interval (60 seconds)
python3 eg4_monitor.py --interval 60

# Save data to JSON file
python3 eg4_monitor.py --mode once --save-json
```

### Command Line Options

- `--mode`: `once` or `continuous` (default: continuous)
- `--display`: `realtime` or `detailed` (default: realtime)
- `--interval`: Update interval in seconds for continuous mode (default: 30)
- `--save-json`: Save data to JSON file (only works with --mode once)

### Display Modes

#### Real-time Mode (Default)
Compact, clean display optimized for continuous monitoring:
- Visual battery state indicator with charge/discharge status
- Power flow visualization
- Key statistics at a glance
- Weather and predictions

#### Detailed Mode
Comprehensive view similar to the web interface:
- Complete energy overview
- All system parameters
- Detailed battery BMS information
- Full historical statistics

## Data Available

### Real-time Data
- **Battery**: SOC, voltage, current, power, BMS status and limits
- **Solar**: Power, voltage, and current for up to 3 PV strings
- **Grid**: Power, voltage, frequency, current
- **Load**: Power consumption and percentage
- **Backup/EPS**: Status and power output
- **Generator**: Dry contact status

### Energy Statistics
- **Today**: Solar yield, consumption, grid import/export, battery charge/discharge
- **Lifetime**: Total generation, consumption, grid exchange
- **Distribution**: Percentage breakdown of solar usage (load, battery, export)

### System Information
- Inverter status and alarms
- System time
- Temperature
- Weather conditions and solar predictions

## Examples

### Basic Monitoring
```bash
# Start monitoring with default settings
python3 eg4_monitor.py
```

Output:
```
================================================================================
EG4 MONITOR - 2025-06-21 17:15:00
================================================================================

⚙️  SYSTEM: Normal Operation | Time: 2025-06-21 17:15:00

🔋 BATTERY
  [████████████████████████████████████████] 100% ↑ CHARGING
  Power:     500 W | Voltage: 53.5 V | Current: 9.3 A
  BMS Limits: Charge 120 A | Discharge 400 A
  BMS Status: Charge Allowed | Discharge Allowed

☀️  SOLAR
  PV1:     4500 W  (365.2 V, 12.3 A)
  PV2:      450 W  (310.5 V, 1.5 A)
  ────────────────────────────────────────
  Total:    4950 W

⚡ POWER FLOW
  Solar  →    4950 W
  Grid   ⇄       0 W  (240.1 V @ 60.00 Hz)
  Load   ←    2450 W  (35% of capacity)
  Battery ⇄     500 W
```

### Export Data for Analysis
```bash
# Run once and save to JSON
python3 eg4_monitor.py --mode once --save-json

# Output: eg4_data_20250621_171500.json
```

### Detailed Statistics View
```bash
# Show detailed view continuously
python3 eg4_monitor.py --display detailed
```

## Troubleshooting

### Login Issues
- Verify credentials in `.env` file
- Check if account works on monitor.eg4electronics.com
- Ensure inverter is registered to your account

### No Data Loading
- Check internet connection
- Verify inverter is online in the web portal
- Wait up to 30 seconds for initial data load
- Ensure only one connection at a time (close web browser)

### Performance
- Use `--interval 60` or higher for slower connections
- Monitor refreshes page every 5 minutes to ensure fresh data
- Consider using `--mode once` for periodic checks via cron

## Integration

### JSON Output Format
The `--save-json` option exports complete inverter data:

```json
{
  "battery": {
    "soc": "100",
    "voltage": "53.5",
    "power": "500",
    ...
  },
  "pv": {
    "pv1_power": "4500",
    "pv1_voltage": "365.2",
    ...
  },
  "grid_exchange": {
    "export_today": "45.5",
    "import_today": "0.0",
    ...
  }
}
```

### Automation
Use cron for periodic data collection:

```bash
# Run every hour and save data
0 * * * * /usr/bin/python3 /path/to/eg4_monitor.py --mode once --save-json
```

## Technical Details

- Uses Playwright for browser automation (handles JavaScript-heavy site)
- Waits for dynamic content to load before extracting data
- Automatic page refresh every 5 minutes in continuous mode
- Headless browser operation for server deployment
- Handles connection timeouts and retries gracefully

## Support

- Report issues on GitHub
- Check EG4 portal directly if data seems incorrect
- Monitor requires active internet connection
- One monitor instance per inverter account