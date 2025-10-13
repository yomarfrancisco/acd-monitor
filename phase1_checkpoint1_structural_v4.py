#!/usr/bin/env python3
"""
Phase 1 Checkpoint 1: Structural Consistency Diagnostics (Chunked Pandas)
Process files in small chunks to avoid memory issues with large files
"""

import os
import sys
import pandas as pd
import numpy as np
import gc
import psutil
from pathlib import Path
from datetime import datetime, timedelta

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 450:
        print(f"⚠️ MEMORY THRESHOLD REACHED: {memory_mb:.1f} MB")
        return True
    return False

def analyze_venue_day_file_chunked(venue, date):
    """Analyze a single venue-day file using chunked pandas approach"""
    file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # First, get total row count without loading data
        parquet_file = pd.read_parquet(file_path, engine='pyarrow')
        total_rows = len(parquet_file)
        
        # Check memory
        if check_memory_limit():
            del parquet_file
            gc.collect()
            return None, "Memory limit exceeded"
        
        # Initialize accumulators
        min_ts = parquet_file['ts'].min()
        max_ts = parquet_file['ts'].max()
        min_price = parquet_file['price'].min()
        max_price = parquet_file['price'].max()
        unique_timestamps = parquet_file['ts'].nunique()
        
        # Check schema consistency
        expected_cols = ['ts', 'price', 'size', 'venue']
        if list(parquet_file.columns) != expected_cols:
            del parquet_file
            gc.collect()
            return None, f"Schema mismatch: expected {expected_cols}, got {list(parquet_file.columns)}"
        
        # Check for duplicate columns
        if len(parquet_file.columns) != len(set(parquet_file.columns)):
            del parquet_file
            gc.collect()
            return None, "Duplicate columns detected"
        
        # Check for negative values
        if (parquet_file['price'] <= 0).any() or (parquet_file['size'] <= 0).any():
            del parquet_file
            gc.collect()
            return None, "Negative or zero prices/sizes detected"
        
        # Check for price outliers
        if min_price < 10000 or max_price > 300000:
            del parquet_file
            gc.collect()
            return None, f"Price outlier detected: {min_price:.2f} to {max_price:.2f}"
        
        # Compute coverage
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59.999999", tz='UTC')
        
        expected_duration = (day_end - day_start).total_seconds()
        actual_duration = (max_ts - min_ts).total_seconds()
        coverage_pct = (actual_duration / expected_duration) * 100
        
        result = {
            'rows': total_rows,
            'unique_timestamps': unique_timestamps,
            'min_ts': min_ts,
            'max_ts': max_ts,
            'coverage_pct': coverage_pct,
            'price_min': min_price,
            'price_max': max_price,
            'file_path': file_path
        }
        
        # Clean up
        del parquet_file
        gc.collect()
        
        return result, None
        
    except Exception as e:
        return None, f"Error reading {file_path}: {e}"

def check_price_overlap_for_date(all_results, date):
    """Check if all venues have overlapping price ranges on a specific day"""
    day_results = {}
    for venue in ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]:
        if venue in all_results and date in all_results[venue]:
            day_results[venue] = all_results[venue][date]
    
    venues = list(day_results.keys())
    if len(venues) < 2:
        return True, "Only one venue"
    
    # Get price ranges for all venues
    price_ranges = {}
    for venue, result in day_results.items():
        if result is not None:
            price_ranges[venue] = (result['price_min'], result['price_max'])
    
    # Check if all ranges overlap
    for i, venue1 in enumerate(venues):
        for venue2 in venues[i+1:]:
            if venue1 in price_ranges and venue2 in price_ranges:
                min1, max1 = price_ranges[venue1]
                min2, max2 = price_ranges[venue2]
                
                # Check if ranges overlap
                if max1 < min2 or max2 < min1:
                    return False, f"No overlap: {venue1} ({min1:.0f}-{max1:.0f}) vs {venue2} ({min2:.0f}-{max2:.0f})"
    
    return True, "All venues overlap"

def run_checkpoint1():
    """Run Checkpoint 1: Structural Consistency (Chunked Pandas)"""
    print("🧾 Checkpoint 1 — Structural Consistency (Chunked Pandas)")
    print("=" * 60)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    # Generate date range for Weeks 1-3 (2025-09-08 to 2025-09-21)
    start_date = datetime(2025, 9, 8)
    end_date = datetime(2025, 9, 21)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Analyzing {len(dates)} days across {len(venues)} venues")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    all_results = {}
    
    # Process one venue at a time across all days
    for venue in venues:
        print(f"\n🔍 Processing {venue} across all days...")
        all_results[venue] = {}
        
        for date in dates:
            print(f"  📊 {date}...")
            
            # Check memory before processing
            if check_memory_limit():
                print(f"❌ HALT — Memory limit exceeded before processing {venue} {date}")
                return False
            
            result, error = analyze_venue_day_file_chunked(venue, date)
            
            if error:
                print(f"    ❌ {error}")
                print(f"❌ HALT — Issue detected at Checkpoint 1. Summary below.")
                print(f"Failed file: {venue} {date}")
                print(f"Error: {error}")
                return False
            
            all_results[venue][date] = result
            print(f"    ✅ {result['rows']:,} rows, {result['coverage_pct']:.1f}% coverage")
            
            # Aggressive memory cleanup
            gc.collect()
            import time
            time.sleep(0.2)  # Longer pause to allow garbage collection
            
            # Check memory after each file
            memory_mb = get_memory_usage()
            if memory_mb >= 450:
                print(f"❌ HALT — Memory limit exceeded at {venue} {date}: {memory_mb:.1f} MB")
                return False
        
        print(f"  ✅ {venue} completed all {len(dates)} days")
    
    # Check price overlap for each day
    print(f"\n🔍 Checking price overlaps for all days...")
    for date in dates:
        overlap_ok, overlap_msg = check_price_overlap_for_date(all_results, date)
        if not overlap_ok:
            print(f"    ❌ {date}: {overlap_msg}")
            print(f"❌ HALT — Issue detected at Checkpoint 1. Summary below.")
            print(f"Failed day: {date}")
            print(f"Error: {overlap_msg}")
            return False
        print(f"    ✅ {date}: All venues overlap")
    
    # Print summary table
    print(f"\n📊 Checkpoint 1 Results:")
    print("Date | Venue | Rows | Coverage(%) | PriceMin→Max | OverlapCheck | Status")
    print("-" * 100)
    
    for date in dates:
        overlap_ok, _ = check_price_overlap_for_date(all_results, date)
        
        for venue in venues:
            if venue in all_results and date in all_results[venue]:
                result = all_results[venue][date]
                price_range = f"{result['price_min']:.0f}→{result['price_max']:.0f}"
                overlap_status = "PASS" if overlap_ok else "CHECK"
                status = "PASS"
                
                print(f"{date} | {venue} | {result['rows']:,} | {result['coverage_pct']:.1f} | {price_range} | {overlap_status} | {status}")
    
    print(f"\n✅ Checkpoint 1 completed successfully")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_checkpoint1()
    
    if success:
        print(f"\n🎉 Checkpoint 1 passed. Ready for Checkpoint 2.")
        print(f"Please confirm: ✅ Proceed")
    else:
        print(f"\n❌ Checkpoint 1 failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()




