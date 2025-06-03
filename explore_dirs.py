#!/usr/bin/env python3
import subprocess

# List directories at different levels
dirs_to_check = [
    '/',
    '/opt',
    '/var',
    '/usr',
    '/home',
    '/etc/systemd/system',
    '/lib/systemd/system',
    '/usr/local',
    '/srv',
    '/var/lib',
    '/var/www',
]

for dir_path in dirs_to_check:
    cmd = ['debugfs', '-R', f'ls -la {dir_path}', 'linux_partition.img']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout and 'EXT2' not in result.stdout:
        print(f"\n=== Directory: {dir_path} ===")
        lines = result.stdout.strip().split('\n')
        for line in lines[:30]:  # Show first 30 entries
            if line and not line.startswith('debugfs'):
                print(line)

# Also check for specific files that might contain configuration
print("\n=== Checking for Solar Assistant service files ===")
service_files = [
    '/lib/systemd/system/solar-assistant.service',
    '/etc/systemd/system/solar-assistant.service',
    '/etc/systemd/system/solarassistant.service',
    '/lib/systemd/system/solarassistant.service',
]

for service_file in service_files:
    cmd = ['debugfs', '-R', f'cat {service_file}', 'linux_partition.img']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout and 'EXT2' not in result.stdout and 'File not found' not in result.stdout:
        print(f"\n=== Content of {service_file} ===")
        print(result.stdout[:1000])