#!/usr/bin/env python3
"""
Analyze IoTOS protocol byte by byte to find the correct decoding
"""

import json
import struct
import binascii

def analyze_byte_patterns():
    """Analyze the raw responses to find patterns"""
    
    # Load the monitoring data
    with open('eg4_iotos_analysis.json', 'r') as f:
        data = json.load(f)
    
    print("Analyzing byte patterns in IoTOS responses...")
    print("=" * 80)
    
    # Get monitoring data
    readings = data['monitoring_data']
    
    # Convert all readings to bytes
    byte_readings = []
    for reading in readings:
        hex_str = reading['data']['raw'][2:-1]  # Remove b' and '
        byte_data = bytes.fromhex(hex_str)
        byte_readings.append({
            'timestamp': reading['timestamp'],
            'bytes': byte_data,
            'length': len(byte_data)
        })
    
    # Show byte-by-byte comparison for first 117 bytes
    print("\nByte-by-byte comparison (showing differences):")
    print("Offset | Reading 1 | Reading 2 | Reading 3 | Reading 4 | Reading 5 | Reading 6")
    print("-" * 80)
    
    # Find bytes that change between readings
    changing_bytes = []
    
    for i in range(117):  # All responses have at least 117 bytes
        values = []
        for reading in byte_readings[:6]:
            if i < len(reading['bytes']):
                values.append(reading['bytes'][i])
            else:
                values.append(0)
        
        # Check if this byte changes
        if len(set(values)) > 1:  # This byte has different values
            changing_bytes.append(i)
            print(f"{i:6} | {values[0]:9} | {values[1]:9} | {values[2]:9} | {values[3]:9} | {values[4]:9} | {values[5]:9}")
    
    print(f"\nTotal changing bytes: {len(changing_bytes)}")
    
    # Analyze specific ranges
    print("\n\nAnalyzing specific byte ranges:")
    
    # Common ranges in inverter protocols
    ranges = [
        (35, 45, "Range 35-45 (after device ID)"),
        (45, 55, "Range 45-55"),
        (55, 65, "Range 55-65"),
        (65, 75, "Range 65-75"),
        (75, 85, "Range 75-85"),
        (85, 95, "Range 85-95"),
        (95, 105, "Range 95-105"),
        (105, 117, "Range 105-117 (end)")
    ]
    
    for start, end, desc in ranges:
        print(f"\n{desc}:")
        for i, reading in enumerate(byte_readings[:3]):
            hex_bytes = binascii.hexlify(reading['bytes'][start:end]).decode()
            # Format as pairs
            formatted = ' '.join(hex_bytes[j:j+2] for j in range(0, len(hex_bytes), 2))
            print(f"  Reading {i+1}: {formatted}")
    
    # Look for specific patterns
    print("\n\nLooking for specific patterns:")
    
    # Check for ASCII strings in different locations
    for i, reading in enumerate(byte_readings[:2]):
        print(f"\nReading {i+1} ASCII strings found:")
        bytes_data = reading['bytes']
        
        # Look for ASCII sequences
        ascii_start = None
        for j in range(len(bytes_data)):
            if 32 <= bytes_data[j] <= 126:  # Printable ASCII
                if ascii_start is None:
                    ascii_start = j
            else:
                if ascii_start is not None and j - ascii_start > 3:
                    ascii_str = bytes_data[ascii_start:j].decode('ascii', errors='ignore')
                    print(f"  Offset {ascii_start}: '{ascii_str}'")
                ascii_start = None
    
    # Look for typical inverter values
    print("\n\nSearching for typical inverter values:")
    
    # Grid voltage should be around 240V (0x00F0 in hex if no decimal)
    # or 2400 (0x0960) if stored as 0.1V units
    # Battery voltage around 51.2V (0x0200 if 0.1V units)
    
    for i, reading in enumerate(byte_readings[:2]):
        bytes_data = reading['bytes']
        print(f"\nReading {i+1} - Searching for voltage patterns:")
        
        # Search for 16-bit values that could be voltages
        for j in range(35, len(bytes_data)-2):
            # Big-endian 16-bit
            val_be = struct.unpack('>H', bytes_data[j:j+2])[0]
            # Little-endian 16-bit
            val_le = struct.unpack('<H', bytes_data[j:j+2])[0]
            
            # Check if this could be a voltage (120-260V range)
            if 1200 <= val_be <= 2600:  # 0.1V units
                print(f"  Offset {j}: {val_be/10.0}V (big-endian)")
            if 1200 <= val_le <= 2600:
                print(f"  Offset {j}: {val_le/10.0}V (little-endian)")
            
            # Check for battery voltage (48-58V range)
            if 480 <= val_be <= 580:
                print(f"  Offset {j}: Battery? {val_be/10.0}V (big-endian)")
            if 480 <= val_le <= 580:
                print(f"  Offset {j}: Battery? {val_le/10.0}V (little-endian)")

if __name__ == "__main__":
    analyze_byte_patterns()