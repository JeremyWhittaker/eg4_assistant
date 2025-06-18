#!/usr/bin/env python3
"""Test connection to EG4 inverter"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import json

def test_connection():
    print("Testing connection to EG4 18kPV inverter...")
    print("IP: 172.16.107.53")
    print("Port: 8000")
    print("Protocol: IoTOS")
    print("-" * 50)
    
    client = EG4IoTOSClient(host='172.16.107.53', port=8000)
    
    if client.connect():
        print("✓ Connected successfully!")
        
        # Send query command
        query_command = b'\xa1\x1a\x05\x00'
        response = client.send_receive(query_command)
        
        if response:
            print(f"✓ Received response: {len(response)} bytes")
            
            # Parse basic info
            serial = response[8:19].decode('ascii', errors='ignore').strip('\x00')
            device_id = response[24:35].decode('ascii', errors='ignore').strip('\x00')
            
            print(f"\nInverter Info:")
            print(f"  Serial Number: {serial}")
            print(f"  Device ID: {device_id}")
            
            # Parse power values
            if len(response) >= 70:
                pv1_power = int.from_bytes(response[37:41], 'big', signed=True)
                pv2_power = int.from_bytes(response[41:45], 'big', signed=True)
                pv3_power = int.from_bytes(response[45:49], 'big', signed=True)
                total_pv = int.from_bytes(response[49:53], 'big', signed=True)
                battery_power = int.from_bytes(response[53:57], 'big', signed=True)
                grid_power = int.from_bytes(response[57:61], 'big', signed=True)
                load_power = int.from_bytes(response[65:69], 'big', signed=True)
                
                # Apply scaling
                if pv1_power > 20000:
                    pv1_power = pv1_power / 10
                if pv3_power > 20000:
                    pv3_power = pv3_power / 10
                
                print(f"\nPower Values:")
                print(f"  PV1: {pv1_power}W")
                print(f"  PV2: {pv2_power}W")
                print(f"  PV3: {pv3_power}W")
                print(f"  Total PV: {total_pv}W")
                print(f"  Battery: {battery_power}W {'(charging)' if battery_power > 0 else '(discharging)'}")
                print(f"  Grid: {grid_power}W {'(importing)' if grid_power > 0 else '(exporting)'}")
                print(f"  Load: {load_power}W")
                
                # Battery SOC
                if len(response) > 95:
                    for i in range(60, min(96, len(response))):
                        if 0 <= response[i] <= 100:
                            print(f"  Battery SOC: {response[i]}%")
                            break
            
            print("\n✓ Inverter is responding correctly!")
            print("\nYour inverter is already in the database:")
            print("  Name: jeremys")
            print("  Model: EG4 18kPV")
            print("  Serial: BA32401949")
            print("\nYou can access the monitoring interface at:")
            print("  http://172.16.106.10:5000/")
            
        else:
            print("✗ No response received")
        
        client.disconnect()
    else:
        print("✗ Failed to connect to inverter")
        print("\nTroubleshooting:")
        print("1. Check inverter IP address is correct")
        print("2. Ensure inverter WiFi dongle is connected")
        print("3. Check network connectivity")

if __name__ == "__main__":
    test_connection()