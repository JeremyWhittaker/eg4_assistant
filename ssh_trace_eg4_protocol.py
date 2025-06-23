#!/usr/bin/env python3
"""Trace the actual protocol being used with EG4"""

import paramiko
import time

def trace_protocol():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # Install strace if needed and trace the connection
        print("=== Tracing EG4 communication (10 seconds) ===")
        print("Looking for actual data being sent/received...\n")
        
        # First find the exact PID
        cmd = "sudo netstat -tnp | grep 172.16.107.129:8000 | awk '{print $7}' | cut -d'/' -f1"
        pid = ssh.exec_command(cmd)[1].read().decode().strip()
        print(f"Process PID: {pid}")
        
        if pid:
            # Trace network calls
            print("\nTracing network communication...")
            cmd = f"sudo timeout 10 strace -p {pid} -e trace=network -s 200 2>&1 | grep -E 'send|recv' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
            
            # Also trace read/write to see data
            print("\n\nTracing read/write operations...")
            cmd = f"sudo timeout 5 strace -p {pid} -e trace=read,write -s 500 2>&1 | grep -A2 -B2 '172.16.107' | head -30"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
            
            # Try to capture actual hex data
            print("\n\nCapturing hex data...")
            cmd = f"sudo timeout 5 strace -p {pid} -e trace=read,write -xx -s 1000 2>&1 | grep -E 'read|write' | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
        
        # Look for the connection parameters
        print("\n\n=== Connection details ===")
        cmd = f"sudo lsof -p {pid} | grep TCP | grep 172.16.107"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check if it's using a specific library
        print("\n=== Libraries used by process ===")
        cmd = f"sudo lsof -p {pid} | grep -E 'modbus|serial|tcp' | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    trace_protocol()