#!/usr/bin/env python3
"""Check how Solar Assistant connects to EG4 inverter"""

import paramiko
import time

def check_eg4_connection():
    """SSH to Solar Assistant and check EG4 connection method"""
    
    host = "172.16.109.214"
    username = "solar-assistant"
    password = "solar123"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to Solar Assistant at {host}...")
        ssh.connect(host, username=username, password=password)
        print("Connected!\n")
        
        # Check network connections to EG4
        print("=== Checking connections to EG4 at 172.16.107.129 ===")
        output = ssh.exec_command("netstat -tn | grep 172.16.107.129")[1].read().decode()
        print(output)
        
        # Check running processes
        print("\n=== Checking processes related to inverter ===")
        output = ssh.exec_command("ps aux | grep -E 'inverter|eg4|modbus|luxpower' | grep -v grep")[1].read().decode()
        print(output)
        
        # Check if there's a config showing EG4 connection
        print("\n=== Checking Solar Assistant config ===")
        output = ssh.exec_command("cat /dev/shm/solar_assistant/*/config_runtime.json 2>/dev/null | grep -A5 -B5 '172.16.107'")[1].read().decode()
        print(output)
        
        # Check logs for EG4 communication
        print("\n=== Recent log entries about 172.16.107.129 ===")
        output = ssh.exec_command("sudo journalctl -u solar-assistant --no-pager | grep '172.16.107' | tail -10")[1].read().decode()
        print(output)
        
        # Look for any scripts or binaries that might communicate with EG4
        print("\n=== Looking for EG4/inverter related files ===")
        output = ssh.exec_command("find /usr/local/bin /opt /home -name '*eg4*' -o -name '*inverter*' 2>/dev/null | head -20")[1].read().decode()
        print(output)
        
        # Check if it's using a different protocol
        print("\n=== Checking for protocol hints ===")
        output = ssh.exec_command("strings /usr/local/bin/solar-assistant 2>/dev/null | grep -E 'eg4|modbus|tcp|8000' | head -20")[1].read().decode()
        print(output)
        
        # Monitor network traffic to EG4
        print("\n=== Monitoring traffic to EG4 (5 seconds) ===")
        output = ssh.exec_command("sudo timeout 5 tcpdump -i any host 172.16.107.129 -c 10 2>&1")[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    check_eg4_connection()