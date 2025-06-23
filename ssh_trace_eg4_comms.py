#!/usr/bin/env python3
"""Trace actual EG4 communications"""

import paramiko
import time

def trace_comms():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # Get the socket details
        print("=== Current connection to EG4 ===")
        cmd = "sudo ss -tnp | grep 172.16.107.129:8000"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Get file descriptor details
        print("\n=== File descriptor details ===")
        cmd = "sudo ls -la /proc/583/fd/ | grep socket"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Try to trace the actual data being sent
        print("\n=== Installing tcpdump and capturing packets ===")
        cmd = "sudo apt-get update && sudo apt-get install -y tcpdump"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()  # Wait for completion
        
        print("\n=== Capturing EG4 communication (10 seconds) ===")
        print("This will show the actual bytes being sent/received...\n")
        
        # Capture packets
        cmd = "sudo timeout 10 tcpdump -i any -A -XX host 172.16.107.129 and port 8000 2>/dev/null | head -200"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Alternative: use strace to see the actual system calls
        print("\n=== Using strace to capture data (5 seconds) ===")
        cmd = "sudo timeout 5 strace -p 583 -e trace=read,write,send,recv -xx 2>&1 | grep -A5 -B5 'recv\\|send' | head -50"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look at the Erlang code that might be loaded
        print("\n=== Checking loaded Erlang modules ===")
        # Connect to the Erlang node and list modules
        cmd = "sudo erl -name debug@localhost -setcookie $(cat /proc/583/environ | tr '\\0' '\\n' | grep COOKIE | cut -d'=' -f2) -eval 'rpc:call(\\'solar_assistant@localhost\\', code, all_loaded, []).' -s init stop 2>/dev/null | grep -E 'inverter|protocol|modbus|driver' | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check for any debug/log output
        print("\n=== Recent log entries about EG4 ===")
        cmd = "sudo journalctl -u solar-assistant -n 100 | grep -E '172.16.107|eg4|EG4|query|command' | tail -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look for the actual query pattern in memory
        print("\n=== Searching process memory for command patterns ===")
        cmd = "sudo gcore -o /tmp/sa_dump 583 2>/dev/null && strings /tmp/sa_dump.583 | grep -E 'a1.*1a.*05|query.*command' | head -10 && rm -f /tmp/sa_dump.583"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    trace_comms()