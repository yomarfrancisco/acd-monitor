#!/usr/bin/env python3
"""
Process a single venue×date combination for Week 2 canonicalization
"""

import os
import sys
import pandas as pd
import gzip
import psutil
from pathlib import Path
import glob
import gc

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def process_venue_date(venue, date):
    """Process a single venue×date combination"""
    print(f"Processing {venue} {date}...")
    print(f"Initial memory: {get_memory_usage():.1f} MB")
    
    # Find raw file
    pattern = f"analysis/flatfiles_ticks_v4/raw/*{venue}*{date}*.csv.gz"
    files = glob.glob(pattern)
    
    if len(files) == 0:
        print(f"ERROR: No files found for {venue} {date}")
        return
    elif len(files) > 1:
        print(f"ERROR: Multiple files found for {venue} {date}: {files}")
        return
    
    raw_file = files[0]
    print(f"Raw file: {raw_file}")
    
    # Check if canonical file already exists
    canonical_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    if os.path.exists(canonical_path):
        try:
            existing_df = pd.read_parquet(canonical_path)
            if len(existing_df) > 0:
                print(f"SKIPPED_OK - {len(existing_df):,} rows")
                return
        except Exception as e:
            print(f"Warning: Could not validate existing file: {e}")
    
    # Process file in small chunks
    chunk_size = 5000  # Very small chunks
    total_raw_rows = 0
    canonical_data = []
    
    print(f"Processing in chunks of {chunk_size:,} rows...")
    
    try:
        for chunk_num, chunk in enumerate(pd.read_csv(raw_file, sep=';', compression='gzip', chunksize=chunk_size)):
            total_raw_rows += len(chunk)
            
            # Convert to canonical format
            canonical_chunk = pd.DataFrame({
                'ts': pd.to_datetime(chunk['time_exchange'], utc=True),
                'price': pd.to_numeric(chunk['price'], errors='coerce'),
                'size': pd.to_numeric(chunk['base_amount'], errors='coerce'),
                'venue': venue
            })
            
            # Filter valid data
            canonical_chunk = canonical_chunk.dropna()
            canonical_chunk = canonical_chunk[
                (canonical_chunk['price'] > 0) & 
                (canonical_chunk['size'] > 0) &
                (canonical_chunk['price'] < 2000000)
            ]
            
            if len(canonical_chunk) > 0:
                canonical_data.append(canonical_chunk)
            
            # Clear chunk from memory
            del chunk
            del canonical_chunk
            gc.collect()
            
            # Check memory
            memory_mb = get_memory_usage()
            if memory_mb > 400:
                print(f"Memory warning: {memory_mb:.1f} MB (chunk {chunk_num + 1})")
            
            if memory_mb > 500:
                print(f"ERROR: Memory limit exceeded ({memory_mb:.1f} MB)")
                return
        
        print(f"Raw rows: {total_raw_rows:,}")
        
        # Combine all chunks
        if not canonical_data:
            print("ERROR: No valid data found")
            return
        
        print(f"Combining {len(canonical_data)} chunks...")
        df_canonical = pd.concat(canonical_data, ignore_index=True)
        
        # Clear canonical_data from memory
        del canonical_data
        gc.collect()
        
        print(f"Combined canonical rows: {len(df_canonical):,}")
        
        # Sort and deduplicate
        df_canonical = df_canonical.sort_values('ts')
        initial_rows = len(df_canonical)
        df_canonical = df_canonical.drop_duplicates(subset=['ts', 'price', 'size'], keep='first')
        duplicates_removed = initial_rows - len(df_canonical)
        
        print(f"Final canonical rows: {len(df_canonical):,} (removed {duplicates_removed:,} duplicates)")
        
        # Create output directory
        output_dir = Path(f"data_v6/views/{venue}/{date}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write parquet file
        try:
            df_canonical.to_parquet(canonical_path, compression='snappy', index=False)
            print(f"Wrote: {canonical_path}")
        except Exception as e:
            print(f"ERROR: Error writing parquet: {e}")
            return
        
        print(f"Final memory: {get_memory_usage():.1f} MB")
        print(f"SUCCESS: {venue} {date} - {len(df_canonical):,} rows")
        
    except Exception as e:
        print(f"ERROR: Error processing file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python process_single_venue.py <venue> <date>")
        sys.exit(1)
    
    venue = sys.argv[1]
    date = sys.argv[2]
    process_venue_date(venue, date)




