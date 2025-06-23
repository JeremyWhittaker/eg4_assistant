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
            # Check Grafana API
            "echo '=== 1. Grafana API ==='",
            "curl -s http://localhost:3000/api/health",
            "curl -s http://localhost:3000/api/datasources",
            
            # Check Grafana dashboards
            "echo '\n=== 2. Grafana Dashboards ==='",
            "ls -la /etc/grafana/solar-assistant/dashboards/",
            "cat /etc/grafana/solar-assistant/dashboards/*.json 2>/dev/null | grep -E 'cpu|temperature|storage|memory' -i | head -20",
            
            # Check InfluxDB for system metrics more thoroughly
            "echo '\n=== 3. InfluxDB System Metrics Search ==='",
            "influx -database solar_assistant -execute 'SHOW MEASUREMENTS' 2>/dev/null | grep -E 'system|cpu|memory|disk|temperature'",
            "influx -database solar_assistant -execute 'SELECT * FROM device ORDER BY time DESC LIMIT 5' 2>/dev/null",
            "influx -database solar_assistant -execute 'SELECT * FROM stats ORDER BY time DESC LIMIT 5' 2>/dev/null",
            
            # Look for the actual Solar Assistant web interface
            "echo '\n=== 4. Solar Assistant Web Interface Discovery ==='",
            "netstat -tlnp 2>&1 | grep beam",
            "curl -s -I http://localhost:80/",
            "curl -s http://localhost:80/ | head -100",
            
            # Check for LiveView websocket
            "echo '\n=== 5. LiveView WebSocket ==='",
            "curl -s http://localhost:80/live/websocket -H 'Upgrade: websocket' -H 'Connection: upgrade' 2>&1 | head -20",
            
            # Look for system info collection in beam files using different approach
            "echo '\n=== 6. Beam Files Analysis ==='",
            "find /dev/shm -name '*.beam' 2>/dev/null | while read f; do strings \"$f\" 2>/dev/null | grep -q 'cpu_temp' && echo \"Found cpu_temp in: $f\"; done | head -10",
            "find /dev/shm -name '*.beam' 2>/dev/null | while read f; do strings \"$f\" 2>/dev/null | grep -q 'df -h' && echo \"Found df -h in: $f\"; done | head -10",
            
            # Check how Solar Assistant might be reading system info
            "echo '\n=== 7. System Info Reading Methods ==='",
            "# Check if it uses Erlang/Elixir system info functions",
            "strings /dev/shm/grafana-sync/*/lib/*/ebin/*.beam 2>/dev/null | grep -E ':os\\.|:system_info|:cpu_info|:memory' | head -20",
            
            # Check for custom collectors
            "echo '\n=== 8. Custom Collectors ==='",
            "find /usr/lib/influx-bridge -type f -exec file {} \\; | grep -E 'ELF|script'",
            "file /usr/lib/influx-bridge/influx-bridge",
            
            # Direct Solar Assistant access
            "echo '\n=== 9. Direct Solar Assistant Access ==='",
            "curl -s 'http://172.16.109.214/' | head -100",
            "curl -s 'http://172.16.109.214/api/stats' 2>&1 | head -50",
            
            # Final check for monitoring
            "echo '\n=== 10. Process Monitoring ==='",
            "ps aux | grep -E 'monitor|collect|stat' | grep -v grep | head -10",
            "# Calculate CPU temp in C",
            "echo \"Current CPU Temp: $(awk '{printf \"%.1f°C\", $1/1000}' /sys/class/thermal/thermal_zone0/temp)\""
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