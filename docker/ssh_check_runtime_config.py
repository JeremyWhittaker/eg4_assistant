#!/usr/bin/env python3
import paramiko

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

def check_runtime_config():
    """Check the runtime configuration"""
    
    # SSH connection details
    host = "172.16.109.214"
    username = "solar-assistant"
    password = "solar123"
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {host}...")
        ssh.connect(host, username=username, password=password)
        print("Connected successfully!\n")
        
        # Check the runtime config file
        print("=== Runtime Configuration File ===")
        output = run_ssh_command(ssh, "cat /dev/shm/grafana-sync/*/tmp/*.runtime.config | head -100", use_sudo=True)
        print(output)
        
        # Check sys.config
        print("\n=== System Configuration ===")
        output = run_ssh_command(ssh, "cat /dev/shm/grafana-sync/*/releases/*/sys.config | head -100", use_sudo=True)
        print(output)
        
        # Check MQTT configuration
        print("\n=== MQTT Configuration ===")
        output = run_ssh_command(ssh, "cat /etc/mosquitto/mosquitto.conf", use_sudo=True)
        print(output)
        
        # Check if there's a database with configuration
        print("\n=== Checking Mnesia Database ===")
        output = run_ssh_command(ssh, "ls -la /usr/lib/influx-bridge/Mnesia.nonode@nohost/", use_sudo=True)
        print(output)
        
        # Look for any stored inverter configuration
        print("\n=== Looking for Inverter Config ===")
        output = run_ssh_command(ssh, "strings /usr/lib/influx-bridge/Mnesia.nonode@nohost/* 2>/dev/null | grep -E '(172.16.107|inverter|luxpower|eg4|modbus)' | head -20", use_sudo=True)
        print(output)
        
        # Check the user.log for configuration details
        print("\n=== Recent User Log Entries ===")
        output = run_ssh_command(ssh, "tail -50 /usr/lib/influx-bridge/user.log | grep -E '(config|inverter|172.16.107|luxpower)'", use_sudo=True)
        print(output)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    check_runtime_config()