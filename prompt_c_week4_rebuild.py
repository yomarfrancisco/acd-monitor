#!/usr/bin/env python3
"""
Prompt C — Week 4 Rebuild (Day-by-Day)
Week 4 CoinAPI Rebuild — 2025-09-22→2025-09-28 (Atomic, Safe)
"""

import os
import sys
import pandas as pd
import numpy as np
import gc
import psutil
import requests
import hashlib
import shutil
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables
load_env_file()

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 400:
        print(f"⚠️  MEMORY_WARNING: {memory_mb:.1f} MB (soft limit 400MB)")
        if memory_mb >= 800:
            print(f"❌ HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
            return True
    return False

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    key = os.getenv('COINAPI_KEY')
    if not key:
        print("❌ HALT: COINAPI_KEY environment variable not set")
        return None
    return key

def list_coinapi_files(date, venue):
    """List files from CoinAPI S3 bucket for a specific date and venue"""
    coinapi_key = get_coinapi_key()
    if not coinapi_key:
        return None, "No API key"
    
    # Symbol mapping
    symbol_map = {
        'BINANCE': 'BTCUSDT',
        'COINBASE': 'BTC__002DUSD',  # URL encoded BTC-USD
        'BYBITSPOT': 'BTCUSDT',
        'BITGET': 'BTCUSDT'
    }
    
    expected_symbol = symbol_map.get(venue)
    if not expected_symbol:
        return None, f"Unknown venue: {venue}"
    
    # List files from CoinAPI
    list_url = f"https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    try:
        response = requests.get(list_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        
        files = []
        for content in root.findall('.//Contents'):
            key_elem = content.find('Key')
            size_elem = content.find('Size')
            
            if key_elem is not None and size_elem is not None:
                key = key_elem.text
                size = int(size_elem.text)
                
                # Filter for exact symbol match
                if expected_symbol in key and key.endswith('.csv.gz'):
                    files.append({
                        'key': key,
                        'size': size
                    })
        
        # Debug: if no files found, check what we got
        if not files:
            all_files = []
            for content in root.findall('.//Contents'):
                key_elem = content.find('Key')
                if key_elem is not None:
                    all_files.append(key_elem.text)
            print(f"    🔍 Debug: Found {len(all_files)} total files, looking for {expected_symbol}")
            if all_files:
                print(f"    🔍 Debug: First few files: {all_files[:3]}")
        
        return files, None
        
    except Exception as e:
        return None, f"Error listing files: {e}"

def download_coinapi_file(file_key, local_path):
    """Download a file from CoinAPI"""
    coinapi_key = get_coinapi_key()
    if not coinapi_key:
        return False, "No API key"
    
    download_url = f"https://s3.flatfiles.coinapi.io/coinapi/{file_key}"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        response = requests.get(download_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True, None
        
    except Exception as e:
        return False, f"Error downloading {file_key}: {e}"

def validate_raw_file(file_path, venue, date):
    """Validate a raw CSV file"""
    try:
        # Check file exists and size
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
        
        # Read first few rows to check schema
        df_sample = pd.read_csv(file_path, nrows=1000, compression='gzip', sep=';')
        
        # Check required columns
        required_cols = ['time_exchange', 'price', 'base_amount']
        missing_cols = [col for col in required_cols if col not in df_sample.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        
        # Check data types
        if not pd.api.types.is_numeric_dtype(df_sample['price']):
            return False, "Price column is not numeric"
        if not pd.api.types.is_numeric_dtype(df_sample['base_amount']):
            return False, "Base_amount column is not numeric"
        
        # Check timestamp format
        try:
            df_sample['time_exchange'] = pd.to_datetime(df_sample['time_exchange'], utc=True)
        except:
            return False, "Invalid timestamp format"
        
        # Check price sanity
        price_min, price_max = df_sample['price'].min(), df_sample['price'].max()
        if price_min < 80000 or price_max > 180000:
            return False, f"Price out of range: {price_min:.2f} - {price_max:.2f}"
        
        # Check size sanity
        if df_sample['base_amount'].min() < 0:
            return False, "Negative base_amount values found"
        
        # Get full row count
        row_count = sum(1 for _ in open(file_path, 'rb')) - 1  # Subtract header
        
        # Check row count floor
        if row_count < 50000:
            return False, f"Row count too low: {row_count:,}"
        
        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()[:8]
        
        return True, {
            'file_size': file_size,
            'row_count': row_count,
            'price_min': price_min,
            'price_max': price_max,
            'sha256': file_hash,
            'ts_min': df_sample['time_exchange'].min(),
            'ts_max': df_sample['time_exchange'].max()
        }
        
    except Exception as e:
        return False, f"Validation error: {e}"

def canonicalize_file(raw_file_path, venue, date):
    """Canonicalize raw file to parquet format"""
    try:
        # Read raw file
        df = pd.read_csv(raw_file_path, compression='gzip', sep=';')
        
        # Convert timestamp to UTC
        df['ts'] = pd.to_datetime(df['time_exchange'], utc=True)
        
        # Select only canonical columns
        canonical_cols = ['ts', 'price', 'size', 'venue']
        df_canonical = df[['ts', 'price', 'base_amount']].copy()
        df_canonical.rename(columns={'base_amount': 'size'}, inplace=True)
        df_canonical['venue'] = venue
        
        # Sort by timestamp
        df_canonical = df_canonical.sort_values('ts')
        
        # Remove duplicates (keep first)
        df_canonical = df_canonical.drop_duplicates(subset=['ts', 'price', 'size'], keep='first')
        
        # Check timestamp bounds (full 24h coverage)
        day_start = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 00:00:00", tz='UTC')
        day_end = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:8]} 23:59:59", tz='UTC')
        
        ts_min, ts_max = df_canonical['ts'].min(), df_canonical['ts'].max()
        
        # Check coverage
        coverage_hours = (ts_max - ts_min).total_seconds() / 3600
        if coverage_hours < 20:  # Less than 20 hours
            return False, f"Coverage too low: {coverage_hours:.1f} hours"
        
        # Create output directory
        output_dir = f"data_v6/views/{venue}/{date}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = f"{output_dir}/ticks_canonical.parquet"
        
        # Backup existing file if it exists
        if os.path.exists(output_path):
            backup_dir = f"data_v6/backup/{venue}/{date}"
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{backup_dir}/ticks_canonical_{timestamp}.parquet"
            shutil.move(output_path, backup_path)
            print(f"    📦 Backed up existing file to {backup_path}")
        
        # Write parquet file
        df_canonical.to_parquet(output_path, compression='snappy', index=False)
        
        result = {
            'canonical_rows': len(df_canonical),
            'ts_min': ts_min,
            'ts_max': ts_max,
            'coverage_hours': coverage_hours,
            'output_path': output_path
        }
        
        # Clean up memory
        del df, df_canonical
        gc.collect()
        
        return True, result
        
    except Exception as e:
        return False, f"Canonicalization error: {e}"

def process_day(date):
    """Process a single day for all venues"""
    print(f"\n📅 Processing {date} (Week 5)")
    print("=" * 60)
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    results = []
    failed_venues = []
    
    # Process each venue
    for venue in venues:
        print(f"\n🔍 Processing {venue}...")
        
        # Check memory before processing
        memory_mb = get_memory_usage()
        if memory_mb >= 400:
            print(f"    ⚠️  Memory warning before {venue}: {memory_mb:.1f} MB")
            gc.collect()
            memory_mb = get_memory_usage()
            print(f"    🧹 After cleanup: {memory_mb:.1f} MB")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded")
            failed_venues.append(f"{venue}: Memory limit exceeded")
            continue
        
        # List files
        files, error = list_coinapi_files(date, venue)
        if error:
            print(f"    ❌ {error}")
            failed_venues.append(f"{venue}: {error}")
            continue
        
        if not files:
            print(f"    ❌ No files found for {venue}")
            failed_venues.append(f"{venue}: No files found")
            continue
        
        print(f"    📋 Found {len(files)} files for {venue}")
        # Show first few file names for debugging
        for i, f in enumerate(files[:3]):
            filename = f['key'].split('/')[-1]
            print(f"      {i+1}. {filename}")
        
        # Find exact symbol match
        symbol_map = {
            'BINANCE': 'BTCUSDT',
            'COINBASE': 'BTC__002DUSD',  # URL encoded BTC-USD
            'BYBITSPOT': 'BTCUSDT', 
            'BITGET': 'BTCUSDT'
        }
        expected_symbol = symbol_map[venue]
        
        matching_files = [f for f in files if expected_symbol in f['key']]
        if not matching_files:
            # Try alternative patterns for COINBASE
            if venue == 'COINBASE':
                alt_patterns = ['BTC_USD', 'BTCUSD', 'BTC-USD']
                for pattern in alt_patterns:
                    matching_files = [f for f in files if pattern in f['key']]
                    if matching_files:
                        print(f"    🔍 Found COINBASE file with pattern: {pattern}")
                        break
            
            if not matching_files:
                print(f"    ❌ No files found with symbol {expected_symbol}")
                print(f"    📋 Available files: {[f['key'].split('/')[-1] for f in files[:5]]}")
                failed_venues.append(f"{venue}: No matching symbol files")
                continue
        
        # Use the correct matching file (prefer exact symbol match)
        file_info = None
        for f in matching_files:
            # Check if this is the exact symbol we want
            if venue == 'COINBASE' and 'BTC__002DUSD' in f['key']:
                file_info = f
                break
            elif venue in ['BINANCE', 'BYBITSPOT', 'BITGET'] and 'BTCUSDT' in f['key'] and 'WBTC' not in f['key'] and 'PUMPBTC' not in f['key'] and 'LBTC' not in f['key']:
                file_info = f
                break
        
        # Fallback to first file if no exact match
        if not file_info:
            file_info = matching_files[0]
        file_key = file_info['key']
        file_size_mb = file_info['size'] / (1024 * 1024)
        
        print(f"    📁 Found: {file_key}")
        print(f"    📊 Size: {file_size_mb:.1f} MB")
        
        # Download file
        staging_dir = f"analysis/flatfiles_ticks_v4/staging/{venue}/{date}"
        os.makedirs(staging_dir, exist_ok=True)
        local_path = f"{staging_dir}/raw.csv.gz"
        
        success, error = download_coinapi_file(file_key, local_path)
        if not success:
            print(f"    ❌ Download failed: {error}")
            failed_venues.append(f"{venue}: Download failed - {error}")
            continue
        
        print(f"    ✅ Downloaded to {local_path}")
        
        # Validate file
        valid, validation_result = validate_raw_file(local_path, venue, date)
        if not valid:
            print(f"    ❌ Validation failed: {validation_result}")
            failed_venues.append(f"{venue}: Validation failed - {validation_result}")
            # Clean up staging file
            if os.path.exists(local_path):
                os.remove(local_path)
            continue
        
        print(f"    ✅ Validated: {validation_result['row_count']:,} rows, {validation_result['sha256']}")
        
        # Canonicalize
        canonical_success, canonical_result = canonicalize_file(local_path, venue, date)
        if not canonical_success:
            print(f"    ❌ Canonicalization failed: {canonical_result}")
            failed_venues.append(f"{venue}: Canonicalization failed - {canonical_result}")
            # Clean up staging file
            if os.path.exists(local_path):
                os.remove(local_path)
            continue
        
        print(f"    ✅ Canonicalized: {canonical_result['canonical_rows']:,} rows")
        
        # Store results
        results.append({
            'venue': venue,
            'file_key': file_key,
            'file_size_mb': file_size_mb,
            'raw_rows': validation_result['row_count'],
            'canonical_rows': canonical_result['canonical_rows'],
            'price_min': validation_result['price_min'],
            'price_max': validation_result['price_max'],
            'sha256': validation_result['sha256'],
            'ts_start': canonical_result['ts_min'],
            'ts_end': canonical_result['ts_max'],
            'status': 'PASS'
        })
        
        # Clean up staging file
        os.remove(local_path)
        
        # Force garbage collection and memory cleanup
        if 'df_sample' in locals():
            del df_sample
        if 'validation_result' in locals():
            del validation_result
        if 'canonical_result' in locals():
            del canonical_result
        gc.collect()
        
        # Check memory after each venue
        memory_after = get_memory_usage()
        print(f"    🧠 Memory after {venue}: {memory_after:.1f} MB")
        
        if check_memory_limit():
            print(f"    ⚠️  Memory warning after {venue}")
            gc.collect()
    
    # Print results table
    print(f"\n📊 Results for {date}:")
    print("=" * 120)
    print(f"{'Venue':<10} {'File_Key':<50} {'Size_MB':<8} {'Raw_Rows':<10} {'Canon_Rows':<10} {'Price_Range':<20} {'SHA256':<8} {'Status':<6}")
    print("-" * 120)
    
    total_raw_rows = 0
    total_canon_rows = 0
    total_size_mb = 0
    
    for result in results:
        price_range = f"{result['price_min']:.0f}→{result['price_max']:.0f}"
        print(f"{result['venue']:<10} {result['file_key'][:49]:<50} {result['file_size_mb']:<8.1f} {result['raw_rows']:<10,} {result['canonical_rows']:<10,} {price_range:<20} {result['sha256']:<8} {result['status']:<6}")
        
        total_raw_rows += result['raw_rows']
        total_canon_rows += result['canonical_rows']
        total_size_mb += result['file_size_mb']
    
    print("-" * 120)
    if results:
        print(f"{'TOTAL':<10} {'':<50} {total_size_mb:<8.1f} {total_raw_rows:<10,} {total_canon_rows:<10,} {'':<20} {'':<8} {'PASS':<6}")
    else:
        print(f"{'TOTAL':<10} {'':<50} {'0.0':<8} {'0':<10} {'0':<10} {'':<20} {'':<8} {'FAIL':<6}")
    
    # Day summary
    print(f"\n📈 Day Summary:")
    print(f"  • Total raw rows: {total_raw_rows:,}")
    print(f"  • Total canonical rows: {total_canon_rows:,}")
    print(f"  • Total size: {total_size_mb:.1f} MB")
    print(f"  • Peak memory: {get_memory_usage():.1f} MB")
    print(f"  • Successful venues: {len(results)}/4")
    if failed_venues:
        print(f"  • Failed venues: {len(failed_venues)}")
        for failed in failed_venues:
            print(f"    - {failed}")
    
    if len(results) == 4:
        print(f"  • Status: ✅ ALL VENUES PASSED")
        return True, failed_venues
    elif len(results) > 0:
        print(f"  • Status: ⚠️  PARTIAL SUCCESS")
        return False, failed_venues
    else:
        print(f"  • Status: ❌ ALL VENUES FAILED")
        return False, failed_venues

def main():
    """Main function"""
    print("🧭 Prompt — Week 5 Rebuild (Day-by-Day, Auto-Continue)")
    print("=" * 70)
    
    # Week 5 dates
    start_date = datetime(2025, 9, 29)
    end_date = datetime(2025, 10, 5)
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date += timedelta(days=1)
    
    print(f"📅 Week 5 dates: {dates[0]} to {dates[-1]} ({len(dates)} days)")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    print(f"🧠 Memory limits: soft 400MB, hard 800MB")
    
    # Track results for week summary
    week_results = []
    successful_venue_days = 0
    skipped_venues = []
    peak_memory = get_memory_usage()
    
    # Process each day
    for day_idx, date in enumerate(dates):
        print(f"\n🚀 Starting Day {day_idx + 1}/7: {date}")
        
        success, day_failed_venues = process_day(date)
        
        if not success:
            print(f"\n❌ Day {date} failed. Continuing to next day.")
            # Record which venues failed for this day
            for failed_venue in day_failed_venues:
                skipped_venues.append(f"{date}: {failed_venue}")
        else:
            print(f"\n✅ Day {date} completed successfully.")
            successful_venue_days += 4  # All 4 venues passed
        
        # Update peak memory
        current_memory = get_memory_usage()
        if current_memory > peak_memory:
            peak_memory = current_memory
    
    # Week summary
    print(f"\n" + "=" * 80)
    print(f"📊 WEEK 5 SUMMARY")
    print(f"=" * 80)
    print(f"• Total successful venue-days: {successful_venue_days}/28")
    print(f"• Skipped venues: {len(skipped_venues)}")
    for skip in skipped_venues:
        print(f"  - {skip}")
    print(f"• Median Δdisp: [placeholder - no analysis yet]")
    print(f"• Median Δlag: [placeholder - no analysis yet]")
    print(f"• Peak memory usage: {peak_memory:.1f} MB")
    print(f"=" * 80)
    
    print(f"\n🎉 Week 5 rebuild completed!")
    return True

if __name__ == "__main__":
    success = main()
    
    if not success:
        print(f"\n❌ Week 4 rebuild failed. Waiting for instructions.")
        sys.exit(1)
