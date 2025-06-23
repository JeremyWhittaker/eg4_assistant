#!/usr/bin/env python3
"""Analyze the EG4 response to find correct offsets"""

import struct

# Response from tcpdump
hex_response = """
a11a05006f0001c24241333234303139343961000004333335323637303235327800505600000000
0000000000000000000000af04af04000000000000000000000000004c0000004c00000082
0ba704ad0447002d0078000c4a0700000c01030000000000000000000000000000000000000000
000000000073e8
"""

# Clean up the hex string
response = bytes.fromhex(hex_response.replace('\n', '').replace(' ', ''))

print(f"Response length: {len(response)} bytes")
print(f"Header: {response[:4].hex()} (a1 1a 05 00)")
print(f"Length byte: {response[4]:02x} ({response[4]} decimal)")
print()

# Known values from Solar Assistant:
# Battery: 53.3V, 0W, 99% SOC
# Grid: -10967W

print("Looking for known values:")
print("Battery voltage: 53.3V = 5330 (0x14d2) or 533 (0x215)")
print("Battery SOC: 99% = 99 (0x63)")
print("Grid power: -10967W = -10967 (0xd529) or -1097 (0xfbb7)")
print()

# Search for battery voltage (53.3V)
for i in range(len(response)-2):
    val = struct.unpack('>H', response[i:i+2])[0]
    if val == 5330:
        print(f"Found 5330 at offset {i}: battery voltage / 100")
    elif val == 533:
        print(f"Found 533 at offset {i}: battery voltage / 10")

# Search for battery SOC (99%)
for i in range(len(response)):
    if response[i] == 99:
        print(f"Found 99 at offset {i}: battery SOC")

# Search for grid power
for i in range(len(response)-2):
    val = struct.unpack('>h', response[i:i+2])[0]  # signed
    if val == -10967:
        print(f"Found -10967 at offset {i}: grid power raw")
    elif val == -1097:
        print(f"Found -1097 at offset {i}: grid power / 10")
    # Also check absolute value
    if abs(val) == 10967:
        print(f"Found {val} at offset {i}: possible grid power")

print("\n=== Hex dump with offsets ===")
for i in range(0, len(response), 16):
    hex_part = ' '.join(f'{b:02x}' for b in response[i:i+16])
    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in response[i:i+16])
    print(f"{i:04x}: {hex_part:<48} {ascii_part}")

print("\n=== Parsing key areas ===")
# Based on tcpdump, power values are around offset 0x50
print(f"Offset 48-54 (power area): {response[48:54].hex()}")
print(f"  48-50: {struct.unpack('>h', response[48:50])[0]} (signed)")
print(f"  50-52: {struct.unpack('>h', response[50:52])[0]} (signed)")
print(f"  52-54: {struct.unpack('>H', response[52:54])[0]} (unsigned)")

print(f"\nOffset 82-86 (battery area): {response[82:86].hex()}")
print(f"  82-84: {struct.unpack('>H', response[82:84])[0]} (battery voltage?)")
print(f"  85: {response[85]} (battery SOC?)")

# Look for grid voltage (around 240V = 2400)
print("\n=== Searching for grid voltage (240V) ===")
for i in range(0, len(response)-2, 2):
    val = struct.unpack('>H', response[i:i+2])[0]
    if 2300 <= val <= 2500:
        print(f"Offset {i}: {val/10:.1f}V (possible grid voltage)")