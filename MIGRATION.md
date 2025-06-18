# Migration Guide

This guide helps you migrate from existing Solar Assistant installations to the new Docker-based system.

## Table of Contents
- [From EG4 Assistant V1/V2](#from-eg4-assistant-v1v2)
- [From Solar Assistant Pi Image](#from-solar-assistant-pi-image)
- [From Other Systems](#from-other-systems)
- [Data Migration](#data-migration)
- [Configuration Migration](#configuration-migration)

## From EG4 Assistant V1/V2

### Step 1: Export Existing Data

#### Export from V1 (app.py)
```bash
cd eg4_assistant
python export_v1_data.py
```

Create `export_v1_data.py`:
```python
import sqlite3
import json
from datetime import datetime

# Connect to V1 database
conn = sqlite3.connect('eg4_data.db')
cursor = conn.cursor()

# Export settings
cursor.execute("SELECT * FROM settings")
settings = cursor.fetchall()

# Export historical data
cursor.execute("SELECT * FROM inverter_data ORDER BY timestamp")
data = cursor.fetchall()

# Create export
export = {
    'version': 'v1',
    'exported_at': datetime.now().isoformat(),
    'settings': settings,
    'data': data
}

with open('v1_export.json', 'w') as f:
    json.dump(export, f, indent=2)

print(f"Exported {len(data)} records to v1_export.json")
```

#### Export from V2 (app_v2.py)
```bash
cd eg4_assistant
python export_v2_data.py
```

### Step 2: Stop Old Service
```bash
# If running as systemd service
sudo systemctl stop eg4-assistant

# If running in screen/tmux
# Find and stop the process
ps aux | grep app.py
kill <PID>
```

### Step 3: Install Docker Version
```bash
cd ../docker
make install
```

### Step 4: Import Data
```bash
# Copy database directly
cp ../eg4_assistant/eg4_data.db data/db/solar_assistant.db

# Or import JSON export
python import_data.py v1_export.json
```

### Step 5: Update Configuration

Convert your `.env` settings to `config/config.yaml`:

Old `.env`:
```env
EG4_IP=192.168.1.100
EG4_WEB_IP=192.168.1.3
```

New `config.yaml`:
```yaml
inverters:
  - name: "EG4 Inverter"
    type: "eg4_18kpv"
    protocol: "iotos"
    host: "192.168.1.100"
    port: 8000
    enabled: true
```

### Step 6: Start Docker System
```bash
make up
```

## From Solar Assistant Pi Image

### Step 1: Access Pi System
```bash
# SSH into your Raspberry Pi
ssh solar@<pi-ip-address>
```

### Step 2: Export Configuration
```bash
# Find and backup configuration
sudo find / -name "*.conf" -o -name "*.yaml" -o -name "*.json" 2>/dev/null | grep solar
```

### Step 3: Export Database
```bash
# Common locations
/var/lib/solar-assistant/data.db
/home/solar-assistant/database.db
/opt/solar-assistant/solar.db

# Copy to accessible location
cp <database-path> /tmp/solar_backup.db
```

### Step 4: Transfer Files
```bash
# From your local machine
scp solar@<pi-ip>:/tmp/solar_backup.db ./
scp solar@<pi-ip>:/path/to/config ./
```

### Step 5: Import to Docker
```bash
# Place database in Docker volume
cp solar_backup.db docker/data/db/solar_assistant.db

# Convert configuration
python convert_pi_config.py config > docker/config/config.yaml
```

### Step 6: Update Network Settings
Since the Docker system runs on a different machine, update inverter IPs if needed.

## From Other Systems

### Home Assistant Integration
If migrating from Home Assistant with solar monitoring:

1. Export data using HA's backup feature
2. Extract energy statistics
3. Convert using provided script:
```bash
python convert_ha_data.py backup.tar > import.json
python import_data.py import.json
```

### OpenEnergyMonitor
1. Export data via EmonCMS API
2. Convert CSV to compatible format
3. Import using batch import tool

### SolarEdge/Enphase
1. Use manufacturer's API to export data
2. Convert to Solar Assistant format
3. Import historical data

## Data Migration

### Database Schema Mapping

#### V1 to Docker
```sql
-- V1 Schema
CREATE TABLE inverter_data (
    timestamp DATETIME,
    pv1_power REAL,
    pv2_power REAL,
    battery_power REAL,
    grid_power REAL,
    load_power REAL
);

-- Docker Schema (simplified)
CREATE TABLE realtime_data (
    id INTEGER PRIMARY KEY,
    inverter_id INTEGER,
    timestamp DATETIME,
    pv_power REAL,
    battery_power REAL,
    grid_power REAL,
    load_power REAL,
    data JSON
);
```

### Migration Script
```python
#!/usr/bin/env python3
import sqlite3
import json

def migrate_v1_to_docker(old_db, new_db):
    # Connect to databases
    old_conn = sqlite3.connect(old_db)
    new_conn = sqlite3.connect(new_db)
    
    # Create new schema
    new_conn.execute('''
        CREATE TABLE IF NOT EXISTS inverters (
            id INTEGER PRIMARY KEY,
            name TEXT,
            model TEXT,
            ip_address TEXT
        )
    ''')
    
    # Insert default inverter
    new_conn.execute(
        "INSERT INTO inverters (name, model, ip_address) VALUES (?, ?, ?)",
        ("Migrated EG4", "eg4_18kpv", "192.168.1.100")
    )
    
    # Migrate data
    old_cursor = old_conn.execute("SELECT * FROM inverter_data")
    for row in old_cursor:
        timestamp, pv1, pv2, battery, grid, load = row
        pv_total = (pv1 or 0) + (pv2 or 0)
        
        new_conn.execute('''
            INSERT INTO realtime_data 
            (inverter_id, timestamp, pv_power, battery_power, grid_power, load_power)
            VALUES (1, ?, ?, ?, ?, ?)
        ''', (timestamp, pv_total, battery, grid, load))
    
    new_conn.commit()
    print("Migration complete!")

if __name__ == "__main__":
    migrate_v1_to_docker("eg4_data.db", "solar_assistant.db")
```

## Configuration Migration

### Environment Variables to YAML

V1/V2 `.env`:
```env
EG4_IP=192.168.1.100
UPDATE_INTERVAL=5
MQTT_HOST=192.168.1.50
MQTT_PORT=1883
```

Docker `config.yaml`:
```yaml
system:
  update_interval: 5

inverters:
  - name: "EG4 Inverter"
    host: "192.168.1.100"

mqtt:
  enabled: true
  host: "192.168.1.50"
  port: 1883
```

### Service Configuration

Systemd to Docker:
```bash
# Old systemd service
sudo systemctl disable eg4-assistant

# New Docker service
cd docker
make install
make up
```

## Verification Steps

### 1. Check Data Integrity
```bash
# Count records in old system
sqlite3 old.db "SELECT COUNT(*) FROM inverter_data"

# Count records in new system
docker exec solar-assistant sqlite3 /data/db/solar_assistant.db \
  "SELECT COUNT(*) FROM realtime_data"
```

### 2. Verify Historical Data
Access http://localhost and check:
- Historical charts show old data
- Energy totals are preserved
- No gaps in data

### 3. Test Real-time Updates
- Ensure live data is updating
- Check all inverters are connected
- Verify MQTT publishing (if used)

## Rollback Plan

If migration fails:

### 1. Stop Docker System
```bash
docker-compose down
```

### 2. Restore Old System
```bash
# Restore V1/V2
cd eg4_assistant
python app.py  # or app_v2.py

# Restore systemd service
sudo systemctl start eg4-assistant
```

### 3. Investigate Issues
- Check migration logs
- Verify data formats
- Test with small data subset

## Common Issues

### Data Type Mismatches
- V1 used different column names
- Some fields may be NULL
- Timestamp formats may differ

### Network Changes
- Docker uses different network
- Update inverter firewall rules
- Check Docker network settings

### Performance
- Initial import may be slow
- Index historical data after import
- Optimize database if needed

## Support

For migration assistance:
1. Backup everything first
2. Test with small dataset
3. Check logs for errors
4. Open GitHub issue with details

Remember: Always backup your data before migration!