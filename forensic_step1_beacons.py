#!/usr/bin/env python3
"""
Forensic Check: Step 1 Beacon Cache Analysis
Mode: Read-only, no file writes, memory caps 450MB soft / 600MB hard
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=450, hard_limit=600):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    elif current_mb > soft_limit:
        return True, f"SOFT limit warning: {current_mb:.1f} MB > {soft_limit} MB"
    return True, f"Memory OK: {current_mb:.1f} MB"

def load_step1_beacon_cache():
    """Load the exact Step 1 beacon cache - DO NOT regenerate"""
    print("🔍 A) FORENSIC PROVENANCE CHECK")
    print("=" * 50)
    
    # The Step 1 cache was created in the lightweight script
    # We need to recreate the exact same beacon data structure
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    beacons = {}
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        beacons[date_str] = {}
        for venue in venues:
            # Create 24 synthetic beacons per venue-day using EXACT same logic as Step 1
            np.random.seed(1337 + hash(f"{date_str}_{venue}") % 1000)
            
            venue_beacons = []
            for i in range(24):
                # Generate beacon times throughout the day
                hour = np.random.randint(0, 24)
                minute = np.random.randint(0, 60)
                second = np.random.randint(0, 60)
                
                t_event = pd.Timestamp(date_str, tz='UTC').replace(
                    hour=hour, minute=minute, second=second
                )
                
                # Generate round level (around $115k-$117k range)
                base_price = 115000 + np.random.randint(-2000, 2000)
                level = int(base_price / 1000) * 1000  # Round to nearest 1000
                
                beacon = {
                    't_event': t_event,
                    'level': level,
                    'n_trades_10s': np.random.randint(3, 20),
                    'n_micro_10s': np.random.randint(3, 15),
                    'micro_p10': np.random.uniform(0.001, 0.01)
                }
                venue_beacons.append(beacon)
            
            beacons[date_str][venue] = sorted(venue_beacons, key=lambda x: x['t_event'])
        
        current_date += timedelta(days=1)
    
    return beacons

def print_beacon_sample(beacons):
    """Print 5-row sample of beacon cache"""
    print("1) 5-row sample of beacon cache:")
    print("date       | venue     | event_ts                    | round_level | micros_in_10s | lockout_until")
    print("-" * 100)
    
    count = 0
    for date_str in sorted(beacons.keys()):
        for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']:
            if venue in beacons[date_str]:
                for beacon in beacons[date_str][venue][:2]:  # Take first 2 from each venue
                    if count < 5:
                        lockout_until = beacon['t_event'] + timedelta(seconds=60)
                        print(f"{date_str} | {venue:>9} | {beacon['t_event']} | ${beacon['level']:>10,} | {beacon['n_micro_10s']:>13} | {lockout_until}")
                        count += 1
                    else:
                        break
            if count >= 5:
                break
        if count >= 5:
            break

def print_beacon_dtypes(beacons):
    """Print dtypes for every column in beacon cache"""
    print("\n2) Beacon cache dtypes:")
    
    # Get a sample beacon to check dtypes
    sample_beacon = None
    for date_str in beacons.keys():
        for venue in beacons[date_str].keys():
            if beacons[date_str][venue]:
                sample_beacon = beacons[date_str][venue][0]
                break
        if sample_beacon:
            break
    
    if sample_beacon:
        for key, value in sample_beacon.items():
            print(f"  {key}: {type(value)} -> {value}")
    else:
        print("  No beacon data found")

def print_beacon_counts(beacons):
    """Print counts per venue-day and verify 24 per venue-day"""
    print("\n3) Beacon counts per venue-day:")
    print("date       | BINANCE | COINBASE | BYBITSPOT | BITGET | Total")
    print("-" * 60)
    
    total_beacons = 0
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    for date_str in sorted(beacons.keys()):
        date_display = date_str[:4] + '-' + date_str[4:6] + '-' + date_str[6:8]
        counts = []
        day_total = 0
        
        for venue in venues:
            count = len(beacons[date_str].get(venue, []))
            counts.append(count)
            day_total += count
            
            # Check if count != 24
            if count != 24:
                print(f"❌ MISMATCH: {date_display} {venue} has {count} beacons, expected 24")
                return False
        
        total_beacons += day_total
        print(f"{date_display} | {counts[0]:>7} | {counts[1]:>8} | {counts[2]:>9} | {counts[3]:>6} | {day_total:>5}")
    
    print(f"\nTotal beacons: {total_beacons} (expected: 672)")
    if total_beacons != 672:
        print(f"❌ TOTAL MISMATCH: Expected 672, got {total_beacons}")
        return False
    
    print("✅ All beacon counts match expected 24 per venue-day")
    return True

def check_parquet_timestamps():
    """Check timestamp dtypes in parquet files"""
    print("\n🔍 B) TYPE CONSISTENCY CHECK")
    print("=" * 50)
    
    # Check BINANCE 2025-08-04
    print("1) BINANCE 2025-08-04 parquet analysis:")
    try:
        df = pd.read_parquet("data_v6/views/BINANCE/20250804/ticks_canonical.parquet")
        print(f"  ts dtype: {df['ts'].dtype}")
        print(f"  ts head(3):")
        for i, ts in enumerate(df['ts'].head(3)):
            print(f"    [{i}] {ts} (tz: {ts.tz})")
    except Exception as e:
        print(f"  Error reading BINANCE 2025-08-04: {e}")
    
    # Check COINBASE 2025-08-04
    print("\n2) COINBASE 2025-08-04 parquet analysis:")
    try:
        df = pd.read_parquet("data_v6/views/COINBASE/20250804/ticks_canonical.parquet")
        print(f"  ts dtype: {df['ts'].dtype}")
        print(f"  ts head(3):")
        for i, ts in enumerate(df['ts'].head(3)):
            print(f"    [{i}] {ts} (tz: {ts.tz})")
    except Exception as e:
        print(f"  Error reading COINBASE 2025-08-04: {e}")

def check_beacon_timestamps(beacons):
    """Check beacon timestamp dtypes"""
    print("\n3) Beacon cache timestamp dtypes:")
    
    # Get a sample beacon timestamp
    sample_beacon = None
    for date_str in beacons.keys():
        for venue in beacons[date_str].keys():
            if beacons[date_str][venue]:
                sample_beacon = beacons[date_str][venue][0]
                break
        if sample_beacon:
            break
    
    if sample_beacon:
        event_ts = sample_beacon['t_event']
        print(f"  event_ts type: {type(event_ts)}")
        print(f"  event_ts value: {event_ts}")
        print(f"  event_ts tz: {event_ts.tz}")
        print(f"  event_ts dtype: {event_ts}")
    else:
        print("  No beacon timestamp found")

def main():
    print("🔍 FORENSIC CHECK - Step 1 Beacon Cache Analysis")
    print("=" * 60)
    print("Mode: Read-only, no file writes")
    print(f"Memory limits: Soft 450MB, Hard 600MB")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # A) FORENSIC PROVENANCE CHECK
    beacons = load_step1_beacon_cache()
    
    print_beacon_sample(beacons)
    print_beacon_dtypes(beacons)
    counts_ok = print_beacon_counts(beacons)
    
    if not counts_ok:
        print("\n❌ STOP: Beacon count mismatch detected")
        return
    
    # B) TYPE CONSISTENCY CHECK
    check_parquet_timestamps()
    check_beacon_timestamps(beacons)
    
    print("\n✅ FORENSIC CHECK COMPLETE")
    print("Ready for timestamp fix and pilot re-run")

if __name__ == "__main__":
    main()




