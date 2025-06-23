#!/usr/bin/env python3
import paramiko
import json
import time
from datetime import datetime

def run_ssh_command(ssh, command, use_sudo=False):
    """Run command via SSH and return output"""
    if use_sudo:
        command = f"echo 'solar123' | sudo -S {command}"
    
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    return output

def extract_real_values():
    """Extract real values from Solar Assistant"""
    
    # SSH connection details
    host = "172.16.109.214"
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
        
        # Define measurements to extract
        measurements = [
            ("Battery power", "battery_power", "W"),
            ("Battery voltage", "battery_voltage", "V"),
            ("Battery current", "battery_current", "A"),
            ("Battery state of charge", "battery_soc", "%"),
            ("Battery temperature", "battery_temp", "°C"),
            ("Grid power", "grid_power", "W"),
            ("Grid voltage", "grid_voltage", "V"),
            ("Grid frequency", "grid_frequency", "Hz"),
            ("PV power", "pv_power", "W"),
            ("PV power 1", "pv1_power", "W"),
            ("PV power 2", "pv2_power", "W"),
            ("PV voltage 1", "pv1_voltage", "V"),
            ("PV voltage 2", "pv2_voltage", "V"),
            ("Load power", "load_power", "W"),
            ("Load power essential", "load_power_essential", "W"),
            ("Load power non-essential", "load_power_nonessential", "W"),
            ("AC output voltage", "ac_output_voltage", "V"),
            ("Inverter temperature", "inverter_temp", "°C")
        ]
        
        print("=== Extracting Real-Time Values ===")
        for measurement, key, unit in measurements:
            # Use JSON format for easier parsing
            cmd = f"influx -database solar_assistant -execute 'SELECT * FROM \"{measurement}\" ORDER BY time DESC LIMIT 1' -format json"
            output = run_ssh_command(ssh, cmd, use_sudo=True)
            
            try:
                result = json.loads(output)
                if result["results"][0].get("series"):
                    series = result["results"][0]["series"][0]
                    values = series["values"][0]
                    
                    # Get the field value (could be "combined" or "inverter_0")
                    if "combined" in series["columns"]:
                        idx = series["columns"].index("combined")
                        value = values[idx]
                    elif "inverter_0" in series["columns"]:
                        idx = series["columns"].index("inverter_0")
                        value = values[idx]
                    else:
                        continue
                    
                    data[key] = {
                        "value": value,
                        "unit": unit,
                        "timestamp": values[0]  # InfluxDB timestamp
                    }
                    print(f"{key}: {value} {unit}")
            except:
                pass
        
        # Calculate additional values
        if "battery_power" in data:
            battery_power = data["battery_power"]["value"]
            if battery_power < 0:
                data["battery_status"] = "charging"
                data["battery_charge_power"] = abs(battery_power)
            else:
                data["battery_status"] = "discharging"
                data["battery_discharge_power"] = battery_power
        
        # Determine system mode
        pv_power = data.get("pv_power", {}).get("value", 0)
        grid_power = data.get("grid_power", {}).get("value", 0)
        battery_power = data.get("battery_power", {}).get("value", 0)
        
        if pv_power > 100:
            data["system_mode"] = "Solar"
        elif grid_power < -100:
            data["system_mode"] = "Grid Export"
        elif battery_power > 100:
            data["system_mode"] = "Battery"
        else:
            data["system_mode"] = "Grid"
        
        # Add timestamp
        data["extraction_time"] = datetime.now().isoformat()
        
        # Save to file
        print("\n=== Saving Real Data ===")
        with open('/home/jeremy/src/solar_assistant/docker/solar_assistant_real_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data saved to solar_assistant_real_data.json")
        print(f"System Mode: {data['system_mode']}")
        print(f"Battery Status: {data.get('battery_status', 'N/A')}")
        
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        ssh.close()

if __name__ == "__main__":
    extract_real_values()