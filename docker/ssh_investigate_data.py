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

def investigate_solar_assistant():
    """SSH into Solar Assistant and investigate data collection"""
    
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
        
        # Check running processes
        print("=== Running Processes ===")
        output = run_ssh_command(ssh, "ps aux | grep -E '(modbus|mqtt|influx|solar|eg4|inverter|elixir|beam|phoenix)' | grep -v grep")
        print(output)
        
        # Check network connections
        print("\n=== Network Connections ===")
        output = run_ssh_command(ssh, "netstat -tunl | grep -E '(502|1883|8086|4000)'", use_sudo=True)
        print(output)
        
        # Check systemd services
        print("\n=== Systemd Services ===")
        output = run_ssh_command(ssh, "systemctl list-units --type=service | grep -E '(solar|modbus|mqtt|elixir)'", use_sudo=True)
        print(output)
        
        # Check Solar Assistant application directory
        print("\n=== Solar Assistant Directory ===")
        output = run_ssh_command(ssh, "ls -la /opt/")
        print(output)
        
        # Find config files
        print("\n=== Configuration Files ===")
        output = run_ssh_command(ssh, "find /opt /etc /var -name '*solar*' -o -name '*config*' 2>/dev/null | grep -E '(solar|modbus|eg4)' | head -20", use_sudo=True)
        print(output)
        
        # Check for Elixir/Phoenix app
        print("\n=== Elixir/Phoenix Application ===")
        output = run_ssh_command(ssh, "find /opt -name '*.ex' -o -name '*.exs' 2>/dev/null | head -10", use_sudo=True)
        print(output)
        
        # Check for logs
        print("\n=== Recent Logs ===")
        output = run_ssh_command(ssh, "journalctl -n 50 --no-pager | grep -E '(solar|modbus|eg4|inverter)'", use_sudo=True)
        print(output)
        
        # Check for MQTT topics
        print("\n=== MQTT Configuration ===")
        output = run_ssh_command(ssh, "find /opt /etc -name '*mqtt*' 2>/dev/null | head -10", use_sudo=True)
        print(output)
        
        # Check crontab
        print("\n=== Crontab ===")
        output = run_ssh_command(ssh, "crontab -l 2>/dev/null", use_sudo=True)
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    investigate_solar_assistant()