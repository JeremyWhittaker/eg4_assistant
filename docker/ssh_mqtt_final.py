#!/usr/bin/env python3
import pexpect
import sys
import time

def run_ssh_commands():
    try:
        # SSH connection details
        host = "172.16.106.13"
        user = "solar-assistant"
        password = "solar123"
        
        print("Connecting to Solar Assistant server...")
        
        # Start SSH connection
        child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {user}@{host}')
        child.timeout = 30
        child.logfile_read = sys.stdout.buffer
        
        # Handle authentication
        i = child.expect(['password:', 'yes/no', pexpect.TIMEOUT])
        if i == 1:
            child.sendline('yes')
            child.expect('password:')
        
        child.sendline(password)
        child.expect(['\\$', '#', '>'])
        
        print("\n=== 1. Check MQTT broker status ===")
        child.sendline('systemctl status mosquitto 2>/dev/null | head -20 || echo "No mosquitto service"')
        i = child.expect(['password for', '\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        if i == 0:
            child.sendline(password)
            child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 2. Check for any configuration in /var/lib ===")
        child.sendline('sudo find /var/lib -name "*solar*" -o -name "*inverter*" 2>/dev/null | grep -v "man\\|dpkg" | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 3. Check the actual application directory ===")
        child.sendline('sudo ls -la /dev/shm/grafana-sync/*/lib/')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 4. Find the solar_assistant application ===")
        child.sendline('sudo find /dev/shm/grafana-sync -name "solar_assistant*" -type d | head -10')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 5. Check for API endpoints ===")
        child.sendline('curl -s http://localhost/api/inverters 2>/dev/null || echo "No inverters API"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 6. Check for web root ===")
        child.sendline('curl -s http://localhost/ | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== Done! Exiting... ===")
        child.sendline('exit')
        child.close()
        
    except pexpect.TIMEOUT:
        print("\nTimeout occurred during command execution")
        child.close()
    except Exception as e:
        print(f"\nError: {e}")
        if 'child' in locals():
            child.close()
        return False
    
    return True

if __name__ == "__main__":
    run_ssh_commands()