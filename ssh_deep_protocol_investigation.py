#!/usr/bin/env python3
"""Deep protocol investigation - find exact commands and parsing"""

import paramiko
import time
import re

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # First, capture network traffic to see exact bytes
    print("=== Capturing EG4 protocol traffic ===")
    print("Installing tcpdump if needed...")
    ssh.exec_command("sudo apt-get update >/dev/null 2>&1 && sudo apt-get install -y tcpdump >/dev/null 2>&1")[1].read()
    
    print("Capturing 20 seconds of traffic...\n")
    cmd = """sudo timeout 20 tcpdump -i any -XX -s0 'host 172.16.107.129 and port 8000' 2>/dev/null | head -500"""
    output = ssh.exec_command(cmd)[1].read().decode()
    
    # Look for commands sent (usually starts with a1 1a)
    print("=== Commands sent to EG4 ===")
    lines = output.split('\n')
    for i, line in enumerate(lines):
        if 'a1 1a' in line or 'a11a' in line.lower():
            print(f"Found command at line {i}:")
            # Print this line and next few for context
            for j in range(max(0, i-2), min(len(lines), i+5)):
                print(lines[j])
            print()
    
    # Now look at the actual Solar Assistant code
    print("\n=== Finding Solar Assistant inverter code ===")
    
    # Find the main app directory
    cmd = "find /opt -name '*.ex' -o -name '*.exs' 2>/dev/null | grep -i 'inverter\\|modbus\\|eg4\\|luxpower' | head -20"
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    print(f"Found {len(files)} relevant files")
    
    # Look for protocol implementations
    for file in files[:10]:
        if file:
            print(f"\nChecking {file}:")
            cmd = f"grep -i 'a1\\|0xa1\\|<<0xa1\\|<<161' '{file}' 2>/dev/null | head -5"
            output = ssh.exec_command(cmd)[1].read().decode()
            if output:
                print(output)
    
    # Check for hex patterns in code
    print("\n=== Looking for hex command patterns ===")
    cmd = """find /opt/solar-assistant -name '*.ex' -exec grep -l '0xa1\\|0x1a\\|<<0xa1\\|<<0x1a' {} \\; 2>/dev/null | head -10"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:5]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -A5 -B5 '0xa1\\|0x1a' '{file}' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Look for response parsing
    print("\n=== Looking for response parsing ===")
    cmd = """find /opt/solar-assistant -name '*.ex' -exec grep -l 'parse_response\\|decode\\|battery_voltage\\|grid_power' {} \\; 2>/dev/null | head -10"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:3]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -A10 -B5 'battery_voltage\\|parse.*response' '{file}' | head -30"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Try to find actual command definitions
    print("\n=== Command definitions ===")
    cmd = """grep -r 'def.*command\\|@command\\|commands.*=' /opt/solar-assistant 2>/dev/null | grep -i 'eg4\\|luxpower\\|a1' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check process memory for commands
    print("\n=== Checking process for command bytes ===")
    cmd = """sudo timeout 5 strace -p 583 -e trace=write,send -xx 2>&1 | grep -E 'write|send' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
finally:
    ssh.close()

print("\n=== ANALYSIS NEEDED ===")
print("Need to find:")
print("1. Exact command bytes sent")
print("2. How responses are parsed") 
print("3. Offset calculations for each field")