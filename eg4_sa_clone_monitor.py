#!/usr/bin/env python3
"""
EG4 Monitor - Clone of Solar Assistant's approach
Connects to EG4 and displays real values exactly like Solar Assistant
"""

import socket
import struct
import time
from datetime import datetime
import sys

class EG4Monitor:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.socket = None
        
    def connect(self):
        """Connect with generous timeout"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(60)  # 60 second timeout
            print(f"Connecting to {self.host}:{self.port}...")
            self.socket.connect((self.host, self.port))
            print("Connected!")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def query_status(self):
        """Query main status like Solar Assistant"""
        if not self.socket:
            return None
            
        try:
            # Send main status command
            cmd = b'\xa1\x1a\x05\x00'
            print(f"Sending command: {cmd.hex()}")
            self.socket.send(cmd)
            
            # Wait for response
            print("Waiting for response...")
            response = b''
            start_time = time.time()
            
            while len(response) < 117 and (time.time() - start_time) < 30:
                try:
                    chunk = self.socket.recv(117 - len(response))
                    if chunk:
                        response += chunk
                        print(f"Received {len(chunk)} bytes, total: {len(response)}")
                except socket.timeout:
                    print("Timeout waiting for data")
                    break
                    
            if len(response) >= 100:
                return response
            else:
                print(f"Response too short: {len(response)} bytes")
                return None
                
        except Exception as e:
            print(f"Query error: {e}")
            return None
    
    def parse_and_display(self, response):
        """Parse response and display like Solar Assistant"""
        print(f"\n{'='*60}")
        print(f"EG4 18kPV Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # Battery voltage (confirmed at offset 82)
            battery_voltage = struct.unpack('>H', response[82:84])[0] / 100.0
            print(f"\nBattery Voltage: {battery_voltage:.1f} V")
            
            # Battery SOC (confirmed at offset 85)
            battery_soc = response[85]
            print(f"Battery SOC: {battery_soc}%")
            
            # Power values
            battery_power = struct.unpack('>h', response[48:50])[0]
            grid_power = struct.unpack('>h', response[50:52])[0]
            load_power = struct.unpack('>H', response[52:54])[0]
            
            # Scale if needed
            if abs(battery_power) > 20000:
                battery_power = battery_power // 10
            if abs(grid_power) > 20000:
                grid_power = grid_power // 10
            if load_power > 20000:
                load_power = load_power // 10
                
            print(f"\nBattery Power: {battery_power} W")
            print(f"Grid Power: {grid_power} W", end='')
            if grid_power < 0:
                print(" (EXPORTING)")
            elif grid_power > 0:
                print(" (IMPORTING)")
            else:
                print()
                
            print(f"Load Power: {load_power} W")
            
            # PV voltages (if available)
            if len(response) >= 80:
                pv1_v = struct.unpack('>H', response[74:76])[0] / 10.0
                pv2_v = struct.unpack('>H', response[76:78])[0] / 10.0
                pv3_v = struct.unpack('>H', response[78:80])[0] / 10.0
                
                print(f"\nPV1 Voltage: {pv1_v:.1f} V")
                print(f"PV2 Voltage: {pv2_v:.1f} V")
                print(f"PV3 Voltage: {pv3_v:.1f} V")
                
            # Grid voltage (search for it)
            grid_voltage = 0
            for offset in [60, 72, 88, 90, 92, 94]:
                if offset + 2 <= len(response):
                    val = struct.unpack('>H', response[offset:offset+2])[0]
                    if 2200 <= val <= 2600:  # 220-260V range
                        grid_voltage = val / 10.0
                        break
                        
            if grid_voltage > 0:
                print(f"\nGrid Voltage: {grid_voltage:.1f} V")
                
            # Show hex dump of critical areas
            print(f"\n{'─'*60}")
            print("Critical data regions (hex):")
            print(f"Power data (48-54): {response[48:54].hex()}")
            print(f"PV data (74-80): {response[74:80].hex()}")
            print(f"Battery (82-86): {response[82:86].hex()}")
            
        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Response length: {len(response)}")
            print(f"First 20 bytes: {response[:20].hex()}")
    
    def run_once(self):
        """Run one query cycle"""
        if not self.connect():
            print("ERROR: Cannot connect to EG4 at 172.16.107.129:8000")
            return False
            
        response = self.query_status()
        if response:
            self.parse_and_display(response)
            return True
        else:
            print("ERROR: No valid response from EG4")
            return False
            
        if self.socket:
            self.socket.close()
            
    def run_continuous(self):
        """Run continuous monitoring"""
        print("EG4 Monitor - Press Ctrl+C to stop\n")
        
        while True:
            try:
                success = self.run_once()
                
                if self.socket:
                    self.socket.close()
                    self.socket = None
                    
                # Wait before next query
                if success:
                    time.sleep(5)
                else:
                    print("\nRetrying in 10 seconds...")
                    time.sleep(10)
                    
            except KeyboardInterrupt:
                print("\n\nStopping monitor...")
                if self.socket:
                    self.socket.close()
                break
            except Exception as e:
                print(f"Error: {e}")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                time.sleep(10)

if __name__ == "__main__":
    monitor = EG4Monitor()
    
    # Try single query first
    print("Testing single query...\n")
    if monitor.run_once():
        print("\n\nSingle query successful!")
        print("Starting continuous monitoring in 5 seconds...")
        time.sleep(5)
        monitor.run_continuous()
    else:
        print("\nERROR: Cannot communicate with EG4")
        print("Please check:")
        print("1. EG4 is powered on")
        print("2. Network connection to 172.16.107.129")
        print("3. Port 8000 is accessible")