#!/usr/bin/env python3
"""
Ultra-Light Timestamp Alignment Diagnostic
Determine if ~2-3s lag is systematic clock offsets or canonicalization artifacts
Reads minimal data (< 10 rows per file) to stay under 50MB memory
"""

import os
import sys
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from datetime import datetime

def get_memory_usage():
    """Get current memory usage in MB"""
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def step1_metadata_only():
    """Step 1: List metadata only (no data read)"""
    print("🔍 Step 1: Metadata inspection (no data read)")
    print("=" * 50)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    date = "20250908"
    
    metadata_results = {}
    
    for venue in venues:
        file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
        
        if not os.path.exists(file_path):
            print(f"❌ {venue}: File not found")
            continue
        
        try:
            f = pq.ParquetFile(file_path)
            meta = f.metadata
            
            # Get timestamp column metadata
            ts_physical_type = meta.row_group(0).column(0).physical_type
            created_by = meta.created_by
            
            metadata_results[venue] = {
                'physical_type': ts_physical_type,
                'created_by': created_by,
                'num_rows': meta.num_rows,
                'num_row_groups': meta.num_row_groups
            }
            
            print(f"{venue}: {ts_physical_type}, created_by={created_by}, rows={meta.num_rows:,}")
            
        except Exception as e:
            print(f"❌ {venue}: Error reading metadata - {e}")
            return None
    
    return metadata_results

def step2_peek_timestamps():
    """Step 2: Peek first and last 3 timestamps only"""
    print(f"\n🔍 Step 2: Peek first and last timestamps")
    print("=" * 50)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    date = "20250908"
    
    timestamp_results = {}
    
    for venue in venues:
        file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
        
        if not os.path.exists(file_path):
            print(f"❌ {venue}: File not found")
            continue
        
        try:
            # Read first 3 timestamps using row group approach
            f = pq.ParquetFile(file_path)
            first_rg = f.read_row_group(0, columns=["ts"]).to_pandas()
            df_head = first_rg.head(3)
            
            # Read last 3 timestamps
            # Get total rows first
            total_rows = f.metadata.num_rows
            num_row_groups = f.metadata.num_row_groups
            
            if num_row_groups > 1:
                # Read last row group
                last_rg = f.read_row_group(num_row_groups - 1, columns=["ts"]).to_pandas()
                df_tail = last_rg.tail(3)
            else:
                df_tail = first_rg.tail(3)
            
            first_ts = df_head["ts"].iloc[0]
            last_ts = df_tail["ts"].iloc[-1]
            
            timestamp_results[venue] = {
                'first_ts': first_ts,
                'last_ts': last_ts,
                'first_ts_str': str(first_ts),
                'last_ts_str': str(last_ts)
            }
            
            print(f"{venue}:")
            print(f"  First: {first_ts} ({str(first_ts)})")
            print(f"  Last:  {last_ts} ({str(last_ts)})")
            
        except Exception as e:
            print(f"❌ {venue}: Error reading timestamps - {e}")
            return None
    
    return timestamp_results

def step3_compare_epoch_ranges(timestamp_results):
    """Step 3: Compare raw epoch ranges across venues"""
    print(f"\n🔍 Step 3: Compare epoch ranges")
    print("=" * 50)
    
    if not timestamp_results or 'BINANCE' not in timestamp_results:
        print("❌ No BINANCE data for comparison")
        return None
    
    binance_first = timestamp_results['BINANCE']['first_ts']
    binance_last = timestamp_results['BINANCE']['last_ts']
    
    print(f"BINANCE reference:")
    print(f"  First: {binance_first}")
    print(f"  Last:  {binance_last}")
    
    offsets = {}
    
    for venue in ["COINBASE", "BYBITSPOT", "BITGET"]:
        if venue not in timestamp_results:
            continue
        
        venue_first = timestamp_results[venue]['first_ts']
        venue_last = timestamp_results[venue]['last_ts']
        
        # Calculate offset (venue - BINANCE)
        first_offset = venue_first - binance_first
        last_offset = venue_last - binance_last
        
        offsets[venue] = {
            'first_offset': first_offset,
            'last_offset': last_offset,
            'first_offset_seconds': first_offset.total_seconds() if hasattr(first_offset, 'total_seconds') else first_offset,
            'last_offset_seconds': last_offset.total_seconds() if hasattr(last_offset, 'total_seconds') else last_offset
        }
        
        print(f"{venue}:")
        print(f"  First offset: {first_offset} ({first_offset.total_seconds():.1f}s)" if hasattr(first_offset, 'total_seconds') else f"  First offset: {first_offset}")
        print(f"  Last offset:  {last_offset} ({last_offset.total_seconds():.1f}s)" if hasattr(last_offset, 'total_seconds') else f"  Last offset:  {last_offset}")
    
    return offsets

def step4_sanity_check():
    """Step 4: Optional sanity check (minimal data load)"""
    print(f"\n🔍 Step 4: Sanity check - earliest records")
    print("=" * 50)
    
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    date = "20250908"
    
    earliest_records = {}
    
    for venue in venues:
        file_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
        
        if not os.path.exists(file_path):
            print(f"❌ {venue}: File not found")
            continue
        
        try:
            # Read just the first row group's timestamps
            f = pq.ParquetFile(file_path)
            first_rg = f.read_row_group(0, columns=["ts"]).to_pandas()
            tmin = first_rg["ts"].min()
            
            earliest_records[venue] = tmin
            print(f"{venue}: {tmin}")
            
        except Exception as e:
            print(f"❌ {venue}: Error reading first row group - {e}")
            return None
    
    return earliest_records

def interpret_results(offsets):
    """Interpret the results and determine likely cause"""
    print(f"\n🧮 Interpretation")
    print("=" * 50)
    
    if not offsets:
        print("❌ No offset data to interpret")
        return
    
    # Analyze patterns
    first_offsets = [offsets[venue]['first_offset_seconds'] for venue in offsets.keys()]
    last_offsets = [offsets[venue]['last_offset_seconds'] for venue in offsets.keys()]
    
    print(f"First timestamp offsets (seconds): {[f'{o:.1f}' for o in first_offsets]}")
    print(f"Last timestamp offsets (seconds):  {[f'{o:.1f}' for o in last_offsets]}")
    
    # Check for patterns
    all_offsets = first_offsets + last_offsets
    mean_offset = np.mean(all_offsets)
    std_offset = np.std(all_offsets)
    
    print(f"Mean offset: {mean_offset:.1f}s")
    print(f"Std deviation: {std_offset:.1f}s")
    
    # Pattern detection
    if all(abs(o - round(o)) < 0.1 for o in all_offsets):
        if abs(mean_offset) < 5:
            interpretation = "All offsets ~ -2–3s → Venue clock drift (real latency)"
            next_step = "Accept as feature; model later"
        else:
            interpretation = "Integer offsets → Parquet rounding / merge artifact"
            next_step = "Inspect canonical merge logic"
    elif std_offset < 1.0:
        if abs(mean_offset) < 5:
            interpretation = "Consistent small offsets → Venue clock drift (real latency)"
            next_step = "Accept as feature; model later"
        else:
            interpretation = "Large consistent offsets → Unit mismatch (ms/μs vs s)"
            next_step = "Fix canonicalization"
    else:
        interpretation = "Variable offsets → Mixed pattern (venue + encoding)"
        next_step = "Investigate per-venue normalization step"
    
    print(f"\n🎯 Interpretation: {interpretation}")
    print(f"📋 Next Step: {next_step}")
    
    return interpretation, next_step

def main():
    """Main function"""
    print("⚙️ Ultra-Light Timestamp Alignment Diagnostic")
    print("=" * 60)
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Step 1: Metadata only
    metadata_results = step1_metadata_only()
    if metadata_results is None:
        print("❌ Step 1 failed")
        return
    
    # Step 2: Peek timestamps
    timestamp_results = step2_peek_timestamps()
    if timestamp_results is None:
        print("❌ Step 2 failed")
        return
    
    # Step 3: Compare epoch ranges
    offsets = step3_compare_epoch_ranges(timestamp_results)
    if offsets is None:
        print("❌ Step 3 failed")
        return
    
    # Step 4: Sanity check
    earliest_records = step4_sanity_check()
    if earliest_records is None:
        print("❌ Step 4 failed")
        return
    
    # Interpret results
    interpretation, next_step = interpret_results(offsets)
    
    print(f"\n✅ Diagnostic completed successfully")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")

if __name__ == "__main__":
    main()
