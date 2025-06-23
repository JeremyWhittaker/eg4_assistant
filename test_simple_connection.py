#!/usr/bin/env python3
"""Test simple connection to EG4"""

import socket
import time

print("Testing connection to EG4 at 172.16.107.129:8000")

# First test - just connect
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    print("Attempting connection...")
    s.connect(('172.16.107.129', 8000))
    print("Connected!")
    
    # Try sending the command immediately
    cmd = b'\xa1\x1a\x05\x00'
    print(f"Sending command: {cmd.hex()}")
    s.send(cmd)
    
    # Try to receive data
    print("Waiting for response...")
    s.settimeout(5)
    data = s.recv(1024)
    
    if data:
        print(f"Received {len(data)} bytes")
        print(f"First 20 bytes (hex): {data[:20].hex()}")
        print(f"First 20 bytes (ascii): {repr(data[:20])}")
        
        # Check if it looks like our expected response
        if len(data) >= 4:
            if data[0] == 0xa1 and data[1] == 0x1a:
                print("This looks like a valid IoTOS response!")
            else:
                print("This doesn't look like the expected response format")
    else:
        print("No data received")
        
    s.close()
    
except socket.timeout:
    print("ERROR: Connection timed out")
except ConnectionRefusedError:
    print("ERROR: Connection refused")
except Exception as e:
    print(f"ERROR: {e}")

# Quick check if port is really open
print("\nPort scan result:")
import subprocess
result = subprocess.run(['nc', '-zv', '172.16.107.129', '8000'], 
                       capture_output=True, text=True, timeout=5)
print(result.stderr)