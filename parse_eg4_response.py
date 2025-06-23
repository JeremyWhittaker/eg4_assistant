#!/usr/bin/env python3
"""Parse EG4 response correctly based on tcpdump analysis"""

import struct

# Real response from tcpdump when Solar Assistant showed:
# Grid: -10967W, Battery: 53.3V, 99% SOC
hex_data = """
a11a05006f0001c242413332343031393439610000043333353236373032353200005004
0017e39d840d15026364041c3219f30bfe0b0000006b090101060
06fe2e000000314e8036a09e9aa6a306f17000000009d2a000004
01d000d200e80131000ee001900000ed00fb00ad0e870c8401
"""

# Clean hex
response = bytes.fromhex(hex_data.replace('\n', '').replace(' ', ''))
print(f"Response length: {len(response)}")

# Parse header
print(f"\nHeader: {response[:4].hex()}")
print(f"Length field: {response[4]} (expecting 111 for 117 total bytes)")
print(f"Serial: {response[8:21].decode('ascii', errors='ignore')}")

# Based on tcpdump analysis and working values, here's the correct parsing:
print("\n=== CORRECT PARSING ===")

# Looking at the tcpdump hex dump more carefully:
# The response that showed grid -10361W had these bytes at offset 50-52: d529
# Let's look for that pattern

# From tcpdump line showing actual data:
# At offset 0x50: we see "0d84 0d15" which is around offset 48-52 in the response

# Let me recalculate from the actual hex dump
print("\nAnalyzing power values region (around offset 48-54):")
for i in range(46, 56, 2):
    if i + 2 <= len(response):
        val_signed = struct.unpack('>h', response[i:i+2])[0]
        val_unsigned = struct.unpack('>H', response[i:i+2])[0]
        print(f"Offset {i}: signed={val_signed}, unsigned={val_unsigned}, hex={response[i:i+2].hex()}")

# From the tcpdump, I can see the actual values are at these offsets:
# The key is that after the header and serial number, the data starts

# Let's find where the actual data starts by looking for known patterns
data_start = 0
for i in range(len(response) - 4):
    if response[i:i+4] == b'\x00\x00\x50\x04':  # This pattern appears before power data
        data_start = i + 4
        print(f"\nFound data start marker at offset {i}, data starts at {data_start}")
        break

if data_start > 0:
    # Now parse from the correct offset
    print("\nParsing from correct offset:")
    
    # The power values appear to be ~16 bytes after the marker
    power_offset = data_start + 16
    
    if power_offset + 6 <= len(response):
        battery_power = struct.unpack('>h', response[power_offset:power_offset+2])[0]
        grid_power = struct.unpack('>h', response[power_offset+2:power_offset+4])[0]
        load_power = struct.unpack('>H', response[power_offset+4:power_offset+6])[0]
        
        print(f"Battery power: {battery_power}")
        print(f"Grid power: {grid_power}")
        print(f"Load power: {load_power}")
        
        # Check if they need scaling
        if abs(grid_power) > 20000:
            print(f"Grid power scaled: {grid_power/10:.0f}W")

# Let's also look for the battery voltage (should be 5330 for 53.3V)
print("\n\nSearching for battery voltage (53.3V = 5330):")
for i in range(len(response) - 2):
    val = struct.unpack('>H', response[i:i+2])[0]
    if 5300 <= val <= 5400:
        print(f"Found possible battery voltage at offset {i}: {val} -> {val/100:.1f}V")

# And battery SOC (99%)
print("\nSearching for battery SOC (99):")
for i in range(len(response)):
    if response[i] == 99:
        print(f"Found 99 at offset {i}")
        
# Let's hex dump the whole thing with offsets
print("\n\n=== HEX DUMP ===")
for i in range(0, len(response), 16):
    hex_part = ' '.join(f'{b:02x}' for b in response[i:i+16])
    ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in response[i:i+16])
    print(f"{i:04x}: {hex_part:<48} {ascii_part}")