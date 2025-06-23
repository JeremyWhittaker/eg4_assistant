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
            # Check the sign in page
            "echo '=== 1. Sign In Page ==='",
            "curl -s http://localhost/sign_in | grep -E 'form|input|csrf|token' | head -20",
            
            # Look for CSRF token
            "echo '\n=== 2. Extract CSRF Token ==='",
            "curl -s -c /tmp/cookies.txt http://localhost/sign_in | grep -o 'csrf_token[^>]*value=\"[^\"]*\"' | head -1",
            
            # Try to authenticate
            "echo '\n=== 3. Authentication Attempt ==='",
            "CSRF=$(curl -s -c /tmp/cookies.txt http://localhost/sign_in | grep -o 'csrf_token[^>]*value=\"[^\"]*\"' | grep -o 'value=\"[^\"]*\"' | cut -d'\"' -f2) && echo \"CSRF Token: $CSRF\"",
            
            # Access authenticated pages
            "echo '\n=== 4. Dashboard Access ==='",
            "curl -s -b /tmp/cookies.txt http://localhost/dashboard | head -50",
            "curl -s -b /tmp/cookies.txt http://localhost/ | grep -E 'cpu|temp|storage|memory' -i | head -20",
            
            # Check Phoenix channels
            "echo '\n=== 5. Phoenix Channel Info ==='",
            "curl -s -b /tmp/cookies.txt http://localhost/socket/info | head -50",
            "curl -s -b /tmp/cookies.txt http://localhost/live/socket | head -50",
            
            # Look for system info in the extracted app more thoroughly
            "echo '\n=== 6. Deep Search for System Info Code ==='",
            "find /dev/shm -type f -name '*.beam' 2>/dev/null -exec sh -c 'strings \"$1\" 2>/dev/null | grep -E \"cpu_temp|system_info|thermal|vcgencmd\" && echo \"Found in: $1\"' _ {} \\; | head -20",
            
            # Check for OS commands execution
            "echo '\n=== 7. OS Command Execution Patterns ==='",
            "strings /usr/lib/influx-bridge/influx-bridge 2>/dev/null | grep -E 'System\\.cmd|os:cmd|exec' | head -20",
            "strings /dev/shm/grafana-sync/*/lib/*/ebin/*.beam 2>/dev/null | grep -E 'System\\.cmd|os:cmd|exec' | head -20",
            
            # Look at the influx-bridge process more closely
            "echo '\n=== 8. Influx Bridge Process Info ==='",
            "cat /proc/583/maps | grep -E 'beam|solar' | head -10",
            "ls -la /proc/583/fd/ | head -20",
            
            # Check for any helper scripts
            "echo '\n=== 9. Helper Scripts ==='",
            "find /usr/lib/influx-bridge -type f -name '*.sh' -o -name '*.py' 2>/dev/null",
            "cat /usr/lib/influx-bridge/signal.sh",
            
            # Direct check for system metrics collection
            "echo '\n=== 10. System Metrics Collection Test ==='",
            "# Simulate what Solar Assistant might do",
            "echo \"CPU Temp: $(cat /sys/class/thermal/thermal_zone0/temp)\"",
            "echo \"CPU Temp (C): $(echo \"scale=2; $(cat /sys/class/thermal/thermal_zone0/temp) / 1000\" | bc)\"",
            "echo \"Storage: $(df -h / | tail -1 | awk '{print $3\" used of \"$2\" (\"$5\")\"}')\""
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