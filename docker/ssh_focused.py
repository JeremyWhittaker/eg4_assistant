#!/usr/bin/env python3
import pexpect
import time

def run_focused_commands():
    try:
        child = pexpect.spawn('ssh solar-assistant@172.16.106.13')
        child.timeout = 30
        
        i = child.expect(['password:', 'yes/no'])
        if i == 1:
            child.sendline('yes')
            child.expect('password:')
        child.sendline('solar123')
        child.expect([pexpect.TIMEOUT], timeout=3)
        
        # More focused commands
        commands = [
            # Find the influx-bridge service details
            "sudo systemctl cat influx-bridge.service",
            
            # Look for configuration in common locations
            "sudo find /usr -name '*solar*' -type d 2>/dev/null",
            "sudo find /usr -name '*influx*' -type d 2>/dev/null",
            
            # Check /etc for configuration files
            "sudo find /etc -name '*influx*' 2>/dev/null",
            "sudo find /etc -name '*solar*' 2>/dev/null",
            
            # Look for database files
            "sudo find /var -name '*.db' 2>/dev/null | head -10",
            
            # Check the actual running process
            "sudo ps aux | grep beam",
            
            # Look for web interface files
            "sudo find /var/www -type f 2>/dev/null | head -10",
            "sudo find /srv -type f 2>/dev/null | head -10",
            
            # Look for configuration in user directories
            "sudo find /home -name '*.conf' -o -name '*.json' -o -name '*.yaml' 2>/dev/null | head -10"
        ]
        
        for cmd in commands:
            print(f"\n=== {cmd} ===")
            child.sendline(cmd)
            time.sleep(1)
            
            # Handle sudo password
            try:
                child.expect('password for', timeout=1)
                child.sendline('solar123')
                time.sleep(1)
            except:
                pass
            
            # Send 'q' to quit any pager
            child.sendline('q')
            time.sleep(2)
            
        child.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_focused_commands()