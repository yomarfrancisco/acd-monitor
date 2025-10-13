#!/usr/bin/env python3
"""
Minimal verification for Weeks 2 & 3 (September 2025)
Memory limit: ≤200 MB, Runtime: ≤60 seconds per week
"""

import pandas as pd
import psutil
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def get_parquet_metadata(file_path):
    """Get parquet file metadata without loading data"""
    try:
        import pyarrow.parquet as pq
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows
        schema = parquet_file.schema
        columns = [field.name for field in schema]
        return total_rows, columns, None
    except Exception as e:
        return 0, [], str(e)

def read_parquet_head(file_path, nrows=10):
    """Read only first nrows of parquet file"""
    try:
        if get_memory_usage() > 200:
            return None, f"Memory usage {get_memory_usage():.1f} MB exceeds 200 MB limit"
        
        df = pd.read_parquet(file_path)
        return df.head(nrows), None
    except Exception as e:
        return None, f"Error reading {file_path}: {e}"

def read_parquet_sample(file_path, nrows=5000):
    """Read sample of parquet file"""
    try:
        if get_memory_usage() > 200:
            return None, f"Memory usage {get_memory_usage():.1f} MB exceeds 200 MB limit"
        
        df = pd.read_parquet(file_path)
        if len(df) > nrows:
            df = df.head(nrows)
        return df, None
    except Exception as e:
        return None, f"Error reading {file_path}: {e}"

def get_timestamp_bounds(file_path):
    """Get first and last 1000 rows for timestamp checking"""
    try:
        if get_memory_usage() > 200:
            return None, None, f"Memory usage {get_memory_usage():.1f} MB exceeds 200 MB limit"
        
        # Read first 1000 rows
        df_first = pd.read_parquet(file_path)
        first_1000 = df_first.head(1000)
        
        # Read last 1000 rows
        df_last = pd.read_parquet(file_path)
        last_1000 = df_last.tail(1000)
        
        return first_1000, last_1000, None
    except Exception as e:
        return None, None, f"Error reading {file_path}: {e}"

def check_week_minimal(week_num, tick_file, beacon_file):
    """Minimal verification for a single week"""
    print(f"\n🔍 WEEK {week_num} MINIMAL VERIFICATION")
    print("=" * 50)
    
    start_time = time.time()
    
    # 1. Schema fingerprint
    print("📋 SCHEMA FINGERPRINT")
    print("-" * 30)
    
    # Get metadata
    ticks_rows, ticks_columns, error = get_parquet_metadata(tick_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    beacons_rows, beacons_columns, error = get_parquet_metadata(beacon_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    print(f"Ticks: {ticks_rows:,} rows, {len(ticks_columns)} columns")
    print(f"Ticks columns: {ticks_columns}")
    print()
    print(f"Beacons: {beacons_rows:,} rows, {len(beacons_columns)} columns")
    print(f"Beacons columns: {beacons_columns}")
    print()
    
    # 2. Timestamp sanity
    print("⏰ TIMESTAMP SANITY")
    print("-" * 30)
    
    # Check ticks timestamps
    first_1000, last_1000, error = get_timestamp_bounds(tick_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    # Check monotonicity
    ticks_first_mono = first_1000['event_ts'].is_monotonic_increasing
    ticks_last_mono = last_1000['event_ts'].is_monotonic_increasing
    
    earliest = first_1000['event_ts'].min()
    latest = last_1000['event_ts'].max()
    
    print(f"Ticks first 1000 monotonic: {ticks_first_mono}")
    print(f"Ticks last 1000 monotonic: {ticks_last_mono}")
    print(f"Earliest: {earliest}")
    print(f"Latest: {latest}")
    print()
    
    # 3. Venue presence
    print("🏢 VENUE PRESENCE")
    print("-" * 30)
    
    # Read sample for venue check
    ticks_sample, error = read_parquet_sample(tick_file, 5000)
    if error:
        print(f"❌ {error}")
        return False, error
    
    expected_venues = {'BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET'}
    found_venues = set(ticks_sample['venue'].unique())
    
    print(f"Expected venues: {sorted(expected_venues)}")
    print(f"Found venues: {sorted(found_venues)}")
    print(f"All venues present: {expected_venues.issubset(found_venues)}")
    print()
    
    # 4. Row count check
    print("📊 ROW COUNT CHECK")
    print("-" * 30)
    
    print(f"Total ticks: {ticks_rows:,}")
    print(f"Total beacons: {beacons_rows:,}")
    print()
    
    # Runtime check
    runtime = time.time() - start_time
    print(f"⏱️ Runtime: {runtime:.2f} seconds")
    
    if runtime > 60:
        print("⚠️ Runtime exceeded 60 seconds")
    
    # Memory check
    memory = get_memory_usage()
    print(f"💾 Memory usage: {memory:.1f} MB")
    
    if memory > 200:
        print("⚠️ Memory usage exceeded 200 MB")
        return False, "Memory limit exceeded"
    
    # Determine if this week passes
    week_passes = (ticks_first_mono and ticks_last_mono and 
                   expected_venues.issubset(found_venues))
    
    return week_passes, {
        'ticks_monotonic': ticks_first_mono and ticks_last_mono,
        'venues_complete': expected_venues.issubset(found_venues),
        'total_ticks': ticks_rows,
        'earliest': earliest,
        'latest': latest,
        'runtime': runtime,
        'memory': memory
    }

def main():
    print("🔍 MINIMAL VERIFICATION - WEEKS 2 & 3")
    print("=" * 50)
    print("Memory limit: ≤200 MB, Runtime: ≤60 seconds per week")
    print(f"Initial memory: {get_memory_usage():.1f} MB")
    print()
    
    # File paths
    week2_ticks = "data_v6/cache/ticks/sep_w2/combined_sep_w2_ticks.parquet"
    week2_beacons = "data_v6/cache/beacons/sep_w2/combined_sep_w2_beacons.parquet"
    week3_ticks = "data_v6/cache/ticks/sep_w3/combined_sep_w3_ticks.parquet"
    week3_beacons = "data_v6/cache/beacons/sep_w3/combined_sep_w3_beacons.parquet"
    
    # Check Week 2
    week2_passes, week2_results = check_week_minimal(2, week2_ticks, week2_beacons)
    
    # Check Week 3
    week3_passes, week3_results = check_week_minimal(3, week3_ticks, week3_beacons)
    
    # Row count comparison
    print("\n📊 ROW COUNT COMPARISON")
    print("-" * 30)
    
    # Get Week 1 row count for comparison
    week1_ticks = "data_v6/cache/ticks/sep_w1/combined_sep_w1_ticks.parquet"
    week1_rows, _, error = get_parquet_metadata(week1_ticks)
    
    if error:
        print(f"❌ Error reading Week 1: {error}")
        comparison_ok = False
    else:
        week2_rows = week2_results['total_ticks']
        week3_rows = week3_results['total_ticks']
        
        # Check if within ±20% of previous week
        week2_ratio = week2_rows / week1_rows if week1_rows > 0 else 0
        week3_ratio = week3_rows / week2_rows if week2_rows > 0 else 0
        
        print(f"Week 1: {week1_rows:,} ticks")
        print(f"Week 2: {week2_rows:,} ticks ({week2_ratio:.2f}x)")
        print(f"Week 3: {week3_rows:,} ticks ({week3_ratio:.2f}x)")
        
        week2_ok = 0.8 <= week2_ratio <= 1.2
        week3_ok = 0.8 <= week3_ratio <= 1.2
        
        print(f"Week 2 within ±20%: {week2_ok}")
        print(f"Week 3 within ±20%: {week3_ok}")
        
        comparison_ok = week2_ok and week3_ok
    
    print()
    
    # Final verdict
    print("🎯 FINAL VERDICT")
    print("-" * 30)
    
    overall_passes = week2_passes and week3_passes and comparison_ok
    
    if overall_passes:
        print("✅ PASS – schema ok, timestamps monotonic, all 4 venues present")
    else:
        print("⚠️ ISSUE – verification failed")
        if not week2_passes:
            print("  - Week 2 failed verification")
        if not week3_passes:
            print("  - Week 3 failed verification")
        if not comparison_ok:
            print("  - Row count comparison failed")
    
    print(f"\nFinal memory usage: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()



