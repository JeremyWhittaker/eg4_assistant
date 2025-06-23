#!/usr/bin/env python3
import pexpect
import sys

def ssh_solar_assistant():
    try:
        # SSH connection details
        host = "172.16.106.13"
        user = "solar-assistant"
        password = "solar123"
        
        print("Connecting to Solar Assistant server...")
        
        # Start SSH connection
        child = pexpect.spawn(f'ssh {user}@{host}')
        child.timeout = 30
        
        # Handle first connection
        i = child.expect(['password:', 'yes/no', pexpect.TIMEOUT])
        if i == 1:
            child.sendline('yes')
            child.expect('password:')
        
        child.sendline(password)
        child.expect(['$ ', '~'])
        
        # Commands to run
        commands = [
            ("Finding Solar Assistant application directories", 
             "sudo find /opt /var/www /home -name 'solar_assistant*' -type d 2>/dev/null | head -10"),
            
            ("Looking for Phoenix/Elixir configuration files",
             "sudo find /opt -name '*.exs' -o -name 'config.exs' 2>/dev/null | grep -i solar | head -20"),
            
            ("Checking PostgreSQL databases",
             "sudo -u postgres psql -l 2>/dev/null | grep -i solar || echo 'No PostgreSQL solar databases found'"),
            
            ("Finding SQLite/DB files",
             "sudo find / -name '*.db' -o -name '*.sqlite*' 2>/dev/null | grep -i solar | head -10"),
            
            ("Searching for inverter IP 172.16.107.129",
             "sudo grep -r '172.16.107.129' /opt 2>/dev/null | head -10"),
            
            ("Finding inverter config files",
             "sudo find /etc /opt /var -name '*inverter*.conf' -o -name '*inverter*.json' 2>/dev/null | head -10"),
            
            ("Checking systemd service configuration",
             "sudo systemctl cat solar-assistant 2>/dev/null | head -50 || echo 'solar-assistant service not found'"),
            
            ("Looking for configuration endpoints in Phoenix app",
             "sudo find /opt -name '*.ex' | xargs grep -l 'configuration' 2>/dev/null | head -10"),
            
            ("Checking /opt directory structure",
             "sudo ls -la /opt/ | grep -i solar"),
            
            ("Finding web assets",
             "sudo find /opt -name 'index.html' -o -name 'app.js' 2>/dev/null | grep -i solar | head -10")
        ]
        
        for description, command in commands:
            print(f"\n=== {description} ===")
            child.sendline(command)
            
            # Check if sudo password is needed
            i = child.expect(['password for', '$ ', '~', pexpect.TIMEOUT], timeout=10)
            if i == 0:
                child.sendline(password)
                child.expect(['$ ', '~'])
            
            # Print output
            output = child.before.decode('utf-8')
            if output.strip():
                print(output.strip())
        
        child.sendline('exit')
        child.close()
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    ssh_solar_assistant()