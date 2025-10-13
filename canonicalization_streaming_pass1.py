#!/usr/bin/env python3
"""
🧠 Canonicalization Pass-1 (Streaming, Safe, Atomic)
Weeks -4 → 4 (2025-08-04 → 2025-09-28)
"""

import os
import pandas as pd
import gzip
import gc
import psutil
import shutil
from datetime import datetime, timedelta
import tempfile
from collections import deque
import hashlib

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=500, hard_limit=700):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    elif current_mb > soft_limit:
        return True, f"SOFT limit exceeded: {current_mb:.1f} MB > {soft_limit} MB"
    return True, f"OK: {current_mb:.1f} MB"

def create_key_hash(ts_ns, price, size):
    """Create a hash key for deduplication"""
    # Use price and size with limited precision to avoid floating point issues
    price_prec = round(price, 8)
    size_prec = round(size, 8)
    return hash((ts_ns, price_prec, size_prec))

def process_venue_day_streaming(venue, date):
    """Process a single venue-day using streaming approach"""
    print(f"  📊 Processing {venue} {date}...")
    
    # Determine input filename
    if venue == 'COINBASE':
        filename = f"{venue}_{date}_BTCUSD.csv.gz"
    else:
        filename = f"{venue}_{date}_BTCUSDT.csv.gz"
    
    raw_file_path = f"analysis/flatfiles_ticks_v4/raw/{filename}"
    
    if not os.path.exists(raw_file_path):
        return None, f"Raw file not found: {raw_file_path}"
    
    # Create staging directory
    staging_dir = f"data_v6/staging/{venue}/{date}"
    os.makedirs(staging_dir, exist_ok=True)
    
    try:
        # Initialize counters
        raw_rows = 0
        kept_rows = 0
        dups_intra = 0
        dups_cross = 0
        chunk_count = 0
        peak_memory = get_memory_usage()
        
        # LRU set for cross-chunk deduplication (last 50k keys)
        lru_keys = deque(maxlen=50000)
        
        # Process file in chunks
        chunk_size = 100000  # Start with 100k rows
        
        with gzip.open(raw_file_path, 'rt') as f:
            chunk_data = []
            
            for line in f:
                chunk_data.append(line.strip())
                
                if len(chunk_data) >= chunk_size:
                    # Process chunk
                    result = process_chunk(chunk_data, lru_keys, venue, date, chunk_count)
                    if result is None:
                        return None, "Chunk processing failed"
                    
                    chunk_raw, chunk_kept, chunk_intra, chunk_cross = result
                    raw_rows += chunk_raw
                    kept_rows += chunk_kept
                    dups_intra += chunk_intra
                    dups_cross += chunk_cross
                    chunk_count += 1
                    
                    # Check memory and adjust chunk size
                    memory_ok, memory_msg = check_memory_limit()
                    current_memory = get_memory_usage()
                    peak_memory = max(peak_memory, current_memory)
                    
                    if not memory_ok:
                        return None, memory_msg
                    
                    if current_memory > 500:
                        chunk_size = max(50000, chunk_size // 2)
                        print(f"    🔄 Adjusted chunk size to {chunk_size} (memory: {current_memory:.1f} MB)")
                    
                    # Clear chunk data
                    chunk_data = []
                    gc.collect()
            
            # Process final chunk if any
            if chunk_data:
                result = process_chunk(chunk_data, lru_keys, venue, date, chunk_count)
                if result is None:
                    return None, "Final chunk processing failed"
                
                chunk_raw, chunk_kept, chunk_intra, chunk_cross = result
                raw_rows += chunk_raw
                kept_rows += chunk_kept
                dups_intra += chunk_intra
                dups_cross += chunk_cross
                chunk_count += 1
        
        # Merge all chunk files into final canonical file
        final_path = f"{staging_dir}/ticks_canonical.parquet"
        merge_chunks(staging_dir, final_path, chunk_count)
        
        # Perform final validation
        validation_result = validate_canonical_file(final_path, date)
        if not validation_result[0]:
            return None, validation_result[1]
        
        # Atomic move to final location
        final_dir = f"data_v6/views/{venue}/{date}"
        os.makedirs(final_dir, exist_ok=True)
        final_canonical_path = f"{final_dir}/ticks_canonical.parquet"
        
        # Backup existing file if it exists
        if os.path.exists(final_canonical_path):
            backup_dir = f"data_v6/backup/{venue}/{date}"
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = f"{backup_dir}/ticks_canonical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            shutil.move(final_canonical_path, backup_path)
        
        # Move staging file to final location
        shutil.move(final_path, final_canonical_path)
        
        # Clean up staging
        shutil.rmtree(staging_dir)
        
        return {
            'venue': venue,
            'date': date,
            'raw_rows': raw_rows,
            'kept_rows': kept_rows,
            'dups_intra': dups_intra,
            'dups_cross': dups_cross,
            'peak_memory': peak_memory,
            'status': 'OK'
        }, None
        
    except Exception as e:
        # Clean up staging on error
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        return None, f"Processing error: {e}"

def process_chunk(chunk_data, lru_keys, venue, date, chunk_num):
    """Process a single chunk of data"""
    try:
        # Parse chunk data
        lines = [line.split(';') for line in chunk_data if line.strip()]
        if not lines:
            return 0, 0, 0, 0
        
        # Create DataFrame
        df = pd.DataFrame(lines, columns=['time_exchange', 'price', 'base_amount'])
        
        # Convert data types
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['base_amount'] = pd.to_numeric(df['base_amount'], errors='coerce')
        
        raw_rows = len(df)
        
        # Filter out nulls and invalid values
        df = df.dropna()
        df = df[(df['price'] > 0) & (df['base_amount'] > 0)]
        
        # Convert timestamps
        df['ts'] = pd.to_datetime(df['time_exchange'], utc=True, errors='coerce')
        df = df.dropna(subset=['ts'])
        
        # Rename base_amount to size
        df = df.rename(columns={'base_amount': 'size'})
        df = df[['ts', 'price', 'size']].copy()
        df['venue'] = venue
        
        # Intra-chunk deduplication
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['ts', 'price', 'size'])
        dups_intra = initial_rows - len(df)
        
        # Cross-chunk deduplication
        df['ts_ns'] = df['ts'].astype('int64')
        df['key_hash'] = df.apply(lambda row: create_key_hash(row['ts_ns'], row['price'], row['size']), axis=1)
        
        # Remove rows that exist in LRU
        df = df[~df['key_hash'].isin(lru_keys)]
        dups_cross = len(df) - len(df)
        
        # Update LRU with new keys
        for key_hash in df['key_hash']:
            lru_keys.append(key_hash)
        
        # Clean up temporary columns
        df = df.drop(['ts_ns', 'key_hash'], axis=1)
        
        # Save chunk
        chunk_path = f"data_v6/staging/{venue}/{date}/part-{chunk_num:05d}.parquet"
        df.to_parquet(chunk_path, index=False)
        
        return raw_rows, len(df), dups_intra, dups_cross
        
    except Exception as e:
        print(f"    ❌ Chunk {chunk_num} error: {e}")
        return None

def merge_chunks(staging_dir, final_path, chunk_count):
    """Merge all chunk files into final canonical file"""
    if chunk_count == 1:
        # Single chunk, just rename
        chunk_path = f"{staging_dir}/part-00000.parquet"
        os.rename(chunk_path, final_path)
    else:
        # Multiple chunks, merge them
        chunk_files = [f"{staging_dir}/part-{i:05d}.parquet" for i in range(chunk_count)]
        
        # Read and concatenate
        dfs = []
        for chunk_file in chunk_files:
            df = pd.read_parquet(chunk_file)
            dfs.append(df)
        
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.to_parquet(final_path, index=False)
        
        # Clean up chunk files
        for chunk_file in chunk_files:
            os.remove(chunk_file)

def validate_canonical_file(file_path, date):
    """Validate the canonical file"""
    try:
        # Read metadata only
        df = pd.read_parquet(file_path)
        
        # Check row count
        if len(df) < 50000:
            return False, f"Row count too low: {len(df):,} (minimum: 50,000)"
        
        # Check timestamp range
        ts_min = df['ts'].min()
        ts_max = df['ts'].max()
        
        expected_date = datetime.strptime(date, "%Y%m%d").date()
        if ts_min.date() != expected_date or ts_max.date() != expected_date:
            return False, f"Timestamp range mismatch: {ts_min.date()} - {ts_max.date()} (expected: {expected_date})"
        
        # Check price range
        price_min = df['price'].min()
        price_max = df['price'].max()
        
        if price_min < 50000 or price_max > 200000:
            return False, f"Price range outside bounds: ${price_min:,.2f} - ${price_max:,.2f} (expected: $50k-$200k)"
        
        # Check monotonicity
        if not df['ts'].is_monotonic_increasing:
            return False, "Timestamps not monotonic"
        
        return True, "Validation passed"
        
    except Exception as e:
        return False, f"Validation error: {e}"

def process_day(date):
    """Process a single day for all venues"""
    print(f"\n📅 Day Summary ({date[:4]}-{date[4:6]}-{date[6:8]}):")
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    results = []
    successful_venues = 0
    
    for venue in venues:
        result, error = process_venue_day_streaming(venue, date)
        if result:
            print(f"  ✅ {venue}: raw_rows={result['raw_rows']:,}, kept_rows={result['kept_rows']:,}, "
                  f"dups_intra={result['dups_intra']:,}, dups_cross={result['dups_cross']:,}, "
                  f"peak_MB={result['peak_memory']:.1f}, status={result['status']}")
            results.append(result)
            successful_venues += 1
        else:
            print(f"  ❌ {venue}: {error}")
            results.append({
                'venue': venue,
                'date': date,
                'status': 'FAIL',
                'error': error
            })
    
    # Determine day status
    if successful_venues == 4:
        day_status = "FULL"
    elif successful_venues > 0:
        day_status = "PARTIAL"
    else:
        day_status = "FAIL"
    
    print(f"Day status: {day_status} ({successful_venues}/4 venues)")
    
    return results, day_status

def main():
    """Main function"""
    print("🧠 Canonicalization Pass-1 (Streaming, Safe, Atomic)")
    print("=" * 80)
    print("Weeks -4 → 4 (2025-08-04 → 2025-09-28)")
    
    # Create output directories
    os.makedirs('data_v6/views', exist_ok=True)
    os.makedirs('data_v6/backup', exist_ok=True)
    os.makedirs('data_v6/staging', exist_ok=True)
    
    # Generate all dates from 2025-08-04 to 2025-09-28
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 9, 28)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Total dates to process: {len(dates)}")
    print(f"🎯 Memory limits: Soft 500MB, Hard 700MB")
    print(f"📊 Row count floor: 50,000 per venue-day")
    print(f"🔄 Streaming: 100k row chunks with adaptive sizing")
    
    # Process each day
    all_results = []
    week_summary = []
    current_week = None
    week_results = []
    
    for i, date in enumerate(dates):
        # Check if we're starting a new week
        date_obj = datetime.strptime(date, "%Y%m%d")
        week_start = date_obj - timedelta(days=date_obj.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        if current_week != week_key:
            if current_week is not None:
                # Process previous week
                week_summary.append({
                    'week': current_week,
                    'results': week_results
                })
            current_week = week_key
            week_results = []
        
        print(f"\n{'='*60}")
        print(f"Processing day {i+1}/{len(dates)}: {date}")
        
        day_results, day_status = process_day(date)
        all_results.extend(day_results)
        week_results.extend(day_results)
        
        # Check memory usage
        memory_mb = get_memory_usage()
        print(f"💾 Memory usage: {memory_mb:.1f} MB")
        
        if memory_mb > 700:
            print(f"❌ HALT: Hard memory limit exceeded ({memory_mb:.1f} MB > 700 MB)")
            break
    
    # Process final week
    if current_week is not None:
        week_summary.append({
            'week': current_week,
            'results': week_results
        })
    
    # Print final summary
    print(f"\n{'='*80}")
    print(f"📊 CANONICALIZATION SUMMARY")
    print(f"{'='*80}")
    
    total_venue_days = len(all_results)
    successful_venue_days = len([r for r in all_results if r.get('status') == 'OK'])
    
    print(f"Total venue-days processed: {total_venue_days}")
    print(f"Successful canonicalizations: {successful_venue_days}")
    print(f"Success rate: {successful_venue_days/total_venue_days*100:.1f}%")
    
    # Print week-by-week summary
    print(f"\n📅 Week-by-Week Summary:")
    print(f"{'Week':<15} {'Days':<6} {'Success':<8} {'Rate':<8}")
    print("-" * 40)
    
    for week_data in week_summary:
        week_results = week_data['results']
        week_success = len([r for r in week_results if r.get('status') == 'OK'])
        week_total = len(week_results)
        week_rate = week_success/week_total*100 if week_total > 0 else 0
        
        print(f"{week_data['week']:<15} {week_total:<6} {week_success:<8} {week_rate:<8.1f}%")
    
    print(f"\n✅ Canonicalization streaming pass 1 completed!")

if __name__ == "__main__":
    main()




