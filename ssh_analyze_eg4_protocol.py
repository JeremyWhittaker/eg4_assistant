#!/usr/bin/env python3
"""Analyze how Solar Assistant communicates with EG4"""

import paramiko
import json

def analyze_eg4():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # Check what process has the connection
        print("=== Process with connection to EG4 ===")
        cmd = "sudo netstat -tnp | grep 172.16.107.129:8000"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Get the PID and check process details
        print("\n=== Process details ===")
        cmd = "sudo lsof -i :59430 2>/dev/null || sudo ss -tnp | grep 172.16.107.129"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check the influx-bridge process (Solar Assistant)
        print("\n=== Solar Assistant process info ===")
        cmd = "ps aux | grep influx-bridge | grep -v grep"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look for runtime config
        print("\n=== Runtime configuration ===")
        cmd = "sudo find /dev/shm -name '*config*' -type f 2>/dev/null | xargs grep -l '172.16.107' 2>/dev/null"
        output = ssh.exec_command(cmd)[1].read().decode()
        if output.strip():
            print(f"Config file: {output.strip()}")
            # Read the config
            cmd = f"sudo cat {output.strip()}"
            config = ssh.exec_command(cmd)[1].read().decode()
            print("Config content:")
            try:
                config_json = json.loads(config)
                print(json.dumps(config_json, indent=2))
            except:
                print(config[:500])
        
        # Check for any protocol libraries or modules
        print("\n=== Checking Solar Assistant modules ===")
        cmd = "cd /usr/local/bin && strings solar-assistant | grep -E 'modbus|eg4|iotos|protocol' | sort -u | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check recent data in InfluxDB
        print("\n=== Recent InfluxDB measurements ===")
        cmd = """sudo influx -database solar_assistant -execute 'SHOW MEASUREMENTS' | head -20"""
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Get a sample of recent data
        print("\n=== Sample battery power data ===")
        cmd = """sudo influx -database solar_assistant -execute 'SELECT * FROM "Battery power" ORDER BY time DESC LIMIT 5' -format csv"""
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look for any EG4 specific handling
        print("\n=== Checking for EG4 specific code ===")
        cmd = "grep -r 'eg4\\|EG4' /opt/solar-assistant /usr/local 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check if using Modbus
        print("\n=== Checking for Modbus usage ===")
        cmd = "sudo netstat -tlnp | grep -E '502|8000'"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    analyze_eg4()