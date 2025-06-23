#!/usr/bin/env python3
import paramiko
import time

def run_ssh_command(ssh, command, use_sudo=False):
    """Run command via SSH and return output"""
    if use_sudo:
        command = f"echo 'solar123' | sudo -S {command}"
    
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    if error and not error.startswith('[sudo]'):
        print(f"Error: {error}")
    
    return output

def investigate_protocol():
    """Deep dive into Solar Assistant protocol implementation"""
    
    # SSH connection details
    host = "172.16.106.13"
    username = "solar-assistant"
    password = "solar123"
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=username, password=password)
        print("Connected successfully!\n")
        
        # Find the actual executable and configuration
        print("=== Finding Solar Assistant Executable ===")
        output = run_ssh_command(ssh, "ls -la /usr/lib/influx-bridge/", use_sudo=True)
        print(output)
        
        # Check environment file
        print("\n=== Environment Configuration ===")
        output = run_ssh_command(ssh, "cat /usr/lib/influx-bridge/influx-bridge.env", use_sudo=True)
        print(output)
        
        # Look for the actual application directory
        print("\n=== Application Files ===")
        output = run_ssh_command(ssh, "find /dev/shm/grafana-sync -name '*.ex' -o -name '*.exs' -o -name '*.erl' -o -name '*.beam' 2>/dev/null | head -20", use_sudo=True)
        print(output)
        
        # Check for configuration in the runtime directory
        print("\n=== Runtime Configuration ===")
        output = run_ssh_command(ssh, "find /dev/shm/grafana-sync -name '*.config' -o -name '*.conf' -o -name '*.toml' -o -name '*.yaml' 2>/dev/null | head -20", use_sudo=True)
        print(output)
        
        # Look for any database or state files
        print("\n=== State/Database Files ===")
        output = run_ssh_command(ssh, "find /var/lib -name '*solar*' -o -name '*influx*' -o -name '*eg4*' 2>/dev/null | grep -v '/proc' | head -20", use_sudo=True)
        print(output)
        
        # Check active network connections from the influx-bridge process
        print("\n=== Active Network Connections ===")
        output = run_ssh_command(ssh, "netstat -tnp 2>/dev/null | grep 583 || lsof -i -P -n | grep 583", use_sudo=True)
        print(output)
        
        # Look for any scripts that might show configuration
        print("\n=== Configuration Scripts ===")
        output = run_ssh_command(ssh, "find /usr/lib/influx-bridge -type f -name '*.sh' -o -name '*.py' 2>/dev/null", use_sudo=True)
        print(output)
        
        # Check if there's a configuration database
        print("\n=== Looking for SQLite databases ===")
        output = run_ssh_command(ssh, "find / -name '*.db' -o -name '*.sqlite' 2>/dev/null | grep -E '(solar|influx|config)' | head -10", use_sudo=True)
        print(output)
        
        # Check the process command line for clues
        print("\n=== Process Command Line ===")
        output = run_ssh_command(ssh, "cat /proc/583/cmdline | tr '\\0' ' '", use_sudo=True)
        print(output)
        
        # Look for any MQTT configuration
        print("\n=== MQTT Configuration ===")
        output = run_ssh_command(ssh, "find /etc /var -name '*mosquitto*' 2>/dev/null", use_sudo=True)
        print(output)
        
        # Check for any web API configuration files
        print("\n=== Web Configuration ===")
        output = run_ssh_command(ssh, "find /etc/nginx /etc/apache2 /etc/httpd -name '*.conf' 2>/dev/null | head -10", use_sudo=True)
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    investigate_protocol()