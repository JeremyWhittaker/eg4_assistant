#!/usr/bin/env python3
"""Test connection to EG4 18kPV"""

import socket
import time
import binascii

def test_connection():
    """Test basic connection to EG4"""
    host = '172.16.107.129'
    port = 8000
    
    print(f"Testing connection to {host}:{port}")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Connect
        sock.connect((host, port))
        print("✓ Connected successfully")
        
        # Try different query commands
        commands = [
            b'\xa1\x1a\x05\x00',  # Original command
            b'\x01\x03\x00\x00\x00\x64\x44\x21',  # Modbus read registers
            b'\x00\x00\x00\x00\x00\x06\x01\x03\x00\x00\x00\x64',  # Modbus TCP
        ]
        
        for i, cmd in enumerate(commands):
            print(f"\nTrying command {i+1}: {binascii.hexlify(cmd)}")
            try:
                sock.send(cmd)
                sock.settimeout(2)
                response = sock.recv(1024)
                if response:
                    print(f"Response length: {len(response)}")
                    print(f"Response hex: {binascii.hexlify(response)[:100]}")
                else:
                    print("No response")
                time.sleep(1)
            except socket.timeout:
                print("Timeout - no response")
            except Exception as e:
                print(f"Error: {e}")
        
        sock.close()
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")

if __name__ == "__main__":
    test_connection()