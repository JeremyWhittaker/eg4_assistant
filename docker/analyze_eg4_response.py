#!/usr/bin/env python3
"""Analyze EG4 response"""

import binascii
import struct

# The response we got
response_hex = 'a11a05006f0001c2424133323430313934396100000333333532363730323532c80050000c3402f40100003200000002001500080205000a000d0015001c02e0015a003c0005001500080262006400530220030c01000000006400530200000000000002001000000000000100040000000000e992'
response = bytes.fromhex(response_hex)

print(f"Response length: {len(response)} bytes")
print(f"Response hex: {response_hex}")
print("\n=== Analysis ===")

# Look for patterns
print(f"Header: {response[:4].hex()}")
print(f"Possible length field: {struct.unpack('>H', response[4:6])[0]}")

# Find ASCII strings
print("\n=== ASCII strings in response ===")
ascii_chars = []
for i, b in enumerate(response):
    if 32 <= b <= 126:  # Printable ASCII
        ascii_chars.append(chr(b))
    else:
        if ascii_chars:
            print(f"Position {i-len(ascii_chars)}: {''.join(ascii_chars)}")
            ascii_chars = []

# Try to parse as different structures
print("\n=== Trying different parse methods ===")

# Method 1: Skip header and parse as 16-bit values
print("\nMethod 1: 16-bit big-endian values starting at offset 10:")
offset = 10
for i in range(10):
    if offset + 2 <= len(response):
        value = struct.unpack('>H', response[offset:offset+2])[0]
        print(f"  Offset {offset}: {value} (0x{value:04x})")
        offset += 2

# Method 2: Look for specific patterns
print("\nMethod 2: Looking for voltage/current patterns (300-400V range):")
for i in range(0, len(response)-2, 2):
    value = struct.unpack('>H', response[i:i+2])[0]
    if 3000 <= value <= 4000:  # Possibly voltage * 10
        print(f"  Offset {i}: {value} -> {value/10.0}V")
    elif 100 <= value <= 150:  # Possibly current * 10
        print(f"  Offset {i}: {value} -> {value/10.0}A")

# Method 3: Find serial number and model
print("\nMethod 3: Device info:")
# The response contains "BA32401949a" which looks like a serial number
serial_start = response.find(b'BA')
if serial_start >= 0:
    serial_end = serial_start + 11
    serial = response[serial_start:serial_end]
    print(f"  Serial number: {serial.decode('ascii', errors='ignore')}")

# Another number "3352670252"
num_start = response.find(b'335')
if num_start >= 0:
    num_end = num_start + 10
    number = response[num_start:num_end]
    print(f"  Device number: {number.decode('ascii', errors='ignore')}")

print("\n=== Potential data values ===")
# Based on typical inverter data positions
positions = {
    0x2C: "PV1 Voltage?",
    0x2E: "PV1 Current?", 
    0x30: "PV1 Power?",
    0x32: "PV2 Voltage?",
    0x34: "PV2 Current?",
    0x36: "PV2 Power?",
    0x38: "Battery Voltage?",
    0x3A: "Battery Current?",
    0x3C: "Battery Power?",
    0x3E: "Battery SOC?",
    0x40: "Grid Voltage?",
    0x42: "Grid Frequency?",
    0x44: "Grid Power?",
    0x46: "Load Power?",
}

for offset, name in positions.items():
    if offset + 2 <= len(response):
        value = struct.unpack('>H', response[offset:offset+2])[0]
        print(f"  {name} at 0x{offset:02x}: {value} (decimal), 0x{value:04x} (hex)")