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
            # Check Solar Assistant service
            "echo '=== 1. Solar Assistant Service ==='",
            "systemctl status solar-assistant | head -30",
            "cat /etc/systemd/system/solar-assistant.service",
            
            # Check what's running on port 3000
            "echo '\n=== 2. Process on port 3000 ==='",
            "echo 'solar123' | sudo -S lsof -i :3000 2>/dev/null | head -10",
            "echo 'solar123' | sudo -S netstat -tlnp | grep 3000 2>/dev/null",
            
            # Check nginx configuration
            "echo '\n=== 3. Nginx Configuration ==='",
            "ls -la /etc/nginx/sites-enabled/",
            "cat /etc/nginx/sites-enabled/default 2>/dev/null | grep -A5 -B5 'proxy_pass' | head -30",
            
            # Try to access the web interface directly
            "echo '\n=== 4. Web Interface Test ==='",
            "curl -s http://localhost/ | head -50",
            "curl -s http://localhost/api/v1/status 2>/dev/null | head -50",
            
            # Check for Solar Assistant directories
            "echo '\n=== 5. Solar Assistant Directories ==='",
            "find /opt -maxdepth 3 -type d -name '*solar*' 2>/dev/null",
            "find /usr/share -maxdepth 3 -type d -name '*solar*' 2>/dev/null",
            "find /var/www -maxdepth 3 -type d -name '*solar*' 2>/dev/null",
            
            # Look for the actual application
            "echo '\n=== 6. Application Location ==='",
            "echo 'solar123' | sudo -S find / -maxdepth 4 -name 'solar_assistant*' -type d 2>/dev/null | grep -v proc | head -20",
            "ls -la /opt/solarassistant/ 2>/dev/null",
            "ls -la /opt/solar-assistant/ 2>/dev/null",
            
            # Check running processes more carefully
            "echo '\n=== 7. Elixir/Phoenix Processes ==='",
            "ps aux | grep -E 'beam|elixir|phoenix' | grep -v grep",
            
            # Try different API endpoints
            "echo '\n=== 8. API Endpoints ==='",
            "curl -s http://localhost/api/stats 2>/dev/null | head -20",
            "curl -s http://localhost/api/system 2>/dev/null | head -20",
            "curl -s http://localhost/api/inverters 2>/dev/null | head -20",
            
            # Check for any web assets
            "echo '\n=== 9. Web Assets ==='",
            "find /usr/share/nginx -name '*.html' 2>/dev/null | grep -i solar | head -10",
            "find /var/www -name '*.html' 2>/dev/null | grep -i solar | head -10"
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