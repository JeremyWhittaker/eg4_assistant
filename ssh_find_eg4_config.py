#!/usr/bin/env python3
"""Find EG4 configuration and protocol details"""

import paramiko
import json

def find_config():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # Find config files
        print("=== Looking for inverter configuration ===")
        cmd = "sudo find /opt /usr/local /etc /home -name '*.json' -o -name '*.toml' -o -name '*.conf' 2>/dev/null | xargs grep -l '172.16.107.129\\|eg4\\|EG4' 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check Elixir application config
        print("\n=== Checking application environment ===")
        cmd = "sudo cat /proc/583/environ | tr '\\0' '\\n' | grep -E 'CONFIG|INVERTER|EG4|PORT'"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look for register mappings
        print("\n=== Looking for register mappings ===")
        cmd = "sudo find /usr/local/bin /opt -type f -exec grep -l 'register\\|modbus\\|0x' {} \\; 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check what exact query is being sent
        print("\n=== Monitoring queries (5 seconds) ===")
        # Create a simple packet capture
        cmd = """sudo timeout 5 sh -c '
        exec 3<>/dev/tcp/172.16.107.129/8000
        while true; do
            if read -t 0.1 -r line <&3; then
                echo "Received: $(echo "$line" | xxd -p)"
            fi
        done
        ' 2>&1 | head -10"""
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check for any documentation
        print("\n=== Looking for protocol documentation ===")
        cmd = "find /opt /usr/local -name '*.md' -o -name '*.txt' -o -name 'README*' 2>/dev/null | xargs grep -l 'protocol\\|register\\|modbus' 2>/dev/null | head -5"
        output = ssh.exec_command(cmd)[1].read().decode()
        if output:
            print(f"Found docs: {output}")
        
        # Get more info about the data format
        print("\n=== Checking data format in InfluxDB ===")
        # Get raw data points
        cmd = """sudo influx -database solar_assistant -execute 'SELECT * FROM "Battery power" ORDER BY time DESC LIMIT 1' -format json"""
        output = ssh.exec_command(cmd)[1].read().decode()
        if output:
            try:
                data = json.loads(output)
                print(json.dumps(data, indent=2))
            except:
                print(output[:500])
        
        # See if we can find the actual binary
        print("\n=== Solar Assistant binary info ===")
        cmd = "file /usr/local/bin/solar-assistant"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check for any modbus configuration
        print("\n=== Checking for Modbus configuration ===")
        cmd = "grep -r 'holding_register\\|input_register\\|coil\\|function_code' /opt /etc 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    find_config()