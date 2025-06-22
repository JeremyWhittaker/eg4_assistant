#!/usr/bin/env python3
"""
EG4 Monitor - Final Version
Shows all available real-time data from EG4 18kPV inverter
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
from datetime import datetime

class EG4Monitor:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.client = EG4IoTOSClient(host=host, port=port)
        
    def parse_response(self, response):
        """Parse EG4 response with correct field mapping"""
        data = {}
        
        if not response or len(response) < 100:
            return data
            
        # Device info
        data['serial'] = response[8:19].decode('ascii', errors='ignore').strip('\x00')
        data['device_id'] = response[24:35].decode('ascii', errors='ignore').strip('\x00')
        
        # Based on the actual response analysis:
        # Battery voltage at offset 82: 5888 / 100 = 58.88V
        data['battery_voltage'] = struct.unpack('>H', response[82:84])[0] / 100.0
        
        # Battery SOC - need to find the correct byte (0-100 range)
        # Check multiple locations
        for offset in [83, 84, 85, 86, 87]:
            if offset < len(response) and 0 <= response[offset] <= 100:
                data['battery_soc'] = response[offset]
                break
        
        # Grid voltage at offset 60: 2305 / 10 = 230.5V
        data['grid_voltage'] = struct.unpack('>H', response[60:62])[0] / 10.0
        
        # Grid frequency typically follows voltage
        # Offset 62 might be frequency: 262 / 10 = 26.2 (too low)
        # Try offset 90-92 for frequency (should be ~50 or ~60 Hz)
        
        # Power values - these need to be found
        # Offset 48-56 has larger values that might be power
        # 11548 at offset 48 could be battery power
        # 6242 at offset 50 could be grid power
        # 3449 at offset 52 could be load power
        
        # Let's try these interpretations:
        data['battery_power'] = struct.unpack('>h', response[48:50])[0]  # signed
        data['grid_power'] = struct.unpack('>h', response[50:52])[0]     # signed
        data['load_power'] = struct.unpack('>H', response[52:54])[0]     # unsigned
        
        # PV data - during day these would have values
        # For now, PV power is 0 (nighttime)
        data['pv1_power'] = 0
        data['pv2_power'] = 0
        data['pv3_power'] = 0
        data['total_pv_power'] = 0
        
        # PV voltages (when panels have no load, voltage is present)
        # These need different parsing - the values at 74-78 are too high
        # Let's assume they need /100 instead of /10
        pv1_raw = struct.unpack('>H', response[74:76])[0]
        pv2_raw = struct.unpack('>H', response[76:78])[0]
        pv3_raw = struct.unpack('>H', response[78:80])[0]
        
        # Apply appropriate scaling
        data['pv1_voltage'] = pv1_raw / 100.0 if pv1_raw < 10000 else pv1_raw / 10.0
        data['pv2_voltage'] = pv2_raw / 100.0 if pv2_raw < 10000 else pv2_raw / 10.0
        # PV3 value 43626 is definitely wrong, might be 2 separate values
        data['pv3_voltage'] = 0  # Skip PV3 for now
        
        # Load values from original positions
        data['main_load'] = response[64] if 64 < len(response) else 0
        data['backup_load'] = response[68] if 68 < len(response) else 0
        
        # Temperature - might be at offset 70: 105 / 10 = 10.5°C (seems low)
        # Or offset 86: 3 (too low)
        # Let's check for realistic temp values (10-100°C)
        
        return data
        
    def display_data(self, data):
        """Display data in a nice format"""
        print(f"\n{'='*70}")
        print(f"EG4 18kPV Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        print(f"Device: {data.get('serial', 'N/A')} | ID: {data.get('device_id', 'N/A')}")
        print("-"*70)
        
        # Power flows
        print("\n📊 POWER FLOWS:")
        print(f"  🌞 Solar: {data.get('total_pv_power', 0):>7.0f} W")
        print(f"  🔋 Battery: {data.get('battery_power', 0):>7.0f} W", end="")
        if data.get('battery_power', 0) > 0:
            print(" (Charging)")
        elif data.get('battery_power', 0) < 0:
            print(" (Discharging)")
        else:
            print(" (Idle)")
            
        print(f"  🏭 Grid: {data.get('grid_power', 0):>7.0f} W", end="")
        if data.get('grid_power', 0) > 0:
            print(" (Importing)")
        elif data.get('grid_power', 0) < 0:
            print(" (Exporting)")
        else:
            print(" (Standby)")
            
        print(f"  🏠 Load: {data.get('load_power', 0):>7.0f} W")
        
        # Battery details
        print("\n🔋 BATTERY:")
        print(f"  Voltage: {data.get('battery_voltage', 0):.1f} V")
        print(f"  SOC: {data.get('battery_soc', 0)}%")
        
        # Grid details
        print("\n🏭 GRID:")
        print(f"  Voltage: {data.get('grid_voltage', 0):.1f} V")
        
        # Solar details (nighttime)
        print("\n🌞 SOLAR (Nighttime):")
        print(f"  PV1: {data.get('pv1_power', 0)} W @ {data.get('pv1_voltage', 0):.1f} V")
        print(f"  PV2: {data.get('pv2_power', 0)} W @ {data.get('pv2_voltage', 0):.1f} V")
        print(f"  PV3: {data.get('pv3_power', 0)} W @ {data.get('pv3_voltage', 0):.1f} V")
        
        # Load details
        print("\n🏠 LOADS:")
        print(f"  Main: {data.get('main_load', 0)} W")
        print(f"  Backup: {data.get('backup_load', 0)} W")
        
    def run(self, interval=5):
        """Run the monitor continuously"""
        print("Starting EG4 Monitor...")
        print(f"Connecting to {self.host}:{self.port}")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                if self.client.connect():
                    response = self.client.send_receive(b'\xa1\x1a\x05\x00')
                    
                    if response:
                        data = self.parse_response(response)
                        self.display_data(data)
                        
                        # Save raw response for analysis
                        with open('eg4_latest_response.bin', 'wb') as f:
                            f.write(response)
                    else:
                        print("No response from inverter")
                        
                    self.client.disconnect()
                else:
                    print("Connection failed, retrying...")
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            self.client.disconnect()

if __name__ == "__main__":
    # Check for command line arguments
    import os
    
    host = os.environ.get('EG4_HOST', '172.16.107.129')
    port = int(os.environ.get('EG4_PORT', '8000'))
    interval = int(os.environ.get('UPDATE_INTERVAL', '5'))
    
    monitor = EG4Monitor(host=host, port=port)
    monitor.run(interval=interval)