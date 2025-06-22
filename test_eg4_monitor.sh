#!/bin/bash
echo "Testing EG4 Monitor with network resilience..."
echo "This will run for 30 seconds..."
echo ""

# Run with timeout and capture output
timeout 30 python3 -u eg4_monitor_stream.py 2>&1 | tee eg4_monitor_output.log

echo ""
echo "Test complete. Check eg4_monitor_output.log for results."
echo "First 20 lines of output:"
head -20 eg4_monitor_output.log