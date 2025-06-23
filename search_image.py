#!/usr/bin/env python3
"""
Search for Solar Assistant files in the image
"""

import subprocess
import os

def search_files():
    """Search for Solar Assistant related files"""
    image_path = "linux_partition_extracted.img"
    
    # Search patterns
    searches = [
        "solar",
        "assistant", 
        "inverter",
        "monitoring",
        "grafana",
        "influxdb"
    ]
    
    print("Searching for Solar Assistant files...")
    print("=" * 50)
    
    # First, let's find all systemd services
    print("\nSystemd services:")
    cmd = 'debugfs -R "ls -l /etc/systemd/system" linux_partition_extracted.img 2>&1 | grep -i solar'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # Check lib/systemd
    print("\nLib systemd services:")
    cmd = 'debugfs -R "ls -l /lib/systemd/system" linux_partition_extracted.img 2>&1 | grep -E "(solar|grafana|influx)"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # Check for web applications in common locations
    web_dirs = [
        "/var/www",
        "/usr/share/nginx",
        "/usr/local/share",
        "/opt",
        "/srv"
    ]
    
    for web_dir in web_dirs:
        print(f"\nChecking {web_dir}:")
        cmd = f'debugfs -R "ls -la {web_dir}" linux_partition_extracted.img 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "File not found" not in result.stdout:
            print(result.stdout[:500])
    
    # Check specific user directories
    print("\nChecking solar-assistant home:")
    cmd = 'debugfs -R "ls -la /home/solar-assistant" linux_partition_extracted.img 2>&1'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # Look for Python files
    print("\nSearching for Python applications:")
    for directory in ["/opt", "/usr/local", "/home/solar-assistant"]:
        cmd = f'debugfs -R "ls -laR {directory}" linux_partition_extracted.img 2>&1 | grep -E "\\.py$"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(f"\nPython files in {directory}:")
            print(result.stdout[:500])

def extract_service_files():
    """Extract systemd service files"""
    print("\n\nExtracting service files...")
    print("=" * 50)
    
    services = [
        "/lib/systemd/system/grafana-server.service",
        "/lib/systemd/system/influxdb.service",
        "/etc/systemd/system/multi-user.target.wants/grafana-server.service"
    ]
    
    for service in services:
        output_path = f"extracted_files{service}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        cmd = f'debugfs -R "dump {service} {output_path}" linux_partition_extracted.img 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"\n✓ Extracted: {service}")
            with open(output_path, 'r', errors='ignore') as f:
                print(f.read()[:300])

if __name__ == "__main__":
    search_files()
    extract_service_files()