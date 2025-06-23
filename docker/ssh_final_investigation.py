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
        
        print("\n=== 1. Check recent logs from influx-bridge ===")
        child.sendline('sudo journalctl -u influx-bridge --no-pager -n 50 | tail -30')
        i = child.expect(['password for', '\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        if i == 0:
            child.sendline(password)
            child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 2. Check network services listening ===")
        child.sendline('sudo netstat -tlnp | grep -E ":80|:443|:4000|:8080"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 3. Find configuration database ===")
        child.sendline('sudo find / -name "*.db" -o -name "*.sqlite" 2>/dev/null | grep -v "/proc" | head -20')
        child.expect(['\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        time.sleep(0.5)
        
        print("\n=== 4. Check the signal.sh script ===")
        child.sendline('cat /usr/lib/influx-bridge/signal.sh')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 5. Check the influx-bridge binary/script ===")
        child.sendline('ls -la /usr/lib/influx-bridge/')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 6. Check environment file ===")
        child.sendline('sudo cat /usr/lib/influx-bridge/influx-bridge.env')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 7. Check what's actually connecting to the inverter ===")
        child.sendline('sudo ss -np | grep "172.16.107.129"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 8. Look at the runtime config ===")
        child.sendline('sudo cat /dev/shm/grafana-sync/*/tmp/*.runtime.config | head -50')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 9. Check for any API endpoints ===")
        child.sendline('curl -s http://localhost:4000/api 2>/dev/null || echo "No API on port 4000"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 10. Check web server logs ===")
        child.sendline('sudo tail -20 /var/log/nginx/access.log 2>/dev/null || echo "No nginx logs"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 11. Check for modbus library usage ===")
        child.sendline('dpkg -l | grep modbus')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 12. Check the actual Elixir application ===")
        child.sendline('sudo ls -la /dev/shm/grafana-sync/*/lib/solar_assistant*/')
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