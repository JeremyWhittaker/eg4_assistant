#!/usr/bin/env python3
"""Parse EG4 18kPV IoTOS response"""

import binascii
import struct

# The actual response we received
response_hex = 'a11a05006f0001c24241333234303139343961000004333335323637303235325000500200a00fa00f3002c20100000000000000000000c00000000000000000000300020030028305000000001b0d120db8019a01000085011902da0100000000000000'
response = binascii.unhexlify(response_hex)

print(f"Response length: {len(response)} bytes")
print(f"Full response (hex): {response_hex}\n")

# Parse header
print("Header analysis:")
print(f"Header (0-4): {response[:4].hex()} = {list(response[:4])}")

# Look for ASCII strings (serial numbers, device IDs)
print("\nASCII strings found:")
for i in range(len(response) - 10):
    chunk = response[i:i+10]
    if all(32 <= b <= 126 for b in chunk):
        print(f"Position {i}: '{chunk.decode('ascii')}'")

# Parse as 16-bit values
print("\n16-bit values (big-endian):")
for i in range(0, min(len(response), 100), 2):
    if i + 2 <= len(response):
        value = struct.unpack('>H', response[i:i+2])[0]
        if 100 <= value <= 30000:  # Reasonable range for power/voltage
            print(f"Position {i}: {value}")

# Parse specific positions based on pattern
print("\nParsing based on Solar Assistant offsets:")
print(f"Bytes 37-41: {response[37:41].hex()} = {struct.unpack('>I', response[37:41])[0]}")
print(f"Bytes 41-45: {response[41:45].hex()} = {struct.unpack('>I', response[41:45])[0]}")

# Try different interpretations
print("\nTrying 16-bit values from position 60:")
for i in range(60, min(100, len(response)), 2):
    if i + 2 <= len(response):
        value = struct.unpack('>H', response[i:i+2])[0]
        print(f"Position {i}: {value} (0x{value:04x})")