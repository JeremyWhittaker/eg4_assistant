#!/usr/bin/env python3
"""
EG4 Response Decoder - Finds correct byte positions for data
"""

import socket
import struct
import binascii
import time

def get_response():
    """Get a fresh response from the inverter"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('172.16.107.129', 8000))
        
        # Send query
        sock.send(b'\xa1\x1a\x05\x00')
        response = sock.recv(4096)
        sock.close()
        
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

def analyze_response(response):
    """Detailed analysis of response structure"""
    if not response:
        return
    
    print(f"Response length: {len(response)} bytes")
    print(f"Header: {binascii.hexlify(response[:8])}")
    print()
    
    # Print hex dump with ASCII
    print("Hex dump with ASCII:")
    for i in range(0, len(response), 16):
        hex_part = ' '.join(f'{b:02x}' for b in response[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in response[i:i+16])
        print(f"{i:04x}: {hex_part:<48} |{ascii_part}|")
    
    print("\n" + "="*70)
    print("SEARCHING FOR DATA PATTERNS")
    print("="*70)
    
    # Method 1: Look for realistic value ranges at different offsets
    print("\n1. Testing different offsets for PV/Battery/Grid patterns:")
    
    best_matches = []
    
    for offset in range(20, min(len(response) - 30, 120), 2):
        try:
            # Read 15 consecutive 16-bit values
            values = []
            for i in range(15):
                if offset + i*2 + 2 <= len(response):
                    val = struct.unpack('>H', response[offset + i*2:offset + i*2 + 2])[0]
                    values.append(val)
            
            # Score this offset based on realistic values
            score = 0
            pv_voltages = []
            
            # Check first 3 values as PV voltages (200-600V when /10)
            for i in range(3):
                if i < len(values) and 2000 <= values[i] <= 6000:
                    score += 10
                    pv_voltages.append(values[i] / 10.0)
            
            # Check next 3 as PV currents (0-30A when /10)
            for i in range(3, 6):
                if i < len(values) and 0 <= values[i] <= 300:
                    score += 5
            
            # Check for battery voltage (40-60V when /10)
            for i in range(6, 9):
                if i < len(values) and 400 <= values[i] <= 600:
                    score += 8
            
            # Check for grid voltage (200-250V when /10)
            for i in range(9, 12):
                if i < len(values) and 2000 <= values[i] <= 2500:
                    score += 7
            
            # Check for frequency (45-65Hz when /10 or /100)
            for i in range(12, 15):
                if i < len(values):
                    if 450 <= values[i] <= 650:  # Hz * 10
                        score += 5
                    elif 4500 <= values[i] <= 6500:  # Hz * 100
                        score += 5
            
            if score > 20:  # Good match
                best_matches.append((offset, score, values[:10], pv_voltages))
        
        except:
            continue
    
    # Show best matches
    if best_matches:
        best_matches.sort(key=lambda x: x[1], reverse=True)
        print(f"\nFound {len(best_matches)} promising offsets:")
        
        for offset, score, values, pv_voltages in best_matches[:3]:
            print(f"\n  Offset {offset} (score: {score}):")
            print(f"    Raw values: {values[:6]}")
            if pv_voltages:
                print(f"    Possible PV voltages: {pv_voltages}")
    
    # Method 2: Look for specific patterns
    print("\n\n2. Looking for specific value patterns:")
    
    # Battery SOC (0-100)
    print("\n  Battery SOC candidates (0-100):")
    for i in range(len(response)):
        if 0 < response[i] <= 100:
            # Check if surrounded by other data (not ASCII)
            if i > 0 and i < len(response)-1:
                if response[i-1] > 127 or response[i+1] > 127:
                    print(f"    Position {i}: {response[i]}%")
    
    # Power values (look for realistic ranges)
    print("\n  Power value candidates (1000-20000):")
    for i in range(0, len(response)-2, 2):
        val = struct.unpack('>H', response[i:i+2])[0]
        if 1000 <= val <= 20000:
            print(f"    Position {i}: {val}W")
    
    # Method 3: Decode based on known response structure
    print("\n\n3. Decoding based on EG4 protocol structure:")
    
    # The response format appears to be:
    # Header (4 bytes): a1 1a 05 00
    # Length (2 bytes): 6f 00 (111 decimal)
    # Unknown (2 bytes): 01 c2
    # Serial number: "BA32401949"
    # More device info
    # Then actual data
    
    # Find end of ASCII device info
    ascii_end = 0
    for i in range(8, min(60, len(response))):
        if response[i] == 0 and response[i+1] == 0:
            ascii_end = i + 2
            break
    
    print(f"  ASCII device info ends at position: {ascii_end}")
    
    # Data likely starts after device info
    if ascii_end > 0 and ascii_end + 40 < len(response):
        print(f"\n  Attempting to decode data starting at position {ascii_end}:")
        
        pos = ascii_end
        
        # Skip some bytes that might be flags/status
        pos += 4
        
        # Try to decode as inverter data
        try:
            # Common pattern: Voltages, Currents, Power, Status
            print(f"\n  Reading from position {pos}:")
            
            # Try different interpretations
            for attempt in range(3):
                print(f"\n  Attempt {attempt + 1} (offset {pos + attempt*2}):")
                p = pos + attempt*2
                
                if p + 20 <= len(response):
                    v1 = struct.unpack('>H', response[p:p+2])[0]
                    v2 = struct.unpack('>H', response[p+2:p+4])[0]
                    v3 = struct.unpack('>H', response[p+4:p+6])[0]
                    
                    print(f"    Values: {v1}, {v2}, {v3}")
                    print(f"    As voltages (/10): {v1/10:.1f}V, {v2/10:.1f}V, {v3/10:.1f}V")
                    print(f"    As currents (/10): {v1/10:.1f}A, {v2/10:.1f}A, {v3/10:.1f}A")
                    print(f"    As power: {v1}W, {v2}W, {v3}W")
        except:
            pass
    
    return best_matches[0] if best_matches else None

def decode_with_offset(response, offset):
    """Decode response using specific offset"""
    try:
        data = {}
        pos = offset
        
        # PV Voltages (3 strings)
        data['pv1_voltage'] = struct.unpack('>H', response[pos:pos+2])[0] / 10.0
        data['pv2_voltage'] = struct.unpack('>H', response[pos+2:pos+4])[0] / 10.0
        data['pv3_voltage'] = struct.unpack('>H', response[pos+4:pos+6])[0] / 10.0
        
        # PV Currents
        data['pv1_current'] = struct.unpack('>H', response[pos+6:pos+8])[0] / 10.0
        data['pv2_current'] = struct.unpack('>H', response[pos+8:pos+10])[0] / 10.0
        data['pv3_current'] = struct.unpack('>H', response[pos+10:pos+12])[0] / 10.0
        
        # Calculate power
        data['pv1_power'] = int(data['pv1_voltage'] * data['pv1_current'])
        data['pv2_power'] = int(data['pv2_voltage'] * data['pv2_current'])
        data['pv3_power'] = int(data['pv3_voltage'] * data['pv3_current'])
        data['total_pv_power'] = data['pv1_power'] + data['pv2_power'] + data['pv3_power']
        
        # Battery (offset + 12)
        data['battery_voltage'] = struct.unpack('>H', response[pos+12:pos+14])[0] / 10.0
        data['battery_current'] = struct.unpack('>h', response[pos+14:pos+16])[0] / 10.0  # Signed
        data['battery_power'] = int(data['battery_voltage'] * data['battery_current'])
        
        # Grid (offset + 16)
        data['grid_voltage'] = struct.unpack('>H', response[pos+16:pos+18])[0] / 10.0
        data['grid_frequency'] = struct.unpack('>H', response[pos+18:pos+20])[0] / 100.0
        
        return data
        
    except Exception as e:
        print(f"Decode error: {e}")
        return None

def main():
    print("EG4 Response Decoder")
    print("=" * 70)
    
    # Get response
    print("\nGetting response from inverter...")
    response = get_response()
    
    if not response:
        print("Failed to get response")
        return
    
    # Analyze response
    best_match = analyze_response(response)
    
    # If we found a good offset, try decoding
    if best_match:
        offset = best_match[0]
        print(f"\n\n{'='*70}")
        print(f"DECODING WITH BEST OFFSET: {offset}")
        print(f"{'='*70}")
        
        data = decode_with_offset(response, offset)
        if data:
            print("\nDecoded values:")
            print(f"PV1: {data['pv1_voltage']:.1f}V × {data['pv1_current']:.1f}A = {data['pv1_power']}W")
            print(f"PV2: {data['pv2_voltage']:.1f}V × {data['pv2_current']:.1f}A = {data['pv2_power']}W")
            print(f"PV3: {data['pv3_voltage']:.1f}V × {data['pv3_current']:.1f}A = {data['pv3_power']}W")
            print(f"Total PV: {data['total_pv_power']}W")
            print(f"Battery: {data['battery_voltage']:.1f}V × {data['battery_current']:.1f}A = {data['battery_power']}W")
            print(f"Grid: {data['grid_voltage']:.1f}V @ {data['grid_frequency']:.2f}Hz")
    
    # Save raw response for further analysis
    with open('/tmp/eg4_response_raw.bin', 'wb') as f:
        f.write(response)
    print(f"\n✓ Raw response saved to /tmp/eg4_response_raw.bin")

if __name__ == "__main__":
    main()