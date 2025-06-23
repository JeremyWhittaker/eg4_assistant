#!/usr/bin/env python3
"""
EG4 Connection Handler with retry logic for intermittent connectivity
"""

import time
import logging
from eg4_iotos_client import EG4IoTOSClient

logger = logging.getLogger(__name__)

class EG4ConnectionHandler:
    def __init__(self, host="172.16.107.129", port=8000, username="admin", password="admin"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self.max_retries = 3
        self.retry_delay = 5
        self.last_successful_connection = None
        
    def connect_with_retry(self):
        """Connect to EG4 with automatic retry on failure"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting connection to {self.host}:{self.port} (attempt {attempt + 1}/{self.max_retries})")
                
                self.client = EG4IoTOSClient(host=self.host, port=self.port)
                if self.client.connect():
                    logger.info(f"Successfully connected to EG4 inverter at {self.host}")
                    self.last_successful_connection = time.time()
                    return True
                else:
                    logger.warning(f"Connection attempt {attempt + 1} failed")
                    
            except Exception as e:
                logger.error(f"Connection error on attempt {attempt + 1}: {e}")
            
            if attempt < self.max_retries - 1:
                logger.info(f"Waiting {self.retry_delay} seconds before retry...")
                time.sleep(self.retry_delay)
        
        logger.error(f"Failed to connect after {self.max_retries} attempts")
        return False
    
    def get_data_with_retry(self):
        """Get data from EG4 with automatic reconnection on failure"""
        if not self.client or not self.client.socket:
            if not self.connect_with_retry():
                return None
        
        try:
            data = self.client.get_realtime_data()
            if data:
                logger.debug("Successfully retrieved data from EG4")
                return data
            else:
                logger.warning("No data received from EG4")
                # Try reconnecting
                if self.connect_with_retry():
                    return self.client.get_realtime_data()
                
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            # Try reconnecting
            if self.connect_with_retry():
                try:
                    return self.client.get_realtime_data()
                except:
                    pass
        
        return None
    
    def is_connected(self):
        """Check if currently connected"""
        return self.client and self.client.socket is not None
    
    def disconnect(self):
        """Disconnect from EG4"""
        if self.client:
            self.client.disconnect()
            self.client = None

# Test the connection
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing EG4 connection with retry logic...")
    print(f"Server: 172.16.107.129")
    print(f"Credentials: admin/admin")
    print("-" * 50)
    
    handler = EG4ConnectionHandler()
    
    if handler.connect_with_retry():
        print("✓ Connection established!")
        
        data = handler.get_data_with_retry()
        if data:
            print("✓ Data retrieved successfully!")
            print(f"  PV Power: {data.get('pv_power', 0)}W")
            print(f"  Battery Power: {data.get('battery_power', 0)}W")
            print(f"  Grid Power: {data.get('grid_power', 0)}W")
            print(f"  Load Power: {data.get('load_power', 0)}W")
            print(f"  Battery SOC: {data.get('battery_soc', 0)}%")
        else:
            print("✗ Could not retrieve data")
        
        handler.disconnect()
    else:
        print("✗ Could not establish connection")
        print("\nNote: The server has intermittent connectivity.")
        print("The system will continue retrying in the background.")