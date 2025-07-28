#!/usr/bin/env python3
"""
Test script to verify Enphase login automation fixes
"""

import asyncio
import logging
import sys
import os

# Add the current directory to the path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import EnphaseMonitor

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_enphase_login():
    """Test the Enphase login automation"""
    logger.info("Starting Enphase login test...")
    
    # Create monitor instance
    monitor = EnphaseMonitor()
    
    # Set credentials
    monitor.username = "me@jeremywhittaker.com"
    monitor.password = "pQb97tELsfOCBW1k"
    
    try:
        # Start the browser
        await monitor.start()
        logger.info("Browser started successfully")
        
        # Test login with retry
        login_success = await monitor.login_with_retry()
        if login_success:
            logger.info("✅ Login test PASSED")
            
            # Test data extraction
            logger.info("Testing data extraction...")
            data = await monitor.get_data()
            if data:
                logger.info("✅ Data extraction test PASSED")
                logger.info(f"Sample data: {data}")
            else:
                logger.error("❌ Data extraction test FAILED")
                
        else:
            logger.error("❌ Login test FAILED")
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        
    finally:
        # Clean up
        await monitor.stop()
        logger.info("Test completed and browser closed")

if __name__ == "__main__":
    asyncio.run(test_enphase_login())