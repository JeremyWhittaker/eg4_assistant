#!/usr/bin/env python3
import paramiko
import time
import json

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
            # Check the actual Solar Assistant web interface
            "echo '=== 1. Web Interface Access ==='",
            "curl -s http://localhost:3000/sign_in | head -50",
            "curl -s http://localhost:3000/api/stats 2>/dev/null | head -50",
            "curl -s -X POST http://localhost:3000/api/sign_in -d '{\"username\":\"admin\",\"password\":\"admin\"}' -H 'Content-Type: application/json' 2>/dev/null | head -50",
            
            # Look in the Solar Assistant application directory
            "echo '\n=== 2. Solar Assistant Application Structure ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && find lib -name '*system*' -o -name '*status*' -o -name '*monitor*' | head -20",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && find lib -name '*.beam' | grep -E 'system|status|monitor|cpu|storage' | head -20",
            
            # Check for system info collection in beam files
            "echo '\n=== 3. System Info Collection Patterns ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && strings lib/solar_assistant-1.9.15/ebin/Elixir.SolarAssistant.SystemInfo.beam 2>/dev/null | grep -E 'cpu|temp|storage|thermal' | head -20",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && strings lib/solar_assistant-1.9.15/ebin/*.beam 2>/dev/null | grep -E 'thermal_zone|vcgencmd|df -h' | head -20",
            
            # Look for LiveView components
            "echo '\n=== 4. LiveView Components ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && find lib -name '*.beam' | grep -i live | head -20",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && ls -la lib/solar_assistant_web-1.9.15/ebin/ | grep -i live | head -20",
            
            # Check for API endpoints
            "echo '\n=== 5. API Endpoints Discovery ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && strings lib/solar_assistant_web-1.9.15/ebin/*.beam 2>/dev/null | grep -E 'api/|/stats|/system|/status' | head -30",
            
            # Look for specific system monitoring modules
            "echo '\n=== 6. System Monitoring Modules ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && ls -la lib/solar_assistant-1.9.15/ebin/ | grep -E 'System|Monitor|Status|Info'",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && ls -la lib/solar_assistant_web-1.9.15/ebin/ | grep -E 'System|Monitor|Status|Info'",
            
            # Check runtime configuration
            "echo '\n=== 7. Runtime Configuration ==='",
            "cat /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520/tmp/solar_assistant-1.9.15-1694653521.runtime 2>/dev/null | head -50",
            
            # Try to find how it reads CPU temp
            "echo '\n=== 8. CPU Temperature Reading ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && strings lib/*/ebin/*.beam 2>/dev/null | grep -B2 -A2 'thermal_zone0' | head -20",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && strings lib/*/ebin/*.beam 2>/dev/null | grep -B2 -A2 'measure_temp' | head -20",
            
            # Check for Phoenix channels
            "echo '\n=== 9. Phoenix Channels ==='",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && find lib -name '*channel*.beam' | head -10",
            "cd /dev/shm/grafana-sync/a428f0a4cb59b6365588b45a5373a9a93f666f62148e838de3728aba2d465520 && strings lib/solar_assistant_web-1.9.15/ebin/*Channel*.beam 2>/dev/null | grep -E 'system|status|monitor' | head -20"
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