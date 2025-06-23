#!/usr/bin/env python3
"""Simple EG4 data dump - shows all available fields"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct

client = EG4IoTOSClient(host='172.16.107.129', port=8000)

if client.connect():
    print("Connected!")
    
    # Send query
    response = client.send_receive(b'\xa1\x1a\x05\x00')
    
    if response:
        print(f"\nReceived {len(response)} bytes")
        
        # Save raw response
        with open('eg4_full_response.bin', 'wb') as f:
            f.write(response)
        print("Saved to eg4_full_response.bin")
        
        # Parse known fields
        print("\n=== PARSED DATA ===")
        print(f"Serial: {response[8:19].decode('ascii', errors='ignore').strip()}")
        print(f"Device ID: {response[24:35].decode('ascii', errors='ignore').strip()}")
        
        # Power values at fixed offsets
        powers = {
            'PV1': 37,
            'PV2': 41, 
            'PV3': 45,
            'Total PV': 49,
            'Battery': 53,
            'Grid': 57,
            'Backup': 61,
            'Load': 65
        }
        
        print("\nPOWER VALUES (raw):")
        for name, offset in powers.items():
            if offset + 4 <= len(response):
                raw_value = int.from_bytes(response[offset:offset+4], 'big', signed=True)
                print(f"  {name}: {raw_value}")
                
                # Also show scaled versions
                if abs(raw_value) > 50000:
                    print(f"    -> /100: {raw_value/100:.1f}")
                    print(f"    -> /1000: {raw_value/1000:.1f}")
                elif abs(raw_value) > 20000:
                    print(f"    -> /10: {raw_value/10:.1f}")
        
        # Look for other patterns
        print("\n=== SEARCHING FOR OTHER VALUES ===")
        
        # Search for voltage patterns (typically 2-byte values)
        print("\nPossible voltages (400-600 range):")
        for i in range(70, min(len(response)-2, 200), 2):
            val = struct.unpack('>H', response[i:i+2])[0]
            if 400 < val < 600:
                print(f"  Offset {i}: {val} -> {val/10:.1f}V")
        
        print("\nPossible battery voltage (450-550 range):")
        for i in range(70, min(len(response)-2, 200), 2):
            val = struct.unpack('>H', response[i:i+2])[0]
            if 450 < val < 550:
                print(f"  Offset {i}: {val} -> {val/10:.1f}V")
                
        print("\nPossible currents (0-300 range):")
        for i in range(70, min(len(response)-2, 200), 2):
            val = struct.unpack('>H', response[i:i+2])[0]
            if 0 < val < 300:
                print(f"  Offset {i}: {val} -> {val/10:.1f}A")
        
        print("\nPossible SOC (0-100):")
        for i in range(70, min(len(response), 150)):
            if 0 < response[i] <= 100:
                print(f"  Offset {i}: {response[i]}%")
        
        # Show hex dump of interesting area
        print("\n=== HEX DUMP (bytes 70-150) ===")
        for i in range(70, min(len(response), 150), 16):
            hex_str = response[i:i+16].hex()
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in response[i:i+16])
            print(f"{i:04x}: {hex_str:<32} {ascii_str}")
            
    client.disconnect()
else:
    print("Failed to connect")