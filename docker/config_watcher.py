#!/usr/bin/env python3
"""
Configuration watcher that monitors for changes and notifies the data collector
"""

import os
import json
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_modified = 0
        
    def on_modified(self, event):
        if event.src_path.endswith('settings.json'):
            # Debounce rapid changes
            current_time = time.time()
            if current_time - self.last_modified > 1:
                self.last_modified = current_time
                print(f"Configuration changed: {event.src_path}")
                self.callback()

class ConfigWatcher:
    def __init__(self, config_dir='./config'):
        self.config_dir = config_dir
        self.observer = Observer()
        self.current_config = {}
        self.callbacks = []
        
    def add_callback(self, callback):
        """Add a callback to be called when config changes"""
        self.callbacks.append(callback)
        
    def load_config(self):
        """Load current configuration"""
        try:
            config_path = os.path.join(self.config_dir, 'settings.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.current_config = json.load(f)
                    return self.current_config
        except Exception as e:
            print(f"Error loading config: {e}")
        return {}
        
    def get_config(self):
        """Get current configuration"""
        return self.current_config
        
    def _on_config_change(self):
        """Handle configuration change"""
        old_config = self.current_config.copy()
        new_config = self.load_config()
        
        # Check what changed
        changed_keys = []
        for key in set(old_config.keys()) | set(new_config.keys()):
            if old_config.get(key) != new_config.get(key):
                changed_keys.append(key)
                
        if changed_keys:
            print(f"Configuration changed: {changed_keys}")
            # Notify all callbacks
            for callback in self.callbacks:
                try:
                    callback(old_config, new_config, changed_keys)
                except Exception as e:
                    print(f"Error in callback: {e}")
                    
    def start(self):
        """Start watching for configuration changes"""
        # Create config directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load initial configuration
        self.load_config()
        
        # Set up file watcher
        event_handler = ConfigChangeHandler(self._on_config_change)
        self.observer.schedule(event_handler, self.config_dir, recursive=False)
        self.observer.start()
        
        print(f"Configuration watcher started for {self.config_dir}")
        
    def stop(self):
        """Stop watching"""
        self.observer.stop()
        self.observer.join()
        
def example_callback(old_config, new_config, changed_keys):
    """Example callback function"""
    print(f"Config updated!")
    if 'inverter_ip' in changed_keys:
        print(f"  Inverter IP changed from {old_config.get('inverter_ip')} to {new_config.get('inverter_ip')}")
    if 'poll_interval' in changed_keys:
        print(f"  Poll interval changed from {old_config.get('poll_interval')} to {new_config.get('poll_interval')}")

if __name__ == '__main__':
    # Example usage
    watcher = ConfigWatcher()
    watcher.add_callback(example_callback)
    watcher.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("Configuration watcher stopped.")