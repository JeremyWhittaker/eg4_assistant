#!/usr/bin/env python3
"""Capture the actual protocol being used"""

import paramiko
import time

def capture_protocol():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.109.214", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # Monitor the connection with netcat
        print("=== Monitoring EG4 connection ===")
        print("Setting up packet capture...\n")
        
        # Use tcpdump if available
        cmd = "which tcpdump"
        output = ssh.exec_command(cmd)[1].read().decode()
        if output.strip():
            print("Using tcpdump to capture packets...")
            cmd = "sudo timeout 5 tcpdump -i any -nn -A host 172.16.107.129 and port 8000 2>&1 | head -100"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
        
        # Try using netcat to proxy and see traffic
        print("\n=== Trying to intercept traffic ===")
        # First kill any existing connection
        cmd = "sudo ss -K dst 172.16.107.129 dport = 8000 2>/dev/null"
        ssh.exec_command(cmd)
        time.sleep(1)
        
        # Set up a proxy to capture traffic
        print("Setting up proxy to capture traffic...")
        cmd = """sudo timeout 10 sh -c '
            mkfifo /tmp/eg4_pipe 2>/dev/null
            nc -l -p 8001 < /tmp/eg4_pipe | tee /tmp/eg4_capture.log | nc 172.16.107.129 8000 > /tmp/eg4_pipe &
            sleep 2
            # Update iptables to redirect
            iptables -t nat -A OUTPUT -p tcp -d 172.16.107.129 --dport 8000 -j REDIRECT --to-port 8001
            sleep 8
            # Clean up
            iptables -t nat -D OUTPUT -p tcp -d 172.16.107.129 --dport 8000 -j REDIRECT --to-port 8001
            pkill -f "nc -l -p 8001"
        ' 2>&1"""
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check what was captured
        print("\n=== Captured data ===")
        cmd = "cat /tmp/eg4_capture.log 2>/dev/null | xxd -g 1 | head -50"
        output = ssh.exec_command(cmd)[1].read().decode()
        if output:
            print("Hex dump of captured data:")
            print(output)
        
        # Alternative: Check Solar Assistant's internal state
        print("\n=== Checking Solar Assistant internals ===")
        # Look for any debug configuration
        cmd = "find /etc /opt /home -name '*.toml' -o -name '*.conf' -o -name '*.yaml' 2>/dev/null | xargs grep -l debug 2>/dev/null | head -5"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(f"Debug configs: {output}")
        
        # Check environment variables
        print("\n=== Environment variables ===")
        cmd = "cat /proc/583/environ | tr '\\0' '\\n' | grep -E 'DEBUG|LOG|PROTOCOL'"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Last resort - check the actual binary
        print("\n=== Checking binary for protocol hints ===")
        cmd = "strings /proc/583/exe 2>/dev/null | grep -E 'eg4|protocol.*hex|command.*byte' | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Clean up
        cmd = "rm -f /tmp/eg4_pipe /tmp/eg4_capture.log 2>/dev/null"
        ssh.exec_command(cmd)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    capture_protocol()