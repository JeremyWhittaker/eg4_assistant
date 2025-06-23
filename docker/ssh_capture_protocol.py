#!/usr/bin/env python3
"""Capture the actual protocol between Solar Assistant and EG4"""

import paramiko
import time
import re

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
    
    # Use strings command to check what data might be in memory
    print("\n=== Checking for protocol patterns ===")
    stdin, stdout, stderr = ssh.exec_command(
        "sudo timeout 5 strings /proc/$(pgrep -f beam.smp | head -1)/fd/* 2>/dev/null | grep -E '(modbus|eg4|inverter|172.16.107)' | head -20", 
        get_pty=True
    )
    print(stdout.read().decode())
    
    # Check open file descriptors
    print("\n=== Checking open connections ===")
    stdin, stdout, stderr = ssh.exec_command(
        "sudo ls -la /proc/$(pgrep -f beam.smp | head -1)/fd/ 2>/dev/null | grep -E 'socket|172.16' | head -10", 
        get_pty=True
    )
    print(stdout.read().decode())
    
    # Try to use strace to see what's being sent
    print("\n=== Attempting to trace network calls (10 seconds) ===")
    stdin, stdout, stderr = ssh.exec_command(
        "sudo timeout 10 strace -p $(pgrep -f beam.smp | head -1) -s 200 -e trace=network 2>&1 | grep -E '(send|recv|172.16.107)' | head -20", 
        get_pty=True
    )
    output = stdout.read().decode()
    if output:
        print(output)
    else:
        print("No strace output captured")
    
    # Check MQTT messages that might contain inverter data
    print("\n=== Checking MQTT topics ===")
    stdin, stdout, stderr = ssh.exec_command(
        "mosquitto_sub -h localhost -t '#' -C 5 -v 2>/dev/null || echo 'Could not subscribe to MQTT'", 
        get_pty=True
    )
    print(stdout.read().decode())
    
finally:
    ssh.close()
    print("\nConnection closed.")