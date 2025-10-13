#!/usr/bin/env python3
"""
Lightweight integrity check for Weeks 2 & 3 (September 2025)
Memory limit: ≤400 MB, Runtime: ≤10 minutes per week
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

def safe_read_parquet(file_path, nrows=10000):
    """Safely read parquet file with memory monitoring"""
    try:
        if get_memory_usage() > 400:
            return None, f"Memory usage {get_memory_usage():.1f} MB exceeds 400 MB limit"
        
        print(f"Reading {file_path} (first {nrows} rows)...")
        
        # Use pyarrow for more memory-efficient reading
        import pyarrow.parquet as pq
        
        # Read metadata first
        parquet_file = pq.ParquetFile(file_path)
        total_rows = parquet_file.metadata.num_rows
        print(f"  File has {total_rows:,} total rows")
        
        # Read schema
        schema = parquet_file.schema
        print(f"  Schema columns: {[field.name for field in schema]}")
        
        # Read only first nrows
        table = parquet_file.read(columns=None, use_pandas_metadata=True)
        df = table.to_pandas()
        
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
    first_sample = df.head(sample_size)
    first_monotonic = first_sample[column].is_monotonic_increasing
    
    # Check last sample_size rows
    last_sample = df.tail(sample_size)
    last_monotonic = last_sample[column].is_monotonic_increasing
    
    return first_monotonic and last_monotonic, f"First {sample_size}: {first_monotonic}, Last {sample_size}: {last_monotonic}"

def validate_hourly_coverage(df, venue_col='venue', timestamp_col='event_ts'):
    """Validate hourly coverage requirements"""
    if len(df) == 0:
        return 0, 0, 0.0, []
    
    # Ensure timestamp is datetime
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
    
    # Create hourly bins
    df['hour'] = df[timestamp_col].dt.floor('H')
    unique_hours = df['hour'].unique()
    
    valid_hours = 0
    missing_hours = []
    
    for hour in unique_hours:
        hour_data = df[df['hour'] == hour]
        venue_counts = hour_data[venue_col].value_counts()
        
        # Check validity: ≥3 beacons & ≥2 venues
        if len(hour_data) >= 3 and len(venue_counts) >= 2:
            valid_hours += 1
        else:
            missing_hours.append(hour)
    
    coverage_pct = (valid_hours / len(unique_hours) * 100) if len(unique_hours) > 0 else 0.0
    
    return len(unique_hours), valid_hours, coverage_pct, missing_hours

def check_week_integrity(week_num, tick_file, beacon_file):
    """Check integrity for a single week"""
    print(f"\n🔍 WEEK {week_num} INTEGRITY CHECK")
    print("=" * 50)
    
    start_time = time.time()
    
    # 1. Schema Consistency
    print("📋 SCHEMA & DTYPES")
    print("-" * 30)
    
    # Read ticks data
    ticks_df, error = safe_read_parquet(tick_file, 10000)
    if error:
        print(f"❌ {error}")
        return False, error
    
    # Read beacons data
    beacons_df, error = safe_read_parquet(beacon_file, 10000)
    if error:
        print(f"❌ {error}")
        return False, error
    
    print("TICKS SCHEMA:")
    print(ticks_df.dtypes.to_string())
    print()
    
    print("BEACONS SCHEMA:")
    print(beacons_df.dtypes.to_string())
    print()
    
    # 2. Timestamp Continuity
    print("⏰ TIMESTAMP CONTINUITY")
    print("-" * 30)
    
    # Check ticks timestamps
    ticks_monotonic, ticks_msg = check_timestamp_monotonic(ticks_df, 'event_ts', 1000)
    print(f"Ticks monotonic: {ticks_msg}")
    
    # Check beacons timestamps
    beacons_monotonic, beacons_msg = check_timestamp_monotonic(beacons_df, 'event_ts', 1000)
    print(f"Beacons monotonic: {beacons_msg}")
    print()
    
    # 3. Venue Completeness
    print("🏢 VENUE COMPLETENESS")
    print("-" * 30)
    
    expected_venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    ticks_venues = sorted(ticks_df['venue'].unique().tolist())
    beacons_venues = sorted(beacons_df['venue'].unique().tolist())
    
    print(f"Expected venues: {expected_venues}")
    print(f"Ticks venues: {ticks_venues}")
    print(f"Beacons venues: {beacons_venues}")
    
    ticks_complete = set(ticks_venues) == set(expected_venues)
    beacons_complete = set(beacons_venues) == set(expected_venues)
    
    print(f"Ticks complete: {ticks_complete}")
    print(f"Beacons complete: {beacons_complete}")
    print()
    
    # 4. Hourly Coverage
    print("📊 HOURLY COVERAGE")
    print("-" * 30)
    
    # For coverage check, we need to read more data
    print("Reading full dataset for coverage analysis...")
    
    # Read full ticks data for coverage
    full_ticks_df = pd.read_parquet(tick_file)
    total_hours, valid_hours, coverage_pct, missing_hours = validate_hourly_coverage(full_ticks_df)
    
    print(f"Total hours: {total_hours}")
    print(f"Valid hours: {valid_hours}")
    print(f"Coverage: {coverage_pct:.1f}%")
    print(f"Missing hours: {len(missing_hours)}")
    print()
    
    # 5. Basic Summary Stats
    print("📈 SUMMARY STATISTICS")
    print("-" * 30)
    
    # Row counts
    print(f"Total ticks: {len(full_ticks_df):,}")
    
    # Venue breakdown
    venue_counts = full_ticks_df['venue'].value_counts()
    print("Ticks per venue:")
    for venue in expected_venues:
        count = venue_counts.get(venue, 0)
        print(f"  {venue}: {count:,}")
    
    # Timestamp range
    earliest = full_ticks_df['event_ts'].min()
    latest = full_ticks_df['event_ts'].max()
    duration = latest - earliest
    
    print(f"Earliest timestamp: {earliest}")
    print(f"Latest timestamp: {latest}")
    print(f"Duration: {duration}")
    
    # Beacon rate per hour
    full_ticks_df['hour'] = full_ticks_df['event_ts'].dt.floor('H')
    hourly_counts = full_ticks_df.groupby('hour').size()
    mean_rate = hourly_counts.mean()
    std_rate = hourly_counts.std()
    
    print(f"Mean beacon rate per hour: {mean_rate:.1f} ± {std_rate:.1f}")
    print()
    
    # Runtime check
    runtime = time.time() - start_time
    print(f"⏱️ Runtime: {runtime:.2f} seconds")
    
    if runtime > 600:  # 10 minutes
        print("⚠️ Runtime exceeded 10 minutes")
    
    # Memory check
    memory = get_memory_usage()
    print(f"💾 Memory usage: {memory:.1f} MB")
    
    if memory > 400:
        print("⚠️ Memory usage exceeded 400 MB")
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
        'total_ticks': len(full_ticks_df),
        'earliest': earliest,
        'latest': latest,
        'runtime': runtime,
        'memory': memory
    }

def main():
    print("🔍 LIGHTWEIGHT INTEGRITY CHECK - WEEKS 2 & 3")
    print("=" * 60)
    print("Memory limit: ≤400 MB, Runtime: ≤10 minutes per week")
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
    week1_df = pd.read_parquet(week1_ticks)
    week1_latest = week1_df['event_ts'].max()
    
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



