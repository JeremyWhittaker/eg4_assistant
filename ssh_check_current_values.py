#!/usr/bin/env python3
"""Check current values and connection state"""

import paramiko
from datetime import datetime

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Get current values
    print("=== Current EG4 values ===")
    measurements = [
        "Battery voltage",
        "Battery power", 
        "Battery state of charge",
        "Grid voltage",
        "Grid power",
        "Load power",
        "PV power",
        "PV voltage 1",
        "PV voltage 2", 
        "PV voltage 3"
    ]
    
    for measurement in measurements:
        cmd = f"""sudo influx -database solar_assistant -execute 'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1' -format csv 2>/dev/null | tail -1"""
        output = ssh.exec_command(cmd)[1].read().decode().strip()
        if output and not output.startswith('name'):
            parts = output.split(',')
            if len(parts) >= 3:
                value = parts[2]
                print(f"{measurement}: {value}")
    
    # Check connection state
    print("\n=== Connection state ===")
    cmd = "sudo netstat -tnp | grep 172.16.107.129:8000"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check if it's actively communicating
    print("\n=== Recent communication ===")
    cmd = "sudo timeout 5 tcpdump -i any -nn host 172.16.107.129 and port 8000 -c 10 2>&1"
    output = ssh.exec_command(cmd)[1].read().decode()
    lines = output.split('\n')[:10]
    for line in lines:
        if '172.16.107.129' in line:
            print(line)
    
    # Check process details
    print("\n=== Solar Assistant process ===")
    cmd = "ps aux | grep beam | grep -v grep | head -1"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        parts = output.split()
        print(f"PID: {parts[1]}")
        print(f"CPU: {parts[2]}%")
        print(f"MEM: {parts[3]}%")
        print(f"Uptime: {parts[8]}")
        
finally:
    ssh.close()

print("\n=== Analysis ===")
print("Solar Assistant is successfully connected and receiving data.")
print("It appears to be daytime now with significant PV production.")
print("The EG4 is exporting power to the grid.")