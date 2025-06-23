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

def check_influx_raw():
    """Check InfluxDB raw queries"""
    
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
        
        # First check if InfluxDB is running and what databases exist
        print("=== Checking InfluxDB Status ===")
        output = run_ssh_command(ssh, "influx -execute 'SHOW DATABASES'", use_sudo=True)
        print(output)
        
        # List all measurements
        print("\n=== All Measurements in solar_assistant DB ===")
        output = run_ssh_command(ssh, "influx -database solar_assistant -execute 'SHOW MEASUREMENTS'", use_sudo=True)
        print(output)
        
        # Check field keys for Battery power
        print("\n=== Field Keys for Battery power ===")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SHOW FIELD KEYS FROM \"Battery power\"'", 
            use_sudo=True)
        print(output)
        
        # Try different query formats
        print("\n=== Testing Different Query Formats ===")
        
        # Method 1: Direct query with CSV format
        print("Method 1: CSV format")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SELECT * FROM \"Battery power\" ORDER BY time DESC LIMIT 1' -format csv", 
            use_sudo=True)
        print(output)
        
        # Method 2: JSON format
        print("\nMethod 2: JSON format")
        output = run_ssh_command(ssh, 
            "influx -database solar_assistant -execute 'SELECT * FROM \"Battery power\" ORDER BY time DESC LIMIT 1' -format json", 
            use_sudo=True)
        print(output)
        
        # Method 3: Check all measurements that have data
        print("\n=== Checking Which Measurements Have Recent Data ===")
        measurements = [
            "Battery power", "Grid power", "PV power", "Load power",
            "Battery voltage", "Battery state of charge"
        ]
        
        for measurement in measurements:
            output = run_ssh_command(ssh, 
                f"influx -database solar_assistant -execute 'SELECT COUNT(*) FROM \"{measurement}\" WHERE time > now() - 1h'", 
                use_sudo=True)
            print(f"\n{measurement}:")
            print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    check_influx_raw()