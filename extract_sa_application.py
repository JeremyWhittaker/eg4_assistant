#!/usr/bin/env python3
"""
Extract and analyze Solar Assistant application from the image
"""

import subprocess
import os
import json
import tempfile

def extract_filesystem():
    """Extract key directories from the filesystem image"""
    
    print("Extracting Solar Assistant application files...")
    
    # First, let's use debugfs to explore the filesystem structure
    directories_to_check = [
        '/opt',
        '/home/solar-assistant',
        '/var/lib',
        '/etc/systemd/system',
        '/usr/local/bin',
        '/var/www',
        '/etc/grafana',
        '/etc/mosquitto',
        '/etc/influxdb'
    ]
    
    results = {}
    
    for directory in directories_to_check:
        print(f"\nChecking {directory}...")
        cmd = ['debugfs', '-R', f'ls -la {directory}', 'linux_partition.img']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout and 'EXT2' not in result.stdout and result.stdout.strip():
                print(f"Found content in {directory}")
                results[directory] = result.stdout
                
                # Try to extract specific files
                if 'solar' in result.stdout.lower() or 'assistant' in result.stdout.lower():
                    print(f"  -> Found Solar Assistant related files!")
                    
                    # List files recursively
                    cmd_recursive = ['debugfs', '-R', f'ls -laR {directory}', 'linux_partition.img']
                    recursive_result = subprocess.run(cmd_recursive, capture_output=True, text=True)
                    if recursive_result.stdout:
                        with open(f'sa_listing_{directory.replace("/", "_")}.txt', 'w') as f:
                            f.write(recursive_result.stdout)
        except Exception as e:
            print(f"Error checking {directory}: {e}")
    
    # Look for specific application files
    print("\n\nSearching for application executables...")
    app_patterns = [
        'find / -name "*.beam" | head -20',  # Elixir BEAM files
        'find / -name "*.ex" | head -20',     # Elixir source
        'find / -name "*.py" | grep -i solar | head -20',  # Python files
        'find / -name "*solar*" -type f | head -20',
        'find / -name "*assistant*" -type f | head -20',
        'find / -name "*.service" | grep -i solar',
        'find /opt -type f | head -50',
        'find /home -name "*.json" | head -20'
    ]
    
    for pattern in app_patterns:
        print(f"\nRunning: {pattern}")
        cmd = ['debugfs', '-R', pattern, 'linux_partition.img']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout and result.stdout.strip():
                print(result.stdout[:500])
        except:
            pass
    
    return results

def extract_config_files():
    """Extract configuration files"""
    
    print("\n\nExtracting configuration files...")
    
    config_files = [
        '/etc/solar-assistant/config.json',
        '/home/solar-assistant/.config/solar-assistant.conf',
        '/opt/solar-assistant/config/config.exs',
        '/etc/mosquitto/mosquitto.conf',
        '/etc/influxdb/influxdb.conf',
        '/etc/grafana/grafana.ini',
        '/home/solar-assistant/config.json',
        '/var/lib/solar-assistant/config.db'
    ]
    
    for config_file in config_files:
        print(f"\nTrying to extract: {config_file}")
        cmd = ['debugfs', '-R', f'cat {config_file}', 'linux_partition.img']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout and 'EXT2' not in result.stdout and 'File not found' not in result.stdout:
                print(f"Found {config_file}!")
                filename = os.path.basename(config_file)
                with open(f'extracted_{filename}', 'w') as f:
                    f.write(result.stdout)
                print(f"Saved to extracted_{filename}")
        except:
            pass

def analyze_strings():
    """Analyze strings in the image for API endpoints and features"""
    
    print("\n\nAnalyzing strings for API endpoints and features...")
    
    # Look for specific patterns
    patterns = [
        'api/v[0-9]',
        'mqtt://',
        'modbus',
        'inverter',
        'battery',
        'solar',
        'export',
        'import',
        'grid',
        'load',
        'consumption',
        'production',
        'websocket',
        'phoenix',
        'live_view'
    ]
    
    print("Searching for API endpoints and features...")
    result = subprocess.run(['strings', 'linux_partition.img'], capture_output=True, text=True)
    
    findings = {pattern: [] for pattern in patterns}
    
    lines = result.stdout.split('\n')
    for i, line in enumerate(lines):
        for pattern in patterns:
            if pattern.lower() in line.lower() and len(line) < 200:
                # Get context
                context = []
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if lines[j].strip():
                        context.append(lines[j])
                findings[pattern].append({
                    'line': line,
                    'context': context
                })
                if len(findings[pattern]) > 10:
                    break
    
    # Save findings
    with open('sa_api_findings.json', 'w') as f:
        # Convert to serializable format
        serializable_findings = {}
        for pattern, items in findings.items():
            if items:
                serializable_findings[pattern] = items[:5]  # Limit to 5 per pattern
        json.dump(serializable_findings, f, indent=2)
    
    print(f"API findings saved to sa_api_findings.json")

if __name__ == "__main__":
    if os.path.exists('linux_partition.img'):
        extract_filesystem()
        extract_config_files()
        analyze_strings()
    else:
        print("Error: linux_partition.img not found!")
        print("Please run extract_image.py first")