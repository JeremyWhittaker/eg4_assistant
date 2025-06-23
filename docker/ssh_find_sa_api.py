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
            # Check all listening ports
            "echo '=== 1. All Listening Ports ==='",
            "echo 'solar123' | sudo -S netstat -tlnp | grep -E 'beam|grafana|influx'",
            "echo 'solar123' | sudo -S ss -tlnp | grep -E 'beam|grafana|influx'",
            
            # Check for Solar Assistant API on different ports
            "echo '\n=== 2. Testing Different Ports ==='",
            "curl -s http://localhost:4000/ 2>&1 | head -20",
            "curl -s http://localhost:5000/ 2>&1 | head -20",
            "curl -s http://localhost:8080/ 2>&1 | head -20",
            "curl -s http://localhost:8086/ 2>&1 | head -20",
            
            # Check InfluxDB for system metrics
            "echo '\n=== 3. InfluxDB System Metrics ==='",
            "influx -execute 'SHOW DATABASES' 2>/dev/null | head -10",
            "influx -database solar_assistant -execute 'SHOW MEASUREMENTS' 2>/dev/null | head -20",
            "influx -database solar_assistant -execute 'SHOW FIELD KEYS FROM system' 2>/dev/null | head -20",
            
            # Check how influx-bridge collects system info
            "echo '\n=== 4. Influx Bridge Binary Analysis ==='",
            "strings /usr/lib/influx-bridge/influx-bridge 2>/dev/null | grep -E 'cpu_temp|thermal_zone|vcgencmd|df -h' | head -20",
            "strings /usr/lib/influx-bridge/influx-bridge 2>/dev/null | grep -E 'system_info|storage_|memory_' | head -20",
            
            # Check for configuration files
            "echo '\n=== 5. Configuration Files ==='",
            "cat /usr/lib/influx-bridge/influx-bridge.env",
            "ls -la /etc/grafana/solar-assistant/",
            
            # Look for system monitoring in the extracted app
            "echo '\n=== 6. System Monitoring in App ==='",
            "find /dev/shm -name '*.beam' 2>/dev/null | xargs strings 2>/dev/null | grep -E 'cpu_temperature|system_status|disk_usage' | head -20",
            
            # Check Grafana datasources
            "echo '\n=== 7. Grafana Configuration ==='",
            "cat /etc/grafana/provisioning/datasources/solar-assistant.yaml 2>/dev/null",
            "cat /etc/grafana/grafana.ini 2>/dev/null | grep -E 'root_url|domain|protocol' | head -10",
            
            # Direct InfluxDB query for system data
            "echo '\n=== 8. Direct InfluxDB Queries ==='",
            "influx -database solar_assistant -execute 'SELECT * FROM system ORDER BY time DESC LIMIT 5' 2>/dev/null",
            "influx -database solar_assistant -execute 'SELECT * FROM cpu ORDER BY time DESC LIMIT 5' 2>/dev/null",
            
            # Check process command line for hints
            "echo '\n=== 9. Process Command Line ==='",
            "cat /proc/583/cmdline 2>/dev/null | tr '\\0' ' ' | fold -w 80",
            
            # Look for web socket connections
            "echo '\n=== 10. WebSocket Connections ==='",
            "echo 'solar123' | sudo -S lsof -i -P | grep -E 'beam.*ESTABLISHED' | head -10"
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