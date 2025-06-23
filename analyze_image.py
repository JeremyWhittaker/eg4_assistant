#!/usr/bin/env python3
"""
Analyze Solar Assistant Raspberry Pi image
Extract key files and configurations
"""

import os
import subprocess
import tempfile
import shutil

def extract_files_from_image():
    """Extract specific files from the image using debugfs"""
    image_path = "linux_partition_extracted.img"
    if not os.path.exists(image_path):
        image_path = "linux_partition.img"
    
    if not os.path.exists(image_path):
        print(f"Error: No Linux partition image found")
        return
    
    print(f"Analyzing image: {image_path}")
    
    # Files to extract
    files_to_extract = [
        # System services
        "/etc/systemd/system/solar-assistant.service",
        "/etc/nginx/nginx.conf",
        "/etc/nginx/sites-available/default",
        "/etc/nginx/sites-enabled/default",
        
        # Application files
        "/opt/solar-assistant/app.py",
        "/opt/solar-assistant/config.py",
        "/opt/solar-assistant/requirements.txt",
        "/opt/solar-assistant/wsgi.py",
        
        # Home directory
        "/home/solar-assistant/app.py",
        "/home/solar-assistant/config.json",
        "/home/solar-assistant/.env",
        
        # Web root possibilities
        "/var/www/html/index.html",
        "/var/www/solar-assistant/app.py",
        
        # Database
        "/var/lib/solar-assistant/solar.db",
        "/home/solar-assistant/solar.db",
    ]
    
    # Create extraction directory
    extract_dir = "extracted_files"
    os.makedirs(extract_dir, exist_ok=True)
    
    for file_path in files_to_extract:
        print(f"\nChecking: {file_path}")
        
        # Use debugfs to check if file exists
        cmd = f'debugfs -R "stat {file_path}" {image_path} 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if "File not found" not in result.stdout:
            # Extract the file
            output_path = os.path.join(extract_dir, file_path.lstrip('/'))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            extract_cmd = f'debugfs -R "dump {file_path} {output_path}" {image_path} 2>&1'
            extract_result = subprocess.run(extract_cmd, shell=True, capture_output=True, text=True)
            
            if os.path.exists(output_path):
                print(f"✓ Extracted: {output_path}")
                
                # Display content if it's a text file
                if output_path.endswith(('.py', '.conf', '.service', '.txt', '.json', '.env')):
                    print(f"Content preview:")
                    with open(output_path, 'r', errors='ignore') as f:
                        content = f.read()[:500]
                        print(content)
                        print("..." if len(content) == 500 else "")

def list_directories():
    """List important directories in the image"""
    image_path = "linux_partition_extracted.img"
    if not os.path.exists(image_path):
        image_path = "linux_partition.img"
    
    directories = [
        "/opt",
        "/home", 
        "/var/www",
        "/etc/nginx",
        "/usr/local/bin",
        "/var/lib"
    ]
    
    print("\n\nDirectory listings:")
    print("=" * 50)
    
    for directory in directories:
        cmd = f'debugfs -R "ls -l {directory}" {image_path} 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if "File not found" not in result.stdout:
            print(f"\n{directory}:")
            print(result.stdout[:1000])

if __name__ == "__main__":
    print("Solar Assistant Image Analysis")
    print("=" * 50)
    
    extract_files_from_image()
    list_directories()