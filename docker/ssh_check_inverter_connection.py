#!/usr/bin/env python3
"""Check how Solar Assistant connects to the inverter"""

import paramiko
import time

# Connection details
HOST = '172.16.106.13'
USERNAME = 'solar-assistant'
PASSWORD = 'solar123'

# Create SSH client
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # Connect
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=10)
    print("Connected successfully!")
    
    # Commands to check inverter connection
    commands = [
        "sudo netstat -antp | grep -E '(172.16.107|ESTABLISHED)' | grep -v ssh",
        "sudo lsof -i -n | grep -E '(172.16.107|ESTABLISHED)' | grep -v ssh",
        "ps aux | grep -E '(modbus|influx|eg4|inverter)' | grep -v grep",
        "sudo tcpdump -i any -c 10 -n host 172.16.107.129 2>/dev/null || echo 'No traffic to inverter'"
    ]
    
    for cmd in commands:
        print(f"\n{'='*60}")
        print(f"Running: {cmd}")
        print('='*60)
        
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        if output:
            print(output)
        if error:
            print(f"Error: {error}")
        
        time.sleep(1)
    
finally:
    ssh.close()
    print("\nConnection closed.")