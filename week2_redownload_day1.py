#!/usr/bin/env python3
"""
Week-2 Re-download: Day 1 (2025-09-08)
Atomic day replacement with comprehensive validation
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

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    return os.environ.get('COINAPI_KEY', '7f036b38-38d6-4ed6-9fce-00a06280a0f6')

def list_coinapi_objects(venue, date):
    """List objects in CoinAPI for specific venue and date"""
    base_url = "https://s3.flatfiles.coinapi.io/bucket/"
    prefix = f"T-TRADES/D-{date}/E-{venue}/"
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    params = {
        'prefix': prefix
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

def parse_s3_listing(xml_content):
    """Parse S3 XML listing response"""
    try:
        root = ET.fromstring(xml_content)
        objects = []
        
        for contents in root.findall('.//Contents'):
            key = contents.find('Key').text
            size = int(contents.find('Size').text)
            last_modified = contents.find('LastModified').text
            objects.append({
                'key': key, 
                'size': size, 
                'last_modified': last_modified
            })
        
        return objects
    except Exception as e:
        return []

def download_coinapi_file(object_key, output_path):
    """Download a file from CoinAPI"""
    base_url = "https://s3.flatfiles.coinapi.io"
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    try:
        response = requests.get(f"{base_url}/{object_key}", headers=headers, timeout=60)
        if response.status_code == 200:
            # Create staging directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write to staging
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True, None
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def validate_venue_data(venue, date, staging_files):
    """Validate venue data against all criteria"""
    print(f"  🔍 Validating {venue}...")
    
    try:
        # 1. Readable & non-empty
        if not staging_files:
            return False, "No files found"
        
        # Load and merge all files for the venue
        all_data = []
        total_rows = 0
        
        for file_path in staging_files:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            if os.path.getsize(file_path) == 0:
                return False, f"Empty file: {file_path}"
            
            # Read CSV safely
            try:
                df = pd.read_csv(file_path, sep=';', compression='gzip')
                if len(df) == 0:
                    return False, f"Empty CSV: {file_path}"
                
                all_data.append(df)
                total_rows += len(df)
                
                # Memory check
                memory_mb = get_memory_usage()
                if memory_mb > 500:
                    return False, f"HALT: Memory limit exceeded ({memory_mb:.1f} MB)"
                
            except Exception as e:
                return False, f"Error reading {file_path}: {e}"
        
        if not all_data:
            return False, "No valid data loaded"
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # 2. Schema check
        required_cols = ['time_exchange', 'price', 'base_amount']
        missing_cols = [col for col in required_cols if col not in combined_df.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # Convert to canonical format
        canonical_df = pd.DataFrame({
            'ts': pd.to_datetime(combined_df['time_exchange'], utc=True),
            'price': pd.to_numeric(combined_df['price'], errors='coerce'),
            'size': pd.to_numeric(combined_df['base_amount'], errors='coerce'),
            'venue': venue
        })
        
        # Remove invalid data
        canonical_df = canonical_df.dropna()
        canonical_df = canonical_df[
            (canonical_df['price'] > 0) & 
            (canonical_df['size'] > 0)
        ]
        
        if len(canonical_df) == 0:
            return False, "No valid data after cleaning"
        
        # 3. Timestamp bounds check
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59.999999", tz='UTC')
        
        ts_min = canonical_df['ts'].min()
        ts_max = canonical_df['ts'].max()
        
        if ts_min < day_start or ts_max > day_end:
            return False, f"Timestamps out of bounds: {ts_min} to {ts_max}"
        
        # 4. De-duplication
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

def process_day_20250908():
    """Process Day 1: 2025-09-08"""
    print("🚀 Week-2 Re-download: Day 1 (2025-09-08)")
    print("=" * 60)
    
    date = "20250908"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    venue_symbols = {
        "BINANCE": "BTCUSDT",
        "COINBASE": "BTCUSD", 
        "BYBITSPOT": "BTCUSDT",
        "BITGET": "BTCUSDT"
    }
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    # Stage 1: Download all venues to staging
    print(f"\n📥 Stage 1: Downloading to staging...")
    staging_results = {}
    
    for venue in venues:
        print(f"  📥 Downloading {venue}...")
        
        # List objects
        status_code, xml_content = list_coinapi_objects(venue, date)
        if status_code != 200:
            print(f"    ❌ HTTP {status_code}")
            return False, f"Failed to list {venue} objects"
        
        objects = parse_s3_listing(xml_content)
        if not objects:
            print(f"    ❌ No objects found for {venue}")
            return False, f"No objects found for {venue}"
        
        # Filter for BTC symbol
        symbol = venue_symbols[venue]
        btc_objects = [obj for obj in objects if symbol in obj['key'].upper()]
        if not btc_objects:
            print(f"    ❌ No {symbol} files found for {venue}")
            return False, f"No {symbol} files found for {venue}"
        
        print(f"    📁 Found {len(btc_objects)} {symbol} files")
        
        # Download all matching files
        staging_files = []
        for i, obj in enumerate(btc_objects):
            staging_path = f"analysis/flatfiles_ticks_v4/staging/{venue}/{date}/raw/{os.path.basename(obj['key'])}"
            success, error = download_coinapi_file(obj['key'], staging_path)
            
            if not success:
                print(f"    ❌ Download failed: {error}")
                return False, f"Failed to download {obj['key']}"
            
            staging_files.append(staging_path)
            print(f"    ✅ Downloaded {os.path.basename(obj['key'])} ({obj['size']/1024/1024:.2f} MB)")
        
        staging_results[venue] = staging_files
        
        # Memory check
        memory_mb = get_memory_usage()
        if memory_mb > 500:
            print(f"    ❌ HALT: Memory limit exceeded ({memory_mb:.1f} MB)")
            return False, f"Memory limit exceeded during download"
    
    # Stage 2: Validate all venues
    print(f"\n🔍 Stage 2: Validating all venues...")
    validation_results = {}
    
    for venue in venues:
        success, result = validate_venue_data(venue, date, staging_results[venue])
        
        if not success:
            print(f"  ❌ {venue} validation failed: {result}")
            return False, f"{venue} validation failed: {result}"
        
        validation_results[venue] = result
        print(f"  ✅ {venue} validation passed")
    
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
    
    # Stage 4: Clean up staging
    print(f"\n🧹 Stage 4: Cleaning up staging...")
    for venue in venues:
        staging_dir = f"analysis/flatfiles_ticks_v4/staging/{venue}/{date}"
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
            print(f"  🗑️  Cleaned {venue} staging")
    
    # Final results
    print(f"\n📊 Day 1 Results:")
    print("Date | Venue | RawFiles | RawMB | Rows | DupsRemoved | PriceMin→Max | tsStart→tsEnd | Status")
    print("-" * 120)
    
    for venue in venues:
        result = validation_results[venue]
        price_range = f"{result['price_min']:.0f}→{result['price_max']:.0f}"
        ts_range = f"{result['ts_start'].strftime('%H:%M:%S')}→{result['ts_end'].strftime('%H:%M:%S')}"
        
        print(f"{date} | {venue} | {result['raw_files']} | {result['raw_mb']:.1f} | {result['rows']:,} | {result['duplicates_removed']:,} | {price_range} | {ts_range} | PASS")
    
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




