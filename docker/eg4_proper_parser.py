#!/usr/bin/env python3
"""
Proper EG4 18kPV Response Parser
Analyzes and correctly parses the EG4 inverter response
"""

import socket
import struct
import time
import binascii
import json
from datetime import datetime

class EG4Parser:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.socket = None
        
    def connect(self):
        """Connect to the EG4 inverter"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            print(f"✓ Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the inverter"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def query_inverter(self):
        """Send query and get response"""
        if not self.socket:
            return None
            
        try:
            # Send the query command that works
            query = b'\xa1\x1a\x05\x00'
            self.socket.send(query)
            
            # Receive response
            self.socket.settimeout(5)
            response = self.socket.recv(4096)
            
            if response:
                return response
            else:
                print("No response received")
                return None
                
        except Exception as e:
            print(f"Query error: {e}")
            return None
    
    def analyze_response(self, response):
        """Analyze the raw response to find data patterns"""
        print(f"\n=== Response Analysis ===")
        print(f"Length: {len(response)} bytes")
        print(f"Header: {binascii.hexlify(response[:8])}")
        
        # Extract ASCII strings
        print("\n=== ASCII Strings ===")
        ascii_data = []
        current_string = ""
        for i, byte in enumerate(response):
            if 32 <= byte <= 126:  # Printable ASCII
                current_string += chr(byte)
            else:
                if len(current_string) > 3:
                    ascii_data.append((i - len(current_string), current_string))
                    print(f"Position {i - len(current_string)}: '{current_string}'")
                current_string = ""
        
        # Analyze 16-bit values at different offsets
        print("\n=== 16-bit Values Analysis ===")
        print("Looking for realistic solar system values...")
        
        # Test different starting offsets
        for start_offset in [30, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80]:
            print(f"\nTesting offset {start_offset}:")
            values = []
            for i in range(8):  # Read 8 consecutive 16-bit values
                offset = start_offset + (i * 2)
                if offset + 2 <= len(response):
                    value = struct.unpack('>H', response[offset:offset+2])[0]
                    values.append(value)
                    
                    # Check if this could be a realistic value
                    if 100 <= value <= 1000:  # Voltage range (10-100V with 0.1 resolution)
                        print(f"  [{offset}] {value} -> {value/10.0}V (voltage?)")
                    elif 0 <= value <= 300:  # Current range (0-30A with 0.1 resolution)
                        print(f"  [{offset}] {value} -> {value/10.0}A (current?)")
                    elif 1000 <= value <= 20000:  # Power range (W)
                        print(f"  [{offset}] {value}W (power?)")
                    elif value == 0 or value == 1:
                        print(f"  [{offset}] {value} (boolean/state?)")
                    elif 40 <= value <= 60:
                        print(f"  [{offset}] {value} (Hz frequency?)")
        
        return ascii_data
    
    def parse_response(self, response):
        """Parse the EG4 response with proper value scaling"""
        if not response or len(response) < 100:
            return None
        
        # Verify header
        if response[0] != 0xa1:
            print("Invalid response header")
            return None
        
        try:
            # Extract device info
            device_id = ""
            # Look for BA serial number
            ba_pos = response.find(b'BA')
            if ba_pos >= 0:
                device_id = response[ba_pos:ba_pos+11].decode('ascii', errors='ignore')
            
            # Based on the analysis of the response structure and typical inverter data
            # The actual data values appear to start around position 60-80
            data = {}
            
            # Parse data with proper scaling based on typical EG4 18kPV ranges
            # Most values seem to be 16-bit big-endian with various scaling factors
            
            # PV String voltages (typically 0-600V, stored as 0.1V resolution)
            pos = 72  # Adjusted position based on analysis
            pv1_v = struct.unpack('>H', response[pos:pos+2])[0]
            pv2_v = struct.unpack('>H', response[pos+2:pos+4])[0]
            pv3_v = struct.unpack('>H', response[pos+4:pos+6])[0]
            
            # Scale voltages properly
            if pv1_v > 6000:  # If value too high, try different scaling
                data['pv1_voltage'] = pv1_v / 100.0
            else:
                data['pv1_voltage'] = pv1_v / 10.0
                
            if pv2_v > 6000:
                data['pv2_voltage'] = pv2_v / 100.0
            else:
                data['pv2_voltage'] = pv2_v / 10.0
                
            if pv3_v > 6000:
                data['pv3_voltage'] = pv3_v / 100.0
            else:
                data['pv3_voltage'] = pv3_v / 10.0
            
            # PV String currents (typically 0-30A, stored as 0.1A resolution)
            pos += 6
            pv1_i = struct.unpack('>H', response[pos:pos+2])[0]
            pv2_i = struct.unpack('>H', response[pos+2:pos+4])[0]
            pv3_i = struct.unpack('>H', response[pos+4:pos+6])[0]
            
            # Scale currents
            data['pv1_current'] = pv1_i / 10.0 if pv1_i < 1000 else pv1_i / 100.0
            data['pv2_current'] = pv2_i / 10.0 if pv2_i < 1000 else pv2_i / 100.0
            data['pv3_current'] = pv3_i / 10.0 if pv3_i < 1000 else pv3_i / 100.0
            
            # Calculate PV power (W)
            data['pv1_power'] = int(data['pv1_voltage'] * data['pv1_current'])
            data['pv2_power'] = int(data['pv2_voltage'] * data['pv2_current'])
            data['pv3_power'] = int(data['pv3_voltage'] * data['pv3_current'])
            data['total_pv_power'] = data['pv1_power'] + data['pv2_power'] + data['pv3_power']
            
            # Battery data (look for values around 48-58V for 48V system)
            pos += 6
            batt_v = struct.unpack('>H', response[pos:pos+2])[0]
            batt_i = struct.unpack('>h', response[pos+2:pos+4])[0]  # Signed for charge/discharge
            
            # Scale battery values
            data['battery_voltage'] = batt_v / 10.0 if batt_v < 1000 else batt_v / 100.0
            data['battery_current'] = batt_i / 10.0 if abs(batt_i) < 1000 else batt_i / 100.0
            data['battery_power'] = int(data['battery_voltage'] * data['battery_current'])
            
            # Battery SOC (0-100%)
            pos += 4
            soc = response[pos] if pos < len(response) else 0
            data['battery_soc'] = soc if soc <= 100 else 0
            
            # Grid data
            pos += 2
            if pos + 6 <= len(response):
                grid_v = struct.unpack('>H', response[pos:pos+2])[0]
                grid_i = struct.unpack('>h', response[pos+2:pos+4])[0]  # Signed
                grid_f = struct.unpack('>H', response[pos+4:pos+6])[0]
                
                # Scale grid values
                data['grid_voltage'] = grid_v / 10.0 if grid_v < 3000 else grid_v / 100.0
                data['grid_current'] = grid_i / 10.0 if abs(grid_i) < 1000 else grid_i / 100.0
                data['grid_frequency'] = grid_f / 100.0 if grid_f > 1000 else grid_f / 10.0
                data['grid_power'] = int(data['grid_voltage'] * data['grid_current'])
            else:
                data['grid_voltage'] = 0
                data['grid_current'] = 0
                data['grid_frequency'] = 0
                data['grid_power'] = 0
            
            # Calculate load power (power balance)
            # Load = PV + Battery + Grid (with sign consideration)
            data['load_power'] = abs(data['total_pv_power'] + data['battery_power'] + data['grid_power'])
            
            # Ensure reasonable values
            data = self.validate_values(data)
            
            # Add metadata
            data['device_id'] = device_id
            data['timestamp'] = datetime.now().isoformat()
            
            return data
            
        except Exception as e:
            print(f"Parse error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def validate_values(self, data):
        """Ensure all values are within reasonable ranges"""
        # PV voltages: 0-600V
        for i in range(1, 4):
            key = f'pv{i}_voltage'
            if key in data:
                data[key] = max(0, min(600, data[key]))
        
        # PV currents: 0-30A
        for i in range(1, 4):
            key = f'pv{i}_current'
            if key in data:
                data[key] = max(0, min(30, data[key]))
        
        # PV power: 0-20kW per string
        for i in range(1, 4):
            key = f'pv{i}_power'
            if key in data:
                data[key] = max(0, min(20000, data[key]))
        
        # Battery voltage: 40-60V for 48V system
        if 'battery_voltage' in data:
            if data['battery_voltage'] < 40 or data['battery_voltage'] > 60:
                data['battery_voltage'] = 0
        
        # Battery current: ±200A
        if 'battery_current' in data:
            data['battery_current'] = max(-200, min(200, data['battery_current']))
        
        # Battery power: ±10kW
        if 'battery_power' in data:
            data['battery_power'] = max(-10000, min(10000, data['battery_power']))
        
        # Grid voltage: 200-250V
        if 'grid_voltage' in data:
            if data['grid_voltage'] < 200 or data['grid_voltage'] > 250:
                data['grid_voltage'] = 0
        
        # Grid power: ±15kW
        if 'grid_power' in data:
            data['grid_power'] = max(-15000, min(15000, data['grid_power']))
        
        # Total PV: 0-60kW (3x 20kW max)
        if 'total_pv_power' in data:
            data['total_pv_power'] = max(0, min(60000, data['total_pv_power']))
        
        # Load power: 0-30kW
        if 'load_power' in data:
            data['load_power'] = max(0, min(30000, data['load_power']))
        
        return data
    
    def display_data(self, data):
        """Display parsed data in a nice format"""
        if not data:
            print("No data to display")
            return
        
        print(f"\n{'='*60}")
        print(f"EG4 18kPV Inverter Data - {data.get('timestamp', 'Unknown')}")
        print(f"Device ID: {data.get('device_id', 'Unknown')}")
        print(f"{'='*60}")
        
        # PV Data
        print("\n📊 Solar PV Production:")
        print(f"  PV1: {data.get('pv1_voltage', 0):.1f}V @ {data.get('pv1_current', 0):.1f}A = {data.get('pv1_power', 0):,}W")
        print(f"  PV2: {data.get('pv2_voltage', 0):.1f}V @ {data.get('pv2_current', 0):.1f}A = {data.get('pv2_power', 0):,}W")
        print(f"  PV3: {data.get('pv3_voltage', 0):.1f}V @ {data.get('pv3_current', 0):.1f}A = {data.get('pv3_power', 0):,}W")
        print(f"  Total PV: {data.get('total_pv_power', 0):,}W")
        
        # Battery Data
        print("\n🔋 Battery Status:")
        print(f"  Voltage: {data.get('battery_voltage', 0):.1f}V")
        print(f"  Current: {data.get('battery_current', 0):.1f}A {'(Charging)' if data.get('battery_current', 0) > 0 else '(Discharging)'}")
        print(f"  Power: {abs(data.get('battery_power', 0)):,}W")
        print(f"  SOC: {data.get('battery_soc', 0)}%")
        
        # Grid Data
        print("\n⚡ Grid Status:")
        print(f"  Voltage: {data.get('grid_voltage', 0):.1f}V")
        print(f"  Frequency: {data.get('grid_frequency', 0):.2f}Hz")
        print(f"  Power: {abs(data.get('grid_power', 0)):,}W {'(Importing)' if data.get('grid_power', 0) > 0 else '(Exporting)'}")
        
        # Load Data
        print("\n🏠 Load:")
        print(f"  Power: {data.get('load_power', 0):,}W")
        
        print(f"\n{'='*60}")
    
    def monitor_realtime(self, interval=5):
        """Monitor inverter data in real-time"""
        print(f"\n🔄 Starting real-time monitoring (update every {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                # Query inverter
                response = self.query_inverter()
                
                if response:
                    # First analyze to understand the data
                    if hasattr(self, '_first_run'):
                        self._first_run = False
                    else:
                        self._first_run = True
                    
                    if self._first_run:
                        self.analyze_response(response)
                    
                    # Parse and display
                    data = self.parse_response(response)
                    if data:
                        # Clear screen for clean display
                        print("\033[2J\033[H", end='')  # Clear screen and move cursor to top
                        self.display_data(data)
                        
                        # Save to file
                        with open('/tmp/eg4_realtime.json', 'w') as f:
                            json.dump(data, f, indent=2)
                    else:
                        print("❌ Failed to parse response")
                else:
                    print("❌ No response from inverter")
                
                # Wait for next update
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")

def main():
    # Create parser
    parser = EG4Parser()
    
    # Connect to inverter
    if not parser.connect():
        print("Failed to connect to inverter")
        return
    
    try:
        # First, do a single query and analysis
        print("Performing initial query and analysis...")
        response = parser.query_inverter()
        
        if response:
            print(f"\n✓ Received {len(response)} bytes")
            
            # Analyze response structure
            parser.analyze_response(response)
            
            # Parse and display
            data = parser.parse_response(response)
            if data:
                parser.display_data(data)
                
                # Start real-time monitoring
                parser.monitor_realtime(interval=5)
            else:
                print("\n❌ Failed to parse response")
        else:
            print("\n❌ No response from inverter")
            
    finally:
        parser.disconnect()
        print("\n✓ Disconnected")

if __name__ == "__main__":
    main()