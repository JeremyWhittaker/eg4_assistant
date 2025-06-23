#!/usr/bin/env python3
"""Trace how charts load their data in Solar Assistant"""

import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # First, let's see what happens when we access the charts endpoint
    print("=== Testing Chart Endpoints ===")
    cmd = "curl -s http://localhost/#charts 2>&1 | grep -E 'script|data-|api|fetch' | head -20"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for GraphQL or REST API endpoints
    print("\n=== API Endpoints in Routes ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -E 'scope.*"/api"|get.*"/data"|post.*"/query"' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check Phoenix LiveView hooks
    print("\n=== LiveView Hooks for Charts ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -B5 -A5 'Chart\\|chart\\|graph' | grep -E 'mount|handle_event|handle_info' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Monitor actual network traffic during chart load
    print("\n=== Starting Network Monitor ===")
    print("Capturing traffic for 20 seconds...")
    print("Please load the /#charts page in your browser NOW\n")
    
    # Start tcpdump in background
    cmd = """
    sudo timeout 20 tcpdump -i any -nn 'not port 22 and (port 80 or port 443 or port 8086)' 2>/dev/null | 
    grep -E 'GET|POST|HTTP|\.com|\.net|\.org' | head -30
    """
    output = ssh.exec_command(cmd)[1].read().decode()
    
    if output:
        print("Network activity detected:")
        print(output)
    else:
        print("No external HTTP/HTTPS traffic detected")
    
    # Check for JavaScript chart libraries
    print("\n\n=== Chart Libraries ===")
    cmd = """find /opt/solar-assistant/priv/static -name '*.js' | xargs grep -l 'Chart\\|chart\\|graph' 2>/dev/null | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for data fetching patterns
    print("\n\n=== Data Fetching Code ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -B3 -A3 'from.*influx\\|query.*measurement\\|select.*from' | head -30"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check for any scheduled data imports
    print("\n\n=== Scheduled Tasks ===")
    cmd = """ps aux | grep -E 'cron|timer|schedule' | grep -v grep"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for WebSocket data push
    print("\n\n=== WebSocket Data Push ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -E 'push.*socket|broadcast.*data' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Final check - see if there are any external data source configs
    print("\n\n=== External Data Sources ===")
    cmd = """find /opt/solar-assistant -type f \\( -name '*.toml' -o -name '*.yaml' -o -name '*.json' -o -name '*.config' \\) -exec grep -l 'url\\|endpoint\\|api' {} \\; 2>/dev/null | head -10"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:3]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -E 'url|endpoint|api|host' '{file}' | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
finally:
    ssh.close()

print("\n\n=== CONCLUSION ===")
print("If charts show data older than what the inverter stores,")
print("check the network capture above for external API calls.")
print("The dongle typically only stores recent data (days/weeks),")
print("so years of historical data must come from elsewhere.")