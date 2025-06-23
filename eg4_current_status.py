#!/usr/bin/env python3
"""Get current status from EG4 inverter"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
from datetime import datetime

# Connect
client = EG4IoTOSClient(host='172.16.107.129', port=8000)

if client.connect():
    print("✅ Connected to EG4 18kPV Inverter")
    
    # Query
    response = client.send_receive(b'\xa1\x1a\x05\x00')
    
    if response and len(response) >= 100:
        print(f"\n📅 Status at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Parse key values based on our analysis
        serial = response[8:19].decode('ascii', errors='ignore').strip('\x00')
        battery_voltage = struct.unpack('>H', response[82:84])[0] / 100.0
        battery_soc = response[85] if response[85] <= 100 else 0
        grid_voltage = struct.unpack('>H', response[60:62])[0] / 10.0
        
        # Power values (these may need adjustment based on actual scaling)
        battery_power = struct.unpack('>h', response[48:50])[0]
        grid_power = struct.unpack('>h', response[50:52])[0]
        load_power = struct.unpack('>H', response[52:54])[0]
        
        print(f"🏷️  Serial: {serial}")
        print()
        
        print("🔋 BATTERY:")
        print(f"   Voltage: {battery_voltage:.1f} V")
        print(f"   SOC: {battery_soc}%")
        print(f"   Power: {battery_power} W")
        print()
        
        print("🏭 GRID:")
        print(f"   Voltage: {grid_voltage:.1f} V")
        print(f"   Power: {grid_power} W")
        print()
        
        print("🏠 LOAD:")
        print(f"   Power: {load_power} W")
        print()
        
        print("🌞 SOLAR (Nighttime - 0W expected):")
        print("   PV1: 0 W")
        print("   PV2: 0 W") 
        print("   PV3: 0 W")
        print()
        
        # Show all available fields
        print("📊 ALL AVAILABLE FIELDS:")
        print("-"*60)
        
        # Show interesting offsets with their values
        offsets = {
            48: ("Battery Power?", "h", 1),
            50: ("Grid Power?", "h", 1), 
            52: ("Load Power?", "H", 1),
            60: ("Grid Voltage", "H", 10),
            64: ("Load 1", "B", 1),
            68: ("Load 2", "B", 1),
            70: ("Temperature?", "B", 1),
            82: ("Battery Voltage", "H", 100),
            85: ("Battery SOC", "B", 1),
        }
        
        for offset, (name, fmt, divisor) in offsets.items():
            if offset + struct.calcsize(fmt) <= len(response):
                if fmt == 'B':
                    value = response[offset]
                else:
                    value = struct.unpack('>' + fmt, response[offset:offset+struct.calcsize(fmt)])[0]
                
                if divisor > 1:
                    print(f"   {name}: {value}/{divisor} = {value/divisor:.1f}")
                else:
                    print(f"   {name}: {value}")
        
        # Save for analysis
        with open('eg4_current_response.bin', 'wb') as f:
            f.write(response)
        print("\n💾 Response saved to eg4_current_response.bin")
        
    else:
        print("❌ No response from inverter")
    
    client.disconnect()
    print("\n✅ Disconnected")
else:
    print("❌ Failed to connect to inverter")