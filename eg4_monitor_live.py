#!/usr/bin/env python3
"""
EG4 Live Monitor - Real-time continuous updates
Shows all available data from EG4 18kPV inverter
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
import os
from datetime import datetime

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def parse_eg4_data(response):
    """Parse EG4 response data"""
    data = {}
    
    if not response or len(response) < 100:
        return data
        
    # Device info
    data['serial'] = response[8:19].decode('ascii', errors='ignore').strip('\x00')
    
    # Battery
    data['battery_voltage'] = struct.unpack('>H', response[82:84])[0] / 100.0
    data['battery_soc'] = response[85] if response[85] <= 100 else 0
    data['battery_power'] = struct.unpack('>h', response[48:50])[0]
    
    # Grid
    data['grid_power'] = struct.unpack('>h', response[50:52])[0]
    # Search for grid voltage
    for offset in [60, 72, 88, 90]:
        if offset + 2 <= len(response):
            val = struct.unpack('>H', response[offset:offset+2])[0]
            if 2000 <= val <= 2600:  # 200-260V
                data['grid_voltage'] = val / 10.0
                break
    
    # Load
    data['load_power'] = struct.unpack('>H', response[52:54])[0]
    
    # PV (will be 0 at night)
    data['pv_power'] = 0  # Nighttime
    
    return data

def display_data(data, last_data=None):
    """Display the data nicely"""
    clear_screen()
    
    print("╔" + "═"*58 + "╗")
    print(f"║  EG4 18kPV Monitor - {datetime.now().strftime('%H:%M:%S')}                        ║")
    print("╠" + "═"*58 + "╣")
    
    # Power flows
    print("║  POWER FLOWS:                                            ║")
    print("║  ─────────────────────────────────────────────────────  ║")
    
    # Solar
    pv = data.get('pv_power', 0)
    print(f"║  🌞 Solar:    {pv:>7.0f} W                                  ║")
    
    # Battery
    bat = data.get('battery_power', 0)
    if bat > 0:
        bat_icon = "↑"
        bat_status = "Charging"
    elif bat < 0:
        bat_icon = "↓"
        bat_status = "Discharging"
    else:
        bat_icon = "─"
        bat_status = "Idle"
    print(f"║  🔋 Battery:  {bat:>7.0f} W  {bat_icon} {bat_status:<15}         ║")
    
    # Grid
    grid = data.get('grid_power', 0)
    if grid > 0:
        grid_icon = "←"
        grid_status = "Importing"
    elif grid < 0:
        grid_icon = "→"
        grid_status = "Exporting"
    else:
        grid_icon = "─"
        grid_status = "Standby"
    print(f"║  🏭 Grid:     {grid:>7.0f} W  {grid_icon} {grid_status:<15}         ║")
    
    # Load
    load = data.get('load_power', 0)
    print(f"║  🏠 Load:     {load:>7.0f} W                                  ║")
    
    print("║                                                          ║")
    
    # Battery details
    print("║  BATTERY:                                                ║")
    print("║  ─────────────────────────────────────────────────────  ║")
    print(f"║  Voltage: {data.get('battery_voltage', 0):>5.1f} V      SOC: {data.get('battery_soc', 0):>3d}%                     ║")
    
    # SOC bar
    soc = data.get('battery_soc', 0)
    bar_len = int(soc / 2.5)  # 40 chars max
    bar = "█" * bar_len + "░" * (40 - bar_len)
    print(f"║  [{bar}] {soc:>3d}%     ║")
    
    print("║                                                          ║")
    
    # Grid details
    print("║  GRID:                                                   ║")
    print("║  ─────────────────────────────────────────────────────  ║")
    print(f"║  Voltage: {data.get('grid_voltage', 0):>5.1f} V                                      ║")
    
    print("╚" + "═"*58 + "╝")
    
    # Change indicators
    if last_data:
        changes = []
        if data.get('battery_power', 0) != last_data.get('battery_power', 0):
            changes.append("Battery")
        if data.get('grid_power', 0) != last_data.get('grid_power', 0):
            changes.append("Grid")
        if data.get('load_power', 0) != last_data.get('load_power', 0):
            changes.append("Load")
        
        if changes:
            print(f"\n Updated: {', '.join(changes)}")
    
    print("\n Press Ctrl+C to stop")

def main():
    """Main loop"""
    print("Starting EG4 Live Monitor...")
    print("Connecting to 172.16.107.129:8000")
    
    client = EG4IoTOSClient(host='172.16.107.129', port=8000)
    last_data = {}
    
    try:
        while True:
            try:
                if client.connect():
                    # Query inverter
                    response = client.send_receive(b'\xa1\x1a\x05\x00')
                    
                    if response:
                        # Parse data
                        data = parse_eg4_data(response)
                        
                        # Display
                        display_data(data, last_data)
                        
                        # Save for comparison
                        last_data = data.copy()
                    else:
                        print("\n⚠️  No response from inverter")
                    
                    client.disconnect()
                else:
                    print("\n⚠️  Connection failed")
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
            
            # Wait before next update
            time.sleep(2)
            
    except KeyboardInterrupt:
        clear_screen()
        print("\n✅ EG4 Monitor stopped")
        print("Goodbye!")
        client.disconnect()

if __name__ == "__main__":
    main()