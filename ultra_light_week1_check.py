#!/usr/bin/env python3
"""
TASK: Run an ultra-light schema and timestamp check for September Week 1 (2025-09-01 → 2025-09-07)
"""

import os
import pandas as pd
import psutil
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def ultra_light_week1_check():
    """Ultra-light schema and timestamp check"""
    start_time = time.time()
    print("⚡ ULTRA-LIGHT SCHEMA & TIMESTAMP CHECK - WEEK 1")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Initial memory: {get_memory_usage():.1f} MB")
    print()
    
    # Input files
    tick_file = 'data_v6/cache/ticks/sep_w1/combined_sep_w1_ticks.parquet'
    beacon_file = 'data_v6/cache/beacons/sep_w1/combined_sep_w1_beacons.parquet'
    
    # Check files exist
    if not os.path.exists(tick_file) or not os.path.exists(beacon_file):
        print("🚨 FAIL – Required files missing")
        return
    
    try:
        # 1. Schema Check - Read only first 10k rows
        print("🔍 **1. Schema Check**")
        print("-" * 30)
        
        # Read minimal data for schema
        tick_sample = pd.read_parquet(tick_file).head(10000)
        beacon_sample = pd.read_parquet(beacon_file).head(10000)
        
        print(f"📊 Tick columns ({len(tick_sample.columns)}): {tick_sample.columns.tolist()}")
        print(f"📊 Tick dtypes: {dict(tick_sample.dtypes)}")
        print(f"📊 Beacon columns ({len(beacon_sample.columns)}): {beacon_sample.columns.tolist()}")
        print(f"📊 Beacon dtypes: {dict(beacon_sample.dtypes)}")
        
        # Check memory
        if get_memory_usage() > 100:
            print(f"🚨 HALTED – Memory usage {get_memory_usage():.1f} MB exceeds 100 MB limit")
            return
        
        # 2. Timestamp Check - First and last 1000 rows
        print(f"\n🔍 **2. Timestamp Check**")
        print("-" * 30)
        
        # Get first 1000 and last 1000 rows for timestamp analysis
        tick_first = pd.read_parquet(tick_file).head(1000)
        tick_last = pd.read_parquet(tick_file).tail(1000)
        
        # Convert timestamps
        tick_first['event_ts'] = pd.to_datetime(tick_first['event_ts'], utc=True)
        tick_last['event_ts'] = pd.to_datetime(tick_last['event_ts'], utc=True)
        
        # Check monotonicity in first 1000
        first_monotonic = tick_first['event_ts'].is_monotonic_increasing
        last_monotonic = tick_last['event_ts'].is_monotonic_increasing
        
        # Get timestamp range
        earliest_ts = tick_first['event_ts'].min()
        latest_ts = tick_last['event_ts'].max()
        
        # Calculate approximate hourly spacing
        time_span = (latest_ts - earliest_ts).total_seconds() / 3600  # hours
        total_rows = len(tick_first) + len(tick_last)
        avg_spacing_seconds = (latest_ts - earliest_ts).total_seconds() / total_rows if total_rows > 0 else 0
        
        print(f"📊 First 1000 monotonic: {first_monotonic}")
        print(f"📊 Last 1000 monotonic: {last_monotonic}")
        print(f"📊 Earliest timestamp: {earliest_ts}")
        print(f"📊 Latest timestamp: {latest_ts}")
        print(f"📊 Time span: {time_span:.1f} hours")
        print(f"📊 Avg spacing: {avg_spacing_seconds:.3f} seconds")
        
        # Check memory and time
        if get_memory_usage() > 100:
            print(f"🚨 HALTED – Memory usage {get_memory_usage():.1f} MB exceeds 100 MB limit")
            return
        
        if time.time() - start_time > 180:  # 3 minutes
            print(f"🚨 HALTED – Runtime exceeds 3 minute limit")
            return
        
        # 3. Schema Analysis
        print(f"\n🔍 **3. Schema Analysis**")
        print("-" * 30)
        
        # Check for extra metadata fields
        core_columns = ['time_exchange', 'time_coinapi', 'guid', 'price', 'base_amount', 'taker_side']
        extra_columns = []
        
        for col in tick_sample.columns:
            if col not in core_columns:
                extra_columns.append(col)
        
        print(f"📊 Core columns: {core_columns}")
        print(f"📊 Extra columns: {extra_columns}")
        
        # Check for type conflicts
        type_conflicts = []
        for col in core_columns:
            if col in tick_sample.columns and col in beacon_sample.columns:
                if tick_sample[col].dtype != beacon_sample[col].dtype:
                    type_conflicts.append(f"{col}: tick={tick_sample[col].dtype}, beacon={beacon_sample[col].dtype}")
        
        print(f"📊 Type conflicts: {type_conflicts}")
        
        # Final verdict
        print(f"\n" + "=" * 60)
        print(f"📦 **ULTRA-LIGHT CHECK SUMMARY**")
        print(f"=" * 60)
        
        final_memory = get_memory_usage()
        final_time = time.time() - start_time
        
        print(f"📊 Runtime: {final_time:.1f} seconds")
        print(f"📊 Memory usage: {final_memory:.1f} MB")
        print(f"📊 Sampled rows: {len(tick_sample):,} ticks, {len(beacon_sample):,} beacons")
        
        # Determine verdict
        if not first_monotonic or not last_monotonic:
            verdict = "🚨 FAIL – timestamp gaps or type conflicts"
        elif type_conflicts:
            verdict = "🚨 FAIL – timestamp gaps or type conflicts"
        elif extra_columns and all(col in ['event_ts', 'venue', 'symbol', 'beacon_type'] for col in extra_columns):
            verdict = "⚠️ MINOR DIFF – extra metadata fields only"
        else:
            verdict = "✅ PASS – schema consistent and monotonic timestamps"
        
        print(f"\n{verdict}")
        
    except Exception as e:
        print(f"🚨 FAIL – Error during check: {str(e)}")
        print(f"Memory usage: {get_memory_usage():.1f} MB")

if __name__ == '__main__':
    ultra_light_week1_check()




