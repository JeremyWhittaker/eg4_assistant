#!/usr/bin/env python3
"""Examine how Solar Assistant handles historical data"""

import paramiko
from datetime import datetime, timedelta

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
    print("Connected to Solar Assistant\n")
    
    # Check how much historical data is actually stored locally
    print("=== Local InfluxDB Data Range ===")
    cmd = """sudo influx -database solar_assistant -execute 'SELECT COUNT(*) FROM "Battery power" WHERE time > now() - 365d' -format csv 2>/dev/null"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(f"Data points in last year: {output}")
    
    # Get oldest data point
    cmd = """sudo influx -database solar_assistant -execute 'SELECT FIRST(*) FROM "Battery power"' -format csv 2>/dev/null | tail -1"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(f"Oldest data point: {output}")
    
    # Check database size
    print("\n=== Database Size ===")
    cmd = "du -sh /var/lib/influxdb/data/solar_assistant/"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(f"InfluxDB size: {output}")
    
    # Look for import/export functionality
    print("\n=== Data Import/Export Functions ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -l 'import\\|export\\|backup\\|restore\\|sync' | head -10"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:3]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -B2 -A2 'import\\|export\\|historical' '{file}' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check for scheduled data fetching
    print("\n=== Cron/Systemd Timers ===")
    cmd = "crontab -l 2>/dev/null; systemctl list-timers --all | grep -E 'solar|data|sync'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for API client modules
    print("\n=== HTTP Client Libraries ===")
    cmd = """find /opt/solar-assistant -path '*/deps/*' -name '*.app' | grep -E 'http|client|api' | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Check mix.exs for dependencies
    print("\n=== Project Dependencies ===")
    cmd = "find /opt/solar-assistant -name 'mix.exs' | head -1 | xargs cat | grep -A20 'defp deps'"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look for EG4-specific modules
    print("\n=== EG4 Specific Code ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -l -i 'eg4\\|luxpower' | head -10"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:2]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -B5 -A5 -i 'eg4\\|cloud\\|api' '{file}' | head -30"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check Phoenix LiveView for data sources
    print("\n=== LiveView Data Sources ===")
    cmd = """find /opt/solar-assistant -name '*.ex' | xargs grep -l 'live_view\\|handle_info\\|mount' | grep -v test | head -5"""
    files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
    
    for file in files[:2]:
        if file:
            print(f"\n{file}:")
            cmd = f"grep -B3 -A3 'handle_params\\|mount\\|fetch' '{file}' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
    
    # Check for any cloud storage references
    print("\n=== Cloud Storage References ===")
    cmd = """strings /opt/solar-assistant/lib/*/ebin/*.beam | grep -E 's3\\.|azure\\.|gcp\\.|cloud' | grep -v localhost | sort -u | head -10"""
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
    # Look at network requests during chart loading
    print("\n=== Recent Network Activity ===")
    cmd = "sudo journalctl -u solar-assistant -n 100 --no-pager | grep -E 'GET|POST|fetch|download' | tail -20"
    output = ssh.exec_command(cmd)[1].read().decode()
    print(output)
    
finally:
    ssh.close()

print("\n=== CONCLUSION ===")
print("Check above for:")
print("1. How much historical data is stored locally")
print("2. Any import/export or sync functionality")
print("3. References to cloud APIs or external data sources")
print("4. How charts fetch their data")