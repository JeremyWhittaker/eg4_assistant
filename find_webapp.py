#!/usr/bin/env python3
"""
Find the Solar Assistant web application
"""

import subprocess
import os

def search_webapp():
    """Search for web application files"""
    
    # Check Grafana configuration
    print("Checking Grafana configuration...")
    grafana_files = [
        "/etc/grafana/grafana.ini",
        "/var/lib/grafana/grafana.db",
        "/usr/share/grafana/conf/defaults.ini"
    ]
    
    for file_path in grafana_files:
        cmd = f'debugfs -R "stat {file_path}" linux_partition_extracted.img 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "File not found" not in result.stdout:
            print(f"✓ Found: {file_path}")
            
            # Extract it
            output_path = f"extracted_files{file_path}"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            extract_cmd = f'debugfs -R "dump {file_path} {output_path}" linux_partition_extracted.img 2>&1'
            subprocess.run(extract_cmd, shell=True, capture_output=True, text=True)
    
    # Check for custom dashboards
    print("\nChecking for Grafana dashboards...")
    cmd = 'debugfs -R "ls /var/lib/grafana/dashboards" linux_partition_extracted.img 2>&1'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    
    # Check nginx configuration
    print("\nChecking nginx configuration...")
    nginx_files = [
        "/etc/nginx/sites-enabled/default",
        "/etc/nginx/conf.d/default.conf",
        "/etc/nginx/nginx.conf"
    ]
    
    for file_path in nginx_files:
        output_path = f"extracted_files{file_path}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = f'debugfs -R "dump {file_path} {output_path}" linux_partition_extracted.img 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"\n✓ Found nginx config: {file_path}")
            with open(output_path, 'r', errors='ignore') as f:
                content = f.read()
                # Look for proxy_pass or root directives
                for line in content.split('\n'):
                    if 'proxy_pass' in line or 'root' in line or 'location' in line:
                        print(f"  {line.strip()}")
    
    # Check for API services
    print("\n\nChecking for API services...")
    api_locations = [
        "/usr/local/bin/solar-assistant",
        "/opt/solar-assistant/server",
        "/home/solar-assistant/api"
    ]
    
    for location in api_locations:
        cmd = f'debugfs -R "ls {location}" linux_partition_extracted.img 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "File not found" not in result.stdout:
            print(f"\nFound directory: {location}")
            print(result.stdout[:500])

if __name__ == "__main__":
    search_webapp()