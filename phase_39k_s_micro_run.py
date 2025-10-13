#!/usr/bin/env python3
"""
Phase 39K-S: Preflight + Micro-run (COINBASE BTC-USD, W-7 single day)
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
TARGET_DATE = '20250709'
TARGET_VENUE = 'COINBASE'
TARGET_PAIR = 'BTC-USD'
TARGET_WEEK = 'W-7'

# Budget limits
MAX_LIST_CALLS = 6
MAX_GET_CALLS = 6
MAX_TOTAL_CALLS = 12
CONCURRENCY = 2

def is_btcusd_class(filename):
    """Check if filename indicates BTCUSD-class pair"""
    filename_upper = filename.upper()
    
    # BTC-USD patterns
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
            return keys, response.status_code
        else:
            return [], response.status_code
    except Exception as e:
        print(f"⚠️ Error listing {date}/{venue}: {e}")
        return [], 500

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

def main():
    """Main execution"""
    print("🚀 Phase 39K-S: Preflight + Micro-run (COINBASE BTC-USD, W-7 single day)")
    print("=" * 70)
    
    start_time = time.time()
    
    # Create directories
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7' / TARGET_DATE / f'E-{TARGET_VENUE}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Tracking
    total_calls = 0
    list_calls = 0
    get_calls = 0
    results = []
    new_files = []
    
    print(f"📅 Target: {TARGET_WEEK} {TARGET_DATE}/{TARGET_VENUE} {TARGET_PAIR}")
    print(f"📁 Output: {output_dir}")
    
    # LIST objects
    print(f"🔍 Listing objects...")
    keys, status_code = list_s3_objects(TARGET_DATE, TARGET_VENUE)
    list_calls += 1
    total_calls += 1
    
    print(f"📊 LIST result: {status_code}, {len(keys)} keys found")
    
    if keys:
        for key in keys[:MAX_GET_CALLS]:  # Limit to budget
            print(f"📥 Downloading: {key}")
            result, message = download_file_atomic(key, output_dir)
            get_calls += 1
            total_calls += 1
            
            results.append({
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
                        'sha256': compute_file_hash(file_path)
                    })
            
            print(f"    {result}: {message}")
            
            # Check budget
            if total_calls >= MAX_TOTAL_CALLS:
                print("⚠️ Reached total call limit")
                break
    
    # Write artifacts
    print(f"\n📝 Writing artifacts...")
    
    # Manifest
    if new_files:
        manifest_df = pd.DataFrame(new_files)
        manifest_path = REPORTS_DIR / '39K_S_manifest.csv'
        manifest_df.to_csv(manifest_path, index=False)
        print(f"✅ Manifest written: {manifest_path}")
    
    # Spend log
    spend_data = {
        'total_calls': total_calls,
        'list_calls': list_calls,
        'get_calls': get_calls,
        'budget_used': f"{total_calls}/{MAX_TOTAL_CALLS}",
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / '39K_S_spend.json', 'w') as f:
        json.dump(spend_data, f, indent=2)
    
    # Run log
    with open(REPORTS_DIR / '39K_S_runlog.txt', 'w') as f:
        f.write(f"""Phase 39K-S Run Log
==================
Start: {datetime.utcnow().isoformat()}Z
Target: {TARGET_WEEK} {TARGET_DATE}/{TARGET_VENUE} {TARGET_PAIR}
Total calls: {total_calls}
List calls: {list_calls}
Get calls: {get_calls}
New files: {len(new_files)}

Results:
""")
        for result in results:
            f.write(f"{result['result']}: {result['key']} - {result['message']}\n")
    
    # BOM hash
    if new_files:
        hashes = sorted([f['sha256'] for f in new_files])
        bom_content = '\n'.join(hashes)
        bom_hash = hashlib.sha256(bom_content.encode()).hexdigest()
        
        with open(REPORTS_DIR / '39K_S_bom_sha256.txt', 'w') as f:
            f.write(f"BOM_SHA256: {bom_hash}\n")
            f.write(f"FILES_COUNT: {len(new_files)}\n")
            f.write(f"CREATED: {datetime.utcnow().isoformat()}Z\n")
    
    # Gate check
    gate_data = {
        'preflight': 'OK',
        'w7_coinbase_20250709': 'OK' if new_files else 'FAIL',
        'total_calls': total_calls,
        'files_saved': len(new_files),
        'no_overwrite': True,
        'budget_ok': total_calls <= MAX_TOTAL_CALLS
    }
    
    with open(REPORTS_DIR / '39K_S_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    # Summary
    runtime_minutes = (time.time() - start_time) / 60
    print(f"\n✅ Phase 39K-S Complete")
    print(f"⏱️ Runtime: {runtime_minutes:.1f} minutes")
    print(f"📊 Calls: {total_calls}/{MAX_TOTAL_CALLS}")
    print(f"📊 Files saved: {len(new_files)}")
    
    if new_files:
        total_bytes = sum(f['size'] for f in new_files)
        first_sha256 = new_files[0]['sha256']
        print(f"📊 Total bytes: {total_bytes:,}")
        print(f"📊 First SHA-256: {first_sha256}")
        print(f"📁 Output dir: {output_dir}")
        
        # 5-line summary
        print(f"\n📋 Summary:")
        print(f"  Calls: {total_calls}")
        print(f"  Files saved: {len(new_files)}")
        print(f"  Bytes: {total_bytes:,}")
        print(f"  SHA-256 (first): {first_sha256}")
        print(f"  Output dir: {output_dir}")
    else:
        print("❌ No files saved")
        sys.exit(1)

if __name__ == "__main__":
    main()
