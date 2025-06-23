#!/usr/bin/env python3
"""Analyze the data pattern to understand the protocol"""

import paramiko
from datetime import datetime
import json

def analyze_pattern():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # Get a snapshot of all current values
        print("=== Current values from EG4 ===")
        measurements = {
            "Battery voltage": "V",
            "Battery current": "A", 
            "Battery power": "W",
            "Battery state of charge": "%",
            "Battery temperature": "°C",
            "Grid voltage": "V",
            "Grid frequency": "Hz",
            "Grid power": "W",
            "AC output voltage": "V",
            "Inverter temperature": "°C",
            "Load power": "W",
            "PV voltage 1": "V",
            "PV voltage 2": "V",
            "PV voltage 3": "V",
            "PV current 1": "A",
            "PV current 2": "A",
            "PV current 3": "A",
            "PV power 1": "W",
            "PV power 2": "W",
            "PV power 3": "W",
            "PV power": "W total"
        }
        
        current_values = {}
        for measurement, unit in measurements.items():
            cmd = f"""sudo influx -database solar_assistant -execute 'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1' -format csv 2>/dev/null | tail -1"""
            output = ssh.exec_command(cmd)[1].read().decode().strip()
            if output and not output.startswith('name'):
                parts = output.split(',')
                if len(parts) >= 3:
                    value = parts[2]
                    current_values[measurement] = f"{value} {unit}"
        
        print("Current readings:")
        for k, v in current_values.items():
            print(f"  {k}: {v}")
        
        # Now let's see if Solar Assistant has any configuration about the protocol
        print("\n\n=== Looking for protocol configuration ===")
        
        # Check common config locations
        config_paths = [
            "/etc/solar-assistant/",
            "/opt/solar-assistant/",
            "/usr/share/solar-assistant/",
            "/var/lib/solar-assistant/",
            "/home/solar-assistant/"
        ]
        
        for path in config_paths:
            cmd = f"ls -la {path} 2>/dev/null"
            output = ssh.exec_command(cmd)[1].read().decode()
            if output and "total" in output:
                print(f"\nFound directory: {path}")
                print(output)
                
                # Check for config files
                cmd = f"find {path} -name '*.json' -o -name '*.yaml' -o -name '*.toml' -o -name '*.conf' 2>/dev/null | head -10"
                files = ssh.exec_command(cmd)[1].read().decode().strip()
                if files:
                    print(f"Config files: {files}")
        
        # Check if there's a modbus map or register definition
        print("\n=== Looking for register definitions ===")
        cmd = "find / -name '*register*.json' -o -name '*modbus*.json' -o -name '*protocol*.json' 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look in the grafana-sync directory more carefully
        print("\n=== Checking grafana-sync directory ===")
        cmd = "find /dev/shm/grafana-sync -type f -name '*.json' -o -name '*.config' | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        files = output.strip().split('\n')
        
        for f in files[:5]:
            if f:
                print(f"\nFile: {f}")
                cmd = f"cat {f} | head -50"
                content = ssh.exec_command(cmd)[1].read().decode()
                if 'inverter' in content.lower() or 'protocol' in content.lower():
                    print(content[:500])
        
        # Check for any Luxpower references (since it was originally connected to Luxpower)
        print("\n=== Checking for inverter type references ===")
        cmd = "ps aux | grep -v grep | grep -E 'luxpower|eg4|inverter'"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Final check - see if there are any Python scripts
        print("\n=== Looking for Python protocol scripts ===")
        cmd = "find / -name '*.py' -exec grep -l 'eg4\\|modbus\\|inverter.*protocol' {} \\; 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    analyze_pattern()