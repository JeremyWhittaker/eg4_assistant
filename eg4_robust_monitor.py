#!/usr/bin/env python3
"""
EG4 Robust Monitor - Handles poor network conditions
Gets all data like Solar Assistant with extreme network tolerance
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
from datetime import datetime
import socket

class EG4RobustMonitor:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.client = None
        self.socket = None
        
    def connect_direct(self):
        """Direct socket connection with extreme timeout"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)  # 30 second timeout for slow network
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def send_receive_direct(self, data, timeout=30):
        """Send and receive with extreme tolerance"""
        if not self.socket:
            return None
            
        try:
            # Send command
            self.socket.send(data)
            
            # Wait for response with long timeout
            self.socket.settimeout(timeout)
            response = b''
            
            # Try to read expected 117 bytes
            while len(response) < 117:
                chunk = self.socket.recv(117 - len(response))
                if not chunk:
                    break
                response += chunk
                
            return response if len(response) >= 100 else None
            
        except socket.timeout:
            print(f"Timeout waiting for response")
            return None
        except Exception as e:
            print(f"Error in send/receive: {e}")
            self.socket = None
            return None
    
    def disconnect(self):
        """Disconnect socket"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def query_all_data(self):
        """Query all data using multiple commands"""
        if not self.socket:
            if not self.connect_direct():
                return None
        
        all_data = {}
        
        # Main status query - this is the most important one
        print("Querying main status (a1 1a 05 00)...")
        resp = self.send_receive_direct(b'\xa1\x1a\x05\x00')
        if resp and len(resp) >= 100:
            print(f"Got {len(resp)} bytes")
            data = self.parse_main_status(resp)
            all_data.update(data)
        else:
            print("No response to main status")
            
        # Try additional queries if main one worked
        if all_data:
            # Extended status
            print("\nQuerying extended status (a1 1a 05 02)...")
            resp = self.send_receive_direct(b'\xa1\x1a\x05\x02')
            if resp and len(resp) >= 100:
                print(f"Got {len(resp)} bytes")
                data = self.parse_extended_status(resp)
                all_data.update(data)
                
        return all_data
    
    def parse_main_status(self, response):
        """Parse main status response with known working offsets"""
        data = {}
        
        try:
            # These offsets are confirmed working:
            # Battery voltage at offset 82
            data['battery_voltage'] = struct.unpack('>H', response[82:84])[0] / 100.0
            
            # Battery SOC at offset 85
            data['battery_soc'] = response[85] if response[85] <= 100 else 0
            
            # Power values (these work but need scaling)
            battery_power_raw = struct.unpack('>h', response[48:50])[0]
            grid_power_raw = struct.unpack('>h', response[50:52])[0]
            load_power_raw = struct.unpack('>H', response[52:54])[0]
            
            # Apply scaling
            data['battery_power'] = battery_power_raw if abs(battery_power_raw) < 20000 else battery_power_raw / 10
            data['grid_power'] = grid_power_raw if abs(grid_power_raw) < 20000 else grid_power_raw / 10
            data['load_power'] = load_power_raw if load_power_raw < 20000 else load_power_raw / 10
            
            # Try to find grid voltage (typically 220-260V)
            for offset in [60, 72, 88, 90, 92]:
                if offset + 2 <= len(response):
                    val = struct.unpack('>H', response[offset:offset+2])[0]
                    if 2200 <= val <= 2600:  # 220-260V range
                        data['grid_voltage'] = val / 10.0
                        break
                        
            # PV data - usually at offsets 74-80
            if len(response) > 80:
                pv1_v = struct.unpack('>H', response[74:76])[0]
                pv2_v = struct.unpack('>H', response[76:78])[0]
                pv3_v = struct.unpack('>H', response[78:80])[0]
                
                # Only include if reasonable values
                if pv1_v < 5000:
                    data['pv1_voltage'] = pv1_v / 10.0
                if pv2_v < 5000:
                    data['pv2_voltage'] = pv2_v / 10.0
                if pv3_v < 5000:
                    data['pv3_voltage'] = pv3_v / 10.0
                    
        except Exception as e:
            print(f"Error parsing main status: {e}")
            
        return data
    
    def parse_extended_status(self, response):
        """Parse extended status for additional fields"""
        data = {}
        
        try:
            # Look for temperature (typically 20-80°C range)
            for offset in range(70, min(len(response), 100)):
                val = response[offset]
                if 20 <= val <= 80:
                    data['inverter_temp'] = val
                    break
                    
            # Grid frequency (59.5-60.5 Hz range)
            for offset in range(60, min(len(response)-2, 100), 2):
                val = struct.unpack('>H', response[offset:offset+2])[0]
                if 5950 <= val <= 6050:
                    data['grid_frequency'] = val / 100.0
                    break
                    
        except Exception as e:
            print(f"Error parsing extended status: {e}")
            
        return data
    
    def display_data(self, data):
        """Display collected data in a clean format"""
        print(f"\n{'='*60}")
        print(f"EG4 18kPV Data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if not data:
            print("NO DATA AVAILABLE - Check connection to 172.16.107.129:8000")
            return
            
        # Battery
        print(f"\nBATTERY:")
        print(f"  Voltage: {data.get('battery_voltage', 0):.1f} V")
        print(f"  Power: {data.get('battery_power', 0):.0f} W", end='')
        bp = data.get('battery_power', 0)
        if bp > 0:
            print(" [CHARGING]")
        elif bp < 0:
            print(" [DISCHARGING]")
        else:
            print(" [IDLE]")
        print(f"  SOC: {data.get('battery_soc', 0)}%")
        
        # Grid
        print(f"\nGRID:")
        print(f"  Voltage: {data.get('grid_voltage', 0):.1f} V")
        print(f"  Frequency: {data.get('grid_frequency', 0):.2f} Hz")
        print(f"  Power: {data.get('grid_power', 0):.0f} W", end='')
        gp = data.get('grid_power', 0)
        if gp > 0:
            print(" [IMPORTING]")
        elif gp < 0:
            print(" [EXPORTING]")
        else:
            print()
            
        # Solar
        print(f"\nSOLAR PV:")
        pv1 = data.get('pv1_voltage', 0)
        pv2 = data.get('pv2_voltage', 0)
        pv3 = data.get('pv3_voltage', 0)
        print(f"  PV1: {pv1:.1f} V")
        print(f"  PV2: {pv2:.1f} V")
        print(f"  PV3: {pv3:.1f} V")
        
        # Load
        print(f"\nLOAD:")
        print(f"  Power: {data.get('load_power', 0):.0f} W")
        
        # System
        print(f"\nSYSTEM:")
        print(f"  Inverter Temp: {data.get('inverter_temp', 0):.0f}°C")
        
        # Summary of what we got
        print(f"\n{'─'*60}")
        print(f"Successfully retrieved {len(data)} data fields")
        
    def run_continuous(self, interval=10):
        """Run continuous monitoring with network resilience"""
        print("Starting EG4 Robust Monitor...")
        print(f"Connecting to {self.host}:{self.port}")
        print("This monitor is designed for poor network conditions")
        print("Press Ctrl+C to stop\n")
        
        consecutive_failures = 0
        
        while True:
            try:
                data = self.query_all_data()
                
                if data:
                    consecutive_failures = 0
                    self.display_data(data)
                else:
                    consecutive_failures += 1
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] No data (attempt {consecutive_failures})")
                    
                    # Disconnect and reconnect after failures
                    if consecutive_failures >= 3:
                        print("Resetting connection...")
                        self.disconnect()
                        time.sleep(5)
                        consecutive_failures = 0
                
                # Wait before next query
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                self.disconnect()
                break
            except Exception as e:
                print(f"Error: {e}")
                self.disconnect()
                time.sleep(interval)

if __name__ == "__main__":
    monitor = EG4RobustMonitor()
    monitor.run_continuous()