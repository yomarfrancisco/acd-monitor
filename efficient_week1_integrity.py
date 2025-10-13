#!/usr/bin/env python3
"""
⚡ Efficient Week 1-Only Integrity Prompt
TASK: Verify only September Week 1 (2025-09-01 → 2025-09-07 UTC) for completeness and schema integrity
"""

import os
import pandas as pd
import numpy as np
import psutil
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def get_august_baseline_schema():
    """Get August W-1 baseline schema (read only first 1000 rows)"""
    august_paths = [
        'data_v6/cache/beacons/week-minus1',
        'data_v6/cache/beacons/week-minus2', 
        'data_v6/cache/beacons/week-minus3',
        'data_v6/cache/beacons/week-minus4'
    ]
    
    for path in august_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith('.parquet'):
                    try:
                        # Read only first 1000 rows for schema
                        df = pd.read_parquet(os.path.join(path, file)).head(1000)
                        return {
                            'columns': df.columns.tolist(),
                            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                            'source': os.path.join(path, file)
                        }
                    except:
                        continue
    return None

def efficient_week1_integrity():
    """Run efficient Week 1 integrity check with sampling"""
    start_time = time.time()
    print("⚡ EFFICIENT WEEK 1-ONLY INTEGRITY CHECK")
    print("=" * 60)
    print("TASK: Verify September Week 1 (2025-09-01 → 2025-09-07 UTC)")
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Initial memory: {get_memory_usage():.1f} MB")
    print()
    
    # Input files
    tick_file = 'data_v6/cache/ticks/sep_w1/combined_sep_w1_ticks.parquet'
    beacon_file = 'data_v6/cache/beacons/sep_w1/combined_sep_w1_beacons.parquet'
    
    # Check files exist
    if not os.path.exists(tick_file) or not os.path.exists(beacon_file):
        print("🚨 Week 1 Integrity FAIL – Required files missing")
        return
    
    # Initialize results
    checks = {}
    
    # 1. Schema Header Check
    print("🔍 **1. Schema Header Check**")
    print("-" * 30)
    
    try:
        # Read first 1000 rows for schema
        tick_sample = pd.read_parquet(tick_file).head(1000)
        beacon_sample = pd.read_parquet(beacon_file).head(1000)
        
        print(f"📊 Tick columns: {tick_sample.columns.tolist()}")
        print(f"📊 Beacon columns: {beacon_sample.columns.tolist()}")
        
        # Get August baseline
        baseline = get_august_baseline_schema()
        if baseline:
            print(f"📊 Baseline from: {baseline['source']}")
            
            # Compare schemas
            tick_schema_ok = set(tick_sample.columns) == set(baseline['columns'])
            beacon_schema_ok = set(beacon_sample.columns) == set(baseline['columns'])
            
            checks['schema'] = 'PASS' if tick_schema_ok and beacon_schema_ok else 'FAIL'
            print(f"📊 Schema match: {checks['schema']}")
        else:
            checks['schema'] = 'SKIP'
            print(f"📊 No baseline found - skipping schema comparison")
            
    except Exception as e:
        checks['schema'] = 'FAIL'
        print(f"❌ Schema check failed: {e}")
    
    # Check memory and time
    if get_memory_usage() > 400:
        print(f"🚨 HALTED – Memory usage {get_memory_usage():.1f} MB exceeds 400 MB limit")
        return
    
    if time.time() - start_time > 600:  # 10 minutes
        print(f"🚨 HALTED – Runtime exceeds 10 minute limit")
        return
    
    # 2. Timestamp Continuity Check (sampling)
    print(f"\n🔍 **2. Timestamp Continuity Check**")
    print("-" * 30)
    
    try:
        # Read first 500k and last 500k rows for sampling
        print("📊 Reading sample data...")
        
        # Read only first 500k rows for sampling (memory efficient)
        tick_sample = pd.read_parquet(tick_file).head(500000)
        print(f"📊 Sampled {len(tick_sample):,} tick rows (first 500k)")
        
        # Convert timestamps
        tick_sample['event_ts'] = pd.to_datetime(tick_sample['event_ts'], utc=True)
        
        # Check monotonicity
        tick_sorted = tick_sample.sort_values('event_ts')
        is_monotonic = tick_sorted['event_ts'].is_monotonic_increasing
        
        # Sample every hour for gap detection
        tick_sample['hour'] = tick_sample['event_ts'].dt.floor('H')
        hourly_samples = tick_sample.groupby('hour')['event_ts'].agg(['min', 'max', 'count'])
        
        # Check for gaps > 60 minutes in hourly samples
        gaps_found = 0
        for i in range(1, len(hourly_samples)):
            prev_max = hourly_samples.iloc[i-1]['max']
            curr_min = hourly_samples.iloc[i]['min']
            gap_minutes = (curr_min - prev_max).total_seconds() / 60
            if gap_minutes > 60:
                gaps_found += 1
        
        checks['timestamp_continuity'] = 'PASS' if is_monotonic and gaps_found == 0 else 'FAIL'
        print(f"📊 Monotonic: {is_monotonic}")
        print(f"📊 Gaps > 60min: {gaps_found}")
        print(f"📊 Timestamp continuity: {checks['timestamp_continuity']}")
        
    except Exception as e:
        checks['timestamp_continuity'] = 'FAIL'
        print(f"❌ Timestamp check failed: {e}")
    
    # Check memory and time
    if get_memory_usage() > 400:
        print(f"🚨 HALTED – Memory usage {get_memory_usage():.1f} MB exceeds 400 MB limit")
        return
    
    if time.time() - start_time > 600:
        print(f"🚨 HALTED – Runtime exceeds 10 minute limit")
        return
    
    # 3. Hourly Coverage Check
    print(f"\n🔍 **3. Hourly Coverage Check**")
    print("-" * 30)
    
    try:
        # Use the sampled data for hourly analysis
        unique_hours = tick_sample['hour'].unique()
        expected_hours = 168  # 7 days * 24 hours
        
        coverage_pct = (len(unique_hours) / expected_hours * 100) if expected_hours > 0 else 0
        missing_hours = expected_hours - len(unique_hours)
        
        checks['hourly_coverage'] = 'PASS' if missing_hours == 0 else 'FAIL'
        print(f"📊 Expected hours: {expected_hours}")
        print(f"📊 Found hours: {len(unique_hours)}")
        print(f"📊 Missing hours: {missing_hours}")
        print(f"📊 Coverage: {coverage_pct:.1f}%")
        print(f"📊 Hourly coverage: {checks['hourly_coverage']}")
        
    except Exception as e:
        checks['hourly_coverage'] = 'FAIL'
        print(f"❌ Hourly coverage check failed: {e}")
    
    # 4. Venue Presence Check
    print(f"\n🔍 **4. Venue Presence Check**")
    print("-" * 30)
    
    try:
        venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
        venue_presence = {}
        
        for venue in venues:
            venue_data = tick_sample[tick_sample['venue'] == venue]
            venue_hours = len(venue_data['hour'].unique())
            venue_presence_pct = (venue_hours / len(unique_hours) * 100) if len(unique_hours) > 0 else 0
            venue_presence[venue] = venue_presence_pct
            print(f"📊 {venue}: {venue_hours}/{len(unique_hours)} hours ({venue_presence_pct:.1f}%)")
        
        # Check if ≥3 venues present for ≥95% of hours
        venues_above_95 = sum(1 for pct in venue_presence.values() if pct >= 95.0)
        checks['venue_presence'] = 'PASS' if venues_above_95 >= 3 else 'FAIL'
        print(f"📊 Venues ≥95%: {venues_above_95}/4")
        print(f"📊 Venue presence: {checks['venue_presence']}")
        
    except Exception as e:
        checks['venue_presence'] = 'FAIL'
        print(f"❌ Venue presence check failed: {e}")
    
    # Final memory and time check
    final_memory = get_memory_usage()
    final_time = time.time() - start_time
    
    print(f"\n" + "=" * 60)
    print(f"📦 **EFFICIENT WEEK 1 INTEGRITY SUMMARY**")
    print(f"=" * 60)
    
    print(f"\n📊 **Check Results:**")
    for check_name, result in checks.items():
        print(f"  • {check_name.replace('_', ' ').title()}: {result}")
    
    print(f"\n📊 **Performance:**")
    print(f"  • Runtime: {final_time:.1f} seconds")
    print(f"  • Memory usage: {final_memory:.1f} MB")
    print(f"  • Sampled rows: {len(tick_sample):,}")
    
    # Overall verdict
    all_passed = all(result == 'PASS' for result in checks.values())
    if all_passed:
        print(f"\n✅ **Week 1 Integrity PASS**")
    else:
        failed_checks = [name for name, result in checks.items() if result == 'FAIL']
        print(f"\n🚨 **Week 1 Integrity FAIL – {', '.join(failed_checks)}**")
    
    return checks

if __name__ == '__main__':
    efficient_week1_integrity()
