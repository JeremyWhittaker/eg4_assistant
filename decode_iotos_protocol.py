#!/usr/bin/env python3
"""
Decode and analyze the IoTOS protocol from EG4 18kPV
Response received: 
\xa1\x1a\x05\x00o\x00\x01\xc2BA32401949a\x00\x00\x043352670252...
"""

import struct
import binascii

def analyze_response():
    # The response we received
    response = b'\xa1\x1a\x05\x00o\x00\x01\xc2BA32401949a\x00\x00\x043352670252\xa0\x00P\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x9c5Y\x02\xae\xcb\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    
    print("Response Analysis:")
    print(f"Total length: {len(response)} bytes")
    print(f"Hex: {binascii.hexlify(response)[:100]}...")
    print()
    
    # Look for patterns
    print("Visible ASCII strings:")
    # BA32401949a - looks like a serial number
    # 3352670252 - another ID or timestamp
    
    # Try different interpretations
    print("\nByte-by-byte analysis:")
    print("Offset | Hex  | Dec | ASCII")
    print("-" * 30)
    
    for i in range(min(50, len(response))):
        byte = response[i]
        ascii_char = chr(byte) if 32 <= byte <= 126 else '.'
        print(f"{i:6} | 0x{byte:02x} | {byte:3} | {ascii_char}")
    
    # Extract visible strings
    print("\nExtracted data:")
    # Serial number starts at offset 8
    serial = response[8:19].decode('ascii', errors='ignore')
    print(f"Serial Number: {serial}")  # BA32401949
    
    # Another ID at offset 24
    id2 = response[24:34].decode('ascii', errors='ignore')
    print(f"Device ID: {id2}")  # 3352670252
    
    # Try to find structure
    print("\nPossible packet structure:")
    print(f"Header: {binascii.hexlify(response[:8])}")
    print(f"  - Byte 0: 0x{response[0]:02x} - Possible packet type or protocol ID")
    print(f"  - Byte 1: 0x{response[1]:02x} - Length or command?")
    print(f"  - Bytes 2-3: 0x{response[2]:02x}{response[3]:02x} - Possible length field")
    
    # Check for common IoT protocols
    if response[0] == 0xa1:
        print("\n0xA1 could indicate a proprietary protocol header")
    
    # Look for timestamps (Unix timestamps would be 4 bytes)
    possible_timestamp = struct.unpack('>I', response[88:92])[0]
    print(f"\nPossible timestamp at offset 88: {possible_timestamp}")
    
    return serial, id2

def create_iotos_client():
    """Create a more sophisticated IoTOS client"""
    print("\nCreating IoTOS protocol decoder...")
    
    # Common message types in IoT protocols
    message_types = {
        0xa1: "Device Info/Status",
        0xa2: "Data Request",
        0xa3: "Data Response",
        0xa4: "Control Command",
        0xa5: "Acknowledgment",
    }
    
    # Possible commands to try
    test_commands = [
        # Try different header bytes
        b'\xa1\x00\x00\x00',  # Simple query with A1 header
        b'\xa2\x00\x00\x00',  # Try A2
        b'\xa1\x1a\x00\x00',  # Mirror what we saw
        b'\xa1\x01\x00\x00',  # Different command byte
        
        # Try some common IoT commands
        b'INFO\r\n',
        b'STATUS\r\n',
        b'DATA\r\n',
        
        # Try JSON
        b'{"cmd":"status"}\n',
        b'{"cmd":"info"}\n',
        b'{"cmd":"data"}\n',
    ]
    
    return test_commands

if __name__ == "__main__":
    serial, device_id = analyze_response()
    commands = create_iotos_client()
    
    print("\nSummary:")
    print(f"- Found serial number: {serial}")
    print(f"- Found device ID: {device_id}")
    print("- Protocol appears to be binary with ASCII embedded data")
    print("- Port 8000 is the IoTOS communication port")
    print("\nNext steps: Try more protocol discovery commands")