#!/usr/bin/env python3
"""
EG4 Streaming Monitor - Shows continuous updates without clearing screen
Handles network issues gracefully
"""

import sys
sys.path.append('.')
from eg4_iotos_client import EG4IoTOSClient
import struct
import time
from datetime import datetime
import socket

def main():
    """Main monitoring loop with robust error handling"""
    print("🚀 EG4 18kPV STREAMING MONITOR")
    print("="*60)
    print("Press Ctrl+C to stop\n")
    
    update_count = 0
    error_count = 0
    last_good_data = None
    
    while True:
        client = None
        try:
            # Create new client for each connection attempt
            client = EG4IoTOSClient(host='172.16.107.129', port=8000)
            
            # Try to connect
            if client.connect():
                error_count = 0  # Reset on successful connection
                
                # Try to get data
                try:
                    response = client.send_receive(b'\xa1\x1a\x05\x00')
                except (socket.timeout, BrokenPipeError, ConnectionResetError) as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Communication error: {type(e).__name__}")
                    response = None
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Unexpected error: {e}")
                    response = None
                
                if response and len(response) >= 100:
                    update_count += 1
                    
                    # Parse data
                    battery_voltage = struct.unpack('>H', response[82:84])[0] / 100.0
                    battery_soc = response[85] if response[85] <= 100 else 0
                    battery_power = struct.unpack('>h', response[48:50])[0]
                    grid_power = struct.unpack('>h', response[50:52])[0]
                    load_power = struct.unpack('>H', response[52:54])[0]
                    
                    # Find grid voltage
                    grid_voltage = 0
                    for offset in [60, 72, 88, 90]:
                        if offset + 2 <= len(response):
                            val = struct.unpack('>H', response[offset:offset+2])[0]
                            if 2000 <= val <= 2600:
                                grid_voltage = val / 10.0
                                break
                    
                    # Display update
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    # Battery status
                    if battery_power > 0:
                        bat_status = "🔋↑CHG"
                    elif battery_power < 0:
                        bat_status = "🔋↓DIS"
                    else:
                        bat_status = "🔋─IDL"
                    
                    # Grid status
                    if grid_power > 0:
                        grid_status = "🏭←IMP"
                    elif grid_power < 0:
                        grid_status = "🏭→EXP"
                    else:
                        grid_status = "🏭─STB"
                    
                    # Print update on one line
                    print(f"[{timestamp}] #{update_count:04d} | "
                          f"🌞 PV:0W | "
                          f"{bat_status}:{battery_power:>5}W {battery_voltage:>4.1f}V {battery_soc:>3}% | "
                          f"{grid_status}:{grid_power:>5}W {grid_voltage:>5.1f}V | "
                          f"🏠 LOAD:{load_power:>5}W")
                    
                    # Store last good data
                    last_good_data = {
                        'battery_power': battery_power,
                        'battery_voltage': battery_voltage,
                        'battery_soc': battery_soc,
                        'grid_power': grid_power,
                        'grid_voltage': grid_voltage,
                        'load_power': load_power
                    }
                elif response:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Response too short: {len(response)} bytes")
                
                # Disconnect safely
                try:
                    client.disconnect()
                except:
                    pass
            else:
                error_count += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔌 Connection failed (attempt {error_count})")
                
                # Show last known data if available
                if last_good_data and error_count == 1:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Last known: "
                          f"Bat:{last_good_data['battery_power']:>5}W {last_good_data['battery_voltage']:>4.1f}V | "
                          f"Grid:{last_good_data['grid_power']:>5}W | "
                          f"Load:{last_good_data['load_power']:>5}W")
            
            # Wait before next attempt
            if error_count > 0:
                wait_time = min(error_count * 2, 10)  # Back off up to 10 seconds
                time.sleep(wait_time)
            else:
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\n✅ Monitor stopped by user")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔥 Critical error: {e}")
            error_count += 1
            time.sleep(5)
        finally:
            # Always try to disconnect
            if client:
                try:
                    client.disconnect()
                except:
                    pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)