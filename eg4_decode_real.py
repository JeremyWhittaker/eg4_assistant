#!/usr/bin/env python3
"""
Real EG4 18kPV IoTOS Protocol Decoder
Based on actual response analysis
"""

import struct

def decode_eg4_iotos(response):
    """
    Decode actual EG4 IoTOS protocol response
    
    Based on response:
    \xa1\x1a\x05\x00o\x00\x01\xc2BA32401949a\x00\x00\x043352670252(\x00PZ'\x00\x00\xe0\x14\x00\x00\x1a\x16...
    
    Structure appears to be:
    0-7: Header (a1 1a 05 00 6f 00 01 c2)
    8-19: Serial (BA32401949)
    20-23: Padding
    24-34: Device ID
    35+: Data values as 32-bit integers
    """
    
    if not response or len(response) < 117:
        return None
    
    data = {}
    
    # Extract serial and device ID
    try:
        serial_end = response.find(b'\x00', 8)
        data['serial'] = response[8:serial_end].decode('ascii', errors='ignore').rstrip('a')
    except:
        data['serial'] = 'Unknown'
    
    try:
        device_end = response.find(b'\x00', 24)
        if device_end == -1:
            device_end = 34
        data['device_id'] = response[24:device_end].decode('ascii', errors='ignore').rstrip()
    except:
        data['device_id'] = 'Unknown'
    
    # The data after byte 35 appears to be 32-bit values
    # Based on the pattern: \x00\x00\xe0\x14\x00\x00\x1a\x16...
    # These look like 32-bit big-endian integers
    
    try:
        offset = 36  # Start after the device ID and first byte
        
        # Read values as 32-bit integers
        values = []
        while offset + 4 <= len(response) - 10:  # Leave room for checksum
            value = struct.unpack('>I', response[offset:offset+4])[0]
            values.append(value)
            offset += 4
            if len(values) >= 20:  # Read up to 20 values
                break
        
        # Map values based on typical inverter data
        # These mappings are estimates and may need adjustment
        if len(values) >= 10:
            # PV values (typically voltage in 0.1V, current in 0.01A, power in W)
            data['pv1_voltage'] = values[0] / 100.0 if values[0] < 10000 else 0
            data['pv1_current'] = values[1] / 100.0 if values[1] < 5000 else 0
            data['pv1_power'] = values[2] if values[2] < 20000 else 0
            
            data['pv2_voltage'] = values[3] / 100.0 if values[3] < 10000 else 0
            data['pv2_current'] = values[4] / 100.0 if values[4] < 5000 else 0
            data['pv2_power'] = values[5] if values[5] < 20000 else 0
            
            # Battery values
            data['battery_voltage'] = values[6] / 100.0 if values[6] < 10000 else 0
            data['battery_current'] = (values[7] - 32768) / 100.0 if values[7] > 0 else 0  # Signed
            data['battery_power'] = values[8] if values[8] < 20000 else 0
            
            # Grid/Load values
            data['grid_power'] = values[9] if values[9] < 50000 else 0
            
        # Look for specific patterns in known locations
        # Battery SOC is often a single byte
        if len(response) > 90:
            data['battery_soc'] = response[90] if response[90] <= 100 else 0
            
        # Grid voltage often around byte 70-80
        if len(response) > 75:
            grid_v = struct.unpack('>H', response[74:76])[0]
            if 2000 < grid_v < 3000:  # 200-300V range
                data['grid_voltage'] = grid_v / 10.0
                
    except Exception as e:
        print(f"Decode error: {e}")
    
    return data


def test_decoder():
    """Test the decoder with actual response"""
    
    # Actual response from the inverter
    response = b"\xa1\x1a\x05\x00o\x00\x01\xc2BA32401949a\x00\x00\x043352670252(\x00PZ'\x00\x00\xe0\x14\x00\x00\x1a\x16\x00\x00\xa5\xc3\x00\x00\xe9\x8b\x00\x00k\xa0\x00\x00\xcc\x8e\x00\x00K\x00\x00\x00\xd8\x07\x00\x00\x00\x98\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00)\x00*\x004\x00\x02\x00\x00\x00n\x80\xc1\x01\x00\x00\x00"
    
    print("Testing EG4 IoTOS decoder with actual response:")
    print(f"Response length: {len(response)} bytes")
    print()
    
    decoded = decode_eg4_iotos(response)
    
    if decoded:
        print("Decoded values:")
        for key, value in decoded.items():
            print(f"  {key}: {value}")
    else:
        print("Failed to decode response")
    
    # Show hex dump of interesting sections
    print("\nHex dump of data section (bytes 36-80):")
    hex_data = response[36:80].hex()
    for i in range(0, len(hex_data), 32):
        print(f"  {hex_data[i:i+32]}")


if __name__ == "__main__":
    test_decoder()