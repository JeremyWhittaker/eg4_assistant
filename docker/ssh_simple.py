#!/usr/bin/env python3
import pexpect
import time

def run_ssh_command():
    try:
        # Connect to SSH
        child = pexpect.spawn('ssh solar-assistant@172.16.106.13')
        child.timeout = 30
        
        # Handle authentication
        i = child.expect(['password:', 'yes/no'])
        if i == 1:
            child.sendline('yes')
            child.expect('password:')
        child.sendline('solar123')
        
        # Wait for prompt
        child.expect([pexpect.TIMEOUT], timeout=3)
        
        # Send commands one by one with clear output
        commands = [
            "sudo find /opt -type d -name '*solar*' 2>/dev/null",
            "sudo ls -la /opt/",
            "sudo find /opt -name '*.exs' 2>/dev/null | head -5",
            "sudo systemctl status solar-assistant",
            "sudo find /etc -name '*solar*' 2>/dev/null",
            "sudo ps aux | grep solar"
        ]
        
        for cmd in commands:
            print(f"\n=== Running: {cmd} ===")
            child.sendline(cmd)
            time.sleep(2)
            
            # Handle sudo password if needed
            try:
                child.expect('password for', timeout=2)
                child.sendline('solar123')
            except:
                pass
            
            time.sleep(3)
            output = child.before.decode('utf-8', errors='ignore')
            print(output)
        
        child.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_ssh_command()