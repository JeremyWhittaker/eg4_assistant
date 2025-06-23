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
        
        print("\n=== 1. Check environment file ===")
        child.sendline('sudo cat /usr/lib/influx-bridge/influx-bridge.env')
        i = child.expect(['password for', '\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        if i == 0:
            child.sendline(password)
            child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 2. Check what's actually connecting to the inverter ===")
        child.sendline('sudo ss -np | grep "172.16.107.129"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 3. Look at the runtime config ===")
        child.sendline('sudo cat /dev/shm/grafana-sync/*/tmp/*.runtime.config | head -50')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 4. Check for any API endpoints on port 80 ===")
        child.sendline('curl -s http://localhost/api 2>/dev/null || echo "No API on port 80"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 5. Check modbus library usage ===")
        child.sendline('dpkg -l | grep modbus')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 6. Check the Elixir application structure ===")
        child.sendline('sudo ls -la /dev/shm/grafana-sync/*/lib/solar_assistant*/')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 7. Check for web assets ===")
        child.sendline('sudo ls -la /dev/shm/grafana-sync/*/lib/solar_assistant*/priv/static/')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 8. Check for database in /tmp ===")
        child.sendline('sudo find /tmp -name "*.db" -o -name "*.sqlite" 2>/dev/null | head -10')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 9. Check MQTT broker status ===")
        child.sendline('systemctl status mosquitto | head -10')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 10. Check for any configuration in /var/lib ===")
        child.sendline('sudo find /var/lib -name "*solar*" -o -name "*inverter*" 2>/dev/null | grep -v "man\\|dpkg" | head -20')
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