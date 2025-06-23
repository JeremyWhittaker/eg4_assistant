# Solar Assistant Backend Configuration Analysis

## SSH Investigation Results

### System Information
- **Host**: 172.16.106.13
- **User**: solar-assistant / solar123
- **OS**: Debian GNU/Linux on Raspberry Pi (aarch64)
- **Kernel**: 6.6.31+rpt-rpi-v8

### Service Architecture
The Solar Assistant application is **NOT** running as a traditional "solar-assistant" service. Instead:

**Main Service**: `influx-bridge.service`
- **Status**: Active (running) since Mon 2025-06-16 21:49:01 UTC
- **Main PID**: 583 (beam.smp) - This is an **Erlang/Elixir BEAM virtual machine**
- **Service File**: `/etc/systemd/system/influx-bridge.service`
- **Post-Start Script**: `/usr/lib/influx-bridge/signal.sh --started`

### Application Location
**Key Finding**: The application runs from a **memory filesystem** (tmpfs):
- **Executable Path**: `/dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f6...`
- **Process Type**: Erlang BEAM VM (beam.smp)
- **Child Processes**: Multiple Erlang processes including `erl_child_setup`

### Web Interface
- **Framework**: Phoenix/Elixir application
- **Web Server**: Cowboy (Erlang HTTP server)
- **Port**: Standard HTTP (80)
- **Authentication**: Cookie-based session management
- **Session Cookie**: `_solar_assistant_key`

### Directory Structure Findings
```
/opt/ - Only contains pigpio (GPIO library for Pi)
/var/www/ - May contain web assets (needs verification)
/usr/lib/influx-bridge/ - Contains service scripts
/dev/shm/grafana-sync/ - Runtime application location
/etc/systemd/system/influx-bridge.service - Service definition
```

### Configuration Storage Hypothesis
Based on the architecture analysis, configuration is likely stored in:

1. **Database**: SQLite or embedded database in `/var/lib/` or memory
2. **Configuration Files**: JSON/YAML in `/etc/` or `/usr/lib/influx-bridge/`
3. **Environment Variables**: Set in systemd service file
4. **Runtime Configuration**: In Elixir application state (ETS tables, GenServer state)

### Inverter Configuration Location
The inverter IP (172.16.107.129) configuration could be in:
- Service configuration files
- Database records
- Elixir application configuration (config.exs or runtime.exs)
- Environment variables in systemd service

## Manual Investigation Commands Required

Since automated SSH didn't provide complete output, run these manually:

```bash
ssh solar-assistant@172.16.106.13
# Password: solar123

# Get complete service configuration
sudo systemctl cat influx-bridge.service

# Find configuration directories
sudo find /usr/lib/influx-bridge -type f 2>/dev/null
sudo ls -la /dev/shm/grafana-sync/ 2>/dev/null

# Look for database files
sudo find /var/lib -name '*.db' -o -name '*.sqlite*' 2>/dev/null

# Find configuration files
sudo grep -r "172.16.107.129" /usr/lib /etc /var 2>/dev/null

# Check for Elixir config
sudo find /usr -name '*.exs' 2>/dev/null
```

## Next Steps for Integration

1. **Locate Configuration API**: Find how Solar Assistant exposes configuration endpoints
2. **Database Schema**: Understand how inverter configurations are stored
3. **Authentication**: Determine how to authenticate with the web interface
4. **Configuration Format**: Understand the JSON/data structure for inverter configs
5. **Update Mechanism**: Find the API endpoint or method to update inverter settings

The key insight is that Solar Assistant uses a **Phoenix/Elixir architecture** running on the **BEAM VM**, not a traditional Python/Node.js application, which changes our integration approach significantly.