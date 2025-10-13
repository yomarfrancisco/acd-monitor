#!/usr/bin/env python3
"""
Week-2 Validate Existing: Day 1 (2025-09-08) - Memory Efficient
Validate existing raw data in chunks to stay within memory limits
"""

import os
import sys
import pandas as pd
import gzip
import hashlib
import psutil
from pathlib import Path
import shutil
from datetime import datetime

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def validate_venue_data_chunked(venue, date, raw_file):
    """Validate venue data in chunks to manage memory"""
    print(f"  🔍 Validating {venue}...")
    
    try:
        # 1. Readable & non-empty
        if not os.path.exists(raw_file):
            return False, f"File not found: {raw_file}"
        
        if os.path.getsize(raw_file) == 0:
            return False, f"Empty file: {raw_file}"
        
        # Process in chunks
        chunk_size = 50000  # Smaller chunks
        all_chunks = []
        total_rows = 0
        
        print(f"    📊 Processing in chunks of {chunk_size:,} rows...")
        
        try:
            for chunk_num, chunk in enumerate(pd.read_csv(raw_file, sep=';', compression='gzip', chunksize=chunk_size)):
                total_rows += len(chunk)
                
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
                    (canonical_chunk['size'] > 0)
                ]
                
                if len(canonical_chunk) > 0:
                    all_chunks.append(canonical_chunk)
                
                # Memory check
                memory_mb = get_memory_usage()
                if memory_mb > 400:
                    print(f"    ⚠️  Memory warning: {memory_mb:.1f} MB (chunk {chunk_num + 1})")
                
                if memory_mb > 500:
                    return False, f"HALT: Memory limit exceeded ({memory_mb:.1f} MB)"
                
        except Exception as e:
            return False, f"Error reading {raw_file}: {e}"
        
        if not all_chunks:
            return False, "No valid data after processing chunks"
        
        # Combine all chunks
        print(f"    📊 Combining {len(all_chunks)} chunks...")
        canonical_df = pd.concat(all_chunks, ignore_index=True)
        
        # Clear chunks from memory
        del all_chunks
        
        # 2. Schema check
        required_cols = ['ts', 'price', 'size', 'venue']
        missing_cols = [col for col in required_cols if col not in canonical_df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # 3. Timestamp bounds check
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59.999999", tz='UTC')
        
        ts_min = canonical_df['ts'].min()
        ts_max = canonical_df['ts'].max()
        
        if ts_min < day_start or ts_max > day_end:
            return False, f"Timestamps out of bounds: {ts_min} to {ts_max}"
        
        # 4. De-duplication
        print(f"    📊 Deduplicating...")
        initial_rows = len(canonical_df)
        canonical_df = canonical_df.drop_duplicates(subset=['ts', 'price', 'size'], keep='first')
        duplicates_removed = initial_rows - len(canonical_df)
        
        # 5. Basic sanity checks
        price_min = canonical_df['price'].min()
        price_max = canonical_df['price'].max()
        
        if price_min < 80000 or price_max > 180000:
            return False, f"Price range out of bounds: {price_min:.2f} to {price_max:.2f}"
        
        if canonical_df['size'].min() <= 0:
            return False, "Negative or zero sizes found"
        
        # 6. Row count check
        final_rows = len(canonical_df)
        if final_rows < 50000:
            return False, f"Too few rows: {final_rows:,} (minimum 50,000)"
        
        # 7. Hash and manifest
        file_hash = compute_file_hash(raw_file)
        file_size = os.path.getsize(raw_file)
        
        return True, {
            'raw_file': raw_file,
            'raw_mb': file_size / 1024 / 1024,
            'rows': final_rows,
            'duplicates_removed': duplicates_removed,
            'price_min': price_min,
            'price_max': price_max,
            'ts_start': ts_min,
            'ts_end': ts_max,
            'file_hash': file_hash,
            'canonical_df': canonical_df
        }
        
    except Exception as e:
        return False, f"Validation error: {e}"

def process_day_20250908():
    """Process Day 1: 2025-09-08 using existing raw data"""
    print("🚀 Week-2 Validate Existing: Day 1 (2025-09-08) - Memory Efficient")
    print("=" * 70)
    
    date = "20250908"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Stage 1: Find existing raw files
    print(f"\n📁 Stage 1: Finding existing raw files...")
    raw_files = {}
    
    for venue in venues:
        pattern = f"analysis/flatfiles_ticks_v4/raw/{venue}_{date}_BTCUSDT.csv.gz"
        
        if os.path.exists(pattern):
            raw_files[venue] = pattern
            print(f"  ✅ Found {venue}: {pattern}")
        else:
            print(f"  ❌ Missing {venue}: {pattern}")
            return False, f"Missing raw file for {venue}"
    
    # Stage 2: Validate all venues
    print(f"\n🔍 Stage 2: Validating all venues...")
    validation_results = {}
    
    for venue in venues:
        success, result = validate_venue_data_chunked(venue, date, raw_files[venue])
        
        if not success:
            print(f"  ❌ {venue} validation failed: {result}")
            return False, f"{venue} validation failed: {result}"
        
        validation_results[venue] = result
        print(f"  ✅ {venue} validation passed")
        
        # Clear memory between venues
        import gc
        gc.collect()
        print(f"    🧠 Memory after {venue}: {get_memory_usage():.1f} MB")
    
    # Stage 3: All venues passed - create canonical files
    print(f"\n📝 Stage 3: Creating canonical files...")
    
    # Backup existing canonical files
    for venue in venues:
        canonical_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
        if os.path.exists(canonical_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data_v6/_backup/{venue}/{date}/ticks_canonical_{timestamp}.parquet"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.move(canonical_path, backup_path)
            print(f"  📦 Backed up {venue} to {backup_path}")
    
    # Write canonical files
    for venue in venues:
        canonical_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
        os.makedirs(os.path.dirname(canonical_path), exist_ok=True)
        
        canonical_df = validation_results[venue]['canonical_df']
        canonical_df.to_parquet(canonical_path, compression='snappy', index=False)
        print(f"  ✅ Wrote {venue} canonical: {len(canonical_df):,} rows")
        
        # Clear dataframe from memory
        del canonical_df
        import gc
        gc.collect()
    
    # Final results
    print(f"\n📊 Day 1 Results:")
    print("Date | Venue | RawFiles | RawMB | Rows | DupsRemoved | PriceMin→Max | tsStart→tsEnd | Status")
    print("-" * 120)
    
    for venue in venues:
        result = validation_results[venue]
        price_range = f"{result['price_min']:.0f}→{result['price_max']:.0f}"
        ts_range = f"{result['ts_start'].strftime('%H:%M:%S')}→{result['ts_end'].strftime('%H:%M:%S')}"
        
        print(f"{date} | {venue} | 1 | {result['raw_mb']:.1f} | {result['rows']:,} | {result['duplicates_removed']:,} | {price_range} | {ts_range} | PASS")
    
    peak_memory = get_memory_usage()
    print(f"\n✅ Day verdict = PASS (replaced)")
    print(f"🧠 Peak RSS: {peak_memory:.1f} MB")
    print(f"📋 No HALT codes")
    
    return True, "Day 1 completed successfully"

def main():
    """Main function"""
    success, message = process_day_20250908()
    
    if success:
        print(f"\n🎉 {message}")
    else:
        print(f"\n❌ {message}")
        sys.exit(1)

if __name__ == "__main__":
    main()




