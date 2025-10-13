#!/usr/bin/env python3
"""
Phase 42A-v7f — Week -7 (July 7-13) Download with BTC Focus
Download July 7-13, 2025 data focusing on BTC trading pairs only
"""

import os
import sys
import requests
import hashlib
import time
import random
import csv
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Configuration
API_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
BASE_URL = 'https://s3.flatfiles.coinapi.io/'
DOWNLOAD_BASE_URL = 'https://s3.flatfiles.coinapi.io/coinapi/'
HEADERS = {
    'X-CoinAPI-Key': API_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

# Date range: July 7-13, 2025 (Week -7)
START_DATE = '2025-07-07'
END_DATE = '2025-07-13'
VENUES = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

# Budget constraints
MAX_HTTP_CALLS = 80
MAX_RUNTIME_MINUTES = 45
MAX_WORKERS = 2

# Output paths
OUTPUT_DIR = Path('data_v7/raw/coinapi_jul_w7')
MANIFEST_FILE = 'data_v7/reports/jul_w7_flatfiles_manifest.csv'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Path('data_v7/reports').mkdir(parents=True, exist_ok=True)

def generate_date_range(start_date, end_date):
    """Generate list of dates in YYYYMMDD format"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    return dates

def list_s3_objects(date, venue):
    """List objects in S3 for a specific date and venue"""
    prefix = f'T-TRADES/D-{date}/E-{venue}/'
    list_url = f'{BASE_URL}bucket/?prefix={prefix}'
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            keys = []
            for contents in root.findall('.//Contents'):
                key_elem = contents.find('Key')
                if key_elem is not None:
                    keys.append(key_elem.text)
            return keys
        else:
            print(f"LIST failed for {date}/{venue}: {response.status_code}")
            return []
    except Exception as e:
        print(f"LIST error for {date}/{venue}: {e}")
        return []

def check_local_file(date, venue, key):
    """Check if file already exists locally"""
    filename = key.split('/')[-1]
    local_path = OUTPUT_DIR / date / venue / filename
    return local_path.exists()

def is_btc_pair(filename):
    """Check if file contains BTC trading pairs"""
    # Look for BTC in the filename (case insensitive)
    return 'BTC' in filename.upper()

def download_file(date, venue, key, max_attempts=3):
    """Download a single file with retry logic"""
    filename = key.split('/')[-1]
    local_path = OUTPUT_DIR / date / venue / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    # CORRECTED download URL
    download_url = f'{DOWNLOAD_BASE_URL}{key}'
    
    for attempt in range(max_attempts):
        try:
            # Exponential backoff with jitter
            if attempt > 0:
                sleep_time = (30 * (2 ** attempt)) + random.uniform(-5, 5)
                print(f"Retry {attempt} for {filename} after {sleep_time:.1f}s")
                time.sleep(sleep_time)
            
            response = requests.get(download_url, headers=HEADERS, timeout=120)
            
            if response.status_code == 200:
                # Save file
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # Compute SHA-256
                sha256_hash = hashlib.sha256(response.content).hexdigest()
                file_size = len(response.content)
                
                print(f"✅ Downloaded {filename} ({file_size:,} bytes)")
                return {
                    'date': date,
                    'venue': venue,
                    'filename': filename,
                    'key': key,
                    'size_bytes': file_size,
                    'sha256': sha256_hash,
                    'attempts': attempt + 1,
                    'status': 'success'
                }
            else:
                print(f"❌ Download failed for {filename}: HTTP {response.status_code}")
                if attempt == max_attempts - 1:
                    return {
                        'date': date,
                        'venue': venue,
                        'filename': filename,
                        'key': key,
                        'size_bytes': 0,
                        'sha256': '',
                        'attempts': attempt + 1,
                        'status': f'failed_http_{response.status_code}'
                    }
        except Exception as e:
            print(f"❌ Download error for {filename}: {e}")
            if attempt == max_attempts - 1:
                return {
                    'date': date,
                    'venue': venue,
                    'filename': filename,
                    'key': key,
                    'size_bytes': 0,
                    'sha256': '',
                    'attempts': attempt + 1,
                    'status': f'failed_error_{str(e)[:50]}'
                }
    
    return None

def main():
    print("🚀 Phase 42A-v7f — Week -7 Download (July 7-13) - BTC Focus")
    print(f"📅 Date range: {START_DATE} to {END_DATE}")
    print(f"🏢 Venues: {', '.join(VENUES)}")
    print(f"₿ Focus: BTC trading pairs only")
    print(f"⏱️  Budget: {MAX_HTTP_CALLS} calls, {MAX_RUNTIME_MINUTES} min")
    print()
    
    start_time = time.time()
    http_calls = 0
    results = []
    
    # Generate expected files
    dates = generate_date_range(START_DATE, END_DATE)
    print(f"📋 Expected files: {len(dates)} days × {len(VENUES)} venues = {len(dates) * len(VENUES)} venue-days")
    
    # Check existing files first and filter for BTC pairs
    missing_files = []
    btc_files_found = 0
    total_files_found = 0
    
    for date in dates:
        for venue in VENUES:
            # List objects for this date/venue
            keys = list_s3_objects(date, venue)
            http_calls += 1
            total_files_found += len(keys)
            
            if not keys:
                print(f"⚠️  No files found for {date}/{venue}")
                continue
            
            # Filter for BTC pairs and check if already downloaded
            btc_keys = [key for key in keys if is_btc_pair(key)]
            btc_files_found += len(btc_keys)
            
            for key in btc_keys:
                if not check_local_file(date, venue, key):
                    missing_files.append((date, venue, key))
                else:
                    print(f"✅ Already have {key.split('/')[-1]}")
    
    print(f"\n📊 File Analysis:")
    print(f"Total files found: {total_files_found}")
    print(f"BTC files found: {btc_files_found}")
    print(f"Missing BTC files to download: {len(missing_files)}")
    print(f"📞 HTTP calls used so far: {http_calls}/{MAX_HTTP_CALLS}")
    
    if len(missing_files) == 0:
        print("🎉 All BTC files already downloaded!")
        return
    
    # Download missing BTC files
    print(f"\n⬇️  Starting BTC downloads with {MAX_WORKERS} workers...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit download tasks
        future_to_file = {}
        for date, venue, key in missing_files:
            if http_calls >= MAX_HTTP_CALLS:
                print(f"⚠️  HTTP call limit reached ({MAX_HTTP_CALLS})")
                break
            
            future = executor.submit(download_file, date, venue, key)
            future_to_file[future] = (date, venue, key)
            http_calls += 1
        
        # Process completed downloads
        for future in as_completed(future_to_file):
            if time.time() - start_time > MAX_RUNTIME_MINUTES * 60:
                print(f"⏰ Time limit reached ({MAX_RUNTIME_MINUTES} min)")
                break
            
            result = future.result()
            if result:
                results.append(result)
    
    # Generate reports
    print(f"\n📊 Download Summary:")
    print(f"⏱️  Runtime: {time.time() - start_time:.1f}s")
    print(f"📞 HTTP calls: {http_calls}/{MAX_HTTP_CALLS}")
    print(f"📁 Files processed: {len(results)}")
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']
    
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    # Coverage report (based on expected BTC pairs per venue per day)
    # Estimate: ~2-3 BTC pairs per venue per day
    estimated_btc_pairs_per_venue_day = 2.5
    total_expected_btc = len(dates) * len(VENUES) * estimated_btc_pairs_per_venue_day
    coverage_pct = (len(successful) / total_expected_btc) * 100
    print(f"📈 BTC Coverage: {len(successful)}/{total_expected_btc:.0f} estimated ({coverage_pct:.1f}%)")
    
    # Write manifest
    with open(MANIFEST_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'venue', 'filename', 'key', 'size_bytes', 'sha256', 'attempts', 'status'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"📄 Manifest saved: {MANIFEST_FILE}")
    
    # Final verdict
    if coverage_pct >= 80:  # Lower threshold since we're filtering for BTC only
        print(f"\n✅ Coverage gate PASSED: {len(successful)} BTC files downloaded. Ready for beacon processing.")
    else:
        print(f"\n❌ Coverage gate FAILED: {len(successful)} BTC files ({coverage_pct:.1f}%). Reason(s): {', '.join(set(r['status'] for r in failed))}")

if __name__ == "__main__":
    main()
