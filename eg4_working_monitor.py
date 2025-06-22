#!/usr/bin/env python3
"""
EG4 Working Monitor - Simple and reliable
Gets real data from EG4 18kPV inverter
"""

import socket
import struct
import time
from datetime import datetime

class EG4WorkingMonitor:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        
    def get_data(self):
        """Get data from EG4"""
        try:
            # Create new connection for each query
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((self.host, self.port))
            
            # Send command
            cmd = b'\xa1\x1a\x05\x00'
            s.send(cmd)
            
            # Receive response
            s.settimeout(5)
            response = s.recv(512)  # Get more than expected 117 bytes
            
            s.close()
            
            if len(response) >= 100:
                return self.parse_response(response)
            else:
                return None
                
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def parse_response(self, response):
        """Parse the response data"""
        data = {}
        
        try:
            # Extract the actual data portion
            # Response format: a1 1a 05 00 [length] [data...]
            if len(response) < 117:
                return None
                
            # Battery voltage at offset 82 (confirmed working)
            data['battery_voltage'] = struct.unpack('>H', response[82:84])[0] / 100.0
            
            # Battery SOC at offset 85 (confirmed working)
            data['battery_soc'] = response[85]
            
            # Power values at offsets 48-54
            battery_power = struct.unpack('>h', response[48:50])[0]  # signed
            grid_power = struct.unpack('>h', response[50:52])[0]     # signed
            load_power = struct.unpack('>H', response[52:54])[0]     # unsigned
            
            # Scale appropriately
            data['battery_power'] = battery_power if abs(battery_power) < 20000 else battery_power // 10
            data['grid_power'] = grid_power if abs(grid_power) < 20000 else grid_power // 10
            data['load_power'] = load_power if load_power < 20000 else load_power // 10
            
            # PV voltages at offsets 74-80
            if len(response) >= 80:
                data['pv1_voltage'] = struct.unpack('>H', response[74:76])[0] / 10.0
                data['pv2_voltage'] = struct.unpack('>H', response[76:78])[0] / 10.0
                data['pv3_voltage'] = struct.unpack('>H', response[78:80])[0] / 10.0
            
            # Grid voltage - search common locations
            for offset in [60, 72, 88, 90, 92, 94, 96]:
                if offset + 2 <= len(response):
                    val = struct.unpack('>H', response[offset:offset+2])[0]
                    if 2200 <= val <= 2600:  # 220-260V range
                        data['grid_voltage'] = val / 10.0
                        break
                        
            # Calculate PV power from current values
            # Look for PV currents near PV voltages
            pv_power_total = 0
            if 'pv1_voltage' in data and data['pv1_voltage'] > 50:
                # Estimate based on typical MPPT behavior
                pv_power_total += data['pv1_voltage'] * 10  # Rough estimate
            if 'pv2_voltage' in data and data['pv2_voltage'] > 50:
                pv_power_total += data['pv2_voltage'] * 10
            if 'pv3_voltage' in data and data['pv3_voltage'] > 50:
                pv_power_total += data['pv3_voltage'] * 10
                
            # Better calculation: PV power = Load + Battery charging - Grid import
            if data['grid_power'] < 0:  # Exporting
                data['pv_power'] = data['load_power'] + data['battery_power'] + abs(data['grid_power'])
            else:  # Importing
                data['pv_power'] = data['load_power'] + data['battery_power'] - data['grid_power']
                
            # Make sure PV power is not negative
            if data['pv_power'] < 0:
                data['pv_power'] = 0
                
        except Exception as e:
            print(f"Parse error: {e}")
            
        return data
    
    def display(self, data):
        """Display the data"""
        print(f"\n{'='*60}")
        print(f"EG4 18kPV Real-Time Data - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        if not data:
            print("ERROR: No data available")
            return
            
        # Battery
        print(f"\nBATTERY:")
        print(f"  Voltage: {data.get('battery_voltage', 0):.1f} V")
        print(f"  SOC: {data.get('battery_soc', 0)}%")
        bp = data.get('battery_power', 0)
        print(f"  Power: {bp:+.0f} W", end='')
        if bp > 50:
            print(" ⚡ CHARGING")
        elif bp < -50:
            print(" 🔋 DISCHARGING")
        else:
            print(" ═ IDLE")
            
        # Grid
        print(f"\nGRID:")
        print(f"  Voltage: {data.get('grid_voltage', 0):.1f} V")
        gp = data.get('grid_power', 0)
        print(f"  Power: {gp:+.0f} W", end='')
        if gp > 50:
            print(" ← IMPORTING")
        elif gp < -50:
            print(" → EXPORTING")
        else:
            print()
            
        # Solar
        print(f"\nSOLAR:")
        pv_total = data.get('pv_power', 0)
        print(f"  Total Power: {pv_total:.0f} W")
        if 'pv1_voltage' in data:
            print(f"  PV1: {data['pv1_voltage']:.1f} V")
        if 'pv2_voltage' in data:
            print(f"  PV2: {data['pv2_voltage']:.1f} V")
        if 'pv3_voltage' in data:
            print(f"  PV3: {data['pv3_voltage']:.1f} V")
            
        # Load
        print(f"\nLOAD:")
        print(f"  Power: {data.get('load_power', 0):.0f} W")
        
        # Energy flow summary
        print(f"\n{'─'*60}")
        print("ENERGY FLOW:")
        if pv_total > 50:
            print(f"  Solar: {pv_total:.0f} W →")
        if gp < -50:
            print(f"  → Grid: {abs(gp):.0f} W (selling)")
        elif gp > 50:
            print(f"  ← Grid: {gp:.0f} W (buying)")
        if bp > 50:
            print(f"  → Battery: {bp:.0f} W (charging)")
        elif bp < -50:
            print(f"  ← Battery: {abs(bp):.0f} W (discharging)")
        print(f"  → Load: {data.get('load_power', 0):.0f} W")
        
    def run_continuous(self):
        """Run continuous monitoring"""
        print("EG4 Real-Time Monitor")
        print("Press Ctrl+C to stop\n")
        
        error_count = 0
        
        while True:
            try:
                data = self.get_data()
                
                if data:
                    error_count = 0
                    self.display(data)
                else:
                    error_count += 1
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] No data (attempt {error_count})")
                    
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    monitor = EG4WorkingMonitor()
    monitor.run_continuous()