#!/usr/bin/env python3
"""
Phase 42A-v7f-Retry — Week -7 Remaining Dates/Venues
Retry download for July 8-13, 2025 across all venues (focusing on BTC pairs)
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

# Remaining dates: July 8-13, 2025 (we already have July 7th)
REMAINING_DATES = ['20250708', '20250709', '20250710', '20250711', '20250712', '20250713']
ALL_VENUES = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

# Budget constraints
MAX_HTTP_CALLS = 80
MAX_RUNTIME_MINUTES = 45
MAX_WORKERS = 2

# Output paths
OUTPUT_DIR = Path('data_v7/raw/coinapi_jul_w7')
MANIFEST_FILE = 'data_v7/reports/jul_w7_retry_manifest.csv'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Path('data_v7/reports').mkdir(parents=True, exist_ok=True)

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

def is_priority_btc_pair(filename):
    """Check if file contains priority BTC trading pairs"""
    priority_pairs = ['BTCUSDT', 'BTCFDUSD', 'ETHBTC', 'LTCBTC', 'BTCJPY']
    filename_upper = filename.upper()
    return any(pair in filename_upper for pair in priority_pairs)

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
                
                priority_flag = "🔥" if is_priority_btc_pair(filename) else "₿"
                print(f"{priority_flag} Downloaded {filename} ({file_size:,} bytes)")
                return {
                    'date': date,
                    'venue': venue,
                    'filename': filename,
                    'key': key,
                    'size_bytes': file_size,
                    'sha256': sha256_hash,
                    'attempts': attempt + 1,
                    'status': 'success',
                    'is_priority': is_priority_btc_pair(filename)
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
                        'status': f'failed_http_{response.status_code}',
                        'is_priority': is_priority_btc_pair(filename)
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
                    'status': f'failed_error_{str(e)[:50]}',
                    'is_priority': is_priority_btc_pair(filename)
                }
    
    return None

def main():
    print("🔄 Phase 42A-v7f-Retry — Week -7 Remaining Dates/Venues")
    print(f"📅 Remaining dates: {', '.join(REMAINING_DATES)}")
    print(f"🏢 All venues: {', '.join(ALL_VENUES)}")
    print(f"₿ Focus: BTC trading pairs (🔥 = priority pairs)")
    print(f"⏱️  Budget: {MAX_HTTP_CALLS} calls, {MAX_RUNTIME_MINUTES} min")
    print()
    
    start_time = time.time()
    http_calls = 0
    results = []
    
    print(f"📋 Expected venue-days: {len(REMAINING_DATES)} days × {len(ALL_VENUES)} venues = {len(REMAINING_DATES) * len(ALL_VENUES)}")
    
    # Check existing files and find missing BTC files
    missing_files = []
    priority_missing = []
    btc_files_found = 0
    total_files_found = 0
    
    for date in REMAINING_DATES:
        for venue in ALL_VENUES:
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
                    if is_priority_btc_pair(key.split('/')[-1]):
                        priority_missing.append((date, venue, key))
                else:
                    print(f"✅ Already have {key.split('/')[-1]}")
    
    print(f"\n📊 File Analysis:")
    print(f"Total files found: {total_files_found}")
    print(f"BTC files found: {btc_files_found}")
    print(f"Missing BTC files: {len(missing_files)}")
    print(f"🔥 Priority BTC files missing: {len(priority_missing)}")
    print(f"📞 HTTP calls used so far: {http_calls}/{MAX_HTTP_CALLS}")
    
    if len(missing_files) == 0:
        print("🎉 All BTC files already downloaded!")
        return
    
    # Prioritize downloads: priority pairs first, then others
    download_queue = priority_missing + [f for f in missing_files if f not in priority_missing]
    print(f"\n⬇️  Starting downloads with {MAX_WORKERS} workers...")
    print(f"🔥 Priority files first: {len(priority_missing)}")
    print(f"₿ Other BTC files: {len(missing_files) - len(priority_missing)}")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit download tasks
        future_to_file = {}
        for date, venue, key in download_queue:
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
    priority_successful = [r for r in successful if r.get('is_priority', False)]
    
    print(f"✅ Successful: {len(successful)}")
    print(f"🔥 Priority successful: {len(priority_successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    # Coverage report
    total_venue_days = len(REMAINING_DATES) * len(ALL_VENUES)
    print(f"📈 Venue-days covered: {len(set((r['date'], r['venue']) for r in successful))}/{total_venue_days}")
    
    # Write manifest
    with open(MANIFEST_FILE, 'w', newline='') as f:
        fieldnames = ['date', 'venue', 'filename', 'key', 'size_bytes', 'sha256', 'attempts', 'status', 'is_priority']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"📄 Manifest saved: {MANIFEST_FILE}")
    
    # Final verdict
    if len(priority_successful) >= 10:  # At least 10 priority BTC pairs
        print(f"\n✅ Coverage gate PASSED: {len(priority_successful)} priority BTC files downloaded. Ready for beacon processing.")
    else:
        print(f"\n❌ Coverage gate FAILED: Only {len(priority_successful)} priority BTC files. Need more major pairs.")

if __name__ == "__main__":
    main()
