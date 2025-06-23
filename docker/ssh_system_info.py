#!/usr/bin/env python3
import paramiko
import time

def execute_commands(ssh, commands):
    """Execute a list of commands and return their outputs"""
    results = []
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        results.append({
            'command': cmd,
            'output': output,
            'error': error
        })
        time.sleep(0.5)  # Small delay between commands
    return results

def main():
    # SSH connection parameters
    hostname = '172.16.106.13'
    username = 'solar-assistant'
    password = 'solar123'
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to the server
        print(f"Connecting to {username}@{hostname}...")
        ssh.connect(hostname, username=username, password=password)
        print("Connected successfully!\n")
        
        # Define commands to execute
        commands = [
            # CPU Temperature
            "echo '=== 1. CPU Temperature Information ==='",
            "cat /sys/class/thermal/thermal_zone0/temp",
            "vcgencmd measure_temp 2>/dev/null || echo 'vcgencmd not available'",
            
            # Storage Information
            "echo '\n=== 2. Storage Information ==='",
            "df -h /",
            "df -h | grep -E '/$|/var|/opt'",
            
            # System Services
            "echo '\n=== 3. System Services ==='",
            "systemctl status influx-bridge.service | head -20",
            "ps aux | grep -E 'beam|elixir|solar' | grep -v grep | head -10",
            
            # System Info Scripts/Config
            "echo '\n=== 4. System Info Scripts/Config ==='",
            "find /opt /var -name '*system*' -type f 2>/dev/null | grep -v log | head -20",
            "find /opt /var -name '*status*' -type f 2>/dev/null | grep -v log | head -20",
            
            # Phoenix LiveView Endpoints
            "echo '\n=== 5. Phoenix LiveView Endpoints ==='",
            "grep -r 'cpu_temp\\|storage\\|system' /opt 2>/dev/null | head -20",
            "find /opt -name '*.ex' -o -name '*.exs' 2>/dev/null | xargs grep -l 'thermal\\|temperature' 2>/dev/null | head -10",
            
            # Device Information
            "echo '\n=== 6. Device Information ==='",
            "cat /proc/device-tree/model 2>/dev/null && echo",
            "uname -a",
            "lsb_release -a 2>/dev/null || cat /etc/os-release",
            
            # Solar Assistant Specific Files
            "echo '\n=== 7. Solar Assistant Specific Files ==='",
            "find /opt/solar_assistant -name '*.ex' 2>/dev/null | xargs grep -l 'system_info\\|cpu_temp\\|storage' 2>/dev/null | head -10",
            
            # Additional checks for system monitoring
            "echo '\n=== 8. Additional System Monitoring Checks ==='",
            "ls -la /opt/solar_assistant/lib/solar_assistant_web/live/ 2>/dev/null | grep -i system",
            "find /opt/solar_assistant -name '*system*' -o -name '*monitor*' 2>/dev/null | grep -E '\\.ex$|\\.exs$' | head -10"
        ]
        
        # Execute commands
        results = execute_commands(ssh, commands)
        
        # Print results
        for result in results:
            if result['output']:
                print(result['output'].rstrip())
            if result['error'] and 'Permission denied' not in result['error']:
                print(f"Error: {result['error'].rstrip()}")
        
        # Try with sudo for some commands
        print("\n=== Attempting with sudo (may require password) ===")
        sudo_commands = [
            "echo 'solar123' | sudo -S find /opt /var -name '*system*' -type f 2>/dev/null | grep -v log | head -20",
            "echo 'solar123' | sudo -S grep -r 'cpu_temp\\|storage\\|system' /opt 2>/dev/null | head -20",
            "echo 'solar123' | sudo -S find /opt/solar_assistant -name '*.ex' | xargs grep -l 'system_info\\|cpu_temp\\|storage' 2>/dev/null | head -10"
        ]
        
        sudo_results = execute_commands(ssh, sudo_commands)
        for result in sudo_results:
            if result['output']:
                print(result['output'].rstrip())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    main()