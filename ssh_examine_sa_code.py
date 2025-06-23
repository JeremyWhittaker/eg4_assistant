#!/usr/bin/env python3
"""SSH to Solar Assistant and examine the actual code"""

import paramiko
import os

def examine_code():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect("172.16.106.13", username="solar-assistant", password="solar123")
        print("Connected to Solar Assistant\n")
        
        # First, find the Solar Assistant process and its files
        print("=== Finding Solar Assistant application ===")
        cmd = "ps aux | grep beam.smp | grep -v grep"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Get the runtime config path
        print("\n=== Getting runtime config path ===")
        cmd = "cat /proc/583/environ | tr '\\0' '\\n' | grep RELEASE_SYS_CONFIG"
        output = ssh.exec_command(cmd)[1].read().decode()
        config_path = output.strip().split('=')[1] if '=' in output else ''
        print(f"Config path: {config_path}")
        
        if config_path:
            # Extract the directory
            config_dir = os.path.dirname(config_path)
            print(f"\nConfig directory: {config_dir}")
            
            # List files in that directory
            print("\n=== Files in config directory ===")
            cmd = f"ls -la {config_dir}/"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
            
            # Look for the actual application files
            print("\n=== Finding application files ===")
            cmd = f"find {config_dir} -name '*.beam' -o -name '*.app' -o -name '*.config' | head -20"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
            
            # Check for protocol/inverter related modules
            print("\n=== Looking for inverter modules ===")
            cmd = f"find {config_dir} -name '*.beam' | xargs -I{{}} sh -c 'echo \"File: {{}}\"; strings {{}} | grep -i \"eg4\\|inverter\\|modbus\\|protocol\" | head -5' 2>/dev/null | head -50"
            output = ssh.exec_command(cmd)[1].read().decode()
            print(output)
        
        # Look in the Erlang release directory
        print("\n=== Checking Erlang release structure ===")
        cmd = "find /usr/lib/solar-assistant /opt/solar-assistant -name '*.beam' 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check for source files
        print("\n=== Looking for source files ===")
        cmd = "find / -name '*.ex' -o -name '*.exs' -o -name '*.erl' 2>/dev/null | grep -E 'inverter|protocol|eg4' | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Try to decompile a BEAM file
        print("\n=== Checking BEAM file contents ===")
        cmd = f"cd {config_dir} && find . -name '*inverter*.beam' -o -name '*protocol*.beam' | head -5"
        beam_files = ssh.exec_command(cmd)[1].read().decode().strip().split('\n')
        
        if beam_files and beam_files[0]:
            print(f"Found BEAM files: {beam_files}")
            # Try to get module info
            for beam in beam_files[:3]:
                if beam:
                    print(f"\n--- Checking {beam} ---")
                    cmd = f"cd {config_dir} && strings {beam} | grep -E 'query|command|register|0xa1|0x1a' | head -10"
                    output = ssh.exec_command(cmd)[1].read().decode()
                    print(output)
        
        # Look for configuration about protocols
        print("\n=== Checking for protocol configuration ===")
        cmd = f"grep -r 'protocol\\|register\\|command' {config_dir} 2>/dev/null | grep -v '.beam' | head -20"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Check sys.config
        print("\n=== Checking sys.config ===")
        cmd = f"cat {config_dir}/sys.config 2>/dev/null | grep -A10 -B10 'inverter\\|protocol'"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
        # Look for hex patterns in config
        print("\n=== Looking for command patterns ===")
        cmd = f"grep -r '0xa1\\|0x1a\\|\\\\xa1\\|\\\\x1a' {config_dir} 2>/dev/null | head -10"
        output = ssh.exec_command(cmd)[1].read().decode()
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    examine_code()