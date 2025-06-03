#!/usr/bin/env python3
import os
import sys
import struct

# Calculate offset for partition 2 (Linux partition)
# Start sector: 1056768, Sector size: 512 bytes
offset = 1056768 * 512

print(f"Extracting Linux partition from offset {offset} (0x{offset:x})")

# Extract the partition to a separate file
with open('2024-08-14-solar-assistant.rpi64.img', 'rb') as img:
    img.seek(offset)
    with open('linux_partition.img', 'wb') as part:
        # Read in chunks
        chunk_size = 1024 * 1024  # 1MB chunks
        while True:
            chunk = img.read(chunk_size)
            if not chunk:
                break
            part.write(chunk)

print("Linux partition extracted to linux_partition.img")
print(f"Size: {os.path.getsize('linux_partition.img') / (1024*1024):.2f} MB")