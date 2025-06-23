#!/usr/bin/env python3
"""Test direct connection to EG4 18kPV using IoTOS protocol"""

import socket
import binascii
import struct
import time

def connect_eg4():
    """Connect to EG4 inverter using IoTOS protocol"""
    host = '172.16.107.129'
    port = 8000
    
    print(f"Connecting to EG4 18kPV at {host}:{port}...")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        # Connect
        sock.connect((host, port))
        print("✓ Connected successfully!")
        
        # Send query command
        query_command = b'\xa1\x1a\x05\x00'
        print(f"\nSending query command: {binascii.hexlify(query_command)}")
        sock.send(query_command)
        
        # Receive response
        sock.settimeout(5)
        response = sock.recv(4096)
        
        if response:
            print(f"\nReceived {len(response)} bytes")
            print(f"Response (hex): {binascii.hexlify(response)[:200]}...")
            
            # Try to parse the response based on Solar Assistant's code
            if len(response) >= 70:
                print("\nParsing data...")
                
                # Extract power values (32-bit big-endian integers)
                pv1_power = struct.unpack('>i', response[37:41])[0]
                pv2_power = struct.unpack('>i', response[41:45])[0]
                pv3_power = struct.unpack('>i', response[45:49])[0]
                total_pv_power = struct.unpack('>i', response[49:53])[0]
                battery_power = struct.unpack('>i', response[53:57])[0]
                grid_power = struct.unpack('>i', response[57:61])[0]
                load_power = struct.unpack('>i', response[65:69])[0]
                
                print(f"\nExtracted values:")
                print(f"PV1 Power: {pv1_power} W")
                print(f"PV2 Power: {pv2_power} W")
                print(f"PV3 Power: {pv3_power} W")
                print(f"Total PV Power: {total_pv_power} W")
                print(f"Battery Power: {battery_power} W")
                print(f"Grid Power: {grid_power} W")
                print(f"Load Power: {load_power} W")
                
                # Look for battery SOC
                if len(response) > 95:
                    for i in range(60, min(96, len(response))):
                        if 0 <= response[i] <= 100:
                            print(f"Battery SOC: {response[i]}%")
                            break
            else:
                print(f"\nResponse too short ({len(response)} bytes), expected at least 70")
        else:
            print("\nNo response received")
            
        sock.close()
        
    except socket.timeout:
        print("✗ Connection timeout")
    except ConnectionRefused:
        print("✗ Connection refused")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    connect_eg4()