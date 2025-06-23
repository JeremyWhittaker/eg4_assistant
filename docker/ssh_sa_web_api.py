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
    hostname = '172.16.109.214'
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
            # Access Solar Assistant web interface
            "echo '=== 1. Solar Assistant Web Interface ==='",
            "curl -s http://localhost/ | head -100",
            
            # Test various API endpoints
            "echo '\n=== 2. API Endpoints ==='",
            "curl -s http://localhost/api/v1/status | head -50",
            "curl -s http://localhost/api/v1/system | head -50",
            "curl -s http://localhost/api/v1/device | head -50",
            "curl -s http://localhost/api/v1/stats | head -50",
            
            # Look for Phoenix LiveView endpoints
            "echo '\n=== 3. LiveView Endpoints ==='",
            "curl -s http://localhost/live | head -50",
            "curl -s http://localhost/dashboard | head -50",
            
            # Check for WebSocket endpoints
            "echo '\n=== 4. WebSocket Endpoints ==='",
            "curl -s http://localhost/socket | head -20",
            "curl -s http://localhost/live/websocket | head -20",
            
            # Look for system information in the UI
            "echo '\n=== 5. System Info in UI ==='",
            "curl -s http://localhost/ | grep -E 'cpu|temperature|storage|disk|memory' -i | head -20",
            
            # Check JavaScript files for API calls
            "echo '\n=== 6. JavaScript API Calls ==='",
            "curl -s http://localhost/ | grep -o 'src=\"[^\"]*\\.js\"' | head -10",
            
            # Try to find the actual system info collection
            "echo '\n=== 7. System Info Collection Methods ==='",
            "find /dev/shm -name '*.so' 2>/dev/null | xargs strings 2>/dev/null | grep -E 'vcgencmd|thermal_zone' | head -10",
            "ps aux | grep -E 'vcgencmd|sensors|hddtemp' | grep -v grep",
            
            # Check for scheduled tasks
            "echo '\n=== 8. Cron Jobs ==='",
            "crontab -l 2>/dev/null",
            "echo 'solar123' | sudo -S crontab -l 2>/dev/null",
            "ls -la /etc/cron.d/",
            
            # Direct system commands that Solar Assistant might use
            "echo '\n=== 9. System Commands Output ==='",
            "cat /sys/class/thermal/thermal_zone0/temp",
            "df -h / | tail -1",
            "free -m | grep Mem:",
            "uptime",
            
            # Check for any monitoring scripts
            "echo '\n=== 10. Monitoring Scripts ==='",
            "find /usr/local/bin /usr/bin -name '*monitor*' -o -name '*collect*' 2>/dev/null | grep -v -E 'apt|dpkg' | head -10",
            "ps aux | grep -E 'monitor|collect' | grep -v grep | head -10"
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