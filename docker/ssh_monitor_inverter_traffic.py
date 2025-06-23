#!/usr/bin/env python3
"""Monitor actual data exchange between Solar Assistant and inverter"""

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
    
    # Check current connections to inverter
    print("\n=== Current connections to inverter ===")
    stdin, stdout, stderr = ssh.exec_command("sudo netstat -antp | grep 172.16.107.129", get_pty=True)
    print(stdout.read().decode())
    
    # Monitor traffic with tcpdump
    print("\n=== Capturing 20 packets to/from inverter ===")
    stdin, stdout, stderr = ssh.exec_command(
        "sudo timeout 10 tcpdump -i any -c 20 -n -X host 172.16.107.129 2>&1", 
        get_pty=True
    )
    output = stdout.read().decode()
    print(output)
    
    # Check what process is using port 8000
    print("\n=== Process using connection to inverter ===")
    stdin, stdout, stderr = ssh.exec_command(
        "sudo netstat -antp | grep ':8000.*ESTABLISHED' | awk '{print $7}'", 
        get_pty=True
    )
    process_info = stdout.read().decode().strip()
    print(f"Process: {process_info}")
    
    if "beam.smp" in process_info:
        print("\nThis is the Erlang BEAM VM (Solar Assistant's runtime)")
        
    # Try to find configuration
    print("\n=== Looking for inverter configuration ===")
    stdin, stdout, stderr = ssh.exec_command(
        "sudo find /var/lib -name '*.conf' -o -name '*.config' -o -name '*.toml' 2>/dev/null | grep -v systemd | head -10", 
        get_pty=True
    )
    print(stdout.read().decode())
    
finally:
    ssh.close()
    print("\nConnection closed.")