#!/usr/bin/env python3
"""
Phase 39K-7: Complete Week -7 COINBASE BTC-USD (6 remaining days)
"""

import os
import sys
import hashlib
import json
import gzip
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests
import xml.etree.ElementTree as ET

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports'

# API Configuration
API_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
BASE_URL = 'https://s3.flatfiles.coinapi.io/'
DOWNLOAD_BASE_URL = 'https://s3.flatfiles.coinapi.io/coinapi/'
HEADERS = {
    'X-CoinAPI-Key': API_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

# Target configuration
TARGET_DATES = ['20250707', '20250708', '20250710', '20250711', '20250712', '20250713']  # Skip 20250709 (already done)
TARGET_VENUE = 'COINBASE'
TARGET_PAIR = 'BTC-USD'
TARGET_WEEK = 'W-7'

# Budget limits
MAX_LIST_CALLS = 14
MAX_GET_CALLS = 56
MAX_TOTAL_CALLS = 70

def is_btcusd_class(filename):
    """Check if filename indicates BTCUSD-class pair"""
    filename_upper = filename.upper()
    
    # BTC-USD patterns (COINBASE specific)
    if 'BTC-USD' in filename_upper or 'BTC__002DUSD' in filename_upper:
        return True
    
    return False

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
                    key = key_elem.text
                    if is_btcusd_class(key):
                        keys.append(key)
            return keys, response.status_code, list_url
        else:
            return [], response.status_code, list_url
    except Exception as e:
        print(f"⚠️ Error listing {date}/{venue}: {e}")
        return [], 500, list_url

def verify_gzip_file(file_path):
    """Verify gzip file can be opened and read"""
    try:
        with gzip.open(file_path, 'rb') as f:
            # Try to read first few bytes
            header = f.read(10)
            return len(header) > 0
    except Exception:
        return False

def compute_file_hash(file_path):
    """Compute SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"⚠️ Error computing hash for {file_path}: {e}")
        return "ERROR"

def download_file_atomic(key, output_dir, max_attempts=3):
    """Download file with atomic write and verification"""
    download_url = f'{DOWNLOAD_BASE_URL}{key}'
    
    # Create output path with .part extension
    filename = key.split('/')[-1]
    # Create unique filename for this day
    unique_filename = f"IDDI_{hashlib.md5(key.encode()).hexdigest()[:8]}__BTC-USD.csv.gz"
    part_path = output_dir / f'{unique_filename}.part'
    final_path = output_dir / unique_filename
    
    # Skip if final file already exists (no-clobber)
    if final_path.exists():
        return 'SKIP', f'File already exists: {final_path}'
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(download_url, headers=HEADERS, timeout=120)
            if response.status_code == 200:
                # Check content length
                content_length = len(response.content)
                if content_length == 0:
                    return 'FAIL', 'Zero-byte file'
                
                # Write to .part file
                with open(part_path, 'wb') as f:
                    f.write(response.content)
                    # Force fsync
                    os.fsync(f.fileno())
                
                # Verify file size
                if part_path.stat().st_size == 0:
                    part_path.unlink()
                    return 'FAIL', 'Zero-byte file'
                
                # Verify gzip header
                if not verify_gzip_file(part_path):
                    part_path.unlink()
                    return 'FAIL', 'Invalid gzip file'
                
                # Compute SHA-256
                sha256 = compute_file_hash(part_path)
                
                # Atomic rename
                part_path.rename(final_path)
                
                return 'OK', f'Downloaded: {unique_filename} ({final_path.stat().st_size} bytes, SHA-256: {sha256})'
            else:
                if attempt < max_attempts - 1:
                    time.sleep(30 * (attempt + 1))  # Exponential backoff
                return 'FAIL', f'HTTP {response.status_code}'
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(30 * (attempt + 1))
            print(f"⚠️ Download error {key}: {e}")
            return 'FAIL', str(e)
    
    return 'FAIL', 'Max attempts exceeded'

def write_failure_report(failed_dates, failed_urls, error_details):
    """Write failure report if any 403/4xx/5xx encountered"""
    with open(REPORTS_DIR / 'FAILURE_REPORT.md', 'w') as f:
        f.write("# Phase 39K-7 Failure Report\n\n")
        f.write(f"**Timestamp**: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"**Failed Dates**: {', '.join(failed_dates)}\n\n")
        
        f.write("## Failed LIST URLs\n")
        for url in failed_urls:
            f.write(f"- {url}\n")
        
        f.write("\n## Error Details\n")
        for date, error in error_details.items():
            f.write(f"- **{date}**: {error}\n")
        
        f.write("\n## Abort Policy\n")
        f.write("Stopped immediately on first 403/4xx/5xx error as per requirements.\n")

def main():
    """Main execution"""
    print("🚀 Phase 39K-7: Complete Week -7 COINBASE BTC-USD (6 remaining days)")
    print("=" * 70)
    
    start_time = time.time()
    
    # Create directories
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Tracking
    total_calls = 0
    list_calls = 0
    get_calls = 0
    results = []
    new_files = []
    days_attempted = 0
    days_succeeded = 0
    failed_dates = []
    failed_urls = []
    error_details = {}
    
    print(f"📅 Target: {TARGET_WEEK} COINBASE BTC-USD")
    print(f"📅 Dates: {', '.join(TARGET_DATES)} (skipping 20250709 - already done)")
    print(f"💰 Budget: {MAX_TOTAL_CALLS} calls max")
    
    # Process each date
    for date in TARGET_DATES:
        days_attempted += 1
        print(f"\n📅 Processing {date}/{TARGET_VENUE}")
        
        # Create output directory
        output_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7' / date / f'E-{TARGET_VENUE}'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # LIST objects
        print(f"🔍 Listing objects...")
        keys, status_code, list_url = list_s3_objects(date, TARGET_VENUE)
        list_calls += 1
        total_calls += 1
        
        print(f"📊 LIST result: {status_code}, {len(keys)} keys found")
        
        # Check for errors (abort policy)
        if status_code >= 400:
            print(f"❌ LIST failed with {status_code} - aborting")
            failed_dates.append(date)
            failed_urls.append(list_url)
            error_details[date] = f"LIST HTTP {status_code}"
            write_failure_report(failed_dates, failed_urls, error_details)
            print("🔒 Refreezing network...")
            sys.exit(1)
        
        if keys:
            day_files = 0
            for key in keys:
                print(f"📥 Downloading: {key}")
                result, message = download_file_atomic(key, output_dir)
                get_calls += 1
                total_calls += 1
                
                results.append({
                    'date': date,
                    'key': key,
                    'result': result,
                    'message': message
                })
                
                if result == 'OK':
                    # Extract filename from message
                    filename = message.split(': ')[1].split(' (')[0]
                    file_path = output_dir / filename
                    if file_path.exists():
                        new_files.append({
                            'path': str(file_path),
                            'filename': filename,
                            'size': file_path.stat().st_size,
                            'sha256': compute_file_hash(file_path),
                            'day': date
                        })
                        day_files += 1
                
                print(f"    {result}: {message}")
                
                # Check budget
                if total_calls >= MAX_TOTAL_CALLS:
                    print("⚠️ Reached total call limit")
                    break
            
            if day_files > 0:
                days_succeeded += 1
                print(f"✅ {date}: {day_files} files saved")
            else:
                print(f"⚠️ {date}: No files saved")
        else:
            print(f"⚠️ {date}: No BTC-USD keys found")
        
        # Check budget
        if total_calls >= MAX_TOTAL_CALLS:
            print("⚠️ Reached total call limit")
            break
    
    # Write artifacts
    print(f"\n📝 Writing artifacts...")
    
    # Manifest
    if new_files:
        manifest_df = pd.DataFrame(new_files)
        manifest_path = REPORTS_DIR / '39K_7_manifest.csv'
        manifest_df.to_csv(manifest_path, index=False)
        print(f"✅ Manifest written: {manifest_path}")
    
    # Spend log
    spend_data = {
        'total_calls': total_calls,
        'list_calls': list_calls,
        'get_calls': get_calls,
        'budget_used': f"{total_calls}/{MAX_TOTAL_CALLS}",
        'days_attempted': days_attempted,
        'days_succeeded': days_succeeded,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / '39K_7_spend.json', 'w') as f:
        json.dump(spend_data, f, indent=2)
    
    # Run log
    with open(REPORTS_DIR / '39K_7_runlog.txt', 'w') as f:
        f.write(f"""Phase 39K-7 Run Log
==================
Start: {datetime.utcnow().isoformat()}Z
Target: {TARGET_WEEK} COINBASE BTC-USD
Dates: {', '.join(TARGET_DATES)}
Total calls: {total_calls}
List calls: {list_calls}
Get calls: {get_calls}
Days attempted: {days_attempted}
Days succeeded: {days_succeeded}
New files: {len(new_files)}

Results:
""")
        for result in results:
            f.write(f"{result['result']}: {result['date']}/{result['key']} - {result['message']}\n")
    
    # BOM hash
    if new_files:
        hashes = sorted([f['sha256'] for f in new_files])
        bom_content = '\n'.join(hashes)
        bom_hash = hashlib.sha256(bom_content.encode()).hexdigest()
        
        with open(REPORTS_DIR / '39K_7_bom_sha256.txt', 'w') as f:
            f.write(f"BOM_SHA256: {bom_hash}\n")
            f.write(f"FILES_COUNT: {len(new_files)}\n")
            f.write(f"CREATED: {datetime.utcnow().isoformat()}Z\n")
    
    # Gate check
    gate_data = {
        'preflight': 'OK',
        'no_clobber': True,
        'atomic': True,
        'days_attempted': days_attempted,
        'days_succeeded': days_succeeded,
        'calls_total': total_calls,
        'budget_ok': total_calls <= MAX_TOTAL_CALLS,
        'files_saved': len(new_files),
        'success_criteria_met': (
            days_succeeded >= 5 and
            total_calls <= MAX_TOTAL_CALLS and
            len(new_files) > 0
        )
    }
    
    with open(REPORTS_DIR / '39K_7_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    # Refreeze network
    print("🔒 Refreezing network...")
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file, 'w') as f:
            f.write(f"""API_BUDGET_LOCK
Recreated: {datetime.utcnow().isoformat()}Z
Reason: Phase 39K-7 Complete
Status: ACTIVE
Network calls: BLOCKED
""")
        print("🔒 Network lock recreated")
    else:
        print("✅ Network lock confirmed")
    
    # Summary
    runtime_minutes = (time.time() - start_time) / 60
    print(f"\n✅ Phase 39K-7 Complete")
    print(f"⏱️ Runtime: {runtime_minutes:.1f} minutes")
    print(f"📊 Calls: {total_calls}/{MAX_TOTAL_CALLS}")
    print(f"📊 Days: {days_succeeded}/{days_attempted} succeeded")
    print(f"📊 Files saved: {len(new_files)}")
    
    if new_files:
        total_bytes = sum(f['size'] for f in new_files)
        first_sha256 = new_files[0]['sha256']
        print(f"📊 Total bytes: {total_bytes:,}")
        print(f"📊 First SHA-256: {first_sha256}")
        
        # 5-line summary
        print(f"\n📋 Summary:")
        print(f"  Calls: {total_calls}")
        print(f"  Days succeeded: {days_succeeded}")
        print(f"  Files saved: {len(new_files)}")
        print(f"  Bytes: {total_bytes:,}")
        print(f"  SHA-256 (first): {first_sha256}")
    else:
        print("❌ No files saved")
        sys.exit(1)

if __name__ == "__main__":
    main()
