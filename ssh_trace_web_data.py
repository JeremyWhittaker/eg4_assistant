#!/usr/bin/env python3
"""Trace how the web interface gets its data"""

import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Monitor HTTP requests when accessing the web interface
    print("=== Setting up HTTP request monitoring ===")
    print("Open the Solar Assistant web interface in next 10 seconds...")
    print("Monitoring for API calls...\n")
    
    # Use tcpdump to capture HTTP traffic
    cmd = """sudo timeout 15 tcpdump -i lo -s0 -A 'tcp port 80 or tcp port 8086' 2>/dev/null | grep -E 'GET|POST|Host:|api|query' | head -50"""
    output = ssh.exec_command(cmd)[1].read().decode()
    
    if output:
        print("Captured HTTP traffic:")
        print(output)
    
    # Check if web interface queries InfluxDB directly
    print("\n\n=== InfluxDB Queries ===")
    cmd = """sudo timeout 5 tcpdump -i lo -s0 -A 'tcp port 8086' 2>/dev/null | grep -E 'SELECT|FROM|WHERE' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("InfluxDB queries detected:")
        print(output)
    
    # Look at the web server logs
    print("\n\n=== Web Server Access Logs ===")
    cmd = "sudo journalctl -u solar-assistant --no-pager | grep -E 'GET|POST' | tail -20"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
    # Check Phoenix routes
    print("\n\n=== Phoenix/Elixir Routes ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -l 'get.*"/"\\|post.*"/"\\|Router' 2>/dev/null | head -5"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:2]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -E 'get|post|live_view' '{file}' | grep '\"/' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check websocket connections
    print("\n\n=== WebSocket Connections ===")
    cmd = "sudo ss -tnp | grep ':80' | grep ESTAB"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Test direct InfluxDB query to compare values
    print("\n\n=== Direct InfluxDB Query Test ===")
    print("Current values from InfluxDB:")
    
    measurements = ["Battery power", "Grid power", "PV power", "Battery voltage"]
    for m in measurements:
        cmd = f"""sudo influx -database solar_assistant -execute 'SELECT last(*) FROM "{m}"' -format csv 2>/dev/null | tail -1"""
        output = ssh.exec_command(cmd)[1].read().decode()
        if output and not output.startswith('name'):
            parts = output.split(',')
            if len(parts) >= 3:
                print(f"{m}: {parts[2]}")
    
    # Check if there are any external API calls
    print("\n\n=== External API Configuration ===")
    cmd = """grep -r 'http://' /opt/solar-assistant 2>/dev/null | grep -v 'localhost\\|127.0.0.1\\|172.16' | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("External URLs found:")
        print(output)
    
    # Check environment for API keys
    print("\n\n=== API Keys/Tokens ===")
    cmd = "env | grep -E 'API|TOKEN|KEY|SECRET' | grep -v PATH"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("Found API credentials:")
        print(output)
        
finally:
    ssh.close()

print("\n\n=== CONCLUSION ===")
print("Based on the traces above:")
print("1. Check if web interface queries local InfluxDB (port 8086)")
print("2. Look for any external API calls")
print("3. Compare InfluxDB values with what's shown in web interface")