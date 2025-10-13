#!/usr/bin/env python3
"""
Week-3 Re-download: Day 7 (2025-09-21) - Exact Symbol Match Filtering
Follow the exact Week 1 download methodology with precise symbol matching
"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import gzip
import hashlib
import psutil
from pathlib import Path
import shutil
from datetime import datetime
import re
import time

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    return os.environ.get('COINAPI_KEY', '7f036b38-38d6-4ed6-9fce-00a06280a0f6')

def list_coinapi_objects_with_retry(venue, date, max_retries=4):
    """List objects with exponential backoff retry logic"""
    list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/'
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key(),
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = 0.5 * (2 ** (attempt - 1))  # 0.5s, 1s, 2s, 4s
                print(f"    ⚠️  Retry {attempt}/{max_retries-1} after {delay}s delay...")
                time.sleep(delay)
            
            response = requests.get(list_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.status_code, response.text
            elif response.status_code >= 500 and attempt < max_retries - 1:
                print(f"    ⚠️  Server error {response.status_code}, retrying...")
                continue
            else:
                return response.status_code, response.text
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    ⚠️  Exception: {e}, retrying...")
                continue
            return None, str(e)
    
    return 500, "Max retries exceeded"

def find_exact_symbol_match(venue, date, expected_symbol):
    """Find exact symbol match using precise filtering"""
    print(f"  🔍 Finding exact {expected_symbol} match for {venue}...")
    
    status_code, xml_content = list_coinapi_objects_with_retry(venue, date)
    if status_code != 200:
        return None, f"Failed to list objects: {status_code}"
    
    try:
        root = ET.fromstring(xml_content)
        
        # Get all candidate keys
        all_objects = []
        for content in root.findall('.//Contents'):
            key = content.find('Key').text
            size = int(content.find('Size').text)
            all_objects.append((key, size))
        
        print(f"    📋 Found {len(all_objects)} total objects")
        
        # Show candidate keys for audit
        print(f"    📋 Candidate keys for {venue}:")
        for i, (key, size) in enumerate(all_objects[:10]):  # Show first 10
            print(f"      {i+1}. {os.path.basename(key)} ({size:,} bytes)")
        if len(all_objects) > 10:
            print(f"      ... and {len(all_objects) - 10} more")
        
        # Apply exact-match filters
        exact_matches = []
        
        for key, size in all_objects:
            key_upper = key.upper()
            
            # Filter 1: Symbol suffix must be exactly correct
            if expected_symbol == 'BTCUSDT':
                if not key_upper.endswith('+S-BTCUSDT.CSV.GZ'):
                    continue
            elif expected_symbol == 'BTCUSD':
                if not key_upper.endswith('+S-BTC__002DUSD.CSV.GZ'):
                    continue
            else:
                continue
            
            # Filter 2: Spot class token must be present
            spot_patterns = {
                'BINANCE': '+SC-BINANCE_SPOT_BTC_USDT+',
                'COINBASE': '+SC-COINBASE_SPOT_BTC_USD+',
                'BYBITSPOT': '+SC-BYBITSPOT_SPOT_BTC_USDT+',
                'BITGET': '+SC-BITGET_SPOT_BTC_USDT+'
            }
            
            if spot_patterns[venue] not in key_upper:
                continue
            
            # Filter 3: Reject extra prefixes (PUMP, WBTC, LBTC, etc.)
            # Check if the symbol segment contains unwanted prefixes
            symbol_match = re.search(r'\+S-([^+]+)\.CSV\.GZ$', key_upper)
            if symbol_match:
                symbol_part = symbol_match.group(1)
                # Reject if contains unwanted prefixes
                if re.search(r'^(PUMP|WBTC|LBTC|MNT|ORDI|FET|LTC|AVAX|SOL)', symbol_part):
                    continue
            
            exact_matches.append((key, size))
        
        print(f"    🎯 Exact matches after filtering: {len(exact_matches)}")
        
        if len(exact_matches) == 0:
            return None, f"No exact {expected_symbol} matches found after filtering"
        elif len(exact_matches) > 1:
            print(f"    ❌ Multiple exact matches found:")
            for i, (key, size) in enumerate(exact_matches):
                print(f"      {i+1}. {os.path.basename(key)} ({size:,} bytes)")
            return None, f"Multiple exact {expected_symbol} matches found - need manual selection"
        else:
            selected_key, selected_size = exact_matches[0]
            print(f"    ✅ Selected: {os.path.basename(selected_key)} ({selected_size:,} bytes)")
            return (selected_key, selected_size), None
        
    except Exception as e:
        return None, f"Error parsing XML: {e}"

def download_coinapi_file_week1(key, output_path):
    """Download file using Week 1 URL pattern with retry logic"""
    full_url = f'https://s3.flatfiles.coinapi.io/coinapi/{key}'
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key(),
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    max_retries = 4
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = 0.5 * (2 ** (attempt - 1))
                print(f"    ⚠️  Download retry {attempt}/{max_retries-1} after {delay}s...")
                time.sleep(delay)
            
            response = requests.get(full_url, headers=headers, timeout=120)
            if response.status_code == 200:
                # Create staging directory
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Write to staging
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                return True, None, response.status_code
            elif response.status_code >= 500 and attempt < max_retries - 1:
                print(f"    ⚠️  Download server error {response.status_code}, retrying...")
                continue
            else:
                return False, f"HTTP {response.status_code}", response.status_code
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    ⚠️  Download exception: {e}, retrying...")
                continue
            return False, str(e), None
    
    return False, "Max download retries exceeded", None

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def validate_venue_data_chunked(venue, date, staging_files):
    """Validate venue data in chunks to manage memory"""
    print(f"  🔍 Validating {venue}...")
    
    try:
        # 1. Readable & non-empty
        if not staging_files:
            return False, "No files found"
        
        # Process in chunks
        chunk_size = 50000
        all_chunks = []
        total_rows = 0
        
        print(f"    📊 Processing in chunks of {chunk_size:,} rows...")
        
        for file_path in staging_files:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            if os.path.getsize(file_path) == 0:
                return False, f"Empty file: {file_path}"
            
            try:
                for chunk_num, chunk in enumerate(pd.read_csv(file_path, sep=';', compression='gzip', chunksize=chunk_size)):
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
                return False, f"Error reading {file_path}: {e}"
        
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
        file_hashes = []
        file_sizes = []
        for file_path in staging_files:
            file_hashes.append(compute_file_hash(file_path))
            file_sizes.append(os.path.getsize(file_path))
        
        return True, {
            'raw_files': len(staging_files),
            'raw_mb': sum(file_sizes) / 1024 / 1024,
            'raw_rows': total_rows,
            'rows': final_rows,
            'duplicates_removed': duplicates_removed,
            'price_min': price_min,
            'price_max': price_max,
            'ts_start': ts_min,
            'ts_end': ts_max,
            'file_hashes': file_hashes,
            'canonical_df': canonical_df
        }
        
    except Exception as e:
        return False, f"Validation error: {e}"

def process_day_20250921():
    """Process Day 7: 2025-09-21 using exact symbol match filtering"""
    print("🚀 Week-3 Re-download: Day 7 (2025-09-21) - Exact Symbol Match Filtering")
    print("=" * 80)
    
    date = "20250921"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    expected_symbols = {
        'BINANCE': 'BTCUSDT',
        'COINBASE': 'BTCUSD',
        'BYBITSPOT': 'BTCUSDT',
        'BITGET': 'BTCUSDT'
    }
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Stage 1: Find exact symbol matches for all venues
    print(f"\n🔍 Stage 1: Finding exact symbol matches...")
    exact_matches = {}
    s3_keys_used = {}
    
    for venue in venues:
        expected_symbol = expected_symbols[venue]
        file_info, error = find_exact_symbol_match(venue, date, expected_symbol)
        
        if error:
            print(f"  ❌ {venue} failed: {error}")
            return False, f"Failed to find exact {venue} {expected_symbol} match: {error}"
        
        key, size = file_info
        exact_matches[venue] = (key, size)
        s3_keys_used[venue] = key
        print(f"  ✅ {venue}: {os.path.basename(key)} ({size:,} bytes)")
    
    # Stage 2: Download all venues to staging
    print(f"\n📥 Stage 2: Downloading exact matches...")
    staging_results = {}
    
    for venue in venues:
        print(f"  📥 Downloading {venue}...")
        
        key, size = exact_matches[venue]
        staging_path = f"analysis/flatfiles_ticks_v4/staging/{venue}/{date}/raw/{os.path.basename(key)}"
        success, error, http_status = download_coinapi_file_week1(key, staging_path)
        
        if not success:
            print(f"    ❌ Download failed: {error}")
            return False, f"Failed to download {key}: {error}"
        
        # Verify file size
        actual_size = os.path.getsize(staging_path)
        if actual_size == size:
            staging_results[venue] = [staging_path]
            print(f"    ✅ Downloaded: {actual_size:,} bytes")
        else:
            print(f"    ❌ Size mismatch: expected {size}, got {actual_size}")
            os.remove(staging_path)
            return False, f"Size mismatch for {venue}"
        
        # Memory check
        memory_mb = get_memory_usage()
        if memory_mb > 500:
            print(f"    ❌ HALT: Memory limit exceeded ({memory_mb:.1f} MB)")
            return False, f"Memory limit exceeded during download"
    
    # Stage 3: Validate all venues
    print(f"\n🔍 Stage 3: Validating all venues...")
    validation_results = {}
    
    for venue in venues:
        success, result = validate_venue_data_chunked(venue, date, staging_results[venue])
        
        if not success:
            print(f"  ❌ {venue} validation failed: {result}")
            return False, f"{venue} validation failed: {result}"
        
        validation_results[venue] = result
        print(f"  ✅ {venue} validation passed")
        
        # Clear memory between venues
        import gc
        gc.collect()
        print(f"    🧠 Memory after {venue}: {get_memory_usage():.1f} MB")
    
    # Stage 4: All venues passed - create canonical files
    print(f"\n📝 Stage 4: Creating canonical files...")
    
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
    
    # Stage 5: Clean up staging
    print(f"\n🧹 Stage 5: Cleaning up staging...")
    for venue in venues:
        staging_dir = f"analysis/flatfiles_ticks_v4/staging/{venue}/{date}"
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
            print(f"  🗑️  Cleaned {venue} staging")
    
    # Final results
    print(f"\n📊 Day 7 Results:")
    print("Date | Venue | RawFiles | RawMB | RawRows | DupsRemoved | CanonRows | PriceMin→Max | tsStart→tsEnd | Status")
    print("-" * 140)
    
    total_raw_rows = 0
    total_canon_rows = 0
    
    for venue in venues:
        result = validation_results[venue]
        price_range = f"{result['price_min']:.0f}→{result['price_max']:.0f}"
        ts_range = f"{result['ts_start'].strftime('%H:%M:%S')}→{result['ts_end'].strftime('%H:%M:%S')}"
        
        print(f"{date} | {venue} | {result['raw_files']} | {result['raw_mb']:.1f} | {result['raw_rows']:,} | {result['duplicates_removed']:,} | {result['rows']:,} | {price_range} | {ts_range} | PASS")
        
        total_raw_rows += result['raw_rows']
        total_canon_rows += result['rows']
    
    # Per-venue manifests
    print(f"\n📋 Per-Venue Manifests:")
    for venue in venues:
        result = validation_results[venue]
        s3_key = s3_keys_used[venue]
        file_hash = result['file_hashes'][0][:16]  # First 16 chars of SHA256
        
        print(f"  {venue}:")
        print(f"    s3_key_used: {os.path.basename(s3_key)}")
        print(f"    sha256(local_gz): {file_hash}...")
    
    peak_memory = get_memory_usage()
    print(f"\n📊 Daily Summary:")
    print(f"  Total raw rows: {total_raw_rows:,}")
    print(f"  Total canonical rows: {total_canon_rows:,}")
    print(f"  Peak memory: {peak_memory:.1f} MB")
    
    print(f"\n✅ Day verdict = PASS (replaced)")
    print(f"🧠 Peak RSS: {peak_memory:.1f} MB")
    print(f"📋 No HALT codes")
    
    return True, "Day 7 completed successfully with exact symbol match filtering"

def main():
    """Main function"""
    success, message = process_day_20250921()
    
    if success:
        print(f"\n🎉 {message}")
    else:
        print(f"\n❌ {message}")
        sys.exit(1)

if __name__ == "__main__":
    main()




