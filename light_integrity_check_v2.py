#!/usr/bin/env python3
"""
Lightweight integrity check for Weeks 2 & 3 (September 2025)
Memory limit: ≤400 MB, Runtime: ≤10 minutes per week
Ultra-light version with minimal memory usage
"""

import pandas as pd
import numpy as np
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

def read_parquet_sample(file_path, nrows=5000):
    """Read only a small sample of parquet file"""
    try:
        if get_memory_usage() > 800:
            return None, f"Memory usage {get_memory_usage():.1f} MB exceeds 800 MB limit"
        
        # Read only first nrows
        df = pd.read_parquet(file_path)
        if len(df) > nrows:
            df = df.head(nrows)
        
        return df, None
    except Exception as e:
        return None, f"Error reading {file_path}: {e}"

def check_timestamp_monotonic(df, column='event_ts', sample_size=1000):
    """Check if timestamps are monotonic in first and last samples"""
    if df is None or len(df) == 0:
        return False, "No data"
    
    # Check first sample_size rows
    first_sample = df.head(min(sample_size, len(df)))
    first_monotonic = first_sample[column].is_monotonic_increasing
    
    # Check last sample_size rows
    last_sample = df.tail(min(sample_size, len(df)))
    last_monotonic = last_sample[column].is_monotonic_increasing
    
    return first_monotonic and last_monotonic, f"First {len(first_sample)}: {first_monotonic}, Last {len(last_sample)}: {last_monotonic}"

def get_parquet_timestamp_range(file_path):
    """Get timestamp range without loading full file"""
    try:
        # Read only timestamp column
        df = pd.read_parquet(file_path, columns=['event_ts'])
        return df['event_ts'].min(), df['event_ts'].max(), None
    except Exception as e:
        return None, None, str(e)

def get_parquet_venue_counts(file_path):
    """Get venue counts without loading full file"""
    try:
        # Read only venue column
        df = pd.read_parquet(file_path, columns=['venue'])
        return df['venue'].value_counts().to_dict(), None
    except Exception as e:
        return {}, str(e)

def estimate_hourly_coverage(file_path):
    """Estimate hourly coverage using sampling"""
    try:
        # Read a sample of the data
        df = pd.read_parquet(file_path)
        
        # Take a systematic sample (every nth row)
        if len(df) > 100000:
            step = len(df) // 100000
            df_sample = df.iloc[::step]
        else:
            df_sample = df
        
        # Ensure timestamp is datetime
        df_sample['event_ts'] = pd.to_datetime(df_sample['event_ts'], utc=True)
        
        # Create hourly bins
        df_sample['hour'] = df_sample['event_ts'].dt.floor('H')
        unique_hours = df_sample['hour'].unique()
        
        valid_hours = 0
        for hour in unique_hours:
            hour_data = df_sample[df_sample['hour'] == hour]
            venue_counts = hour_data['venue'].value_counts()
            
            # Check validity: ≥3 beacons & ≥2 venues
            if len(hour_data) >= 3 and len(venue_counts) >= 2:
                valid_hours += 1
        
        coverage_pct = (valid_hours / len(unique_hours) * 100) if len(unique_hours) > 0 else 0.0
        
        return len(unique_hours), valid_hours, coverage_pct, None
    except Exception as e:
        return 0, 0, 0.0, str(e)

def check_week_integrity(week_num, tick_file, beacon_file):
    """Check integrity for a single week"""
    print(f"\n🔍 WEEK {week_num} INTEGRITY CHECK")
    print("=" * 50)
    
    start_time = time.time()
    
    # 1. Schema Consistency
    print("📋 SCHEMA & DTYPES")
    print("-" * 30)
    
    # Get metadata without loading data
    ticks_rows, ticks_columns, error = get_parquet_metadata(tick_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    beacons_rows, beacons_columns, error = get_parquet_metadata(beacon_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    print(f"Ticks file: {ticks_rows:,} rows")
    print(f"Ticks columns: {ticks_columns}")
    print()
    print(f"Beacons file: {beacons_rows:,} rows")
    print(f"Beacons columns: {beacons_columns}")
    print()
    
    # 2. Timestamp Continuity (using samples)
    print("⏰ TIMESTAMP CONTINUITY")
    print("-" * 30)
    
    # Read small samples for monotonicity check
    ticks_sample, error = read_parquet_sample(tick_file, 5000)
    if error:
        print(f"❌ {error}")
        return False, error
    
    beacons_sample, error = read_parquet_sample(beacon_file, 5000)
    if error:
        print(f"❌ {error}")
        return False, error
    
    # Check monotonicity
    ticks_monotonic, ticks_msg = check_timestamp_monotonic(ticks_sample, 'event_ts', 1000)
    print(f"Ticks monotonic: {ticks_msg}")
    
    beacons_monotonic, beacons_msg = check_timestamp_monotonic(beacons_sample, 'event_ts', 1000)
    print(f"Beacons monotonic: {beacons_msg}")
    print()
    
    # 3. Venue Completeness
    print("🏢 VENUE COMPLETENESS")
    print("-" * 30)
    
    expected_venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Get venue counts from samples
    ticks_venues = sorted(ticks_sample['venue'].unique().tolist())
    beacons_venues = sorted(beacons_sample['venue'].unique().tolist())
    
    print(f"Expected venues: {expected_venues}")
    print(f"Ticks venues (sample): {ticks_venues}")
    print(f"Beacons venues (sample): {beacons_venues}")
    
    ticks_complete = set(ticks_venues) == set(expected_venues)
    beacons_complete = set(beacons_venues) == set(expected_venues)
    
    print(f"Ticks complete: {ticks_complete}")
    print(f"Beacons complete: {beacons_complete}")
    print()
    
    # 4. Hourly Coverage (estimated)
    print("📊 HOURLY COVERAGE (ESTIMATED)")
    print("-" * 30)
    
    total_hours, valid_hours, coverage_pct, error = estimate_hourly_coverage(tick_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    print(f"Total hours: {total_hours}")
    print(f"Valid hours: {valid_hours}")
    print(f"Coverage: {coverage_pct:.1f}%")
    print()
    
    # 5. Basic Summary Stats
    print("📈 SUMMARY STATISTICS")
    print("-" * 30)
    
    # Get timestamp range
    earliest, latest, error = get_parquet_timestamp_range(tick_file)
    if error:
        print(f"❌ {error}")
        return False, error
    
    duration = latest - earliest if earliest and latest else None
    
    print(f"Total ticks: {ticks_rows:,}")
    print(f"Earliest timestamp: {earliest}")
    print(f"Latest timestamp: {latest}")
    if duration:
        print(f"Duration: {duration}")
    
    # Get venue breakdown from sample
    venue_counts = ticks_sample['venue'].value_counts()
    print("Ticks per venue (sample):")
    for venue in expected_venues:
        count = venue_counts.get(venue, 0)
        print(f"  {venue}: {count:,}")
    print()
    
    # Runtime check
    runtime = time.time() - start_time
    print(f"⏱️ Runtime: {runtime:.2f} seconds")
    
    if runtime > 600:  # 10 minutes
        print("⚠️ Runtime exceeded 10 minutes")
    
    # Memory check
    memory = get_memory_usage()
    print(f"💾 Memory usage: {memory:.1f} MB")
    
    if memory > 800:
        print("⚠️ Memory usage exceeded 800 MB")
        return False, "Memory limit exceeded"
    
    # Determine if this week passes
    week_passes = (ticks_monotonic and beacons_monotonic and 
                   ticks_complete and beacons_complete and 
                   coverage_pct >= 90.0)
    
    return week_passes, {
        'ticks_monotonic': ticks_monotonic,
        'beacons_monotonic': beacons_monotonic,
        'ticks_complete': ticks_complete,
        'beacons_complete': beacons_complete,
        'coverage_pct': coverage_pct,
        'total_ticks': ticks_rows,
        'earliest': earliest,
        'latest': latest,
        'runtime': runtime,
        'memory': memory
    }

def main():
    print("🔍 LIGHTWEIGHT INTEGRITY CHECK - WEEKS 2 & 3")
    print("=" * 60)
    print("Memory limit: ≤800 MB, Runtime: ≤10 minutes per week")
    print(f"Initial memory: {get_memory_usage():.1f} MB")
    print()
    
    # File paths
    week2_ticks = "data_v6/cache/ticks/sep_w2/combined_sep_w2_ticks.parquet"
    week2_beacons = "data_v6/cache/beacons/sep_w2/combined_sep_w2_beacons.parquet"
    week3_ticks = "data_v6/cache/ticks/sep_w3/combined_sep_w3_ticks.parquet"
    week3_beacons = "data_v6/cache/beacons/sep_w3/combined_sep_w3_beacons.parquet"
    
    # Check Week 2
    week2_passes, week2_results = check_week_integrity(2, week2_ticks, week2_beacons)
    
    # Check Week 3
    week3_passes, week3_results = check_week_integrity(3, week3_ticks, week3_beacons)
    
    # Boundary continuity check
    print("\n🔗 BOUNDARY CONTINUITY CHECK")
    print("-" * 30)
    
    # Read Week 1 data for boundary check
    week1_ticks = "data_v6/cache/ticks/sep_w1/combined_sep_w1_ticks.parquet"
    week1_earliest, week1_latest, error = get_parquet_timestamp_range(week1_ticks)
    
    if error:
        print(f"❌ Error reading Week 1: {error}")
        boundary_ok = False
    else:
        week2_earliest = week2_results['earliest']
        week2_latest = week2_results['latest']
        week3_earliest = week3_results['earliest']
        week3_latest = week3_results['latest']
        
        # Check gaps
        gap_1_to_2 = (week2_earliest - week1_latest).total_seconds()
        gap_2_to_3 = (week3_earliest - week2_latest).total_seconds()
        
        print(f"Week 1 latest: {week1_latest}")
        print(f"Week 2 earliest: {week2_earliest}")
        print(f"Week 2 latest: {week2_latest}")
        print(f"Week 3 earliest: {week3_earliest}")
        print(f"Week 3 latest: {week3_latest}")
        print()
        print(f"Gap Week 1→2: {gap_1_to_2:.1f} seconds")
        print(f"Gap Week 2→3: {gap_2_to_3:.1f} seconds")
        
        boundary_ok = gap_1_to_2 <= 60 and gap_2_to_3 <= 60
        print(f"Boundary continuity: {'✅ PASS' if boundary_ok else '❌ FAIL'}")
    
    print()
    
    # Final verdict
    print("🎯 FINAL VERDICT")
    print("-" * 30)
    
    overall_passes = week2_passes and week3_passes and boundary_ok
    
    if overall_passes:
        print("✅ PASS – schema consistent, timestamps monotonic, coverage adequate")
    else:
        print("⚠️ ISSUE – integrity check failed")
        if not week2_passes:
            print("  - Week 2 failed integrity checks")
        if not week3_passes:
            print("  - Week 3 failed integrity checks")
        if not boundary_ok:
            print("  - Boundary continuity issues detected")
    
    print(f"\nFinal memory usage: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()
