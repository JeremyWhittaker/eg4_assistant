#!/usr/bin/env python3
"""Debug real data collector"""

from real_data_collector import RealDataCollector
import time
import json

collector = RealDataCollector()
print("Starting collector...")
collector.start()

print("Waiting 10 seconds for data...")
time.sleep(10)

data = collector.get_data()
print("\nCollector data:")
print(json.dumps(data, indent=2))

collector.stop()
print("\nStopped collector")