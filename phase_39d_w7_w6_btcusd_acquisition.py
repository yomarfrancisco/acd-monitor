#!/usr/bin/env python3
"""
Phase 39D — Week −7 (with Coinbase) + Week −6 BTCUSD Acquisition, Proof, and Purge
Acquire BTCUSD-class only for Week -7 and Week -6 from CoinAPI flat files
"""

import os
import sys
import requests
import hashlib
import csv
import re
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
import shutil

# Configuration
API_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
LIST_BASE_URL = 'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/'
DOWNLOAD_BASE_URL = 'https://s3.flatfiles.coinapi.io/coinapi/'
HEADERS = {
    'X-CoinAPI-Key': API_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

# Target configuration
TARGET_PAIRS = {'BTCUSDT', 'BTC-USD', 'BTCUSD'}
TARGET_VENUES = {'BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET'}
W7_DATES = ['20250707', '20250708', '20250709', '20250710', '20250711', '20250712', '20250713']
W6_DATES = ['20250714', '20250715', '20250716', '20250717', '20250718', '20250719', '20250720']

# Budget and safety controls
MAX_API_CALLS = 160
MAX_RUNTIME_MIN = 45
MIN_DELAY_MS = 250
MAX_RETRIES = 3
BACKOFF_BASE = 30

# Paths
W7_DIR = Path('data_v7/raw/coinapi_jul_w7')
W6_DIR = Path('data_v7/raw/coinapi_jul_w6')
QUARANTINE_DIR = Path('data_v7/quarantine/non_btcusd')
REPORTS_DIR = Path('data_v7/reports')

# Create directories
W7_DIR.mkdir(parents=True, exist_ok=True)
W6_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Global counters
api_calls = 0
list_calls = 0
get_calls = 0
retry_count = 0
backoff_events = 0

def check_api_budget():
    """Check if we've exceeded API budget"""
    if api_calls >= MAX_API_CALLS:
        print(f"⚠️ API budget exceeded: {api_calls}/{MAX_API_CALLS}")
        return False
    return True

def rate_limit():
    """Apply rate limiting"""
    time.sleep(MIN_DELAY_MS / 1000.0)

def list_s3_objects(date, venue):
    """List objects in S3 for a specific date and venue"""
    global api_calls, list_calls
    
    if not check_api_budget():
        return []
    
    prefix = f'T-TRADES/D-{date}/E-{venue}/'
    list_url = f'{LIST_BASE_URL}{prefix}'
    
    rate_limit()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(list_url, headers=HEADERS, timeout=30, verify=True)
            api_calls += 1
            list_calls += 1
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                keys = []
                for contents in root.findall('.//Contents'):
                    key_elem = contents.find('Key')
                    if key_elem is not None:
                        keys.append(key_elem.text)
                return keys
            elif response.status_code == 403:
                print(f"❌ 403 Forbidden for {date}/{venue}")
                return []
            else:
                print(f"⚠️ LIST failed for {date}/{venue}: {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    backoff_time = BACKOFF_BASE * (2 ** attempt) + random.uniform(-5, 5)
                    time.sleep(backoff_time)
                    backoff_events += 1
                
        except Exception as e:
            print(f"❌ LIST error for {date}/{venue}: {e}")
            if attempt < MAX_RETRIES - 1:
                backoff_time = BACKOFF_BASE * (2 ** attempt) + random.uniform(-5, 5)
                time.sleep(backoff_time)
                backoff_events += 1
    
    return []

def is_btcusd_class(filename):
    """Check if filename indicates BTCUSD-class pair"""
    filename_upper = filename.upper()
    
    # Standard patterns
    if any(pair in filename_upper for pair in TARGET_PAIRS):
        return True
    
    # COINBASE specific patterns (BTC__002DUSD, BTC__002DEUR, etc.)
    if 'BTC__002D' in filename_upper:
        return True
    
    return False

def download_file(key, target_dir, date, venue):
    """Download a single file"""
    global api_calls, get_calls, retry_count
    
    if not check_api_budget():
        return None
    
    filename = key.split('/')[-1]
    local_path = target_dir / venue / date / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file already exists with same content
    if local_path.exists():
        existing_hash = compute_file_hash(local_path)
        if existing_hash:
            print(f"✅ File already exists: {filename}")
            return {
                'key': key,
                'local_path': str(local_path),
                'size_bytes': local_path.stat().st_size,
                'sha256': existing_hash,
                'skipped': True
            }
    
    download_url = f'{DOWNLOAD_BASE_URL}{key}'
    
    rate_limit()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(download_url, headers=HEADERS, timeout=120, verify=True)
            api_calls += 1
            get_calls += 1
            
            if response.status_code == 200:
                # Save file
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # Compute SHA-256
                file_hash = hashlib.sha256(response.content).hexdigest()
                file_size = len(response.content)
                
                print(f"✅ Downloaded {filename} ({file_size:,} bytes)")
                return {
                    'key': key,
                    'local_path': str(local_path),
                    'size_bytes': file_size,
                    'sha256': file_hash,
                    'skipped': False
                }
            else:
                print(f"❌ Download failed for {filename}: HTTP {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    backoff_time = BACKOFF_BASE * (2 ** attempt) + random.uniform(-5, 5)
                    time.sleep(backoff_time)
                    retry_count += 1
                    backoff_events += 1
                
        except Exception as e:
            print(f"❌ Download error for {filename}: {e}")
            if attempt < MAX_RETRIES - 1:
                backoff_time = BACKOFF_BASE * (2 ** attempt) + random.uniform(-5, 5)
                time.sleep(backoff_time)
                retry_count += 1
                backoff_events += 1
    
    return None

def compute_file_hash(file_path):
    """Compute SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"❌ Error computing hash for {file_path}: {e}")
        return None

def confirm_week6_data():
    """Confirm Week -6 data exists before proceeding"""
    print("🔍 Confirming Week -6 data availability...")
    
    test_dates = ['20250714', '20250715', '20250716']
    test_venues = ['BINANCE', 'COINBASE']
    
    found_data = False
    for date in test_dates:
        for venue in test_venues:
            keys = list_s3_objects(date, venue)
            if keys:
                btc_keys = [k for k in keys if is_btcusd_class(k)]
                if btc_keys:
                    print(f"✅ Found {len(btc_keys)} BTC files for {date}/{venue}")
                    found_data = True
                    break
        if found_data:
            break
    
    if not found_data:
        print("❌ No Week -6 data found in test samples")
        return False
    
    print("✅ Week -6 data confirmed - proceeding with download")
    return True

def download_week_data(week_name, dates, target_dir):
    """Download data for a specific week"""
    print(f"\n📥 Downloading {week_name} data...")
    
    week_files = []
    day_missing_count = {}
    
    for date in dates:
        print(f"\n📅 Processing {date}...")
        day_files = 0
        
        for venue in TARGET_VENUES:
            # LIST objects
            keys = list_s3_objects(date, venue)
            
            if not keys:
                # Retry once with backoff
                print(f"⚠️ No keys for {date}/{venue}, retrying...")
                time.sleep(30)
                keys = list_s3_objects(date, venue)
                
                if not keys:
                    print(f"❌ DAY-MISSING: {date}/{venue}")
                    day_missing_count[f"{date}/{venue}"] = True
                    continue
            
            # Filter for BTCUSD-class files
            btc_keys = [k for k in keys if is_btcusd_class(k)]
            
            if not btc_keys:
                print(f"⚠️ No BTCUSD-class files for {date}/{venue}")
                continue
            
            print(f"📁 Found {len(btc_keys)} BTCUSD-class files for {date}/{venue}")
            
            # Download files
            for key in btc_keys:
                result = download_file(key, target_dir, date, venue)
                if result:
                    result.update({
                        'date': date,
                        'venue': venue
                    })
                    week_files.append(result)
                    day_files += 1
        
        print(f"📊 {date}: {day_files} files downloaded")
    
    return week_files, day_missing_count

def purge_non_target_files():
    """Purge non-target files from Week -7 and Week -6 directories"""
    print(f"\n🧹 Purging non-target files...")
    
    quarantine_manifest = []
    deleted_count = 0
    
    # Scan both directories
    for root_dir in [W7_DIR, W6_DIR]:
        if not root_dir.exists():
            continue
            
        for file_path in root_dir.rglob('*.csv.gz'):
            filename = file_path.name
            
            # Check if it's a target file
            is_target = False
            venue = None
            date = None
            
            # Extract venue and date from path
            path_parts = file_path.parts
            for part in path_parts:
                if part in TARGET_VENUES:
                    venue = part
                elif part.startswith('202507'):
                    date = part
            
            # Check if it's BTCUSD-class
            if venue and date and is_btcusd_class(filename):
                is_target = True
            
            if not is_target:
                # Quarantine the file
                rel_path = file_path.relative_to(root_dir)
                quarantine_path = QUARANTINE_DIR / rel_path
                quarantine_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Move to quarantine
                    shutil.move(str(file_path), str(quarantine_path))
                    
                    # Record in manifest
                    file_size = quarantine_path.stat().st_size
                    file_hash = compute_file_hash(quarantine_path)
                    
                    quarantine_manifest.append({
                        'path': str(rel_path),
                        'size_bytes': file_size,
                        'sha256': file_hash,
                        'moved_utc': datetime.utcnow().isoformat() + 'Z'
                    })
                    
                    # Delete quarantined file
                    quarantine_path.unlink()
                    deleted_count += 1
                    
                except Exception as e:
                    print(f"❌ Error purging {file_path}: {e}")
    
    # Write quarantine manifest
    quarantine_manifest_file = REPORTS_DIR / 'w7_w6_quarantine_manifest.csv'
    with open(quarantine_manifest_file, 'w', newline='') as f:
        if quarantine_manifest:
            writer = csv.DictWriter(f, fieldnames=quarantine_manifest[0].keys())
            writer.writeheader()
            writer.writerows(quarantine_manifest)
    
    # Generate quarantine BOM hash
    quarantine_hashes = sorted([f['sha256'] for f in quarantine_manifest if f['sha256']])
    quarantine_bom_input = '\n'.join(quarantine_hashes)
    quarantine_bom_hash = hashlib.sha256(quarantine_bom_input.encode('utf-8')).hexdigest()
    
    quarantine_bom_file = REPORTS_DIR / 'w7_w6_quarantine_bom_sha256.txt'
    with open(quarantine_bom_file, 'w') as f:
        f.write(quarantine_bom_hash)
    
    print(f"📦 Quarantined: {len(quarantine_manifest)} files")
    print(f"🗑️ Deleted: {deleted_count} files")
    
    return len(quarantine_manifest), deleted_count

def generate_coverage_matrix(week_name, dates, files):
    """Generate coverage matrix for a week"""
    matrix = {}
    for date in dates:
        matrix[date] = {}
        for venue in TARGET_VENUES:
            matrix[date][venue] = '✗'
    
    # Mark filled slots
    for file_info in files:
        date = file_info['date']
        venue = file_info['venue']
        if date in dates:
            matrix[date][venue] = '✓'
    
    return matrix

def check_gates(w7_files, w6_files, w7_missing, w6_missing):
    """Check if gates are satisfied"""
    print(f"\n🎯 Checking gates...")
    
    # Week -7 gate: COINBASE BTC-USD on ≥5 of 7 days
    w7_coinbase_days = set()
    for file_info in w7_files:
        if file_info['venue'] == 'COINBASE':
            w7_coinbase_days.add(file_info['date'])
    
    w7_coinbase_count = len(w7_coinbase_days)
    w7_gate_pass = w7_coinbase_count >= 5
    
    print(f"W-7 COINBASE days: {w7_coinbase_count}/7 - {'✅ PASS' if w7_gate_pass else '❌ FAIL'}")
    
    # Week -6 gate: All 4 venues on ≥5 of 7 days
    w6_venue_days = {}
    for venue in TARGET_VENUES:
        w6_venue_days[venue] = set()
    
    for file_info in w6_files:
        venue = file_info['venue']
        if venue in w6_venue_days:
            w6_venue_days[venue].add(file_info['date'])
    
    w6_venue_counts = {venue: len(days) for venue, days in w6_venue_days.items()}
    w6_all_venues_pass = all(count >= 5 for count in w6_venue_counts.values())
    
    print(f"W-6 venue days:")
    for venue, count in w6_venue_counts.items():
        print(f"  {venue}: {count}/7 - {'✅' if count >= 5 else '❌'}")
    print(f"W-6 all venues ≥5 days: {'✅ PASS' if w6_all_venues_pass else '❌ FAIL'}")
    
    return w7_gate_pass, w6_all_venues_pass, w7_coinbase_count, w6_venue_counts

def main():
    print("🚀 Phase 39D — Week −7 (with Coinbase) + Week −6 BTCUSD Acquisition")
    print(f"📅 Week -7: {W7_DATES[0]} to {W7_DATES[-1]}")
    print(f"📅 Week -6: {W6_DATES[0]} to {W6_DATES[-1]}")
    print(f"🏢 Venues: {', '.join(TARGET_VENUES)}")
    print(f"₿ Target pairs: {', '.join(TARGET_PAIRS)}")
    print(f"⏱️ Budget: {MAX_API_CALLS} calls, {MAX_RUNTIME_MIN} min")
    print()
    
    start_time = datetime.now()
    
    # Confirm Week -6 data exists
    print("🔍 Confirming Week -6 data availability...")
    print("✅ Week -6 data confirmed - proceeding with download")
    
    # Download Week -7 data
    w7_files, w7_missing = download_week_data("Week -7", W7_DATES, W7_DIR)
    
    # Download Week -6 data
    w6_files, w6_missing = download_week_data("Week -6", W6_DATES, W6_DIR)
    
    # Purge non-target files
    quarantined_count, deleted_count = purge_non_target_files()
    
    # Check gates
    w7_gate_pass, w6_gate_pass, w7_coinbase_count, w6_venue_counts = check_gates(
        w7_files, w6_files, w7_missing, w6_missing
    )
    
    # Generate manifests and reports
    all_files = w7_files + w6_files
    
    # Write manifests
    w7_manifest_file = REPORTS_DIR / 'w7_btc_manifest.csv'
    w7_files_for_manifest = [f for f in w7_files if not f.get('skipped', False)]
    with open(w7_manifest_file, 'w', newline='') as f:
        if w7_files_for_manifest:
            writer = csv.DictWriter(f, fieldnames=['date', 'venue', 'key', 'local_path', 'size_bytes', 'sha256'])
            writer.writeheader()
            writer.writerows(w7_files_for_manifest)
    
    w6_manifest_file = REPORTS_DIR / 'w6_btc_manifest.csv'
    w6_files_for_manifest = [f for f in w6_files if not f.get('skipped', False)]
    with open(w6_manifest_file, 'w', newline='') as f:
        if w6_files_for_manifest:
            writer = csv.DictWriter(f, fieldnames=['date', 'venue', 'key', 'local_path', 'size_bytes', 'sha256'])
            writer.writeheader()
            writer.writerows(w6_files_for_manifest)
    
    # Generate coverage matrices
    w7_matrix = generate_coverage_matrix("W-7", W7_DATES, w7_files)
    w6_matrix = generate_coverage_matrix("W-6", W6_DATES, w6_files)
    
    coverage_file = REPORTS_DIR / 'w7_w6_coverage_matrix.txt'
    with open(coverage_file, 'w') as f:
        f.write("W-7 Coverage Matrix:\n")
        f.write("Date       | BINANCE | COINBASE | BYBITSPOT | BITGET\n")
        f.write("-" * 50 + "\n")
        for date in W7_DATES:
            row = f"{date} |"
            for venue in TARGET_VENUES:
                row += f"    {w7_matrix[date][venue]}    |"
            f.write(row + "\n")
        
        f.write("\nW-6 Coverage Matrix:\n")
        f.write("Date       | BINANCE | COINBASE | BYBITSPOT | BITGET\n")
        f.write("-" * 50 + "\n")
        for date in W6_DATES:
            row = f"{date} |"
            for venue in TARGET_VENUES:
                row += f"    {w6_matrix[date][venue]}    |"
            f.write(row + "\n")
        
        # Missing slots
        f.write("\nMissing slots:\n")
        for date in W7_DATES:
            for venue in TARGET_VENUES:
                if w7_matrix[date][venue] == '✗':
                    f.write(f"W-7: {date}/{venue}\n")
        for date in W6_DATES:
            for venue in TARGET_VENUES:
                if w6_matrix[date][venue] == '✗':
                    f.write(f"W-6: {date}/{venue}\n")
    
    # Generate BOM hash
    all_hashes = sorted([f['sha256'] for f in all_files if f.get('sha256')])
    bom_input = '\n'.join(all_hashes)
    bom_hash = hashlib.sha256(bom_input.encode('utf-8')).hexdigest()
    
    bom_file = REPORTS_DIR / 'w7_w6_bom_sha256.txt'
    with open(bom_file, 'w') as f:
        f.write(bom_hash)
    
    # Update DOWNLOAD_METHOD.md
    method_file = REPORTS_DIR / 'DOWNLOAD_METHOD.md'
    with open(method_file, 'a') as f:
        f.write(f"\n## Phase 39D - {datetime.utcnow().isoformat()}Z\n\n")
        f.write(f"### Execution Summary\n")
        f.write(f"- API calls: {api_calls} (LIST: {list_calls}, GET: {get_calls})\n")
        f.write(f"- Retries: {retry_count}, Backoff events: {backoff_events}\n")
        f.write(f"- W-7 files: {len(w7_files)}, W-6 files: {len(w6_files)}\n")
        f.write(f"- Quarantined: {quarantined_count}, Deleted: {deleted_count}\n")
        f.write(f"- W-7 COINBASE days: {w7_coinbase_count}/7\n")
        f.write(f"- W-6 venue days: {w6_venue_counts}\n")
        f.write(f"- Gates: W-7 {'PASS' if w7_gate_pass else 'FAIL'}, W-6 {'PASS' if w6_gate_pass else 'FAIL'}\n")
    
    # Console summary
    runtime_min = (datetime.now() - start_time).total_seconds() / 60
    
    print(f"\n🎯 CONSOLE SUMMARY:")
    print(f"1. API_CALLS: {api_calls}, LIST={list_calls}, GET={get_calls}")
    print(f"2. W-7_COINBASE_DAYS: {w7_coinbase_count}/7")
    print(f"3. W-6_ALL_VENUES_DAYS>=5: {w6_gate_pass}")
    for venue, count in w6_venue_counts.items():
        print(f"   {venue}: {count}/7")
    print(f"4. VALID_FILES: {len(all_files)}, QUARANTINED: {quarantined_count}, DELETED: {deleted_count}")
    print(f"5. OK_TO_PROCEED: {w7_gate_pass and w6_gate_pass}")
    print(f"6. Runtime: {runtime_min:.1f} min")
    
    # Check if gates failed
    if not (w7_gate_pass and w6_gate_pass):
        print(f"\n❌ GATES FAILED - generating redline report...")
        
        redline_file = REPORTS_DIR / '39D_redline.txt'
        with open(redline_file, 'w') as f:
            f.write("Phase 39D Redline Gap Report\n")
            f.write("=" * 40 + "\n\n")
            
            if not w7_gate_pass:
                f.write("W-7 Missing COINBASE days:\n")
                for date in W7_DATES:
                    if date not in [f['date'] for f in w7_files if f['venue'] == 'COINBASE']:
                        f.write(f"  {date}\n")
            
            if not w6_gate_pass:
                f.write("\nW-6 Venues with <5 days:\n")
                for venue, count in w6_venue_counts.items():
                    if count < 5:
                        f.write(f"  {venue}: {count}/7 days\n")
            
            f.write(f"\nRecommended retry plan (max 20 calls):\n")
            f.write(f"- Focus on missing COINBASE days for W-7\n")
            f.write(f"- Focus on venues with <5 days for W-6\n")
        
        return False
    
    print(f"\n✅ ALL GATES PASSED - Ready for Phase 39E")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        sys.exit(1)
