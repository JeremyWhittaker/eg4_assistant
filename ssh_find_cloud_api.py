#!/usr/bin/env python3
"""Find EG4 cloud API connections for historical data"""

import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Check for SSL certificates that might indicate cloud connections
    print("=== SSL Certificates ===")
    cmd = "find /opt/solar-assistant -name '*.pem' -o -name '*.crt' -o -name '*.key' | grep -v localhost | head -10"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for HTTPS connections
    print("\n=== HTTPS Connections (port 443) ===")
    cmd = "sudo netstat -tnp | grep ':443' | grep ESTABLISHED"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check DNS cache for EG4 domains
    print("\n=== DNS Resolution History ===")
    cmd = "sudo systemd-resolve --statistics | grep -A20 'Current Cache'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for API endpoints in compiled beam files
    print("\n=== Searching compiled code for APIs ===")
    cmd = """find /opt/solar-assistant -name '*.beam' -exec strings {} \\; | grep -E 'https://|monitor\\.|api\\.|cloud\\.' | grep -v localhost | sort -u | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check for stored API credentials
    print("\n=== Configuration files with credentials ===")
    cmd = "find /opt/solar-assistant -name '*.json' -o -name '*.toml' -o -name '*.yaml' -o -name '*.config' | xargs grep -l 'token\\|api_key\\|secret\\|credential' 2>/dev/null | head -10"
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:3]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -E 'token|api_key|secret|url' '{file}' | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Monitor network traffic for cloud connections
    print("\n=== Monitoring for cloud connections (20 seconds) ===")
    cmd = """sudo timeout 20 tcpdump -n 'not src net 172.16.0.0/16 and not dst net 172.16.0.0/16 and not net 127.0.0.0/8' 2>/dev/null | grep -v ARP | head -30"""
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("External traffic detected:")
        print(output)
    
    # Check systemd timer units for scheduled syncs
    print("\n=== Scheduled sync jobs ===")
    cmd = "systemctl list-timers | grep -E 'solar|sync|cloud'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for historical data storage
    print("\n=== Historical data storage ===")
    cmd = "du -sh /opt/solar-assistant/*/data 2>/dev/null | head -10"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check InfluxDB retention policies
    print("\n=== InfluxDB retention policies ===")
    cmd = """sudo influx -execute 'SHOW RETENTION POLICIES ON solar_assistant' 2>/dev/null"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for websocket connections to cloud
    print("\n=== WebSocket endpoints ===")
    cmd = """find /opt/solar-assistant -name '*.ex' -exec grep -l 'ws://\\|wss://' {} \\; 2>/dev/null | head -5"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:2]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -E 'ws://|wss://' '{file}' | head -5"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check for EG4 specific endpoints
    print("\n=== EG4 specific endpoints ===")
    cmd = """strings /opt/solar-assistant/lib/*/ebin/*.beam | grep -E 'eg4.*\\.com|monitor.*eg4|eg4.*cloud|eg4.*api' | sort -u | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look at HTTP client configuration
    print("\n=== HTTP client configuration ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -A5 'HTTPoison\\|Tesla\\|Finch' | grep -E 'base_url|endpoint' | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
finally:
    ssh.close()

print("\n=== ANALYSIS ===")
print("Look for:")
print("1. HTTPS connections to external servers")
print("2. API endpoints for monitor.eg4electronics.com or similar")
print("3. Stored credentials for cloud access")
print("4. WebSocket connections for real-time updates")