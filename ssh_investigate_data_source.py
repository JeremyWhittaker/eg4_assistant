#!/usr/bin/env python3
"""Investigate if Solar Assistant is pulling data from cloud/API servers"""

import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Check for external connections
    print("=== Checking external network connections ===")
    cmd = "sudo netstat -tnp | grep -v '172.16' | grep ESTABLISHED | grep -v '127.0.0.1'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for DNS queries to EG4 or monitoring domains
    print("\n=== Recent DNS lookups ===")
    cmd = "sudo grep -E 'eg4|monitor|cloud|api' /var/log/syslog 2>/dev/null | grep -i 'query' | tail -20"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
    # Check hosts file for any hardcoded entries
    print("\n=== Checking hosts file ===")
    cmd = "cat /etc/hosts | grep -E 'eg4|monitor|cloud|api'"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
    # Look for API endpoints in configuration
    print("\n=== Searching for API endpoints in config ===")
    cmd = """find /opt/solar-assistant -name '*.json' -o -name '*.yaml' -o -name '*.toml' -o -name '*.conf' | xargs grep -l 'http\\|api\\|cloud\\|monitor' 2>/dev/null | head -10"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:5]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -i 'http\\|api\\|cloud\\|monitor' '{file}' | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check environment variables
    print("\n=== Environment variables ===")
    cmd = "sudo grep -E 'API|CLOUD|MONITOR|EG4' /proc/$(pgrep beam)/environ 2>/dev/null | tr '\\0' '\\n'"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
    # Monitor network traffic for 10 seconds
    print("\n=== Monitoring network traffic (10 seconds) ===")
    print("Looking for connections to external servers...")
    cmd = """sudo timeout 10 tcpdump -n 'not net 172.16.0.0/16 and not net 127.0.0.0/8 and (port 80 or port 443 or port 8080)' 2>/dev/null | head -30"""
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("External connections detected:")
        print(output)
    else:
        print("No external HTTP/HTTPS connections detected")
    
    # Check for monitor.eg4electronics.com specifically
    print("\n=== Checking for monitor.eg4electronics.com ===")
    cmd = "sudo grep -r 'monitor.eg4electronics.com' /opt/solar-assistant 2>/dev/null | head -10"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print("Found references:")
        print(output)
    
    # Try to resolve the domain
    cmd = "nslookup monitor.eg4electronics.com 2>&1"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(f"\nDNS lookup result:\n{output}")
    
    # Check iptables for any redirections
    print("\n=== Checking firewall rules ===")
    cmd = "sudo iptables -t nat -L -n | grep -E 'DNAT|REDIRECT'"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
    # Look at running processes for any cloud sync
    print("\n=== Checking for cloud sync processes ===")
    cmd = "ps aux | grep -E 'sync|cloud|api|upload' | grep -v grep"
    output = ssh.exec_command(cmd)[1].read().decode()
    if output:
        print(output)
    
finally:
    ssh.close()

print("\n=== ANALYSIS ===")
print("Check the output above for:")
print("1. External network connections (not 172.16.x.x)")
print("2. References to cloud APIs or monitor.eg4electronics.com")
print("3. Any sync or upload processes")
print("4. API keys or cloud configuration")