#!/usr/bin/env python3
"""Test EG4 data parsing"""

import socket
import struct
import binascii

def test_eg4_connection():
    """Test connection and parse real data"""
    host = '172.16.107.129'
    port = 8000
    
    try:
        # Connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")
        
        # Send query
        query = b'\xa1\x1a\x05\x00'
        sock.send(query)
        
        # Receive
        response = sock.recv(4096)
        sock.close()
        
        print(f"\nReceived {len(response)} bytes")
        print(f"Header: {response[:8].hex()}")
        print(f"Device ID: {response[8:18].decode('ascii', errors='ignore')}")
        
        # Analyze the response in detail
        print("\n=== Detailed Analysis ===")
        
        # Look for patterns in 16-bit values
        print("\n16-bit values from position 30:")
        for i in range(30, min(100, len(response)), 2):
            if i + 2 <= len(response):
                value = struct.unpack('>H', response[i:i+2])[0]
                # Show values that look like reasonable measurements
                if 10 <= value <= 5000:
                    print(f"Pos {i}: {value} (could be {value/10:.1f}V or {value/10:.1f}A)")
        
        # Check specific positions based on Solar Assistant patterns
        if len(response) >= 100:
            print("\nChecking standard positions:")
            
            # PV voltages/currents often start around position 36-44
            pos = 36
            pv1_v = struct.unpack('>H', response[pos:pos+2])[0] / 10.0
            pv1_a = struct.unpack('>H', response[pos+2:pos+4])[0] / 10.0
            pv2_v = struct.unpack('>H', response[pos+4:pos+6])[0] / 10.0
            pv2_a = struct.unpack('>H', response[pos+6:pos+8])[0] / 10.0
            
            print(f"\nPV1: {pv1_v:.1f}V @ {pv1_a:.1f}A = {pv1_v * pv1_a:.0f}W")
            print(f"PV2: {pv2_v:.1f}V @ {pv2_a:.1f}A = {pv2_v * pv2_a:.0f}W")
            
            # Battery data often around position 78-82
            pos = 78
            bat_v = struct.unpack('>H', response[pos:pos+2])[0] / 10.0
            bat_a = struct.unpack('>h', response[pos+2:pos+4])[0] / 10.0  # Signed
            
            print(f"\nBattery: {bat_v:.1f}V @ {bat_a:.1f}A = {bat_v * bat_a:.0f}W")
            
            # Check for SOC
            for i in [86, 87, 88, 89, 90]:
                if i < len(response) and 0 <= response[i] <= 100:
                    print(f"Possible SOC at position {i}: {response[i]}%")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_eg4_connection()