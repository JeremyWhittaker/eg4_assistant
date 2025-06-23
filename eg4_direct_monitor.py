#!/usr/bin/env python3
"""
EG4 Direct Monitor - Connects directly to the dongle
No Solar Assistant required
"""

import socket
import struct
import time
from datetime import datetime
import sys

def get_eg4_direct():
    """Connect directly to EG4 dongle"""
    s = socket.socket()
    s.settimeout(10)
    
    try:
        print("Connecting to EG4 dongle at 172.16.107.129:8000...")
        s.connect(('172.16.107.129', 8000))
        print("Connected! Sending query...")
        
        # Send IoTOS command
        s.send(b'\xa1\x1a\x05\x00')
        
        # Get response
        response = s.recv(512)
        print(f"Received {len(response)} bytes")
        
        if len(response) >= 100:
            data = {}
            
            # Parse the response
            data['battery_voltage'] = struct.unpack('>H', response[82:84])[0] / 100.0
            data['battery_soc'] = response[85]
            
            # Power values
            battery_power = struct.unpack('>h', response[48:50])[0]
            grid_power = struct.unpack('>h', response[50:52])[0]
            load_power = struct.unpack('>H', response[52:54])[0]
            
            # Scale if needed
            data['battery_power'] = battery_power if abs(battery_power) < 20000 else battery_power // 10
            data['grid_power'] = grid_power if abs(grid_power) < 20000 else grid_power // 10
            data['load_power'] = load_power if load_power < 20000 else load_power // 10
            
            # PV voltages
            data['pv1_voltage'] = struct.unpack('>H', response[74:76])[0] / 10.0
            data['pv2_voltage'] = struct.unpack('>H', response[76:78])[0] / 10.0
            data['pv3_voltage'] = struct.unpack('>H', response[78:80])[0] / 10.0
            
            # Grid voltage
            for offset in [90, 92, 94, 96]:
                if offset + 2 <= len(response):
                    val = struct.unpack('>H', response[offset:offset+2])[0]
                    if 2200 <= val <= 2600:
                        data['grid_voltage'] = val / 10.0
                        break
            
            # Calculate PV power
            if data['grid_power'] < 0:
                data['pv_power'] = data['load_power'] + data['battery_power'] + abs(data['grid_power'])
            else:
                data['pv_power'] = max(0, data['load_power'] + data['battery_power'] - data['grid_power'])
            
            return data
        else:
            print(f"Response too short: {len(response)} bytes")
            return None
            
    except ConnectionRefusedError:
        print("\nERROR: Connection refused")
        print("The EG4 dongle may only allow one connection at a time.")
        print("Solar Assistant is currently connected at 172.16.109.214")
        print("\nTo connect directly, you need to stop Solar Assistant:")
        print("1. SSH to solar-assistant@172.16.109.214")
        print("2. Run: sudo systemctl stop solar-assistant")
        print("3. Then run this monitor")
        print("4. When done, restart: sudo systemctl start solar-assistant")
        return None
    except Exception as e:
        print(f"\nERROR: {e}")
        return None
    finally:
        s.close()

def display_direct(data):
    """Display data from direct connection"""
    print(f"\n{'='*60}")
    print(f"EG4 DIRECT CONNECTION - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    if not data:
        return
        
    print(f"\nBATTERY: {data['battery_voltage']:.1f}V @ {data['battery_soc']}%")
    print(f"  Power: {data['battery_power']:+d}W")
    
    print(f"\nGRID: {data.get('grid_voltage', 0):.1f}V")
    print(f"  Power: {data['grid_power']:+d}W", end='')
    if data['grid_power'] < 0:
        print(" [EXPORTING]")
    elif data['grid_power'] > 0:
        print(" [IMPORTING]")
    else:
        print()
    
    print(f"\nSOLAR: {data['pv_power']:.0f}W")
    print(f"  PV1: {data['pv1_voltage']:.1f}V")
    print(f"  PV2: {data['pv2_voltage']:.1f}V")
    print(f"  PV3: {data['pv3_voltage']:.1f}V")
    
    print(f"\nLOAD: {data['load_power']}W")

def run_continuous():
    """Run continuous monitoring"""
    print("EG4 Direct Monitor - Connecting to dongle at 172.16.107.129")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            data = get_eg4_direct()
            if data:
                display_direct(data)
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            break

if __name__ == "__main__":
    # Try once first
    data = get_eg4_direct()
    if data:
        display_direct(data)
        print("\n✓ Direct connection successful!")
        print("\nStarting continuous monitoring...")
        time.sleep(2)
        run_continuous()
    else:
        print("\n✗ Cannot connect directly while Solar Assistant is connected")