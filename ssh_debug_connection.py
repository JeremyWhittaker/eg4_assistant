#!/usr/bin/env python3
"""Debug why our connection fails but Solar Assistant works"""

import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Check if Solar Assistant is still getting data
    print("=== Is Solar Assistant still getting data? ===")
    cmd = """sudo influx -database solar_assistant -execute 'SELECT last(*) FROM "Battery power" WHERE time > now() - 1m' -format csv 2>/dev/null"""
    output = ssh.exec_command(cmd)[1].read().decode()
    if "Battery power" in output:
        print("YES - Solar Assistant is receiving current data")
    else:
        print("NO - No recent data")
    
    # Check the connection
    print("\n=== Active connection ===")
    cmd = "sudo ss -tnp | grep 172.16.107.129:8000"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Try to capture what Solar Assistant sends
    print("\n=== Capturing Solar Assistant traffic (10 seconds) ===")
    print("Installing tcpdump...")
    cmd = "sudo apt-get update && sudo apt-get install -y tcpdump >/dev/null 2>&1"
    ssh.exec_command(cmd)[1].read()
    
    print("Capturing packets...")
    cmd = "sudo timeout 10 tcpdump -i any -XX -s0 host 172.16.107.129 and port 8000 2>/dev/null | grep -A2 -B2 'a1 1a' | head -50"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("Found protocol data:")
        print(output)
    else:
        # Try different approach
        print("Trying strace...")
        cmd = "sudo timeout 5 strace -p 583 -e trace=write,send -xx 2>&1 | grep -A2 'a1.*1a' | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
    
    # Check if there's any special network configuration
    print("\n=== Network configuration ===")
    cmd = "ip addr show | grep 172.16"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check routing
    print("\n=== Route to EG4 ===")
    cmd = "ip route get 172.16.107.129"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Test if we can connect from Solar Assistant box
    print("\n=== Testing connection from Solar Assistant ===")
    cmd = "timeout 2 nc -v 172.16.107.129 8000 2>&1"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
finally:
    ssh.close()

print("\n=== CONCLUSION ===")
print("Check if:")
print("1. The EG4 only allows one connection at a time")
print("2. There's a specific source IP requirement")
print("3. The protocol requires immediate handshake")