#!/usr/bin/env python3
"""
EG4 Protocol Parser - Based on reverse engineering Solar Assistant
This correctly parses the IoTOS protocol response
"""

import socket
import struct
import time
from datetime import datetime

class EG4Parser:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        
    def connect_and_query(self):
        """Connect and send query command"""
        try:
            s = socket.socket()
            s.settimeout(10)
            s.connect((self.host, self.port))
            
            # Send the command Solar Assistant uses
            s.send(b'\xa1\x1a\x05\x00')
            
            # Get response
            response = s.recv(512)
            s.close()
            
            if len(response) >= 100:
                return response
            return None
            
        except Exception as e:
            print(f"Connection error: {e}")
            return None
    
    def parse_response(self, response):
        """Parse response based on Solar Assistant's method"""
        if len(response) < 100:
            return None
            
        data = {}
        
        # The response format is:
        # 0-3: Header (a1 1a 05 00)
        # 4: Length
        # 8-20: Serial number
        # After some fixed headers, the data begins
        
        # Based on tcpdump analysis, the actual data offsets are:
        # Power values start around offset 48-54 in most responses
        # But we need to account for the variable header length
        
        # Find the data section by looking for known markers
        # The pattern "00 00 50" often appears before power data
        data_offset = 0
        for i in range(30, min(len(response)-20, 60)):
            # Look for patterns that indicate start of data
            if i + 20 < len(response):
                # Power values are typically in this region
                # Let's try different offsets based on response patterns
                
                # Method 1: Fixed offset from tcpdump analysis
                if i == 48:  # This is where power often starts
                    battery_power = struct.unpack('>h', response[i:i+2])[0]
                    grid_power = struct.unpack('>h', response[i+2:i+4])[0]
                    load_power = struct.unpack('>H', response[i+4:i+6])[0]
                    
                    # Sanity check - power values should be reasonable
                    if abs(battery_power) < 20000 and abs(grid_power) < 20000 and load_power < 20000:
                        data['battery_power'] = battery_power
                        data['grid_power'] = grid_power
                        data['load_power'] = load_power
                        data_offset = i
                        break
        
        # Battery voltage and SOC are more consistent in location
        # From tcpdump: typically at offset 82-85
        if len(response) > 85:
            batt_v = struct.unpack('>H', response[82:84])[0]
            if 4000 <= batt_v <= 6000:  # 40-60V range
                data['battery_voltage'] = batt_v / 100.0
                
            soc = response[85]
            if soc <= 100:
                data['battery_soc'] = soc
        
        # PV voltages at offset 74-80
        if len(response) > 80:
            pv1 = struct.unpack('>H', response[74:76])[0]
            pv2 = struct.unpack('>H', response[76:78])[0]
            pv3 = struct.unpack('>H', response[78:80])[0]
            
            # PV voltages should be 0-500V
            if pv1 < 5000:
                data['pv1_voltage'] = pv1 / 10.0
            if pv2 < 5000:
                data['pv2_voltage'] = pv2 / 10.0
            if pv3 < 5000:
                data['pv3_voltage'] = pv3 / 10.0
        
        # Grid voltage - search in typical locations
        for offset in [90, 92, 94, 96]:
            if offset + 2 <= len(response):
                val = struct.unpack('>H', response[offset:offset+2])[0]
                if 2200 <= val <= 2600:  # 220-260V
                    data['grid_voltage'] = val / 10.0
                    break
        
        # Calculate PV power
        if 'grid_power' in data and 'load_power' in data:
            if data['grid_power'] < 0:  # Exporting
                data['pv_power'] = data['load_power'] + data.get('battery_power', 0) + abs(data['grid_power'])
            else:
                data['pv_power'] = max(0, data['load_power'] + data.get('battery_power', 0) - data['grid_power'])
                
        return data
    
    def display(self, data):
        """Display parsed data"""
        print(f"\n{'='*60}")
        print(f"EG4 18kPV Data - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        if not data:
            print("NO DATA")
            return
            
        # Battery
        print(f"\nBATTERY:")
        if 'battery_voltage' in data:
            print(f"  Voltage: {data['battery_voltage']:.1f} V")
        if 'battery_soc' in data:
            print(f"  SOC: {data['battery_soc']}%")
        if 'battery_power' in data:
            bp = data['battery_power']
            print(f"  Power: {bp:+d} W", end='')
            if bp > 50:
                print(" [CHARGING]")
            elif bp < -50:
                print(" [DISCHARGING]")
            else:
                print(" [IDLE]")
        
        # Grid
        print(f"\nGRID:")
        if 'grid_voltage' in data:
            print(f"  Voltage: {data['grid_voltage']:.1f} V")
        if 'grid_power' in data:
            gp = data['grid_power']
            print(f"  Power: {gp:+d} W", end='')
            if gp < -50:
                print(" [EXPORTING]")
            elif gp > 50:
                print(" [IMPORTING]")
            else:
                print()
        
        # Solar
        print(f"\nSOLAR:")
        if 'pv_power' in data:
            print(f"  Total Power: {data['pv_power']:.0f} W")
        if 'pv1_voltage' in data:
            print(f"  PV1: {data['pv1_voltage']:.1f} V")
        if 'pv2_voltage' in data:
            print(f"  PV2: {data['pv2_voltage']:.1f} V")
        if 'pv3_voltage' in data:
            print(f"  PV3: {data['pv3_voltage']:.1f} V")
        
        # Load
        if 'load_power' in data:
            print(f"\nLOAD: {data['load_power']} W")
            
    def run_once(self):
        """Get and display data once"""
        response = self.connect_and_query()
        if response:
            data = self.parse_response(response)
            self.display(data)
            return data
        return None
        
    def run_continuous(self):
        """Run continuous monitoring"""
        print("EG4 Direct Monitor - Connecting to 172.16.107.129:8000")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                self.run_once()
                time.sleep(5)
            except KeyboardInterrupt:
                print("\nStopping...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    parser = EG4Parser()
    
    # First test single query
    print("Testing connection...")
    data = parser.run_once()
    
    if data:
        print("\n✓ Successfully connected to EG4!")
        print("\nStarting continuous monitoring...")
        time.sleep(2)
        parser.run_continuous()
    else:
        print("\n✗ Failed to connect to EG4")
        print("Solar Assistant may be using the connection")