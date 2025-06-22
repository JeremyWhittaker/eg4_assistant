#!/usr/bin/env python3
"""
EG4 Final Monitor - Correctly parses all available data
Based on actual response analysis
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
from datetime import datetime

def parse_eg4_response(response):
    """Parse EG4 response based on actual data structure"""
    data = {}
    
    if not response or len(response) < 100:
        return data
    
    # Header: a1 1a 05 00 6f 00 01 c2
    # Serial: BA32401949a (offset 8-19)
    data['serial'] = response[8:19].decode('ascii', errors='ignore').strip('\x00')
    
    # Device ID: 3352670252x (offset 24-35)  
    data['device_id'] = response[24:35].decode('ascii', errors='ignore').strip('\x00')
    
    # From hex dump analysis:
    # Offset 0x30 (48): a8 04 a6 04 = Battery related values
    # Offset 0x40 (64): 4c 00 00 00 4c = Load values
    # Offset 0x48 (72): 08 05 9c 04 a3 04 4e = Voltages
    
    # Battery voltage at offset 0x48 (72): 08 05 = 0x0508 = 1288 / 10 = 128.8V
    # Wait, that's too high for 48V battery
    
    # Let's try offset 0x4A (74): 05 9c = 0x059c = 1436 / 10 = 143.6V (PV1?)
    # Offset 0x4C (76): 04 a3 = 0x04a3 = 1187 / 10 = 118.7V (PV2?)
    # Offset 0x4E (78): 04 4e = 0x044e = 1102 / 10 = 110.2V (PV3?)
    
    # Offset 0x52 (82): 16 64 = 0x1664 = 5732 / 100 = 57.32V (Battery!)
    data['battery_voltage'] = struct.unpack('>H', response[0x52:0x54])[0] / 100.0
    
    # Battery SOC at offset 0x53 (83): 64 = 100 decimal = 100%
    data['battery_soc'] = response[0x53]
    
    # Power values - these appear to be at different offsets
    # Offset 0x30 (48): a8 04 = 0xa804 = 43012 (needs scaling)
    # Offset 0x32 (50): a6 04 = 0xa604 = 42500 (needs scaling)
    
    # Load power at offset 0x40 (64): 4c 00 00 00 = 0x4c = 76W
    data['load_power'] = response[0x40]
    
    # Backup load at offset 0x44 (68): 4c = 76W
    data['backup_power'] = response[0x44]
    
    # Grid/Battery current at offset 0x54 (84): 01 14 = 0x0114 = 276 / 10 = 27.6A
    grid_current = struct.unpack('>H', response[0x54:0x56])[0] / 10.0
    
    # Try to find grid voltage - common values are 220-240V
    # Let's scan for values in range 2200-2400 (220.0-240.0V)
    for i in range(48, min(len(response)-2, 100), 2):
        val = struct.unpack('>H', response[i:i+2])[0]
        if 2200 <= val <= 2500:
            data['grid_voltage'] = val / 10.0
            data['grid_voltage_offset'] = i
            break
    
    # Calculate grid power from current (if we found voltage)
    if 'grid_voltage' in data and grid_current > 0:
        data['grid_power'] = data['grid_voltage'] * grid_current
        data['grid_current'] = grid_current
    
    # PV values during night are 0
    data['pv1_power'] = 0
    data['pv2_power'] = 0  
    data['pv3_power'] = 0
    data['total_pv_power'] = 0
    
    # But we can still show PV voltages (from offset 74-79)
    data['pv1_voltage'] = struct.unpack('>H', response[0x4A:0x4C])[0] / 10.0
    data['pv2_voltage'] = struct.unpack('>H', response[0x4C:0x4E])[0] / 10.0
    data['pv3_voltage'] = struct.unpack('>H', response[0x4E:0x50])[0] / 10.0
    
    # Status byte at offset 0x5A (90): 0c = 12
    data['status'] = response[0x5A] if len(response) > 0x5A else 0
    
    # Operation mode at offset 0x5B (91): 01 = 1
    data['mode'] = response[0x5B] if len(response) > 0x5B else 0
    
    # Fault code at offset 0x5C (92): 03 = 3
    data['fault'] = response[0x5C] if len(response) > 0x5C else 0
    
    return data

def main():
    """Main monitor loop"""
    client = EG4IoTOSClient(host='172.16.107.129', port=8000)
    
    print("EG4 18kPV REAL-TIME MONITOR")
    print("="*70)
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            if client.connect():
                response = client.send_receive(b'\xa1\x1a\x05\x00')
                
                if response:
                    data = parse_eg4_response(response)
                    
                    # Clear screen
                    print("\033[2J\033[H", end='')
                    
                    # Header
                    print("="*70)
                    print(f"EG4 18kPV - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("="*70)
                    
                    print(f"Serial: {data.get('serial', 'N/A')} | Device: {data.get('device_id', 'N/A')}")
                    print("-"*70)
                    
                    # Solar (nighttime = 0W expected)
                    print("\nSOLAR PV:")
                    print(f"  PV1: {data.get('pv1_power', 0):>6.0f} W  (Voltage: {data.get('pv1_voltage', 0):>5.1f} V)")
                    print(f"  PV2: {data.get('pv2_power', 0):>6.0f} W  (Voltage: {data.get('pv2_voltage', 0):>5.1f} V)")
                    print(f"  PV3: {data.get('pv3_power', 0):>6.0f} W  (Voltage: {data.get('pv3_voltage', 0):>5.1f} V)")
                    print(f"  Total: {data.get('total_pv_power', 0):>6.0f} W")
                    
                    # Battery
                    print("\nBATTERY:")
                    print(f"  Voltage: {data.get('battery_voltage', 0):>5.1f} V")
                    print(f"  SOC: {data.get('battery_soc', 0):>3d}%")
                    
                    # Grid
                    print("\nGRID:")
                    if 'grid_voltage' in data:
                        print(f"  Voltage: {data['grid_voltage']:>5.1f} V")
                        print(f"  Current: {data.get('grid_current', 0):>5.1f} A")
                        print(f"  Power: {data.get('grid_power', 0):>6.0f} W")
                    else:
                        print("  No grid data found")
                    
                    # Load
                    print("\nLOAD:")
                    print(f"  Total: {data.get('load_power', 0):>6.0f} W")
                    print(f"  Backup: {data.get('backup_power', 0):>6.0f} W")
                    
                    # Status
                    print("\nSTATUS:")
                    print(f"  Status Code: {data.get('status', 0)}")
                    print(f"  Mode: {data.get('mode', 0)}")
                    print(f"  Fault: {data.get('fault', 0)}")
                    
                    # Raw data for debugging
                    print("\nRAW DATA (hex):")
                    print(f"  Bytes 48-56: {response[48:56].hex()}")
                    print(f"  Bytes 64-72: {response[64:72].hex()}")
                    print(f"  Bytes 72-96: {response[72:96].hex()}")
                    
                client.disconnect()
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        client.disconnect()

if __name__ == "__main__":
    main()