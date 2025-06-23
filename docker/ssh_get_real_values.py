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
    return output

def get_real_values():
    """Get real values from Solar Assistant InfluxDB"""
    
    # SSH connection details
    host = "172.16.109.214"
    username = "solar-assistant"
    password = "solar123"
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=username, password=password)
        print("Connected to Solar Assistant\n")
        
        # Get the most recent values with a single query
        query = """
        influx -database solar_assistant -execute "
        SELECT LAST(combined) FROM \"Battery power\";
        SELECT LAST(combined) FROM \"Battery voltage\";
        SELECT LAST(combined) FROM \"Battery state of charge\";
        SELECT LAST(combined) FROM \"Grid power\";
        SELECT LAST(combined) FROM \"Grid voltage\";
        SELECT LAST(combined) FROM \"PV power\";
        SELECT LAST(combined) FROM \"Load power\";
        SELECT LAST(combined) FROM \"Grid frequency\";
        SELECT LAST(combined) FROM \"Inverter temperature\";
        SELECT LAST(combined) FROM \"Battery temperature\";
        SELECT LAST(combined) FROM \"AC output voltage\";
        "
        """
        
        output = run_ssh_command(ssh, query, use_sudo=True)
        print("Raw InfluxDB output:")
        print(output)
        print("\n" + "="*50 + "\n")
        
        # Parse the output
        data = {}
        current_measurement = None
        
        for line in output.split('\n'):
            if line.startswith('name:'):
                current_measurement = line.split('name:')[1].strip()
            elif line and not line.startswith('time') and not line.startswith('----') and current_measurement:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        value = float(parts[1])
                        # Map measurement names to keys
                        key_map = {
                            'Battery power': 'battery_power',
                            'Battery voltage': 'battery_voltage',
                            'Battery state of charge': 'battery_soc',
                            'Grid power': 'grid_power',
                            'Grid voltage': 'grid_voltage',
                            'PV power': 'pv_power',
                            'Load power': 'load_power',
                            'Grid frequency': 'grid_frequency',
                            'Inverter temperature': 'inverter_temp',
                            'Battery temperature': 'battery_temp',
                            'AC output voltage': 'ac_output_voltage'
                        }
                        if current_measurement in key_map:
                            data[key_map[current_measurement]] = value
                            print(f"{key_map[current_measurement]}: {value}")
                    except:
                        pass
        
        # Calculate additional values
        if 'battery_power' in data and data['battery_power'] < 0:
            data['battery_status'] = 'charging'
            data['battery_charge_rate'] = abs(data['battery_power']) / 50  # Approximate
        else:
            data['battery_status'] = 'discharging'
            data['battery_charge_rate'] = 0
        
        # Determine inverter mode
        if data.get('pv_power', 0) > 100:
            data['inverter_mode'] = 'Solar/Grid mode'
        elif data.get('battery_power', 0) < -100:
            data['inverter_mode'] = 'Battery mode'
        else:
            data['inverter_mode'] = 'Grid mode'
        
        print(f"\n=== Parsed Data ===")
        print(json.dumps(data, indent=2))
        
        # Save to file
        with open('/home/jeremy/src/solar_assistant/docker/real_solar_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        ssh.close()

if __name__ == "__main__":
    get_real_values()