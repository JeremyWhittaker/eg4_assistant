#!/usr/bin/env python3
import pexpect
import sys
import time

def run_ssh_commands():
    try:
        # SSH connection details
        host = "172.16.109.214"
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
        
        print("\n=== 1. Check running services for data collection ===")
        child.sendline('ps aux | grep -E "solar|eg4|inverter|data|collector" | grep -v grep')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 2. Check influx-bridge service status ===")
        child.sendline('systemctl status influx-bridge | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 3. Look for data collection scripts or binaries ===")
        child.sendline('sudo find /opt /usr/local -name "*collector*" -type f 2>/dev/null | head -20')
        i = child.expect(['password for', '\\$', '#', '>', pexpect.TIMEOUT], timeout=10)
        if i == 0:
            child.sendline(password)
            child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 4. Look for EG4-related files ===")
        child.sendline('sudo find /opt /usr/local -name "*eg4*" -type f 2>/dev/null | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 5. Look for inverter-related files ===")
        child.sendline('sudo find /opt /usr/local -name "*inverter*" -type f 2>/dev/null | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 6. Check network connections to the inverter ===")
        child.sendline('netstat -an | grep 172.16.107.129')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 7. Check connections on port 8000 ===")
        child.sendline('netstat -an | grep :8000')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 8. Look for configuration files with inverter IP ===")
        child.sendline('sudo find /etc /opt -name "*.conf" -o -name "*.config" | xargs grep -l "172.16.107" 2>/dev/null | head -10')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 9. Look for JSON files with inverter config ===")
        child.sendline('sudo find /etc /opt -name "*.json" | xargs grep -l "inverter" 2>/dev/null | head -10')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 10. Check InfluxDB databases ===")
        child.sendline('influx -execute "SHOW DATABASES" 2>/dev/null || echo "influx CLI not available"')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 11. Check InfluxDB via HTTP API ===")
        child.sendline('curl -s http://localhost:8086/query?q=SHOW%20DATABASES 2>/dev/null | head -20')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 12. Check processes using port 8000 ===")
        child.sendline('sudo lsof -i :8000 2>/dev/null')
        child.expect(['\\$', '#', '>'])
        time.sleep(0.5)
        
        print("\n=== 13. Capture network traffic to inverter (5 packets) ===")
        child.sendline('sudo tcpdump -i any host 172.16.107.129 -c 5 2>/dev/null')
        child.expect(['\\$', '#', '>', pexpect.TIMEOUT], timeout=15)
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