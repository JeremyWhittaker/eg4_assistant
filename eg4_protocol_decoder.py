#!/usr/bin/env python3
"""
EG4 18kPV IoTOS Protocol Decoder
Decodes binary data from the inverter into actual values
"""

import struct
import binascii

def decode_eg4_response(response):
    """
    Decode the EG4 IoTOS protocol response into actual inverter data
    
    Response structure:
    0-7: Header (a1 1a 05 00 6f 00 01 c2)
    8-19: Serial number (BA32401949)
    20-23: Unknown bytes
    24-34: Device ID (3352670252)
    35+: Binary data containing inverter values
    """
    
    if not response or len(response) < 117:
        return None
        
    # Basic structure
    data = {
        'serial': response[8:19].decode('ascii', errors='ignore').rstrip('\x00'),
        'device_id': response[24:34].decode('ascii', errors='ignore').rstrip('\x00'),
    }
    
    # Based on analysis of the responses, different byte offsets contain different data
    # The last byte before checksum seems to indicate data type
    data_type = response[34] if len(response) > 34 else 0
    
    # Decode based on patterns observed in the responses
    if len(response) >= 117:
        # Common data appears to be 2-byte values (big-endian)
        # Looking at monitoring data with timestamps, we can see variations in specific bytes
        
        # Power/Voltage data typically starts after the device ID
        offset = 35
        
        # Extract values as 16-bit unsigned integers (common in inverter protocols)
        # These offsets are based on observed variations in the data
        try:
            # PV Input Data (observed variations in bytes 36-50)
            data['pv1_voltage'] = struct.unpack('>H', response[36:38])[0] / 10.0  # Typically in 0.1V units
            data['pv1_current'] = struct.unpack('>H', response[38:40])[0] / 10.0  # Typically in 0.1A units
            data['pv1_power'] = struct.unpack('>H', response[40:42])[0]  # Watts
            
            data['pv2_voltage'] = struct.unpack('>H', response[42:44])[0] / 10.0
            data['pv2_current'] = struct.unpack('>H', response[44:46])[0] / 10.0
            data['pv2_power'] = struct.unpack('>H', response[46:48])[0]
            
            data['pv3_voltage'] = struct.unpack('>H', response[48:50])[0] / 10.0
            data['pv3_current'] = struct.unpack('>H', response[50:52])[0] / 10.0
            data['pv3_power'] = struct.unpack('>H', response[52:54])[0]
            
            # Battery Data (observed in bytes 54-70)
            data['battery_voltage'] = struct.unpack('>H', response[54:56])[0] / 10.0
            data['battery_current'] = struct.unpack('>h', response[56:58])[0] / 10.0  # Signed for charge/discharge
            data['battery_power'] = struct.unpack('>h', response[58:60])[0]  # Signed
            data['battery_soc'] = response[60] if response[60] <= 100 else 0  # Percentage
            
            # Grid Data (observed in bytes 70-85)
            data['grid_voltage'] = struct.unpack('>H', response[70:72])[0] / 10.0
            data['grid_current'] = struct.unpack('>H', response[72:74])[0] / 10.0
            data['grid_power'] = struct.unpack('>h', response[74:76])[0]  # Signed for import/export
            data['grid_frequency'] = struct.unpack('>H', response[76:78])[0] / 100.0  # Hz
            
            # Load Data (observed in bytes 85-95)
            data['load_voltage'] = struct.unpack('>H', response[85:87])[0] / 10.0
            data['load_current'] = struct.unpack('>H', response[87:89])[0] / 10.0
            data['load_power'] = struct.unpack('>H', response[89:91])[0]
            data['load_percentage'] = response[91] if response[91] <= 100 else 0
            
            # Temperature (observed around byte 95-100)
            data['inverter_temp'] = struct.unpack('>h', response[95:97])[0] / 10.0  # Celsius
            
            # Status flags (observed in last 10 bytes before checksum)
            data['inverter_status'] = response[105]
            data['battery_status'] = response[106]
            data['grid_status'] = response[107]
            
            # Energy counters (32-bit values)
            if len(response) >= 110:
                data['today_generation'] = struct.unpack('>I', response[100:104])[0] / 10.0  # kWh
                
        except Exception as e:
            # If decoding fails, return what we have
            print(f"Decode error: {e}")
            
    return data

def analyze_protocol_variations(json_data):
    """
    Analyze the protocol responses to identify data patterns
    """
    print("Analyzing IoTOS Protocol Responses")
    print("=" * 50)
    
    # Look at monitoring data which should show real-time variations
    monitoring = json_data.get('monitoring_data', [])
    
    for i, reading in enumerate(monitoring):
        response_hex = reading['data']['raw']
        # Convert hex string back to bytes
        response_bytes = bytes.fromhex(response_hex[2:-1])  # Remove b' and '
        
        print(f"\nReading {i+1} at {reading['timestamp']}:")
        print(f"Length: {len(response_bytes)} bytes")
        
        # Decode the response
        decoded = decode_eg4_response(response_bytes)
        if decoded:
            print(f"Serial: {decoded.get('serial')}")
            print(f"Device ID: {decoded.get('device_id')}")
            print(f"PV1: {decoded.get('pv1_voltage', 0):.1f}V, {decoded.get('pv1_current', 0):.1f}A, {decoded.get('pv1_power', 0)}W")
            print(f"Battery: {decoded.get('battery_voltage', 0):.1f}V, {decoded.get('battery_current', 0):.1f}A, SOC: {decoded.get('battery_soc', 0)}%")
            print(f"Grid: {decoded.get('grid_voltage', 0):.1f}V, {decoded.get('grid_power', 0)}W")
            print(f"Load: {decoded.get('load_power', 0)}W")

if __name__ == "__main__":
    # Test with sample data
    import json
    
    # Load the analysis file
    try:
        with open('eg4_iotos_analysis.json', 'r') as f:
            json_data = json.load(f)
            analyze_protocol_variations(json_data)
    except Exception as e:
        print(f"Error loading analysis file: {e}")
        
    # Test with a sample response
    sample = b'\xa1\x1a\x05\x00o\x00\x01\xc2BA32401949a\x00\x00\x043352670252\x00\x00P\x04\x00d\x0e\xca\x0d!\x0e\x15\x02dd\x00\x1f:\x13|\x0d\xa0\x0d\x00\x00\x00\x00\x8c\x09\x05\x01\x04\x00o\x17V,\x00\x00\xc6\x12\xe8\x03\x8b\x09\xe1\x1ao0o\x17\x00\x00\x00\x00\xa8$\x00\x00U\x00k\x00l\x00\x15\x01\x0d\x00\x1b\x00\x01\x00\x00\x00\xc7\x00\xd1\x00\xa3\x0e\x86\x0cO\xed'
    
    print("\n\nDecoding sample response:")
    decoded = decode_eg4_response(sample)
    if decoded:
        for key, value in decoded.items():
            print(f"{key}: {value}")