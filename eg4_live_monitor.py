#!/usr/bin/env python3
"""
EG4 Live Monitor - Shows real-time data from EG4 inverter
Based on the working test_inverter_connection.py
"""

import sys
import time
from datetime import datetime
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient

def monitor_eg4():
    """Monitor EG4 inverter continuously"""
    print("EG4 18kPV LIVE MONITOR")
    print("=" * 60)
    print(f"Connecting to 172.16.107.129:8000")
    print("Press Ctrl+C to stop\n")
    
    client = EG4IoTOSClient(host='172.16.107.129', port=8000)
    
    try:
        while True:
            if client.connect():
                # Send query command
                query_command = b'\xa1\x1a\x05\x00'
                response = client.send_receive(query_command)
                
                if response and len(response) >= 70:
                    # Clear previous lines (move cursor up)
                    print("\033[10A", end='')  # Move up 10 lines
                    
                    # Print timestamp
                    print(f"\nEG4 DATA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print("=" * 60)
                    
                    # Parse basic info
                    serial = response[8:19].decode('ascii', errors='ignore').strip('\x00')
                    device_id = response[24:35].decode('ascii', errors='ignore').strip('\x00')
                    
                    # Parse power values
                    pv1_power = int.from_bytes(response[37:41], 'big', signed=True)
                    pv2_power = int.from_bytes(response[41:45], 'big', signed=True)
                    pv3_power = int.from_bytes(response[45:49], 'big', signed=True)
                    total_pv = int.from_bytes(response[49:53], 'big', signed=True)
                    battery_power = int.from_bytes(response[53:57], 'big', signed=True)
                    grid_power = int.from_bytes(response[57:61], 'big', signed=True)
                    backup_power = int.from_bytes(response[61:65], 'big', signed=True)
                    load_power = int.from_bytes(response[65:69], 'big', signed=True)
                    
                    # Apply proper scaling based on realistic values
                    # If values seem too high, they might be in different units
                    
                    # PV values - if > 20kW, divide by 10
                    if abs(pv1_power) > 20000:
                        pv1_power = pv1_power / 10
                    if abs(pv2_power) > 20000:
                        pv2_power = pv2_power / 10
                    if abs(pv3_power) > 20000:
                        pv3_power = pv3_power / 10
                    
                    # Total PV should be sum of individual PVs
                    calculated_total_pv = pv1_power + pv2_power + pv3_power
                    
                    # Battery power - typical range ±10kW
                    if abs(battery_power) > 20000:
                        battery_power = battery_power / 10
                    
                    # Grid power - typical range ±15kW
                    if abs(grid_power) > 30000:
                        grid_power = grid_power / 10
                    
                    # Load power - typical range 0-30kW
                    if abs(load_power) > 50000:
                        load_power = load_power / 10
                    
                    print(f"Serial: {serial} | Device: {device_id}")
                    print("-" * 60)
                    
                    print("SOLAR PV:")
                    print(f"  PV1: {pv1_power:>8.1f} W")
                    print(f"  PV2: {pv2_power:>8.1f} W")
                    print(f"  PV3: {pv3_power:>8.1f} W")
                    print(f"  Total: {calculated_total_pv:>8.1f} W")
                    
                    print("\nPOWER FLOWS:")
                    battery_status = "(Charging)" if battery_power > 0 else "(Discharging)" if battery_power < 0 else "(Idle)"
                    print(f"  Battery: {battery_power:>8.1f} W {battery_status}")
                    
                    grid_status = "(Importing)" if grid_power > 0 else "(Exporting)" if grid_power < 0 else "(Standby)"
                    print(f"  Grid: {grid_power:>8.1f} W {grid_status}")
                    
                    print(f"  Load: {load_power:>8.1f} W")
                    print(f"  Backup: {backup_power:>8.1f} W")
                    
                    # Look for battery SOC
                    battery_soc = 0
                    for i in range(70, min(len(response), 120)):
                        if 0 < response[i] <= 100:
                            battery_soc = response[i]
                            break
                    
                    if battery_soc > 0:
                        print(f"\nBATTERY SOC: {battery_soc}%")
                    
                    # Try to find more data with extended queries
                    extended_queries = [
                        b'\xa1\x1a\x05\x01',  # Extended query 1
                        b'\xa1\x1a\x05\x02',  # Extended query 2
                    ]
                    
                    for query in extended_queries:
                        ext_response = client.send_receive(query)
                        if ext_response and len(ext_response) > 100:
                            # Look for voltage/current values
                            # Voltages are typically 200-600V for PV, 40-60V for battery
                            # Currents are typically 0-30A
                            pass
                    
                    # Show raw data for first few bytes after power values
                    print(f"\nRAW DATA (bytes 70-90): {response[70:90].hex()}")
                    
                else:
                    print("No valid response")
                
                client.disconnect()
                
            else:
                print("Connection failed, retrying...")
            
            # Wait before next update
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        client.disconnect()

if __name__ == "__main__":
    monitor_eg4()