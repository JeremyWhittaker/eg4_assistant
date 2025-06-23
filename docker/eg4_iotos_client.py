#!/usr/bin/env python3
"""
EG4 18kPV IoTOS Protocol Client
Based on analysis of the Solar Assistant system and EG4 dongle
"""

import socket
import struct
import time
import binascii
from dotenv import load_dotenv
import os
import json

load_dotenv()

class EG4IoTOSClient:
    def __init__(self, host='172.16.107.129', port=8000):
        self.host = host
        self.port = port
        self.socket = None
        
    def connect(self):
        """Connect to the EG4 inverter IoTOS port"""
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
    
    def send_receive(self, data, timeout=5):
        """Send data and receive response"""
        if not self.socket:
            print("Not connected!")
            return None
            
        try:
            print(f"\nSending: {binascii.hexlify(data)}")
            self.socket.send(data)
            
            self.socket.settimeout(timeout)
            response = self.socket.recv(4096)
            
            if response:
                print(f"Received: {binascii.hexlify(response)[:100]}...")
                return response
            else:
                print("No response received")
                return None
                
        except socket.timeout:
            print("Response timeout")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def decode_response(self, response):
        """Decode IoTOS response"""
        if not response:
            return None
            
        result = {
            'raw': binascii.hexlify(response),
            'length': len(response),
            'header': binascii.hexlify(response[:8]) if len(response) >= 8 else None,
        }
        
        # Based on our previous analysis
        if len(response) >= 20 and response[0] == 0xa1:
            # Extract serial number
            try:
                serial_start = 8
                serial_end = response.find(b'\x00', serial_start)
                if serial_end > serial_start:
                    result['serial'] = response[serial_start:serial_end].decode('ascii', errors='ignore')
            except:
                pass
                
            # Look for other ASCII strings
            ascii_strings = []
            current_string = ""
            for byte in response:
                if 32 <= byte <= 126:  # Printable ASCII
                    current_string += chr(byte)
                else:
                    if len(current_string) > 3:  # Save strings longer than 3 chars
                        ascii_strings.append(current_string)
                    current_string = ""
            
            if ascii_strings:
                result['ascii_strings'] = ascii_strings
        
        return result
    
    def probe_protocol(self):
        """Try different protocol messages to understand the communication"""
        print("\n=== Probing IoTOS Protocol ===")
        
        test_messages = [
            # Based on the response pattern we saw
            (b'\xa1\x00\x00\x00', "Simple A1 query"),
            (b'\xa1\x1a\x00\x00', "A1 with 1A command"),
            (b'\xa1\x1a\x05\x00', "A1 1A 05 (mirror response header)"),
            
            # Try sequential command bytes
            (b'\xa1\x01\x00\x00', "A1 command 01"),
            (b'\xa1\x02\x00\x00', "A1 command 02"),
            (b'\xa1\x03\x00\x00', "A1 command 03"),
            
            # Try different headers
            (b'\xa2\x00\x00\x00', "A2 header"),
            (b'\xa3\x00\x00\x00', "A3 header"),
            
            # Try with length fields
            (b'\xa1\x01\x00\x04\x00\x00\x00\x00', "A1 with length field"),
            
            # Common Modbus-like queries (even though port 502 is closed)
            (b'\x01\x03\x00\x00\x00\x01', "Modbus-style read holding registers"),
            (b'\x01\x04\x00\x00\x00\x01', "Modbus-style read input registers"),
        ]
        
        results = []
        
        for message, description in test_messages:
            print(f"\n--- Testing: {description} ---")
            response = self.send_receive(message)
            
            if response:
                decoded = self.decode_response(response)
                results.append({
                    'command': binascii.hexlify(message),
                    'description': description,
                    'response': decoded
                })
                
                # If we found ASCII strings, print them
                if decoded and 'ascii_strings' in decoded:
                    print(f"Found strings: {decoded['ascii_strings']}")
            
            time.sleep(0.5)  # Small delay between commands
        
        return results
    
    def monitor_inverter(self, interval=5, duration=60):
        """Monitor inverter data periodically"""
        print(f"\n=== Monitoring EG4 Inverter for {duration} seconds ===")
        
        # Use the command that got us a response before
        query_command = b'\xa1\x1a\x05\x00'
        
        start_time = time.time()
        readings = []
        
        while time.time() - start_time < duration:
            response = self.send_receive(query_command)
            
            if response:
                decoded = self.decode_response(response)
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                
                reading = {
                    'timestamp': timestamp,
                    'data': decoded
                }
                readings.append(reading)
                
                print(f"\n[{timestamp}] Reading captured")
                if decoded and 'ascii_strings' in decoded:
                    print(f"Strings: {decoded['ascii_strings']}")
            
            time.sleep(interval)
        
        return readings

def main():
    # Initialize client
    client = EG4IoTOSClient(
        host=os.getenv('EG4_IP', '172.16.107.129'),
        port=8000
    )
    
    # Connect
    if not client.connect():
        print("Failed to connect to EG4 inverter")
        return
    
    try:
        # Probe the protocol
        print("\n1. PROTOCOL DISCOVERY")
        probe_results = client.probe_protocol()
        
        # Find which commands got responses
        successful_commands = [r for r in probe_results if r['response'] and r['response']['length'] > 0]
        
        if successful_commands:
            print(f"\n✓ Found {len(successful_commands)} working commands")
            
            # Short monitoring session
            print("\n2. MONITORING TEST (30 seconds)")
            readings = client.monitor_inverter(interval=5, duration=30)
            
            print(f"\n✓ Collected {len(readings)} readings")
            
            # Save results
            results = {
                'protocol_probe': probe_results,
                'monitoring_data': readings,
                'summary': {
                    'host': client.host,
                    'port': client.port,
                    'working_commands': len(successful_commands),
                    'total_readings': len(readings)
                }
            }
            
            with open('eg4_iotos_analysis.json', 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print("\n✓ Results saved to eg4_iotos_analysis.json")
            
    finally:
        client.disconnect()
        print("\n✓ Disconnected")

if __name__ == "__main__":
    main()