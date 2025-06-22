#!/usr/bin/env python3
"""
EG4 Final Display - Shows real data from EG4
Simple, working implementation
"""

import socket
import struct
from datetime import datetime

def get_eg4_data():
    """Get one reading from EG4"""
    s = socket.socket()
    s.settimeout(5)
    
    try:
        # Connect
        s.connect(('172.16.107.129', 8000))
        
        # Send command
        s.send(b'\xa1\x1a\x05\x00')
        
        # Get response
        data = s.recv(512)
        
        if len(data) >= 117:
            # Parse data
            result = {}
            
            # Battery
            result['battery_voltage'] = struct.unpack('>H', data[82:84])[0] / 100.0
            result['battery_soc'] = data[85] if data[85] <= 100 else 0
            
            # Power values
            battery_power = struct.unpack('>h', data[48:50])[0]
            grid_power = struct.unpack('>h', data[50:52])[0]
            load_power = struct.unpack('>H', data[52:54])[0]
            
            # Scale if needed
            result['battery_power'] = battery_power if abs(battery_power) < 20000 else battery_power // 10
            result['grid_power'] = grid_power if abs(grid_power) < 20000 else grid_power // 10
            result['load_power'] = load_power if load_power < 20000 else load_power // 10
            
            # PV voltages
            result['pv1_voltage'] = struct.unpack('>H', data[74:76])[0] / 10.0
            result['pv2_voltage'] = struct.unpack('>H', data[76:78])[0] / 10.0
            result['pv3_voltage'] = struct.unpack('>H', data[78:80])[0] / 10.0
            
            # Grid voltage - check multiple locations
            for offset in [90, 92, 94, 96]:
                if offset + 2 <= len(data):
                    val = struct.unpack('>H', data[offset:offset+2])[0]
                    if 2200 <= val <= 2600:
                        result['grid_voltage'] = val / 10.0
                        break
                        
            # Calculate PV power
            if result['grid_power'] < 0:  # Exporting
                result['pv_power'] = result['load_power'] + result['battery_power'] + abs(result['grid_power'])
            else:
                result['pv_power'] = max(0, result['load_power'] + result['battery_power'] - result['grid_power'])
                
            return result
            
    except Exception as e:
        print(f"Connection error: {e}")
        return None
    finally:
        s.close()

def display_data(data):
    """Display the data"""
    print(f"\nEG4 18kPV Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    if not data:
        print("ERROR: No data available")
        return
        
    print(f"\nBattery: {data['battery_voltage']:.1f}V, {data['battery_soc']}% SOC")
    print(f"  Power: {data['battery_power']:+d}W", end='')
    if data['battery_power'] > 50:
        print(" (Charging)")
    elif data['battery_power'] < -50:
        print(" (Discharging)")
    else:
        print(" (Idle)")
        
    print(f"\nGrid: {data.get('grid_voltage', 0):.1f}V")
    print(f"  Power: {data['grid_power']:+d}W", end='')
    if data['grid_power'] < -50:
        print(" (Exporting)")
    elif data['grid_power'] > 50:
        print(" (Importing)")
    else:
        print()
        
    print(f"\nSolar PV: {data['pv_power']:.0f}W total")
    print(f"  PV1: {data['pv1_voltage']:.1f}V")
    print(f"  PV2: {data['pv2_voltage']:.1f}V")
    print(f"  PV3: {data['pv3_voltage']:.1f}V")
    
    print(f"\nLoad: {data['load_power']}W")
    
    print("\n" + "-"*50)
    if data['pv_power'] > 0:
        print(f"Solar → {data['pv_power']:.0f}W")
    if data['grid_power'] > 0:
        print(f"Grid → {data['grid_power']}W")
    elif data['grid_power'] < 0:
        print(f"→ Grid {abs(data['grid_power'])}W")
    if data['battery_power'] > 0:
        print(f"→ Battery {data['battery_power']}W")
    elif data['battery_power'] < 0:
        print(f"Battery → {abs(data['battery_power'])}W")
    print(f"→ Load {data['load_power']}W")

# Main execution
if __name__ == "__main__":
    print("EG4 Data Display - Getting current values...")
    
    data = get_eg4_data()
    display_data(data)
    
    if data:
        print("\n✓ Successfully retrieved data from EG4 at 172.16.107.129")
    else:
        print("\n✗ Failed to get data from EG4")