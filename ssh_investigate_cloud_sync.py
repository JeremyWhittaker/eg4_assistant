#!/usr/bin/env python3
"""Deep dive into Solar Assistant cloud sync functionality"""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Investigate the grafana-sync directory
    print("=== Grafana Sync Directory ===")
    cmd = "ls -la /dev/shm/grafana-sync/ 2>/dev/null | head -20"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check what the DNAT rule is doing
    print("\n=== DNAT Rule Details ===")
    print("Traffic to 10.0.0.5:80 is redirected to 10.225.74.193")
    cmd = "sudo iptables -t nat -L -n -v | grep -A2 -B2 '10.225.74.193'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Try to trace what host 10.225.74.193 is
    print("\n=== What is 10.225.74.193? ===")
    cmd = "host 10.225.74.193 2>&1"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check network connections to cloud services
    print("\n=== Active connections to external IPs ===")
    cmd = "sudo ss -tn | grep -v '172.16' | grep -v '127.0' | grep ESTAB"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for config files mentioning cloud or sync
    print("\n=== Cloud/Sync Configuration ===")
    cmd = "find /opt/solar-assistant -name '*.ex' | xargs grep -l 'cloud\\|sync\\|api_key\\|grafana' 2>/dev/null | head -10"
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:3]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -A3 -B3 'cloud\\|sync\\|api_key' '{file}' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check for API requests in logs
    print("\n=== API Requests in Logs ===")
    cmd = "sudo journalctl -u solar-assistant --no-pager | grep -E 'POST|GET|api|cloud' | tail -20"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
    # Check the grafana-sync process more closely
    print("\n=== Grafana Sync Process Details ===")
    cmd = "sudo ls -la /proc/$(pgrep -f grafana-sync | head -1)/fd/ 2>/dev/null | grep -E 'socket|pipe' | head -10"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for websocket connections
    print("\n=== Checking for WebSocket connections ===")
    cmd = "sudo ss -tnp | grep beam | grep -v '172.16'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check if there's a local API that might be proxying
    print("\n=== Local API Endpoints ===")
    cmd = "sudo ss -tlnp | grep -E '8080|3000|4000|80' | grep -v '172.16.107.129'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for EG4 specific cloud endpoints
    print("\n=== EG4 Cloud Endpoints ===")
    cmd = """grep -r 'eg4\\|monitor\\.eg4' /opt/solar-assistant 2>/dev/null | grep -E 'http|api' | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("Found EG4 references:")
        print(output)
    
    # Check cron jobs for sync
    print("\n=== Cron Jobs ===")
    cmd = "sudo crontab -l 2>/dev/null"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
finally:
    ssh.close()

print("\n=== ANALYSIS ===")
print("1. Solar Assistant has 'grafana-sync' functionality")
print("2. DNAT rule redirects traffic to 10.225.74.193")
print("3. This suggests cloud data synchronization")
print("4. The real-time data might come from cloud, not just local inverter")