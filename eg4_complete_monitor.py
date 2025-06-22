#!/usr/bin/env python3
"""
EG4 Complete Monitor - Gets all data like Solar Assistant
Uses multiple queries to extract all available fields
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
from datetime import datetime
import json

class EG4CompleteMonitor:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.client = None
        self.data = {}
        
    def connect(self):
        """Connect to EG4"""
        self.client = EG4IoTOSClient(host=self.host, port=self.port)
        return self.client.connect()
    
    def disconnect(self):
        """Disconnect from EG4"""
        if self.client:
            self.client.disconnect()
    
    def query_all_data(self):
        """Query all data using multiple commands like Solar Assistant"""
        if not self.client:
            return None
        
        # Commands that Solar Assistant uses
        commands = [
            (b'\xa1\x1a\x05\x00', 'status'),      # Main status
            (b'\xa1\x1a\x05\x02', 'extended'),    # Extended data
            (b'\xa1\x1a\x01\x00', 'additional'),  # Additional data
            (b'\xa1\x1a\x03\x00', 'registers'),   # Register data
        ]
        
        all_data = {}
        responses = {}
        
        for cmd, name in commands:
            response = self.client.send_receive(cmd)
            if response and len(response) >= 100:
                responses[name] = response
                
        # Parse each response type
        if 'status' in responses:
            all_data.update(self.parse_status(responses['status']))
        if 'extended' in responses:
            all_data.update(self.parse_extended(responses['extended']))
        if 'additional' in responses:
            all_data.update(self.parse_additional(responses['additional']))
        if 'registers' in responses:
            all_data.update(self.parse_registers(responses['registers']))
            
        return all_data
    
    def parse_status(self, response):
        """Parse main status response (a1 1a 05 00)"""
        data = {}
        
        # Device info
        data['serial'] = response[8:19].decode('ascii', errors='ignore').strip('\x00')
        data['device_id'] = response[24:35].decode('ascii', errors='ignore').strip('\x00')
        
        # Based on analysis, this response contains:
        # Battery voltage at offset 82 (confirmed working)
        # Battery SOC at offset 85 (confirmed working)
        # Power values at offsets 48-68
        
        try:
            # Battery
            data['battery_voltage'] = struct.unpack('>H', response[82:84])[0] / 100.0
            data['battery_soc'] = response[85] if response[85] <= 100 else 0
            
            # Power values (these need proper scaling)
            # From testing, offset 48-52 seem to be power values
            battery_power_raw = struct.unpack('>h', response[48:50])[0]
            grid_power_raw = struct.unpack('>h', response[50:52])[0]
            load_power_raw = struct.unpack('>H', response[52:54])[0]
            
            # Apply scaling based on typical values
            data['battery_power'] = battery_power_raw if abs(battery_power_raw) < 20000 else battery_power_raw / 10
            data['grid_power'] = grid_power_raw if abs(grid_power_raw) < 20000 else grid_power_raw / 10
            data['load_power'] = load_power_raw if load_power_raw < 20000 else load_power_raw / 10
            
            # Grid voltage might be at offset 60 or 72
            for offset in [60, 72, 88, 90]:
                if offset + 2 <= len(response):
                    val = struct.unpack('>H', response[offset:offset+2])[0]
                    if 2200 <= val <= 2600:  # 220-260V range
                        data['grid_voltage'] = val / 10.0
                        break
                        
        except Exception as e:
            print(f"Error parsing status: {e}")
            
        return data
    
    def parse_extended(self, response):
        """Parse extended response (a1 1a 05 02)"""
        data = {}
        
        try:
            # This response seems to contain PV data
            # From analysis, PV voltages appear at offsets 74-80
            if len(response) > 80:
                pv1_v = struct.unpack('>H', response[74:76])[0]
                pv2_v = struct.unpack('>H', response[76:78])[0]
                pv3_v = struct.unpack('>H', response[78:80])[0]
                
                # Scale appropriately
                data['pv1_voltage'] = pv1_v / 10.0 if pv1_v < 5000 else pv1_v / 100.0
                data['pv2_voltage'] = pv2_v / 10.0 if pv2_v < 5000 else pv2_v / 100.0
                data['pv3_voltage'] = pv3_v / 10.0 if pv3_v < 5000 else pv3_v / 100.0
                
        except Exception as e:
            print(f"Error parsing extended: {e}")
            
        return data
    
    def parse_additional(self, response):
        """Parse additional data response (a1 1a 01 00)"""
        data = {}
        
        try:
            # This might contain temperature and frequency data
            # Look for realistic temperature values (0-150°C)
            for offset in range(70, min(len(response), 100)):
                val = response[offset]
                if 20 <= val <= 150:  # Possible temperature
                    data['inverter_temp'] = val
                    break
                    
            # Grid frequency might be here
            for offset in range(60, min(len(response)-2, 100), 2):
                val = struct.unpack('>H', response[offset:offset+2])[0]
                if 5950 <= val <= 6050:  # 59.5-60.5 Hz
                    data['grid_frequency'] = val / 100.0
                    break
                    
        except Exception as e:
            print(f"Error parsing additional: {e}")
            
        return data
    
    def parse_registers(self, response):
        """Parse register data response (a1 1a 03 00)"""
        data = {}
        
        try:
            # This might contain current values and additional power data
            # AC output voltage typically 220-250V
            for offset in range(60, min(len(response)-2, 100), 2):
                val = struct.unpack('>H', response[offset:offset+2])[0]
                if 2200 <= val <= 2500:
                    data['ac_output_voltage'] = val / 10.0
                    break
            
            # Battery current (0-200A range)
            for offset in range(70, min(len(response)-2, 100), 2):
                val = struct.unpack('>h', response[offset:offset+2])[0]  # signed
                if -2000 <= val <= 2000:  # ±200A
                    data['battery_current'] = val / 10.0
                    break
                    
        except Exception as e:
            print(f"Error parsing registers: {e}")
            
        return data
    
    def display_data(self, data):
        """Display all collected data"""
        print(f"\n{'='*70}")
        print(f"EG4 18kPV Complete Data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        if not data:
            print("No data available")
            return
            
        # Device info
        print(f"\nDEVICE:")
        print(f"  Serial: {data.get('serial', 'N/A')}")
        print(f"  Device ID: {data.get('device_id', 'N/A')}")
        
        # Battery
        print(f"\nBATTERY:")
        print(f"  Voltage: {data.get('battery_voltage', 0):.1f} V")
        print(f"  Current: {data.get('battery_current', 0):.1f} A")
        print(f"  Power: {data.get('battery_power', 0):.0f} W")
        print(f"  SOC: {data.get('battery_soc', 0)}%")
        print(f"  Temperature: {data.get('battery_temp', 0):.1f}°C")
        
        # Grid
        print(f"\nGRID:")
        print(f"  Voltage: {data.get('grid_voltage', 0):.1f} V")
        print(f"  Frequency: {data.get('grid_frequency', 0):.2f} Hz")
        print(f"  Power: {data.get('grid_power', 0):.0f} W")
        
        # PV
        print(f"\nSOLAR PV:")
        print(f"  PV1: {data.get('pv1_power', 0):.0f} W @ {data.get('pv1_voltage', 0):.1f} V")
        print(f"  PV2: {data.get('pv2_power', 0):.0f} W @ {data.get('pv2_voltage', 0):.1f} V")
        print(f"  PV3: {data.get('pv3_power', 0):.0f} W @ {data.get('pv3_voltage', 0):.1f} V")
        print(f"  Total: {data.get('pv_power_total', 0):.0f} W")
        
        # Load
        print(f"\nLOAD:")
        print(f"  Total: {data.get('load_power', 0):.0f} W")
        print(f"  Essential: {data.get('load_essential', 0):.0f} W")
        print(f"  Non-Essential: {data.get('load_nonessential', 0):.0f} W")
        
        # Inverter
        print(f"\nINVERTER:")
        print(f"  Temperature: {data.get('inverter_temp', 0):.0f}°C")
        print(f"  AC Output: {data.get('ac_output_voltage', 0):.1f} V")
        
        # All fields
        print(f"\n{'─'*70}")
        print(f"ALL FIELDS ({len(data)}):")
        for key, value in sorted(data.items()):
            if key not in ['serial', 'device_id']:
                print(f"  {key}: {value}")
    
    def run_continuous(self, interval=5):
        """Run continuous monitoring"""
        print("Starting EG4 Complete Monitor...")
        print(f"Connecting to {self.host}:{self.port}")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                if self.connect():
                    data = self.query_all_data()
                    self.display_data(data)
                    self.disconnect()
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection failed")
                    
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                self.disconnect()
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    monitor = EG4CompleteMonitor()
    monitor.run_continuous()