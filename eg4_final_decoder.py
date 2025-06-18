#!/usr/bin/env python3
"""
Final EG4 18kPV IoTOS Protocol Decoder
Based on careful analysis of actual responses
"""

import struct
import binascii

def decode_eg4_response_final(response):
    """
    Decode the EG4 IoTOS protocol response
    
    The response contains 32-bit big-endian integers after the device ID
    """
    
    if not response or len(response) < 50:
        return None
    
    data = {}
    
    # Extract serial (starts at byte 8)
    try:
        serial_end = response.find(b'\x00', 8)
        if serial_end == -1:
            serial_end = 19
        data['serial'] = response[8:serial_end].decode('ascii', errors='ignore').rstrip('a')
    except:
        data['serial'] = 'Unknown'
    
    # Extract device ID (starts around byte 24)
    try:
        # Find start of device ID (after 0x04)
        id_start = 24
        if response[23] == 0x04:
            id_start = 24
        id_end = response.find(b'\x00', id_start)
        if id_end == -1 or id_end > 35:
            id_end = 34
        data['device_id'] = response[id_start:id_end].decode('ascii', errors='ignore').rstrip('(')
    except:
        data['device_id'] = 'Unknown'
    
    # The actual data starts after the device ID
    # Looking at the hex: 27 00 00 e0 14 00 00 1a 16...
    # These appear to be 32-bit values
    
    try:
        # Find where the numeric data starts (after device ID and some padding)
        data_start = 37  # Skip the 0x27 byte
        
        # Read 32-bit big-endian values
        values_32bit = []
        offset = data_start
        while offset + 4 <= len(response) - 2:  # Leave room for checksum
            value = struct.unpack('>I', response[offset:offset+4])[0]
            values_32bit.append(value)
            offset += 4
            if len(values_32bit) >= 15:
                break
        
        # Now interpret these values
        # Based on the actual values: 0xe014=57364, 0x1a16=6678, 0xa5c3=42435, etc.
        # These need to be scaled appropriately
        
        if len(values_32bit) >= 10:
            # Values observed: 57364, 6678, 42435, 59787, 27552, 52366, 75, 2008, 1432
            
            # PV1 data (first set of values)
            # 57364 could be voltage * 100 = 573.64V (too high)
            # More likely these are power values in watts
            data['pv1_power'] = values_32bit[0] if values_32bit[0] < 20000 else values_32bit[0] / 10
            data['pv2_power'] = values_32bit[1] if values_32bit[1] < 20000 else 0
            data['pv3_power'] = values_32bit[2] if values_32bit[2] < 20000 else values_32bit[2] / 10
            
            # Total PV power
            data['total_pv_power'] = values_32bit[3] if values_32bit[3] < 100000 else 0
            
            # Battery power (can be negative for discharge)
            data['battery_power'] = values_32bit[4] if values_32bit[4] < 50000 else 0
            
            # Grid power (can be negative for export)
            data['grid_power'] = values_32bit[5] if values_32bit[5] < 50000 else 0
            
            # Load power
            data['load_power'] = values_32bit[7] if values_32bit[7] < 20000 else 0
            
            # Daily generation
            data['today_generation'] = values_32bit[8] / 10.0 if values_32bit[8] < 100000 else 0
        
        # Look for other data in different format
        # Check for 16-bit values in specific locations
        if len(response) > 80:
            # Battery SOC often single byte
            for i in range(60, min(95, len(response))):
                if 0 < response[i] <= 100:
                    data['battery_soc'] = response[i]
                    break
            
            # Grid voltage (16-bit) - look for values in 200-250V range
            for i in range(50, min(90, len(response)-2)):
                val = struct.unpack('>H', response[i:i+2])[0]
                if 2000 < val < 2500:  # 200-250V in 0.1V units
                    data['grid_voltage'] = val / 10.0
                    break
        
        # Calculate PV voltages/currents from power if possible
        # Typical MPPT voltage for 18kPV is around 300-400V per string
        if 'pv1_power' in data and data['pv1_power'] > 0:
            data['pv1_voltage'] = 380.0  # Estimate
            data['pv1_current'] = round(data['pv1_power'] / data['pv1_voltage'], 1)
        
    except Exception as e:
        print(f"Decode error: {e}")
        import traceback
        traceback.print_exc()
    
    return data


def analyze_response_detailed():
    """Detailed analysis of the response"""
    
    response = b"\xa1\x1a\x05\x00o\x00\x01\xc2BA32401949a\x00\x00\x043352670252(\x00PZ'\x00\x00\xe0\x14\x00\x00\x1a\x16\x00\x00\xa5\xc3\x00\x00\xe9\x8b\x00\x00k\xa0\x00\x00\xcc\x8e\x00\x00K\x00\x00\x00\xd8\x07\x00\x00\x00\x98\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00)\x00*\x004\x00\x02\x00\x00\x00n\x80\xc1\x01\x00\x00\x00"
    
    print("Detailed Response Analysis")
    print("=" * 60)
    print(f"Total length: {len(response)} bytes")
    print(f"\nHex dump:")
    print(binascii.hexlify(response))
    
    print("\nStructure breakdown:")
    print(f"Header (0-7): {binascii.hexlify(response[0:8])}")
    print(f"Serial (8-19): {response[8:20]}")
    print(f"Unknown (20-23): {binascii.hexlify(response[20:24])}")
    print(f"Device ID (24-35): {response[24:35]}")
    print(f"Data section (36+): {binascii.hexlify(response[36:])}")
    
    print("\n32-bit values starting at byte 37:")
    offset = 37
    idx = 0
    while offset + 4 <= len(response):
        value = struct.unpack('>I', response[offset:offset+4])[0]
        print(f"  Value {idx} (offset {offset}): {value} (0x{value:08x})")
        offset += 4
        idx += 1
        if idx >= 15:
            break
    
    print("\n16-bit values in data section:")
    for i in range(36, min(90, len(response)-2), 2):
        val = struct.unpack('>H', response[i:i+2])[0]
        if val > 100:  # Only show significant values
            print(f"  Offset {i}: {val} ({val/10.0} if /10, {val/100.0} if /100)")
    
    print("\nDecoded data:")
    decoded = decode_eg4_response_final(response)
    if decoded:
        for key, value in sorted(decoded.items()):
            print(f"  {key}: {value}")


if __name__ == "__main__":
    analyze_response_detailed()