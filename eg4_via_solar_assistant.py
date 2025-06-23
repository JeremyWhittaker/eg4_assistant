#!/usr/bin/env python3
"""
EG4 Data via Solar Assistant
Gets real-time data from Solar Assistant's InfluxDB
"""

import paramiko
import time
from datetime import datetime

class EG4ViaSolarAssistant:
    def __init__(self):
        self.host = "172.16.106.13"
        self.username = "solar-assistant"
        self.password = "solar123"
        
    def get_data(self):
        """Get current data from Solar Assistant"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(self.host, username=self.username, password=self.password)
            
            # Measurements to retrieve
            measurements = {
                "Battery voltage": "battery_voltage",
                "Battery power": "battery_power",
                "Battery state of charge": "battery_soc",
                "Grid voltage": "grid_voltage",
                "Grid power": "grid_power",
                "Load power": "load_power",
                "PV power": "pv_power",
                "PV voltage 1": "pv1_voltage",
                "PV voltage 2": "pv2_voltage",
                "PV voltage 3": "pv3_voltage",
                "Inverter temperature": "inverter_temp"
            }
            
            data = {}
            
            for measurement, key in measurements.items():
                cmd = f"""sudo influx -database solar_assistant -execute 'SELECT last(*) FROM "{measurement}"' -format csv 2>/dev/null | tail -1"""
                output = ssh.exec_command(cmd)[1].read().decode().strip()
                
                if output and not output.startswith('name'):
                    parts = output.split(',')
                    if len(parts) >= 3:
                        try:
                            value = float(parts[2])
                            data[key] = value
                        except:
                            pass
                            
            return data
            
        except Exception as e:
            print(f"Error: {e}")
            return None
        finally:
            ssh.close()
    
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
        print(f"  SOC: {data.get('battery_soc', 0):.0f}%")
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
        print(f"  PV1: {data.get('pv1_voltage', 0):.1f} V")
        print(f"  PV2: {data.get('pv2_voltage', 0):.1f} V")
        print(f"  PV3: {data.get('pv3_voltage', 0):.1f} V")
            
        # Load
        print(f"\nLOAD:")
        print(f"  Power: {data.get('load_power', 0):.0f} W")
        
        # System
        if 'inverter_temp' in data:
            print(f"\nSYSTEM:")
            print(f"  Inverter Temperature: {data['inverter_temp']:.0f}°C")
        
        # Energy flow summary
        print(f"\n{'─'*60}")
        print("ENERGY FLOW:")
        if pv_total > 50:
            print(f"  ☀️  Solar: {pv_total:.0f} W →")
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
        print("EG4 Monitor (via Solar Assistant)")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                data = self.get_data()
                self.display(data)
                time.sleep(5)
                
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    monitor = EG4ViaSolarAssistant()
    monitor.run_continuous()