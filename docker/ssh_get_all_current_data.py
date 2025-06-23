#!/usr/bin/env python3
import paramiko
import json
import re

def run_ssh_command(ssh, command, use_sudo=False):
    """Run command via SSH and return output"""
    if use_sudo:
        command = f"echo 'solar123' | sudo -S {command}"
    
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    if error and not error.startswith('[sudo]'):
        print(f"Error: {error}")
    
    return output

def parse_influx_output(output):
    """Parse InfluxDB query output to get the most recent value"""
    lines = output.strip().split('\n')
    if len(lines) > 2:  # Has header and data
        try:
            # The data line is usually the 3rd line (after name: and header)
            data_line = lines[2]
            parts = data_line.split()
            if len(parts) >= 2:
                return float(parts[1])
        except:
            pass
    return None

def get_all_current_data():
    """Get all current data from Solar Assistant"""
    
    # SSH connection details
    host = "172.16.106.13"
    username = "solar-assistant"
    password = "solar123"
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=username, password=password)
        print("Connected successfully!\n")
        
        data = {}
        
        # Get all measurements
        measurements = [
            ("Battery power", "battery_power"),
            ("Battery voltage", "battery_voltage"),
            ("Battery current", "battery_current"),
            ("Battery state of charge", "battery_soc"),
            ("Battery temperature", "battery_temp"),
            ("Grid power", "grid_power"),
            ("Grid voltage", "grid_voltage"),
            ("Grid frequency", "grid_frequency"),
            ("PV power", "pv_power"),
            ("PV power 1", "pv1_power"),
            ("PV power 2", "pv2_power"),
            ("PV voltage 1", "pv1_voltage"),
            ("PV voltage 2", "pv2_voltage"),
            ("Load power", "load_power"),
            ("Load power essential", "load_power_essential"),
            ("Inverter temperature", "inverter_temp"),
            ("AC output voltage", "ac_output_voltage")
        ]
        
        print("=== Getting Current Values from InfluxDB ===")
        for measurement, key in measurements:
            output = run_ssh_command(ssh, 
                f"influx -database solar_assistant -execute 'SELECT * FROM \"{measurement}\" ORDER BY time DESC LIMIT 1' 2>/dev/null", 
                use_sudo=True)
            value = parse_influx_output(output)
            if value is not None:
                data[key] = value
                print(f"{key}: {value}")
        
        # Get Load voltage (might be same as AC output)
        print("\n=== Checking for Load Voltage ===")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SHOW MEASUREMENTS' | grep -i voltage", 
            use_sudo=True)
        print("Available voltage measurements:")
        print(output)
        
        # Save the data
        print("\n=== Complete Current Data ===")
        print(json.dumps(data, indent=2))
        
        # Write to file for our system
        with open('/home/jeremy/src/solar_assistant/docker/solar_assistant_real_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\nData saved to solar_assistant_real_data.json")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    get_all_current_data()