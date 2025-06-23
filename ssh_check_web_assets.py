#!/usr/bin/env python3
"""Check web interface for external API calls"""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Find static web assets
    print("=== Web Assets Location ===")
    cmd = "find /opt/solar-assistant -name '*.js' -o -name '*.html' | grep -E 'priv/static|assets' | head -10"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Search JavaScript for API calls
    print("\n=== JavaScript API Calls ===")
    cmd = """find /opt/solar-assistant -name '*.js' | xargs grep -E 'fetch\\(|axios|XMLHttpRequest|ajax' | grep -v localhost | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for WebSocket connections in JS
    print("\n=== WebSocket Connections ===")
    cmd = """find /opt/solar-assistant -name '*.js' | xargs grep -E 'WebSocket|ws://|wss://' | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check for external script includes
    print("\n=== External Scripts in HTML ===")
    cmd = """find /opt/solar-assistant -name '*.html' -o -name '*.heex' | xargs grep -E 'src="http|src="//|api\\.eg4|monitor\\.' | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look at Phoenix channels for data
    print("\n=== Phoenix Channels ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -l 'channel\\|socket' | head -5"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:2]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -B3 -A3 'channel\\|broadcast' '{file}' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check nginx config for proxying
    print("\n=== Nginx Configuration ===")
    cmd = "cat /etc/nginx/sites-enabled/* 2>/dev/null | grep -E 'proxy_pass|upstream' | head -10"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for API keys in environment
    print("\n=== Environment Variables ===")
    cmd = "sudo strings /proc/$(pgrep beam)/environ | grep -E 'API|KEY|SECRET|TOKEN|EG4' | grep -v PATH"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check for hidden API endpoints
    print("\n=== Hidden API Endpoints ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -E 'defp?.*api|defp?.*fetch|defp?.*cloud' | head -20"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Monitor HTTP traffic while loading charts
    print("\n=== Instructions for Live Test ===")
    print("To see if charts load external data:")
    print("1. Run: sudo tcpdump -i any -s0 'port 80 or port 443' -w /tmp/capture.pcap")
    print("2. Load Solar Assistant web interface with long-term charts")
    print("3. Check capture for external connections")
    
finally:
    ssh.close()

print("\n=== ANALYSIS ===")
print("Solar Assistant appears to store data locally in InfluxDB")
print("The 2.7M data points suggest extensive local storage")
print("Check the outputs above for any external API references")