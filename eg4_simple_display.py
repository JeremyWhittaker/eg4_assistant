#!/usr/bin/env python3
"""Simple EG4 display - shows parsed data"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
from datetime import datetime

client = EG4IoTOSClient(host='172.16.107.129', port=8000)

if client.connect():
    print("Connected to EG4 18kPV")
    
    response = client.send_receive(b'\xa1\x1a\x05\x00')
    
    if response and len(response) >= 100:
        print(f"\nData received at {datetime.now()}:")
        print("="*60)
        
        # Parse based on hex dump analysis
        serial = response[8:19].decode('ascii', errors='ignore').strip('\x00')
        print(f"Serial: {serial}")
        
        # Battery data
        battery_voltage = struct.unpack('>H', response[0x52:0x54])[0] / 100.0
        battery_soc = response[0x53]
        print(f"\nBATTERY:")
        print(f"  Voltage: {battery_voltage:.1f} V")
        print(f"  SOC: {battery_soc}%")
        
        # Load data
        load_power = response[0x40]
        backup_power = response[0x44]
        print(f"\nLOAD:")
        print(f"  Main: {load_power} W")
        print(f"  Backup: {backup_power} W")
        
        # PV voltages (nighttime, so power is 0)
        pv1_v = struct.unpack('>H', response[0x4A:0x4C])[0] / 10.0
        pv2_v = struct.unpack('>H', response[0x4C:0x4E])[0] / 10.0
        pv3_v = struct.unpack('>H', response[0x4E:0x50])[0] / 10.0
        print(f"\nSOLAR PV (Night - 0W expected):")
        print(f"  PV1: 0 W @ {pv1_v:.1f} V")
        print(f"  PV2: 0 W @ {pv2_v:.1f} V")
        print(f"  PV3: 0 W @ {pv3_v:.1f} V")
        
        # Try to find more values
        print(f"\nSearching for additional values...")
        
        # Look for realistic power values (0-20000W range)
        for i in range(36, min(len(response)-4, 100), 4):
            val = struct.unpack('>I', response[i:i+4])[0]
            if 100 < val < 20000:
                print(f"  Possible power at offset {i}: {val} W")
                
        # Look for grid voltage (2200-2500 = 220-250V)
        for i in range(48, min(len(response)-2, 100), 2):
            val = struct.unpack('>H', response[i:i+2])[0]
            if 2200 <= val <= 2500:
                print(f"  Grid voltage at offset {i}: {val/10.0:.1f} V")
                
        # Show all non-zero 2-byte values in interesting range
        print(f"\nNon-zero values (offset 48-96):")
        for i in range(48, min(len(response)-2, 96), 2):
            val = struct.unpack('>H', response[i:i+2])[0]
            if val > 0:
                print(f"  Offset {i}: {val} (/{10}={val/10:.1f}, /{100}={val/100:.1f})")
        
    client.disconnect()
    print("\nDisconnected")
else:
    print("Failed to connect")