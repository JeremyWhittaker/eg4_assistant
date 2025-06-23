#!/usr/bin/env python3
import paramiko
import json

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

def find_real_data():
    """Find where Solar Assistant stores its real data"""
    
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
        
        # Check InfluxDB for real data
        print("=== Checking InfluxDB for Recent Data ===")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SELECT * FROM \"Battery power\" ORDER BY time DESC LIMIT 5' 2>/dev/null || echo 'InfluxDB query failed'", 
            use_sudo=True)
        print(output)
        
        print("\n=== Checking Grid Power ===")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SELECT * FROM \"Grid power\" ORDER BY time DESC LIMIT 5' 2>/dev/null", 
            use_sudo=True)
        print(output)
        
        print("\n=== Checking PV Power ===")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SELECT * FROM \"PV power\" ORDER BY time DESC LIMIT 5' 2>/dev/null", 
            use_sudo=True)
        print(output)
        
        print("\n=== Checking Battery SOC ===")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SELECT * FROM \"Battery state of charge\" ORDER BY time DESC LIMIT 5' 2>/dev/null", 
            use_sudo=True)
        print(output)
        
        # Check for any runtime data files
        print("\n=== Looking for Runtime Data Files ===")
        output = run_ssh_command(ssh, "find /dev/shm -name '*.json' -o -name '*.dat' -o -name '*.db' 2>/dev/null | head -20", use_sudo=True)
        print(output)
        
        # Check process memory for data
        print("\n=== Checking Process Environment ===")
        output = run_ssh_command(ssh, "cat /proc/583/cmdline | tr '\\0' ' ' | grep -o 'config.*runtime' | head -1", use_sudo=True)
        if output.strip():
            config_file = output.strip()
            print(f"Found config: {config_file}")
            
            # Try to read the runtime config
            output = run_ssh_command(ssh, f"cat /dev/shm/*/{config_file} 2>/dev/null | head -100", use_sudo=True)
            print(output)
        
        # Check for Phoenix channel state
        print("\n=== Looking for Phoenix Channel State ===")
        output = run_ssh_command(ssh, "find /dev/shm -name '*.beam' -o -name '*.dets' 2>/dev/null | head -10", use_sudo=True)
        print(output)
        
        # Check if there's a REST API endpoint
        print("\n=== Checking for Internal API ===")
        output = run_ssh_command(ssh, "netstat -tlnp 2>/dev/null | grep 583 | grep -v ':80'", use_sudo=True)
        print(output)
        
        # Try to access Phoenix internal port
        print("\n=== Checking Phoenix Port 4000 ===")
        output = run_ssh_command(ssh, "curl -s http://localhost:4000/api/live_data 2>/dev/null || echo 'No API on 4000'")
        print(output)
        
        # Check MQTT for real data
        print("\n=== Checking MQTT Messages ===")
        output = run_ssh_command(ssh, "timeout 5 mosquitto_sub -h localhost -t '#' -v 2>&1 | head -20 || echo 'MQTT check failed'")
        print(output)
        
        # Look for WebSocket data
        print("\n=== Checking for WebSocket Data Files ===")
        output = run_ssh_command(ssh, "find /var/lib /tmp /dev/shm -name '*websocket*' -o -name '*channel*' 2>/dev/null | head -10", use_sudo=True)
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    find_real_data()