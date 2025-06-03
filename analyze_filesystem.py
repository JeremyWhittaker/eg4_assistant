#!/usr/bin/env python3
import os
import subprocess
import tempfile
import shutil

# Try using debugfs to explore the filesystem without mounting
def explore_with_debugfs():
    print("Using debugfs to explore the filesystem...")
    
    # List root directory
    cmd = ['debugfs', '-R', 'ls -la', 'linux_partition.img']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("Root directory listing:")
        print(result.stdout)
        
        # Look for important files
        important_files = [
            '/etc/passwd',
            '/etc/shadow',
            '/etc/ssh/sshd_config',
            '/home/pi/.ssh/authorized_keys',
            '/root/.ssh/authorized_keys',
            '/etc/hostname',
            '/etc/motd',
            '/etc/default/ssh',
            '/etc/init.d/ssh'
        ]
        
        for file in important_files:
            cmd = ['debugfs', '-R', f'cat {file}', 'linux_partition.img']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout and not result.stdout.startswith('debugfs'):
                print(f"\n=== Content of {file} ===")
                print(result.stdout[:500])  # Print first 500 chars
                
    except Exception as e:
        print(f"Error with debugfs: {e}")

# Try extracting files using e2tools
def try_e2tools():
    print("\nTrying e2tools...")
    try:
        # List directories
        result = subprocess.run(['e2ls', '-la', 'linux_partition.img:/'], capture_output=True, text=True)
        if result.returncode == 0:
            print("Root directory:")
            print(result.stdout)
    except:
        print("e2tools not available")

if __name__ == "__main__":
    if os.path.exists('linux_partition.img'):
        explore_with_debugfs()
        try_e2tools()
    else:
        print("linux_partition.img not found!")