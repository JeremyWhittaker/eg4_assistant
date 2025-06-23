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
        
        print("\n=== 1. Check the influx-bridge process more closely ===")
        child.sendline('ps aux | grep "beam.smp" | grep -v grep')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 2. Check what's in /dev/shm/grafana-sync ===")
        child.sendline('sudo ls -la /dev/shm/grafana-sync/')
        i = child.expect(['password for', '\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        if i == 0:
            child.sendline(password)
            child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 3. Check the Solar Assistant configuration ===")
        child.sendline('sudo find /dev/shm -name "*.config" -o -name "*.json" 2>/dev/null | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 4. Look at the systemd service file ===")
        child.sendline('cat /etc/systemd/system/influx-bridge.service')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 5. Check what libraries are in use ===")
        child.sendline('sudo ls -la /dev/shm/grafana-sync/*/lib/ | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 6. Check for configuration in the beam process ===")
        child.sendline('sudo strings /proc/583/environ | grep -E "inverter|172.16|PORT|HOST" | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 7. Check network connections in detail ===")
        child.sendline('sudo lsof -p 583 | grep -E "TCP|UDP" | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 8. Check for any modbus-related files ===")
        child.sendline('sudo find / -name "*modbus*" -type f 2>/dev/null | grep -v "/proc" | head -20')
        child.expect(['\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        time.sleep(0.5)
        
        print("\n=== 9. Check recent logs from influx-bridge ===")
        child.sendline('sudo journalctl -u influx-bridge --no-pager -n 50 | tail -30')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 10. Check if there's a web interface ===")
        child.sendline('sudo netstat -tlnp | grep -E ":80|:443|:4000|:8080"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 11. Look for any configuration database ===")
        child.sendline('sudo find / -name "*.db" -o -name "*.sqlite" 2>/dev/null | grep -v "/proc" | head -20')
        child.expect(['\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        time.sleep(0.5)
        
        print("\n=== 12. Check the signal.sh script ===")
        child.sendline('cat /usr/lib/influx-bridge/signal.sh')
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