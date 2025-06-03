#!/usr/bin/env python3
import subprocess
import os

# Create extraction directory
os.makedirs('extracted_files', exist_ok=True)

# Try to extract entire opt directory
print("Attempting to extract /opt directory...")
try:
    # Use e2cp if available
    subprocess.run(['e2cp', '-r', 'linux_partition.img:/opt', 'extracted_files/'], 
                   capture_output=True)
except:
    pass

# Try using 7z to extract the filesystem
print("Attempting to extract with 7z...")
try:
    subprocess.run(['7z', 'x', 'linux_partition.img', '-oextracted_7z'], 
                   capture_output=True)
except:
    pass

# Search for strings in the image that might indicate API endpoints
print("\nSearching for API-related strings in the image...")
api_patterns = [
    'luxpower',
    'eg4.*api',
    'inverter.*api',
    'modbus',
    'solar.*assistant.*api',
    'http.*172\\.16',
    'tcp.*502',  # Modbus TCP port
    'serial.*tty',
    'RS485',
    'register.*0x',
    'holding.*register',
    'function.*code',
]

for pattern in api_patterns:
    print(f"\n=== Searching for: {pattern} ===")
    result = subprocess.run(['strings', 'linux_partition.img'], 
                          capture_output=True, text=True)
    
    lines = result.stdout.split('\n')
    matches = []
    for i, line in enumerate(lines):
        if pattern.replace('\\', '').replace('.*', '').lower() in line.lower():
            # Get context lines
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                if lines[j].strip():
                    matches.append(lines[j])
            if len(matches) > 10:
                break
    
    for match in matches[:10]:
        print(match[:200])