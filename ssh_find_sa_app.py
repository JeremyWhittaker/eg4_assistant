#!/usr/bin/env python3
"""Find Solar Assistant application files"""

import paramiko

def find_app():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # From the process, we can see it's in /dev/shm/grafana-sync/...
        print("=== Finding Solar Assistant files ===")
        cmd = "find /dev/shm -name '*.beam' 2>/dev/null | grep -E 'inverter|protocol|modbus|client' | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print("BEAM files related to inverter/protocol:")
        print(output)
        
        # Get the base directory
        print("\n=== Getting application directory ===")
        cmd = "ls -la /dev/shm/grafana-sync/*/lib/ 2>/dev/null | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look for Solar Assistant app
        print("\n=== Finding Solar Assistant app ===")
        cmd = "find /dev/shm/grafana-sync -name 'solar_assistant*' -type d | head -5"
        output = ssh.exec_command(cmd)[1].read().decode()
        app_dirs = output.strip().split('\n')
        print(f"App directories: {app_dirs}")
        
        if app_dirs and app_dirs[0]:
            app_dir = app_dirs[0]
            print(f"\nExploring: {app_dir}")
            
            # List BEAM files
            cmd = f"ls -la {app_dir}/ebin/*.beam | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print("\nBEAM files:")
            print(output)
            
            # Look for protocol/inverter modules
            print("\n=== Looking for protocol modules ===")
            cmd = f"ls {app_dir}/ebin/ | grep -E 'protocol|inverter|modbus|driver|client'"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
            
            # Check strings in relevant modules
            print("\n=== Checking for EG4/protocol strings ===")
            cmd = f"strings {app_dir}/ebin/*.beam | grep -i 'eg4' | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print("EG4 references:")
            print(output)
            
            # Look for hex commands
            print("\n=== Looking for command bytes ===")
            cmd = f"strings {app_dir}/ebin/*.beam | grep -E 'a1.*1a|0xa1.*0x1a' | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
            
            # Check for Modbus references
            print("\n=== Checking for Modbus ===")
            cmd = f"strings {app_dir}/ebin/*.beam | grep -i modbus | head -10"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
        
        # Check configuration
        print("\n=== Looking for configuration ===")
        cmd = "find /dev/shm/grafana-sync -name '*.config' -o -name 'sys.config' | xargs grep -l inverter 2>/dev/null"
        output = ssh.exec_command(cmd)[1].read().decode()
        if output:
            config_file = output.strip().split('\n')[0]
            print(f"Config file: {config_file}")
            cmd = f"cat {config_file} | grep -A20 -B5 inverter"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output[:1000])
        
        # Try to find the actual protocol implementation
        print("\n=== Searching for protocol implementation ===")
        cmd = "find /dev/shm -name '*.beam' -exec grep -l 'query\\|command\\|register' {} \\; 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    find_app()