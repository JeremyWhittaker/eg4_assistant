#!/usr/bin/env python3
"""
Solar Assistant Linux Image Analysis Results
===========================================

## Key Findings

### 1. System Architecture
- Based on Elixir/Phoenix framework
- Uses Grafana for data visualization with custom dashboards
- MQTT broker (Mosquitto) running on default port 1883
- Modbus library (libmodbus) for inverter communication

### 2. User & System
- Main user: solar-assistant (UID 1000)
- Home directory: /home/solar-assistant
- System service: solar-assistant.service
- Web interface served on port 80/443
- Local IP: 10.0.0.5

### 3. Grafana Configuration
- Custom dashboard path: /etc/grafana/solar-assistant/dashboards/charts.json
- Dashboard folder: SolarAssistant
- Root URL configured with /grafana prefix
- Datasources configured for time series data

### 4. Network & Communication
- MQTT: mosquitto service
- Modbus: libmodbus for RS485/TCP communication
- API endpoint found: http://127.0.0.1/api/v1/network

### 5. Key Services
- grafana-server
- mosquitto (MQTT broker)
- solar-assistant (main application)

## Next Steps for Deeper Analysis

1. Mount the image to explore actual files
2. Search for:
   - /etc/grafana/solar-assistant/
   - /home/solar-assistant/
   - Phoenix/Elixir app structure
   - Web assets and JavaScript files
   - API route definitions
   - Database schema
   - MQTT topics structure
"""

import subprocess
import re

def search_image(pattern, description, max_results=50):
    """Search for patterns in the linux_partition.img file"""
    print(f"\n=== Searching for: {description} ===")
    try:
        cmd = f"strings /home/jeremy/src/solar_assistant/linux_partition.img | grep -E '{pattern}' | head -{max_results}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        else:
            print("No results found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Additional search patterns to explore
    searches = [
        ("beam|\.beam|erlang", "Erlang BEAM files"),
        ("priv/static|app\.js|app\.css", "Phoenix static assets"),
        ("_build/prod|releases", "Elixir release paths"),
        ("config/prod\\.exs|config/runtime\\.exs", "Elixir config files"),
        ("Repo\\.|Ecto\\.", "Database/Ecto references"),
        ("defmodule|def |defp ", "Elixir module definitions"),
        ("plug |router |pipeline", "Phoenix router patterns"),
        ("socket\\.js|channel\\.js", "Phoenix channels/websockets"),
        ("solar_assistant_web|SolarAssistantWeb", "Phoenix web module"),
        ("mqtt_topic|mqtt_publish", "MQTT topic patterns"),
    ]
    
    for pattern, desc in searches:
        search_image(pattern, desc)