#!/usr/bin/env python3
"""
Week 2 Canonicalization - Days 1-2 (2025-09-08, 2025-09-09)
Convert raw CSV files to canonical parquet format
"""

import os
import sys
import pandas as pd
import gzip
import psutil
from pathlib import Path
import glob
from datetime import datetime

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def find_raw_file(venue, date):
    """Find the single raw file for venue×date"""
    pattern = f"analysis/flatfiles_ticks_v4/raw/*{venue}*{date}*.csv.gz"
    files = glob.glob(pattern)
    
    if len(files) == 0:
        return None, f"No files found for {venue} {date}"
    elif len(files) > 1:
        return None, f"Multiple files found for {venue} {date}: {files}"
    else:
        return files[0], None

def load_raw_csv(file_path):
    """Load raw CSV file and return DataFrame in chunks"""
    try:
        # Read the CSV file in chunks to manage memory
        chunk_size = 100000  # Process 100k rows at a time
        chunks = []
        
        for chunk in pd.read_csv(file_path, sep=';', compression='gzip', chunksize=chunk_size):
            # Check if we have the expected columns
            expected_cols = ['time_exchange', 'time_coinapi', 'guid', 'price', 'base_amount', 'taker_side']
            missing_cols = [col for col in expected_cols if col not in chunk.columns]
            
            if missing_cols:
                return None, f"Missing columns: {missing_cols}"
            
            chunks.append(chunk)
            
            # Check memory after each chunk
            memory_mb = get_memory_usage()
            if memory_mb > 300:  # Soft limit
                print(f"    Memory warning: {memory_mb:.1f} MB")
            
            if memory_mb > 350:  # Hard limit
                return None, f"HALT: Memory limit exceeded during loading ({memory_mb:.1f} MB)"
        
        # Combine chunks
        df = pd.concat(chunks, ignore_index=True)
        return df, None
        
    except Exception as e:
        return None, f"Error loading CSV: {e}"

def convert_to_canonical(df, venue):
    """Convert raw DataFrame to canonical format"""
    try:
        # Create canonical DataFrame with only needed columns
        canonical_df = pd.DataFrame({
            'ts': pd.to_datetime(df['time_exchange'], utc=True),
            'price': pd.to_numeric(df['price'], errors='coerce'),
            'size': pd.to_numeric(df['base_amount'], errors='coerce'),
            'venue': venue
        })
        
        # Remove rows with invalid data
        canonical_df = canonical_df.dropna()
        
        # Filter out invalid prices/sizes
        canonical_df = canonical_df[
            (canonical_df['price'] > 0) & 
            (canonical_df['size'] > 0) &
            (canonical_df['price'] < 2000000)  # Reasonable BTC price cap
        ]
        
        return canonical_df, None
        
    except Exception as e:
        return None, f"Error converting to canonical: {e}"

def deduplicate_canonical(df):
    """Remove duplicates using Week 1 rule"""
    try:
        # Sort by timestamp
        df = df.sort_values('ts')
        
        # Count duplicates before removal
        initial_rows = len(df)
        
        # Remove duplicates keeping first occurrence
        df_deduped = df.drop_duplicates(subset=['ts', 'price', 'size'], keep='first')
        
        duplicates_removed = initial_rows - len(df_deduped)
        
        return df_deduped, duplicates_removed, None
        
    except Exception as e:
        return None, 0, f"Error deduplicating: {e}"

def process_venue_date(venue, date):
    """Process a single venue×date combination"""
    print(f"  Processing {venue} {date}...")
    
    # Check memory
    memory_mb = get_memory_usage()
    if memory_mb > 350:
        return None, f"HALT: Memory limit exceeded ({memory_mb:.1f} MB)"
    
    # Find raw file
    raw_file, error = find_raw_file(venue, date)
    if error:
        return None, f"HALT: {error}"
    
    print(f"    Raw file: {raw_file}")
    
    # Check if canonical file already exists
    canonical_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    if os.path.exists(canonical_path):
        try:
            existing_df = pd.read_parquet(canonical_path)
            if len(existing_df) > 0:
                # Check if timestamps are within the day
                day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
                day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
                
                if (existing_df['ts'].min() >= day_start and 
                    existing_df['ts'].max() <= day_end and
                    list(existing_df.columns) == ['ts', 'price', 'size', 'venue']):
                    return {
                        'venue': venue,
                        'date': date,
                        'raw_rows': 0,
                        'duplicates_removed': 0,
                        'canon_rows': len(existing_df),
                        'ts_start': existing_df['ts'].min(),
                        'ts_end': existing_df['ts'].max(),
                        'price_min': existing_df['price'].min(),
                        'price_max': existing_df['price'].max(),
                        'action': 'SKIPPED_OK',
                        'memory_mb': memory_mb
                    }, None
        except Exception as e:
            print(f"    Warning: Could not validate existing file: {e}")
    
    # Load raw CSV
    df_raw, error = load_raw_csv(raw_file)
    if error:
        return None, f"HALT: {error}"
    
    raw_rows = len(df_raw)
    print(f"    Raw rows: {raw_rows:,}")
    
    # Convert to canonical
    df_canonical, error = convert_to_canonical(df_raw, venue)
    if error:
        return None, f"HALT: {error}"
    
    # Check memory after conversion
    memory_mb = get_memory_usage()
    if memory_mb > 350:
        return None, f"HALT: Memory limit exceeded after conversion ({memory_mb:.1f} MB)"
    
    # Deduplicate
    df_final, duplicates_removed, error = deduplicate_canonical(df_canonical)
    if error:
        return None, f"HALT: {error}"
    
    canon_rows = len(df_final)
    print(f"    Canonical rows: {canon_rows:,} (removed {duplicates_removed:,} duplicates)")
    
    # Validate timestamps are within the day
    day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
    day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
    
    if df_final['ts'].min() < day_start or df_final['ts'].max() > day_end:
        return None, f"HALT: Timestamps out of day range"
    
    # Create output directory
    output_dir = Path(f"data_v6/views/{venue}/{date}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write parquet file
    try:
        df_final.to_parquet(canonical_path, compression='snappy', index=False)
        print(f"    Wrote: {canonical_path}")
    except Exception as e:
        return None, f"HALT: Error writing parquet: {e}"
    
    # Final memory check
    memory_mb = get_memory_usage()
    
    return {
        'venue': venue,
        'date': date,
        'raw_rows': raw_rows,
        'duplicates_removed': duplicates_removed,
        'canon_rows': canon_rows,
        'ts_start': df_final['ts'].min(),
        'ts_end': df_final['ts'].max(),
        'price_min': df_final['price'].min(),
        'price_max': df_final['price'].max(),
        'action': 'WROTE',
        'memory_mb': memory_mb
    }, None

def main():
    """Main canonicalization function"""
    print("🚀 Starting Week 2 Canonicalization - Days 1-2")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    dates = ['20250908', '20250909']
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    results = []
    
    for date in dates:
        print(f"\n📅 Processing date: {date}")
        
        for venue in venues:
            result, error = process_venue_date(venue, date)
            
            if error:
                print(f"❌ {error}")
                return
            
            results.append(result)
            print(f"    ✅ {result['action']} - {result['canon_rows']:,} rows")
    
    # Print results table
    print(f"\n📊 Canonicalization Results:")
    print("=" * 120)
    print(f"{'Date':<12} {'Venue':<10} {'Raw Rows':<10} {'Dups Removed':<12} {'Canon Rows':<10} {'TS Range':<35} {'Price Range':<20} {'Action':<12}")
    print("-" * 120)
    
    for result in results:
        ts_range = f"{result['ts_start'].strftime('%H:%M:%S')} → {result['ts_end'].strftime('%H:%M:%S')}"
        price_range = f"{result['price_min']:.0f} → {result['price_max']:.0f}"
        
        print(f"{result['date']:<12} {result['venue']:<10} {result['raw_rows']:<10} {result['duplicates_removed']:<12} {result['canon_rows']:<10} {ts_range:<35} {price_range:<20} {result['action']:<12}")
    
    # Daily summaries
    for date in dates:
        day_results = [r for r in results if r['date'] == date]
        total_raw = sum(r['raw_rows'] for r in day_results)
        total_canon = sum(r['canon_rows'] for r in day_results)
        total_dups = sum(r['duplicates_removed'] for r in day_results)
        peak_memory = max(r['memory_mb'] for r in day_results)
        
        print(f"\nDay summary ({date}): total raw rows={total_raw:,}, total canonical rows={total_canon:,}, total dups removed={total_dups:,}, peak RSS memory={peak_memory:.1f}MB")
    
    print(f"\n🧠 Final memory: {get_memory_usage():.1f} MB")
    print("✅ Week 2 Days 1-2 canonicalization complete. Stopping as requested.")

if __name__ == "__main__":
    main()
