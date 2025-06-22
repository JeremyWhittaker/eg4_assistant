#!/usr/bin/env python3
"""
EG4 Monitor - Works day and night
Shows all available data with proper parsing
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
from datetime import datetime

def parse_eg4_night_data(response):
    """Parse EG4 data including nighttime values"""
    data = {}
    
    if not response or len(response) < 100:
        return data
    
    # Basic info
    data['serial'] = response[8:19].decode('ascii', errors='ignore').strip('\x00')
    data['device_id'] = response[24:35].decode('ascii', errors='ignore').strip('\x00')
    
    # Power values (4-byte big-endian at fixed offsets)
    # During night, PV values will be 0
    data['pv1_power'] = int.from_bytes(response[37:41], 'big', signed=True)
    data['pv2_power'] = int.from_bytes(response[41:45], 'big', signed=True)
    data['pv3_power'] = int.from_bytes(response[45:49], 'big', signed=True)
    
    # The response shows mostly zeros, but let's look at the non-zero areas
    # Bytes 70-90 contain some data
    
    # From hex dump: 00000008059c04a3044e002d16640114
    # Let's parse this area more carefully
    offset = 70
    
    # Try different interpretations
    if len(response) > offset + 20:
        # 2-byte values starting at offset 76
        val1 = struct.unpack('>H', response[76:78])[0]  # 059c = 1436
        val2 = struct.unpack('>H', response[78:80])[0]  # 04a3 = 1187
        val3 = struct.unpack('>H', response[80:82])[0]  # 044e = 1102
        val4 = struct.unpack('>H', response[82:84])[0]  # 002d = 45
        val5 = struct.unpack('>H', response[84:86])[0]  # 1664 = 5732
        val6 = struct.unpack('>H', response[86:88])[0]  # 0114 = 276
        
        # These could be voltages (divide by 10)
        if 400 < val1 < 600:  # PV voltage range
            data['pv1_voltage'] = val1 / 10
        if 400 < val2 < 600:
            data['pv2_voltage'] = val2 / 10
        if 400 < val3 < 600:
            data['pv3_voltage'] = val3 / 10
            
        # Battery voltage (48V system = 40-60V range)
        if 400 < val5 < 600:
            data['battery_voltage'] = val5 / 10
            
        # Grid voltage (200-250V range)
        # val6 = 276, but if this is voltage*10 = 27.6V (too low)
        # Could be current instead
        
        # Look for grid voltage in other locations
        grid_offset = 90
        if len(response) > grid_offset + 4:
            # Try 4-byte value
            grid_val = struct.unpack('>I', response[grid_offset:grid_offset+4])[0]
            if 2000 < grid_val < 2500:  # 200-250V * 10
                data['grid_voltage'] = grid_val / 10
    
    # Battery SOC - single byte value 0-100
    # From the hex dump, byte 83 shows value 100 (0x64)
    if len(response) > 83:
        soc = response[83]
        if 0 <= soc <= 100:
            data['battery_soc'] = soc
    
    # Try to find actual power values in extended area
    # Since it's nighttime, we expect:
    # - PV power = 0
    # - Battery power = negative (discharging) or 0
    # - Grid power = positive (importing)
    # - Load power = positive
    
    # The large values in the original parse might need different scaling
    # Let's check bytes 45-69 more carefully
    raw_total_pv = int.from_bytes(response[49:53], 'big', signed=True)
    raw_battery = int.from_bytes(response[53:57], 'big', signed=True)
    raw_grid = int.from_bytes(response[57:61], 'big', signed=True)
    raw_backup = int.from_bytes(response[61:65], 'big', signed=True)
    raw_load = int.from_bytes(response[65:69], 'big', signed=True)
    
    # Show raw values for debugging
    data['raw_values'] = {
        'total_pv': raw_total_pv,
        'battery': raw_battery,
        'grid': raw_grid,
        'backup': raw_backup,
        'load': raw_load
    }
    
    # Apply scaling based on typical values
    # If it's nighttime and values are 0, that's correct
    data['total_pv_power'] = 0 if abs(raw_total_pv) > 1000000 else raw_total_pv
    data['battery_power'] = raw_battery
    data['grid_power'] = raw_grid
    data['backup_power'] = raw_backup
    data['load_power'] = raw_load if raw_load < 100000 else raw_load / 100
    
    return data

def monitor_eg4():
    """Monitor EG4 continuously"""
    client = EG4IoTOSClient(host='172.16.107.129', port=8000)
    
    print("EG4 18kPV NIGHTTIME MONITOR")
    print("="*60)
    print("Connecting to 172.16.107.129:8000")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            if client.connect():
                response = client.send_receive(b'\xa1\x1a\x05\x00')
                
                if response:
                    data = parse_eg4_night_data(response)
                    
                    # Display
                    print(f"\n{'='*60}")
                    print(f"UPDATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"{'='*60}")
                    
                    print(f"Device: {data.get('serial', 'N/A')} - {data.get('device_id', 'N/A')}")
                    print()
                    
                    # It's nighttime, so PV should be 0
                    print("SOLAR PV (Nighttime - Expected 0W):")
                    print(f"  PV1: {data.get('pv1_power', 0)} W @ {data.get('pv1_voltage', 0):.1f} V")
                    print(f"  PV2: {data.get('pv2_power', 0)} W @ {data.get('pv2_voltage', 0):.1f} V")
                    print(f"  PV3: {data.get('pv3_power', 0)} W @ {data.get('pv3_voltage', 0):.1f} V")
                    print(f"  Total: {data.get('total_pv_power', 0)} W")
                    
                    print("\nBATTERY:")
                    print(f"  Voltage: {data.get('battery_voltage', 0):.1f} V")
                    print(f"  SOC: {data.get('battery_soc', 0)}%")
                    print(f"  Power: {data.get('battery_power', 0)} W")
                    
                    print("\nGRID:")
                    print(f"  Voltage: {data.get('grid_voltage', 0):.1f} V")
                    print(f"  Power: {data.get('grid_power', 0)} W")
                    
                    print("\nLOAD:")
                    print(f"  Power: {data.get('load_power', 0):.1f} W")
                    print(f"  Backup: {data.get('backup_power', 0)} W")
                    
                    # Debug info
                    print("\nDEBUG - Raw values:")
                    for k, v in data.get('raw_values', {}).items():
                        print(f"  {k}: {v}")
                    
                    # Show interesting bytes
                    print(f"\nResponse bytes 70-90: {response[70:90].hex()}")
                
                client.disconnect()
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        client.disconnect()

if __name__ == "__main__":
    monitor_eg4()