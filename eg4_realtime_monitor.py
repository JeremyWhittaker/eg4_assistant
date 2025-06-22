#!/usr/bin/env python3
"""
EG4 Real-time Monitor
Shows all available data from EG4 inverter continuously
"""

import socket
import time
import struct
from datetime import datetime
import os

class EG4RealtimeMonitor:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.sock = None
        
    def connect(self):
        """Connect to EG4 dongle"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from EG4 dongle"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def send_receive(self, data):
        """Send data and receive response"""
        try:
            self.sock.send(data)
            time.sleep(0.1)
            response = self.sock.recv(4096)
            return response
        except Exception as e:
            print(f"Communication error: {e}")
            return None
    
    def parse_eg4_response(self, response):
        """Parse EG4 protocol response to extract all available fields"""
        data = {}
        
        if not response or len(response) < 100:
            return data
        
        try:
            # Header info
            if len(response) >= 35:
                data['serial_number'] = response[8:19].decode('ascii', errors='ignore').strip('\x00')
                data['device_id'] = response[24:35].decode('ascii', errors='ignore').strip('\x00')
            
            # Power values (4-byte big-endian integers)
            if len(response) >= 69:
                data['pv1_power'] = int.from_bytes(response[37:41], 'big', signed=True)
                data['pv2_power'] = int.from_bytes(response[41:45], 'big', signed=True)
                data['pv3_power'] = int.from_bytes(response[45:49], 'big', signed=True)
                data['total_pv_power'] = int.from_bytes(response[49:53], 'big', signed=True)
                data['battery_power'] = int.from_bytes(response[53:57], 'big', signed=True)
                data['grid_power'] = int.from_bytes(response[57:61], 'big', signed=True)
                data['backup_power'] = int.from_bytes(response[61:65], 'big', signed=True)
                data['load_power'] = int.from_bytes(response[65:69], 'big', signed=True)
                
                # Apply scaling for some values
                if data['pv1_power'] > 20000:
                    data['pv1_power'] = data['pv1_power'] / 10
                if data['pv3_power'] > 20000:
                    data['pv3_power'] = data['pv3_power'] / 10
            
            # Extended data query for more fields
            if len(response) >= 200:
                # Try to find voltage values (usually 2-byte values scaled by 10)
                offset = 70
                
                # Battery data
                if offset + 20 < len(response):
                    data['battery_voltage'] = struct.unpack('>H', response[offset:offset+2])[0] / 10.0
                    data['battery_current'] = struct.unpack('>h', response[offset+2:offset+4])[0] / 10.0
                    data['battery_soc'] = response[offset+4] if response[offset+4] <= 100 else 0
                    data['battery_temp'] = struct.unpack('>h', response[offset+6:offset+8])[0] / 10.0
                    offset += 10
                
                # Grid data
                if offset + 10 < len(response):
                    data['grid_voltage'] = struct.unpack('>H', response[offset:offset+2])[0] / 10.0
                    data['grid_frequency'] = struct.unpack('>H', response[offset+2:offset+4])[0] / 100.0
                    data['grid_current'] = struct.unpack('>h', response[offset+4:offset+6])[0] / 10.0
                    offset += 8
                
                # PV data
                if offset + 30 < len(response):
                    data['pv1_voltage'] = struct.unpack('>H', response[offset:offset+2])[0] / 10.0
                    data['pv1_current'] = struct.unpack('>H', response[offset+2:offset+4])[0] / 10.0
                    data['pv2_voltage'] = struct.unpack('>H', response[offset+4:offset+6])[0] / 10.0
                    data['pv2_current'] = struct.unpack('>H', response[offset+6:offset+8])[0] / 10.0
                    data['pv3_voltage'] = struct.unpack('>H', response[offset+8:offset+10])[0] / 10.0
                    data['pv3_current'] = struct.unpack('>H', response[offset+10:offset+12])[0] / 10.0
                    offset += 12
                
                # Inverter data
                if offset + 20 < len(response):
                    data['inverter_temp'] = struct.unpack('>h', response[offset:offset+2])[0] / 10.0
                    data['dc_bus_voltage'] = struct.unpack('>H', response[offset+2:offset+4])[0] / 10.0
                    data['output_voltage'] = struct.unpack('>H', response[offset+4:offset+6])[0] / 10.0
                    data['output_frequency'] = struct.unpack('>H', response[offset+6:offset+8])[0] / 100.0
                    offset += 10
                
                # Energy counters
                if offset + 40 < len(response):
                    data['today_pv_energy'] = struct.unpack('>I', response[offset:offset+4])[0] / 10.0
                    data['total_pv_energy'] = struct.unpack('>I', response[offset+4:offset+8])[0] / 10.0
                    data['today_battery_charge'] = struct.unpack('>I', response[offset+8:offset+12])[0] / 10.0
                    data['today_battery_discharge'] = struct.unpack('>I', response[offset+12:offset+16])[0] / 10.0
                    data['today_grid_import'] = struct.unpack('>I', response[offset+16:offset+20])[0] / 10.0
                    data['today_grid_export'] = struct.unpack('>I', response[offset+20:offset+24])[0] / 10.0
                    data['today_load_energy'] = struct.unpack('>I', response[offset+24:offset+28])[0] / 10.0
                
            # Try to find additional fields in the response
            # Look for battery SOC in different locations
            if 'battery_soc' not in data or data['battery_soc'] == 0:
                for i in range(70, min(len(response), 150)):
                    if 0 < response[i] <= 100:
                        # Likely battery SOC
                        data['battery_soc'] = response[i]
                        break
            
            # System status flags
            if len(response) > 180:
                status_offset = 150
                data['inverter_status'] = response[status_offset]
                data['battery_status'] = response[status_offset + 1]
                data['grid_status'] = response[status_offset + 2]
                data['load_status'] = response[status_offset + 3]
                
                # Decode status
                status_map = {0: 'Standby', 1: 'Running', 2: 'Fault', 3: 'Warning'}
                data['inverter_status_text'] = status_map.get(data['inverter_status'], 'Unknown')
            
        except Exception as e:
            print(f"Parse error: {e}")
        
        return data
    
    def query_all_data(self):
        """Query all available data from inverter"""
        # EG4 IoTOS protocol query commands
        commands = [
            b'\xa1\x1a\x05\x00',  # Basic query
            b'\xa1\x1a\x05\x01',  # Extended query 1
            b'\xa1\x1a\x05\x02',  # Extended query 2
            b'\xa1\x1b\x06\x00\x00\x64',  # Read 100 registers
        ]
        
        all_data = {}
        
        for cmd in commands:
            response = self.send_receive(cmd)
            if response:
                data = self.parse_eg4_response(response)
                all_data.update(data)
                
                # Save raw response for analysis
                with open(f'eg4_response_{cmd.hex()}.bin', 'wb') as f:
                    f.write(response)
        
        return all_data
    
    def display_data(self, data):
        """Display all data in organized format"""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("="*80)
        print(f"EG4 18kPV REAL-TIME MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        if not data:
            print("NO DATA AVAILABLE")
            return
        
        # Device info
        print(f"\nDEVICE INFO:")
        print(f"  Serial: {data.get('serial_number', 'N/A')}")
        print(f"  Device ID: {data.get('device_id', 'N/A')}")
        print(f"  Status: {data.get('inverter_status_text', 'Unknown')}")
        
        # Solar PV
        print(f"\nSOLAR PV:")
        print(f"  PV1: {data.get('pv1_voltage', 0):.1f}V  {data.get('pv1_current', 0):.1f}A  {data.get('pv1_power', 0):.0f}W")
        print(f"  PV2: {data.get('pv2_voltage', 0):.1f}V  {data.get('pv2_current', 0):.1f}A  {data.get('pv2_power', 0):.0f}W")
        print(f"  PV3: {data.get('pv3_voltage', 0):.1f}V  {data.get('pv3_current', 0):.1f}A  {data.get('pv3_power', 0):.0f}W")
        print(f"  Total: {data.get('total_pv_power', 0):.0f}W")
        
        # Battery
        print(f"\nBATTERY:")
        print(f"  Voltage: {data.get('battery_voltage', 0):.1f}V")
        print(f"  Current: {data.get('battery_current', 0):.1f}A")
        print(f"  Power: {data.get('battery_power', 0):.0f}W")
        print(f"  SOC: {data.get('battery_soc', 0)}%")
        print(f"  Temperature: {data.get('battery_temp', 0):.1f}°C")
        print(f"  Status: {'Charging' if data.get('battery_power', 0) > 0 else 'Discharging' if data.get('battery_power', 0) < 0 else 'Idle'}")
        
        # Grid
        print(f"\nGRID:")
        print(f"  Voltage: {data.get('grid_voltage', 0):.1f}V")
        print(f"  Frequency: {data.get('grid_frequency', 0):.2f}Hz")
        print(f"  Current: {data.get('grid_current', 0):.1f}A")
        print(f"  Power: {data.get('grid_power', 0):.0f}W")
        print(f"  Status: {'Importing' if data.get('grid_power', 0) > 0 else 'Exporting' if data.get('grid_power', 0) < 0 else 'Standby'}")
        
        # Load
        print(f"\nLOAD:")
        print(f"  Power: {data.get('load_power', 0):.0f}W")
        print(f"  Backup Power: {data.get('backup_power', 0):.0f}W")
        
        # Inverter
        print(f"\nINVERTER:")
        print(f"  Temperature: {data.get('inverter_temp', 0):.1f}°C")
        print(f"  DC Bus Voltage: {data.get('dc_bus_voltage', 0):.1f}V")
        print(f"  Output Voltage: {data.get('output_voltage', 0):.1f}V")
        print(f"  Output Frequency: {data.get('output_frequency', 0):.2f}Hz")
        
        # Energy counters
        print(f"\nTODAY'S ENERGY:")
        print(f"  PV Generation: {data.get('today_pv_energy', 0):.1f} kWh")
        print(f"  Battery Charge: {data.get('today_battery_charge', 0):.1f} kWh")
        print(f"  Battery Discharge: {data.get('today_battery_discharge', 0):.1f} kWh")
        print(f"  Grid Import: {data.get('today_grid_import', 0):.1f} kWh")
        print(f"  Grid Export: {data.get('today_grid_export', 0):.1f} kWh")
        print(f"  Load Consumption: {data.get('today_load_energy', 0):.1f} kWh")
        
        print(f"\nTOTAL ENERGY:")
        print(f"  PV Generation: {data.get('total_pv_energy', 0):.1f} kWh")
        
        # Show all fields
        print(f"\nALL AVAILABLE FIELDS ({len(data)}):")
        print("-"*40)
        for key, value in sorted(data.items()):
            print(f"  {key}: {value}")
    
    def run(self):
        """Run the monitor"""
        print("Starting EG4 Real-time Monitor...")
        print(f"Connecting to {self.host}:{self.port}")
        
        if not self.connect():
            print("Failed to connect!")
            return
        
        print("Connected! Press Ctrl+C to stop.\n")
        
        try:
            while True:
                data = self.query_all_data()
                self.display_data(data)
                time.sleep(2)  # Update every 2 seconds
                
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.disconnect()
            print("Disconnected")

if __name__ == "__main__":
    monitor = EG4RealtimeMonitor()
    monitor.run()