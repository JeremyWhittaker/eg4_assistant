#!/usr/bin/env python3
"""
Simple EG4 connection test - shows all available data
"""

import socket
import time
import struct
from datetime import datetime

def connect_eg4(host='172.16.107.129', port=8000):
    """Connect to EG4 and get data"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        print(f"Connected to EG4 at {host}:{port}")
        
        # Send query command
        query_cmd = b'\xa1\x1a\x05\x00'
        sock.send(query_cmd)
        time.sleep(0.2)
        
        # Get response
        response = sock.recv(4096)
        print(f"Received {len(response)} bytes")
        
        if len(response) >= 70:
            # Parse basic data
            serial = response[8:19].decode('ascii', errors='ignore').strip('\x00')
            device_id = response[24:35].decode('ascii', errors='ignore').strip('\x00')
            
            pv1_power = int.from_bytes(response[37:41], 'big', signed=True)
            pv2_power = int.from_bytes(response[41:45], 'big', signed=True)
            pv3_power = int.from_bytes(response[45:49], 'big', signed=True)
            total_pv = int.from_bytes(response[49:53], 'big', signed=True)
            battery_power = int.from_bytes(response[53:57], 'big', signed=True)
            grid_power = int.from_bytes(response[57:61], 'big', signed=True)
            backup_power = int.from_bytes(response[61:65], 'big', signed=True)
            load_power = int.from_bytes(response[65:69], 'big', signed=True)
            
            # Apply scaling
            if pv1_power > 20000:
                pv1_power = pv1_power / 10
            if pv3_power > 20000:
                pv3_power = pv3_power / 10
            
            print(f"\n{'='*60}")
            print(f"EG4 INVERTER DATA - {datetime.now()}")
            print(f"{'='*60}")
            print(f"Serial: {serial}")
            print(f"Device ID: {device_id}")
            print(f"\nPOWER VALUES:")
            print(f"  PV1: {pv1_power} W")
            print(f"  PV2: {pv2_power} W")  
            print(f"  PV3: {pv3_power} W")
            print(f"  Total PV: {total_pv} W")
            print(f"  Battery: {battery_power} W {'(charging)' if battery_power > 0 else '(discharging)'}")
            print(f"  Grid: {grid_power} W {'(importing)' if grid_power > 0 else '(exporting)'}")
            print(f"  Backup: {backup_power} W")
            print(f"  Load: {load_power} W")
            
            # Try to find more data
            print(f"\nSEARCHING FOR ADDITIONAL DATA...")
            
            # Look for battery SOC
            for i in range(70, min(len(response), 120)):
                if 0 < response[i] <= 100:
                    print(f"  Battery SOC: {response[i]}%")
                    break
            
            # Try extended queries
            extended_cmds = [
                (b'\xa1\x1a\x05\x01', 'Extended Query 1'),
                (b'\xa1\x1a\x05\x02', 'Extended Query 2'),
                (b'\xa1\x1b\x06\x00\x00\x64', 'Read 100 registers'),
            ]
            
            for cmd, desc in extended_cmds:
                print(f"\nTrying {desc}...")
                sock.send(cmd)
                time.sleep(0.2)
                
                ext_response = sock.recv(4096)
                print(f"  Received {len(ext_response)} bytes")
                
                if len(ext_response) > 100:
                    # Try to parse voltage/current values
                    for offset in range(70, min(len(ext_response)-4, 200), 2):
                        value = struct.unpack('>H', ext_response[offset:offset+2])[0]
                        if 400 < value < 600:  # Likely voltage * 10
                            print(f"  Possible voltage at offset {offset}: {value/10.0}V")
                        elif 0 < value < 1000:  # Likely current * 10
                            print(f"  Possible current at offset {offset}: {value/10.0}A")
                
                # Save response for analysis
                with open(f'eg4_response_{cmd.hex()}.bin', 'wb') as f:
                    f.write(ext_response)
            
            print(f"\nRaw responses saved to eg4_response_*.bin files")
            print("You can analyze these with a hex editor to find more fields")
            
        else:
            print("Response too short!")
            print(f"Raw response (hex): {response.hex()}")
        
        sock.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        connect_eg4()
        print("\nWaiting 5 seconds before next update...")
        time.sleep(5)