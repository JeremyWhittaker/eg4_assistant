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
            # Check for the application in /dev/shm (from the process info)
            "echo '=== 1. Checking Solar Assistant in /dev/shm ==='",
            "ls -la /dev/shm/grafana-sync/",
            "ls -la /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/lib/ | head -20",
            
            # Look for web interface files
            "echo '\n=== 2. Looking for Solar Assistant web files ==='",
            "find /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 -name '*web*' -type d | head -10",
            "find /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 -name '*live*' -type d | head -10",
            
            # Check for system monitoring code
            "echo '\n=== 3. Searching for system monitoring code ==='",
            "grep -r 'thermal_zone' /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/lib 2>/dev/null | head -10",
            "grep -r 'cpu_temp' /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/lib 2>/dev/null | head -10",
            "grep -r 'df -h' /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/lib 2>/dev/null | head -10",
            
            # Check releases directory
            "echo '\n=== 4. Checking releases directory ==='",
            "ls -la /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/releases/",
            "cat /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/releases/RELEASES.txt 2>/dev/null",
            
            # Check API endpoints that might return system info
            "echo '\n=== 5. Checking API endpoints ==='",
            "curl -s http://localhost:4000/api/v1/status 2>/dev/null | head -100",
            "curl -s http://localhost:4000/api/v1/system 2>/dev/null | head -100",
            "curl -s http://localhost:4000/api/live/system 2>/dev/null | head -100",
            
            # Check for any monitoring scripts
            "echo '\n=== 6. Looking for monitoring scripts ==='",
            "find /usr/lib /usr/local -name '*solar*' -type f 2>/dev/null | head -20",
            "ls -la /usr/lib/influx-bridge/ 2>/dev/null",
            
            # Check process environment for clues
            "echo '\n=== 7. Checking process environment ==='",
            "cat /proc/583/environ 2>/dev/null | tr '\\0' '\\n' | grep -E 'PATH|HOME|CONFIG' | head -10",
            
            # Look for configuration files
            "echo '\n=== 8. Configuration files ==='",
            "find /etc -name '*solar*' -o -name '*influx*' 2>/dev/null | head -20",
            "cat /etc/influx-bridge.conf 2>/dev/null | head -50",
            
            # Check for web sockets or live view endpoints
            "echo '\n=== 9. Web socket/LiveView routes ==='",
            "netstat -tlnp 2>/dev/null | grep -E '4000|8080|3000'",
            "ss -tlnp 2>/dev/null | grep -E '4000|8080|3000'"
        ]
        
        # Execute commands
        results = execute_commands(ssh, commands)
        
        # Print results
        for result in results:
            if result['output']:
                print(result['output'].rstrip())
            if result['error'] and 'Permission denied' not in result['error'] and 'No such file' not in result['error']:
                print(f"Error: {result['error'].rstrip()}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    main()