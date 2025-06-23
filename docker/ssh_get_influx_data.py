#!/usr/bin/env python3
import paramiko
import json

def run_ssh_command(ssh, command, use_sudo=False):
    """Run command via SSH and return output"""
    if use_sudo:
        command = f"echo 'solar123' | sudo -S {command}"
    
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    return output

def get_influx_data():
    """Get real values from Solar Assistant InfluxDB"""
    
    # SSH connection details
    host = "172.16.106.13"
    username = "solar-assistant"
    password = "solar123"
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=username, password=password)
        print("Connected to Solar Assistant\n")
        
        data = {}
        
        # Query each measurement individually
        measurements = [
            ("Battery power", "battery_power"),
            ("Battery voltage", "battery_voltage"),
            ("Battery state of charge", "battery_soc"),
            ("Battery temperature", "battery_temp"),
            ("Grid power", "grid_power"),
            ("Grid voltage", "grid_voltage"),
            ("Grid frequency", "grid_frequency"),
            ("PV power", "pv_power"),
            ("Load power", "load_power"),
            ("Inverter temperature", "inverter_temp"),
            ("AC output voltage", "ac_output_voltage"),
            ("Load power essential", "load_essential"),
            ("Load power non-essential", "load_nonessential")
        ]
        
        print("=== Getting Real-Time Values ===")
        for measurement, key in measurements:
            cmd = f'influx -database solar_assistant -execute "SELECT LAST(combined) FROM \\"{measurement}\\"" -format csv'
            output = run_ssh_command(ssh, cmd, use_sudo=True)
            
            # Parse CSV output
            lines = output.strip().split('\n')
            if len(lines) > 1:  # Has header and data
                try:
                    data_line = lines[1]  # Second line is data
                    parts = data_line.split(',')
                    if len(parts) >= 3:  # time,last,measurement
                        value = float(parts[1])
                        data[key] = value
                        print(f"{key}: {value}")
                except:
                    pass
        
        # Get current load from the web page (if accessible)
        print("\n=== Checking Web Interface Values ===")
        output = run_ssh_command(ssh, "curl -s http://localhost/", use_sudo=False)
        
        # Try to extract values from the HTML using the DOM IDs we found
        import re
        patterns = {
            'load-value': r'id="load-value"[^>]*>([0-9.]+)\s*W',
            'pv-value': r'id="pv-value"[^>]*>([0-9.]+)\s*W',
            'grid-value': r'id="grid-value"[^>]*>([0-9.-]+)\s*W',
            'battery-value': r'id="battery-value"[^>]*>([0-9.]+)\s*W',
            'battery-soc': r'id="battery-soc"[^>]*>([0-9]+)%',
            'grid-voltage': r'id="grid-voltage"[^>]*>([0-9.]+)\s*V',
        }
        
        web_data = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                web_data[key] = match.group(1)
                print(f"Web {key}: {match.group(1)}")
        
        # Combine data
        print(f"\n=== Complete Data ===")
        complete_data = {
            'influxdb': data,
            'web_interface': web_data,
            'timestamp': run_ssh_command(ssh, "date -Iseconds").strip()
        }
        
        print(json.dumps(complete_data, indent=2))
        
        # Save to file
        with open('/home/jeremy/src/solar_assistant/docker/real_solar_data.json', 'w') as f:
            json.dump(complete_data, f, indent=2)
        
        return complete_data
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        ssh.close()

if __name__ == "__main__":
    get_influx_data()