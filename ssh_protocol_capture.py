#!/usr/bin/env python3
"""Capture exact protocol between Solar Assistant and EG4"""

import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # First get current values from InfluxDB
    print("=== Current values in Solar Assistant ===")
    measurements = ["Battery voltage", "Battery power", "Grid power", "Battery state of charge"]
    for m in measurements:
        cmd = f"""sudo influx -database solar_assistant -execute 'SELECT last(*) FROM "{m}"' -format csv 2>/dev/null | tail -1 | cut -d, -f3"""
        value = ssh.exec_command(cmd)[1].read().decode().strip()
        print(f"{m}: {value}")
    
    # Capture raw bytes with tcpdump
    print("\n=== Capturing raw protocol (10 seconds) ===")
    
    # Use tcpdump with hex output
    cmd = """sudo timeout 10 tcpdump -i any -X -s0 'host 172.16.107.129 and port 8000' 2>/dev/null | grep -A20 -B5 '0xa1.*0x1a\\|a1.*1a' | head -200"""
    output = ssh.exec_command(cmd)[1].read().decode()
    
    if not output:
        # Try different approach - capture with netcat
        print("Trying socat intercept...")
        
        # Kill Solar Assistant connection temporarily
        print("Stopping Solar Assistant momentarily...")
        ssh.exec_command("sudo systemctl stop solar-assistant")[1].read()
        time.sleep(2)
        
        # Use socat to intercept
        print("Setting up intercept...")
        cmd = """
        # Start socat in background to intercept
        sudo timeout 10 socat -x -v TCP-LISTEN:8001,reuseaddr,fork TCP:172.16.107.129:8000 2>&1 &
        SOCAT_PID=$!
        sleep 1
        
        # Connect to our intercept port
        (echo -ne '\xa1\x1a\x05\x00'; sleep 2) | nc localhost 8001 | xxd -g1
        
        # Kill socat
        sudo kill $SOCAT_PID 2>/dev/null
        """
        output = ssh.exec_command(cmd)[1].read().decode()
        print("Intercepted data:")
        print(output)
        
        # Restart Solar Assistant
        ssh.exec_command("sudo systemctl start solar-assistant")[1].read()
    else:
        print("Captured traffic:")
        print(output)
    
    # Try to read the actual Solar Assistant source
    print("\n=== Looking for inverter implementation ===")
    
    # Find Elixir beam files
    cmd = "find /opt/solar-assistant -name '*.beam' | xargs strings | grep -i 'a1.*1a\\|battery_voltage\\|parse' | head -50"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("Found in compiled code:")
        print(output)
    
    # Check for configuration or protocol files
    print("\n=== Protocol configuration ===")
    cmd = "find /opt/solar-assistant -name '*.json' -o -name '*.yaml' -o -name '*.toml' | xargs grep -l 'eg4\\|luxpower\\|protocol' 2>/dev/null | head -10"
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files:
        if file:
            print(f"\n{file}:")
            cmd = f"cat '{file}' | head -50"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Last resort - monitor the actual connection
    print("\n=== Monitoring active connection ===")
    cmd = """
    # Get the socket info
    sudo ss -tnp | grep 172.16.107.129:8000
    
    # Try to capture data being sent
    sudo timeout 5 tcpdump -i any -A 'host 172.16.107.129 and port 8000' 2>/dev/null | grep -A5 -B5 'BA32' | head -50
    """
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
finally:
    ssh.close()

print("\n=== NEXT STEPS ===")
print("Based on the captured data, we need to:")
print("1. Send command: a1 1a 05 00")
print("2. Parse response starting after header")
print("3. Use correct offsets for each field")