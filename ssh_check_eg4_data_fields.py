#!/usr/bin/env python3
"""Check all data fields being collected from EG4"""

import paramiko
from datetime import datetime

def check_all_fields():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        print("=== ALL AVAILABLE MEASUREMENTS FROM EG4 ===\n")
        
        # Get all measurements with recent data
        measurements = [
            "AC output voltage",
            "Battery current", 
            "Battery power",
            "Battery state of charge",
            "Battery temperature",
            "Battery voltage",
            "Grid frequency",
            "Grid power",
            "Grid voltage",
            "Inverter temperature",
            "Load power",
            "Load power essential",
            "Load power non-essential",
            "PV current 1",
            "PV current 2", 
            "PV current 3",
            "PV power",
            "PV power 1",
            "PV power 2",
            "PV power 3",
            "PV voltage 1",
            "PV voltage 2",
            "PV voltage 3",
            "DC bus voltage",
            "Inverter current",
            "Inverter frequency",
            "Inverter power",
            "Backup battery voltage",
            "Main battery voltage"
        ]
        
        # Check each measurement
        found_measurements = {}
        for measurement in measurements:
            cmd = f"""sudo influx -database solar_assistant -execute 'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1' -format csv 2>/dev/null"""
            output = ssh.exec_command(cmd)[1].read().decode()
            
            if output and "name,time" in output:
                lines = output.strip().split('\n')
                if len(lines) > 1:
                    # Parse the CSV
                    headers = lines[0].split(',')
                    values = lines[1].split(',')
                    
                    if len(values) >= 3:
                        timestamp = values[1]
                        # Convert timestamp to readable format
                        try:
                            ts = int(timestamp) / 1e9
                            dt = datetime.fromtimestamp(ts)
                            time_str = dt.strftime('%H:%M:%S')
                        except:
                            time_str = "unknown"
                        
                        # Get the actual value
                        if len(values) > 2:
                            value = values[2]
                            found_measurements[measurement] = {
                                'value': value,
                                'time': time_str,
                                'fields': headers[2:] if len(headers) > 2 else []
                            }
        
        # Display all found measurements
        print("FOUND MEASUREMENTS:")
        print("-" * 60)
        for measurement, data in sorted(found_measurements.items()):
            print(f"{measurement:30} = {data['value']:>10} @ {data['time']}")
            if len(data['fields']) > 1:
                print(f"  Fields: {', '.join(data['fields'])}")
        
        # Check for any other measurements we might have missed
        print("\n\n=== ALL MEASUREMENTS IN DATABASE ===")
        cmd = "sudo influx -database solar_assistant -execute 'SHOW MEASUREMENTS'"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Get field keys for important measurements
        print("\n=== FIELD KEYS FOR KEY MEASUREMENTS ===")
        for measurement in ["Battery power", "Grid power", "PV power", "Load power"]:
            cmd = f"""sudo influx -database solar_assistant -execute 'SHOW FIELD KEYS FROM "{measurement}"'"""
            output = ssh.exec_command(cmd)[1].read().decode()
            if output:
                print(f"\n{measurement}:")
                print(output)
        
        # Check tag keys
        print("\n=== TAG KEYS (for multiple inverters) ===")
        cmd = """sudo influx -database solar_assistant -execute 'SHOW TAG KEYS FROM "Battery power"'"""
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    check_all_fields()