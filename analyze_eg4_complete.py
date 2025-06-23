#!/usr/bin/env python3
"""Complete analysis of EG4 data available"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import binascii

def analyze_all_commands():
    """Try different commands to get all available data"""
    
    client = EG4IoTOSClient(host='172.16.107.129', port=8000)
    
    # Commands to try based on protocol analysis
    commands = [
        # Original working command
        (b'\xa1\x1a\x05\x00', 'Status Query (05 00)'),
        # Try variations
        (b'\xa1\x1a\x05\x01', 'Extended Query 1 (05 01)'),
        (b'\xa1\x1a\x05\x02', 'Extended Query 2 (05 02)'),
        (b'\xa1\x1a\x05\x03', 'Extended Query 3 (05 03)'),
        # Try different function codes
        (b'\xa1\x1a\x01\x00', 'Function 01'),
        (b'\xa1\x1a\x02\x00', 'Function 02'),
        (b'\xa1\x1a\x03\x00', 'Function 03'),
        (b'\xa1\x1a\x04\x00', 'Function 04'),
        (b'\xa1\x1a\x06\x00', 'Function 06'),
        # Try with length specifier
        (b'\xa1\x1b\x05\x00\x00\x64', 'Status with length 100'),
        (b'\xa1\x1b\x05\x00\x00\xff', 'Status with length 255'),
        # Try register read commands
        (b'\xa1\x1a\x03\x00\x00\x00\x64', 'Read 100 registers'),
    ]
    
    print("EG4 Protocol Analysis - Finding All Available Data")
    print("="*60)
    
    if client.connect():
        print("Connected successfully!\n")
        
        responses = {}
        
        for cmd, desc in commands:
            print(f"\nTrying: {desc}")
            print(f"Command: {binascii.hexlify(cmd)}")
            
            response = client.send_receive(cmd)
            
            if response:
                print(f"Response length: {len(response)} bytes")
                responses[desc] = response
                
                # Save each response
                filename = f"eg4_response_{binascii.hexlify(cmd).decode()}.bin"
                with open(filename, 'wb') as f:
                    f.write(response)
                print(f"Saved to: {filename}")
                
                # Quick analysis
                if len(response) > 100:
                    print("Possible data found:")
                    # Check for voltage patterns
                    for i in range(0, min(len(response)-2, 200), 2):
                        val = struct.unpack('>H', response[i:i+2])[0]
                        if 3000 <= val <= 4500:  # 300-450V for PV
                            print(f"  PV voltage? at {i}: {val/10:.1f}V")
                        elif 480 <= val <= 580:  # 48-58V for battery
                            print(f"  Battery voltage? at {i}: {val/10:.1f}V")
                        elif 2200 <= val <= 2500:  # 220-250V for grid
                            print(f"  Grid voltage? at {i}: {val/10:.1f}V")
            else:
                print("No response")
        
        # Compare responses
        print("\n\n=== RESPONSE COMPARISON ===")
        for desc, resp in responses.items():
            print(f"\n{desc}: {len(resp)} bytes")
            # Show first 100 bytes in hex
            print(f"First 100 bytes: {binascii.hexlify(resp[:100])}")
        
        client.disconnect()
        
        # Analyze the best response
        if responses:
            best = max(responses.items(), key=lambda x: len(x[1]))
            print(f"\n\nBest response: {best[0]} with {len(best[1])} bytes")
            print("\nAnalyzing for all possible fields...")
            
            response = best[1]
            
            # Try to map all fields based on Solar Assistant's data
            print("\nPossible field mapping:")
            print("-"*60)
            
            # Based on what Solar Assistant shows, try to find:
            fields_to_find = {
                'AC output voltage': (2300, 2500),  # 230-250V
                'Battery current': (0, 1000),       # 0-100A (*10)
                'Battery voltage': (480, 600),      # 48-60V (*10)
                'Grid frequency': (5950, 6050),     # 59.5-60.5Hz (*100)
                'Inverter temp': (200, 1500),       # 20-150°C (*10)
                'PV voltage 1-3': (2000, 4500),     # 200-450V (*10)
            }
            
            for field, (min_val, max_val) in fields_to_find.items():
                print(f"\n{field} (range {min_val}-{max_val}):")
                for i in range(0, min(len(response)-2, 300), 2):
                    val = struct.unpack('>H', response[i:i+2])[0]
                    if min_val <= val <= max_val:
                        print(f"  Offset {i}: {val} -> {val/10:.1f} or {val/100:.2f}")
                        
    else:
        print("Failed to connect")

if __name__ == "__main__":
    analyze_all_commands()