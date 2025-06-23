#!/usr/bin/env python3
"""Test raw response from EG4"""

import socket
import binascii
import time

def test_eg4_connection():
    """Test connection and get raw response"""
    host = '172.16.107.129'
    port = 8000
    
    print(f"Connecting to {host}:{port}...")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print("✓ Connected successfully")
        
        # Wait a moment for the connection to stabilize
        time.sleep(0.5)
        
        # Try to receive any data the inverter might send
        print("\nWaiting for any initial data from inverter...")
        sock.settimeout(2)
        try:
            initial_data = sock.recv(1024)
            if initial_data:
                print(f"Received initial data: {binascii.hexlify(initial_data)}")
                with open('eg4_initial_response.bin', 'wb') as f:
                    f.write(initial_data)
        except socket.timeout:
            print("No initial data received")
        
        # Send different commands to see what works
        test_commands = [
            # IoTOS style command
            bytes([0xAA, 0x55, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x55, 0xAA]),
            # Simple query
            bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x64, 0x44, 0x21]),
            # Another IoTOS variant
            bytes([0xA1, 0x1A, 0x05, 0x00]),
            # EG4 specific command found in some docs
            bytes([0x7E, 0x01, 0x03, 0x00, 0x00, 0x00, 0x20, 0x85, 0xC0, 0x7E]),
        ]
        
        for i, cmd in enumerate(test_commands):
            print(f"\n--- Test Command {i+1} ---")
            print(f"Sending: {binascii.hexlify(cmd)}")
            
            try:
                sock.send(cmd)
                time.sleep(0.5)
                
                sock.settimeout(3)
                response = sock.recv(4096)
                
                if response:
                    print(f"Response length: {len(response)} bytes")
                    print(f"Response hex: {binascii.hexlify(response)}")
                    print(f"Response ASCII: {repr(response)}")
                    
                    # Save response
                    filename = f'eg4_response_cmd{i+1}.bin'
                    with open(filename, 'wb') as f:
                        f.write(response)
                    print(f"Response saved to {filename}")
                else:
                    print("No response received")
                    
            except socket.timeout:
                print("Timeout - no response")
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(1)
        
        sock.close()
        print("\nConnection closed")
        
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    test_eg4_connection()