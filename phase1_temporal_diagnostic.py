#!/usr/bin/env python3
"""
Phase 1 Temporal Diagnostic: Determine if 2-3s lags are systemic or preprocessing artifacts
Analyze metadata from existing VWAP bars for 2025-09-08 → 2025-09-10
"""

import os
import sys
import pandas as pd
import numpy as np
import gc
import psutil
import pyarrow.parquet as pq
from datetime import datetime, timedelta
from collections import defaultdict

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 300:
        print(f"HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
        return True
    return False

def inspect_timestamp_schema(venue, date):
    """Inspect timestamp schema and metadata for a venue-day file"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Read just the timestamp column to inspect schema
        parquet_file = pq.ParquetFile(file_path)
        
        # Get schema information
        schema = parquet_file.schema
        ts_field = None
        for field in schema:
            if field.name == 'ts':
                ts_field = field
                break
        
        if ts_field is None:
            return None, "Timestamp column 'ts' not found in schema"
        
        # Read a small sample to check actual data
        sample_batch = parquet_file.read_row_groups([0], columns=['ts']).to_pandas()
        
        if len(sample_batch) == 0:
            return None, "No data in first row group"
        
        ts_sample = sample_batch['ts'].iloc[0]
        
        # Analyze timestamp properties
        ts_dtype = str(sample_batch['ts'].dtype)
        ts_unit = None
        ts_tz = None
        
        if hasattr(ts_sample, 'tz'):
            ts_tz = str(ts_sample.tz)
        
        # Determine unit
        if 'ns' in ts_dtype:
            ts_unit = 'nanoseconds'
        elif 'us' in ts_dtype:
            ts_unit = 'microseconds'
        elif 'ms' in ts_dtype:
            ts_unit = 'milliseconds'
        elif 's' in ts_dtype:
            ts_unit = 'seconds'
        else:
            ts_unit = 'unknown'
        
        return {
            'dtype': ts_dtype,
            'unit': ts_unit,
            'timezone': ts_tz,
            'sample_value': ts_sample,
            'sample_str': str(ts_sample)
        }, None
        
    except Exception as e:
        return None, f"Error inspecting {file_path}: {e}"

def load_vwap_bars_metadata(venue, date):
    """Load VWAP bars and compute metadata without heavy processing"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Process in small batches to create VWAP bars
        parquet_file = pq.ParquetFile(file_path)
        
        # Initialize VWAP aggregation
        sum_pxsz = defaultdict(float)
        sum_sz = defaultdict(float)
        
        # Process in small batches
        batch_size = 50000  # Smaller batches for memory efficiency
        total_rows = 0
        
        for batch in parquet_file.iter_batches(batch_size=batch_size, columns=['ts', 'price', 'size']):
            # Check memory
            if check_memory_limit():
                return None, "Memory limit exceeded"
            
            df_batch = batch.to_pandas()
            total_rows += len(df_batch)
            
            # Build 1-second VWAP bars
            df_batch['second'] = df_batch['ts'].dt.floor('S')
            
            for _, row in df_batch.iterrows():
                second = row['second']
                price = row['price']
                size = row['size']
                
                sum_pxsz[second] += price * size
                sum_sz[second] += size
            
            # Clean up batch
            del df_batch
            gc.collect()
        
        # Create VWAP bars DataFrame
        bars_data = []
        for second in sorted(sum_pxsz.keys()):
            if sum_sz[second] > 0:
                bars_data.append({'second': second})
        
        bars_df = pd.DataFrame(bars_data)
        
        # Clean up
        del sum_pxsz, sum_sz, bars_data
        gc.collect()
        
        return bars_df, None
        
    except Exception as e:
        return None, f"Error processing {file_path}: {e}"

def compute_clock_drift(binance_bars, other_bars, venue_name):
    """Compute clock drift between BINANCE and another venue"""
    # Find overlapping seconds
    binance_seconds = set(binance_bars['second'])
    other_seconds = set(other_bars['second'])
    shared_seconds = binance_seconds.intersection(other_seconds)
    
    if len(shared_seconds) < 100:
        return None, f"Insufficient overlapping seconds: {len(shared_seconds)}"
    
    # Convert to sorted lists
    shared_seconds_list = sorted(list(shared_seconds))
    
    # Find first shared second for each venue
    binance_first_shared = None
    other_first_shared = None
    
    for second in shared_seconds_list:
        if binance_first_shared is None and second in binance_seconds:
            binance_first_shared = second
        if other_first_shared is None and second in other_seconds:
            other_first_shared = second
    
    if binance_first_shared is None or other_first_shared is None:
        return None, "Could not find first shared second"
    
    # Compute lag series
    lag_series = []
    for second in shared_seconds_list:
        # Find the lag for this second
        binance_idx = None
        other_idx = None
        
        for i, s in enumerate(binance_bars['second']):
            if s == second:
                binance_idx = i
                break
        
        for i, s in enumerate(other_bars['second']):
            if s == second:
                other_idx = i
                break
        
        if binance_idx is not None and other_idx is not None:
            lag = other_idx - binance_idx  # Positive means other venue is ahead
            lag_series.append(lag)
    
    if len(lag_series) == 0:
        return None, "No valid lag measurements"
    
    # Compute median lag per hour
    hourly_lags = defaultdict(list)
    
    for i, second in enumerate(shared_seconds_list):
        if i < len(lag_series):
            hour = second.hour
            hourly_lags[hour].append(lag_series[i])
    
    # Compute median lag per hour
    median_lags_by_hour = {}
    for hour in range(24):
        if hour in hourly_lags and len(hourly_lags[hour]) > 0:
            median_lags_by_hour[hour] = np.median(hourly_lags[hour])
    
    # Overall median lag
    overall_median_lag = np.median(lag_series)
    
    return {
        'overall_median_lag': overall_median_lag,
        'median_lags_by_hour': median_lags_by_hour,
        'total_shared_seconds': len(shared_seconds),
        'lag_series_length': len(lag_series)
    }, None

def run_temporal_diagnostic():
    """Run temporal diagnostic for 2025-09-08 → 2025-09-10"""
    print("🧩 Phase 1 Temporal Diagnostic: Systemic vs Preprocessing Analysis")
    print("=" * 70)
    
    dates = ["20250908", "20250909", "20250910"]
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Step 1: Inspect timestamp schemas
    print(f"\n🔍 Step 1: Inspecting timestamp schemas...")
    schema_results = {}
    
    for venue in venues:
        schema_results[venue] = {}
        for date in dates:
            result, error = inspect_timestamp_schema(venue, date)
            if error:
                print(f"    ❌ {venue} {date}: {error}")
                return False
            
            schema_results[venue][date] = result
            print(f"    ✅ {venue} {date}: {result['dtype']}, {result['unit']}, TZ={result['timezone']}")
    
    # Check for schema consistency
    print(f"\n🔍 Checking schema consistency...")
    reference_schema = schema_results['BINANCE']['20250908']
    
    for venue in venues:
        for date in dates:
            schema = schema_results[venue][date]
            if (schema['dtype'] != reference_schema['dtype'] or 
                schema['unit'] != reference_schema['unit'] or 
                schema['timezone'] != reference_schema['timezone']):
                print(f"❌ HALT: Schema inconsistency detected")
                print(f"Reference (BINANCE 20250908): {reference_schema['dtype']}, {reference_schema['unit']}, TZ={reference_schema['timezone']}")
                print(f"Different ({venue} {date}): {schema['dtype']}, {schema['unit']}, TZ={schema['timezone']}")
                return False
    
    print(f"    ✅ All schemas consistent: {reference_schema['dtype']}, {reference_schema['unit']}, TZ={reference_schema['timezone']}")
    
    # Step 2: Load VWAP bars and compute clock drift
    print(f"\n🔍 Step 2: Computing clock drift analysis...")
    
    all_bars = {}
    drift_results = {}
    
    for date in dates:
        print(f"\n📊 Processing {date}...")
        all_bars[date] = {}
        
        # Load bars for all venues
        for venue in venues:
            print(f"  Loading {venue} bars...")
            
            if check_memory_limit():
                print(f"❌ HALT: Memory limit exceeded")
                return False
            
            bars, error = load_vwap_bars_metadata(venue, date)
            if error:
                print(f"    ❌ {error}")
                return False
            
            all_bars[date][venue] = bars
            print(f"    ✅ {venue}: {len(bars):,} bars")
            
            gc.collect()
        
        # Compute clock drift for non-BINANCE venues
        drift_results[date] = {}
        binance_bars = all_bars[date]['BINANCE']
        
        for venue in venues[1:]:  # Skip BINANCE
            print(f"  Computing {venue} drift...")
            
            result, error = compute_clock_drift(binance_bars, all_bars[date][venue], venue)
            if error:
                print(f"    ❌ {error}")
                return False
            
            drift_results[date][venue] = result
            print(f"    ✅ {venue}: median lag = {result['overall_median_lag']:.1f}s")
        
        # Clean up bars for this date
        del all_bars[date]
        gc.collect()
    
    # Step 3: Analyze patterns
    print(f"\n🔍 Step 3: Analyzing lag patterns...")
    
    # Check for systematic offset
    all_median_lags = []
    for date in dates:
        for venue in venues[1:]:
            lag = drift_results[date][venue]['overall_median_lag']
            all_median_lags.append(lag)
    
    lag_std = np.std(all_median_lags)
    lag_mean = np.mean(all_median_lags)
    
    print(f"    Mean lag across all venues/days: {lag_mean:.1f}s")
    print(f"    Std deviation: {lag_std:.1f}s")
    
    # Check for integer multiples (canonicalization artifact)
    integer_lags = [round(lag) for lag in all_median_lags]
    if all(abs(lag - round(lag)) < 0.1 for lag in all_median_lags):
        interpretation = "Likely timestamp normalization issue (integer lags)"
    elif lag_std < 0.5:
        interpretation = "Likely real latency (consistent lags)"
    else:
        interpretation = "Mixed pattern (venue + encoding)"
    
    # Step 4: Output summary
    print(f"\n📊 Summary Table:")
    print("Venue | MedianLag(09-08) | MedianLag(09-09) | MedianLag(09-10) | Unit | TZ | Interpretation")
    print("-" * 100)
    
    for venue in venues[1:]:  # Skip BINANCE
        lags = []
        for date in dates:
            lag = drift_results[date][venue]['overall_median_lag']
            lags.append(f"{lag:.1f}")
        
        lag_str = " | ".join(lags)
        print(f"{venue} | {lag_str} | {reference_schema['unit']} | {reference_schema['timezone']} | {interpretation}")
    
    print(f"\n🎯 Interpretation: {interpretation}")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_temporal_diagnostic()
    
    if success:
        print(f"\n🎉 Temporal diagnostic completed successfully.")
    else:
        print(f"\n❌ Temporal diagnostic failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




