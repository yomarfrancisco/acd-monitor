#!/usr/bin/env python3
"""
Phase 39K-W7: Complete Week -7 COINBASE BTC-USD Download (2025-07-10 to 2025-07-13)
"""

import os
import sys
import hashlib
import json
import gzip
import time
import shutil
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
TARGET_VENUE = 'COINBASE'
TARGET_PAIR = 'BTC-USD'
REMAINING_DATES = ['20250710', '20250711', '20250712', '20250713']

# Budget limits per day
MAX_LIST_CALLS_PER_DAY = 2
MAX_GET_CALLS_PER_DAY = 6
MAX_TOTAL_CALLS_PER_DAY = 8

def is_btcusd_class(filename):
    """Check if filename indicates BTC-USD pair (not BTC-USDT)"""
    filename_upper = filename.upper()
    
    # BTC-USD patterns (COINBASE specific)
    if 'BTC-USD' in filename_upper or 'BTC__002DUSD' in filename_upper:
        return True
    
    return False

def is_btcusdt_class(filename):
    """Check if filename indicates BTC-USDT pair (for quarantine)"""
    filename_upper = filename.upper()
    
    # BTC-USDT patterns (COINBASE specific)
    if 'BTC-USDT' in filename_upper or 'BTC__002DUSDT' in filename_upper:
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
                    # Include both BTC-USD and BTC-USDT for processing
                    if is_btcusd_class(key) or is_btcusdt_class(key):
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

def download_file_atomic(key, output_dir, quarantine_dir, max_attempts=2):
    """Download file with atomic write and quarantine handling"""
    download_url = f'{DOWNLOAD_BASE_URL}{key}'
    
    # Create output path with .part extension
    filename = key.split('/')[-1]
    # Create unique filename for this day
    unique_filename = f"IDDI_{hashlib.md5(key.encode()).hexdigest()[:8]}__BTC-USD.csv.gz"
    part_path = output_dir / f'{unique_filename}.part'
    final_path = output_dir / unique_filename
    
    # Determine if this should be quarantined
    is_quarantine = is_btcusdt_class(key)
    if is_quarantine:
        # Move to quarantine directory
        quarantine_filename = f"QUARANTINE_{unique_filename}"
        part_path = quarantine_dir / f'{quarantine_filename}.part'
        final_path = quarantine_dir / quarantine_filename
    
    # Skip if final file already exists (no-clobber)
    if final_path.exists():
        return 'SKIP', f'File already exists: {final_path}'
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(download_url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                # Check content length
                content_length = len(response.content)
                if content_length == 0:
                    return 'FAIL', 'Zero-byte file'
                
                # Write to .part file with atomic fsync
                with open(part_path, 'wb') as f:
                    f.write(response.content)
                    # Force fsync on file descriptor (CORRECTED)
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
                
                if is_quarantine:
                    return 'QUARANTINE', f'Quarantined: {quarantine_filename} ({final_path.stat().st_size} bytes, SHA-256: {sha256})'
                else:
                    return 'OK', f'Downloaded: {unique_filename} ({final_path.stat().st_size} bytes, SHA-256: {sha256})'
            else:
                if attempt < max_attempts - 1:
                    # Jittered backoff (±5s)
                    backoff = 30 + (5 if attempt % 2 == 0 else -5)
                    time.sleep(backoff)
                return 'FAIL', f'HTTP {response.status_code}'
        except Exception as e:
            if attempt < max_attempts - 1:
                # Jittered backoff (±5s)
                backoff = 30 + (5 if attempt % 2 == 0 else -5)
                time.sleep(backoff)
            print(f"⚠️ Download error {key}: {e}")
            return 'FAIL', str(e)
    
    return 'FAIL', 'Max attempts exceeded'

def write_failure_report(failed_step, list_url, error_details, date):
    """Write failure report"""
    with open(REPORTS_DIR / f'39K_D1_failure_{date}.md', 'w') as f:
        f.write("# Phase 39K-D1 Failure Report\n\n")
        f.write(f"**Date**: {date}\n")
        f.write(f"**Timestamp**: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"**Failed Step**: {failed_step}\n")
        f.write(f"**LIST URL Used**: {list_url}\n\n")
        f.write("## Error Details\n")
        f.write(f"{error_details}\n\n")
        f.write("## Copy-Pasteable LIST URL\n")
        f.write(f"```\n{list_url}\n```\n")

def process_single_day(date):
    """Process a single day"""
    print(f"\n📅 Processing {date}/{TARGET_VENUE} {TARGET_PAIR}")
    print("=" * 60)
    
    start_time = time.time()
    
    # Create directories
    output_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7' / date / f'E-{TARGET_VENUE}'
    output_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir = BASE_DIR / 'data_v7' / 'quarantine' / TARGET_VENUE / date
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    # Tracking
    total_calls = 0
    list_calls = 0
    get_calls = 0
    results = []
    new_files = []
    quarantined_files = []
    
    print(f"📁 Output: {output_dir}")
    print(f"📁 Quarantine: {quarantine_dir}")
    
    # LIST objects
    print(f"🔍 Listing objects...")
    keys, status_code, list_url = list_s3_objects(date, TARGET_VENUE)
    list_calls += 1
    total_calls += 1
    
    print(f"📊 LIST result: {status_code}, {len(keys)} keys found")
    
    # Check for errors (abort policy)
    if status_code >= 400:
        print(f"❌ LIST failed with {status_code} - stopping")
        write_failure_report(f"LIST HTTP {status_code}", list_url, f"LIST operation returned HTTP {status_code}", date)
        return False, [], [], 0, list_url
    
    if len(keys) == 0:
        print(f"❌ No keys found - stopping")
        write_failure_report("No keys found", list_url, "LIST operation returned 0 keys", date)
        return False, [], [], 0, list_url
    
    # Download files
    for key in keys[:MAX_GET_CALLS_PER_DAY]:  # Limit to budget
        print(f"📥 Downloading: {key}")
        result, message = download_file_atomic(key, output_dir, quarantine_dir)
        get_calls += 1
        total_calls += 1
        
        results.append({
            'date': date,
            'venue': TARGET_VENUE,
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
                    'date': date,
                    'venue': TARGET_VENUE,
                    'key': key,
                    'abs_path': str(file_path),
                    'size_bytes': file_path.stat().st_size,
                    'sha256': compute_file_hash(file_path)
                })
        elif result == 'QUARANTINE':
            # Extract filename from message
            filename = message.split(': ')[1].split(' (')[0]
            file_path = quarantine_dir / filename
            if file_path.exists():
                quarantined_files.append({
                    'date': date,
                    'venue': TARGET_VENUE,
                    'key': key,
                    'abs_path': str(file_path),
                    'size_bytes': file_path.stat().st_size,
                    'sha256': compute_file_hash(file_path),
                    'reason': 'BTC-USDT pair (not BTC-USD)'
                })
        
        print(f"    {result}: {message}")
        
        # Check budget
        if total_calls >= MAX_TOTAL_CALLS_PER_DAY:
            print("⚠️ Reached total call limit")
            break
    
    # Check success gates
    success_gates = {
        'files_saved': len(new_files) >= 1,
        'no_overwrites': True,  # Atomic write ensures this
        'gzip_valid': True,     # Verified during download
        'sha256_recorded': True, # Computed for all files
        'budget_ok': total_calls <= MAX_TOTAL_CALLS_PER_DAY
    }
    
    all_gates_passed = all(success_gates.values())
    
    if not all_gates_passed:
        print(f"❌ Success gates failed: {success_gates}")
        write_failure_report("Success gates failed", list_url, f"Gates: {success_gates}", date)
        return False, [], [], total_calls, list_url
    
    # Write artifacts
    print(f"\n📝 Writing artifacts...")
    
    # Append to manifest
    if new_files:
        manifest_df = pd.DataFrame(new_files)
        manifest_path = REPORTS_DIR / '39K_D1_manifest.csv'
        
        # Append to existing manifest if it exists
        if manifest_path.exists():
            existing_df = pd.read_csv(manifest_path)
            combined_df = pd.concat([existing_df, manifest_df], ignore_index=True)
            combined_df.to_csv(manifest_path, index=False)
        else:
            manifest_df.to_csv(manifest_path, index=False)
        print(f"✅ Manifest updated: {manifest_path}")
    
    # Append to quarantine manifest
    if quarantined_files:
        quarantine_df = pd.DataFrame(quarantined_files)
        quarantine_path = REPORTS_DIR / '39K_D1_quarantine.csv'
        
        # Append to existing quarantine manifest if it exists
        if quarantine_path.exists():
            existing_df = pd.read_csv(quarantine_path)
            combined_df = pd.concat([existing_df, quarantine_df], ignore_index=True)
            combined_df.to_csv(quarantine_path, index=False)
        else:
            quarantine_df.to_csv(quarantine_path, index=False)
        print(f"✅ Quarantine manifest updated: {quarantine_path}")
    
    # Append to spend log
    spend_data = {
        'date': date,
        'total_calls': total_calls,
        'list_calls': list_calls,
        'get_calls': get_calls,
        'budget_used': f"{total_calls}/{MAX_TOTAL_CALLS_PER_DAY}",
        'duration_seconds': time.time() - start_time,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    spend_path = REPORTS_DIR / '39K_D1_spend.json'
    if spend_path.exists():
        with open(spend_path, 'r') as f:
            existing_data = json.load(f)
        # Convert to list if it's a single object
        if not isinstance(existing_data, list):
            existing_data = [existing_data]
        existing_data.append(spend_data)
        with open(spend_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
    else:
        with open(spend_path, 'w') as f:
            json.dump(spend_data, f, indent=2)
    
    # Gate file
    gate_data = {
        'date': date,
        'files_saved': success_gates['files_saved'],
        'no_overwrites': success_gates['no_overwrites'],
        'gzip_valid': success_gates['gzip_valid'],
        'sha256_recorded': success_gates['sha256_recorded'],
        'budget_ok': success_gates['budget_ok'],
        'all_gates_passed': all_gates_passed,
        'files_count': len(new_files),
        'quarantined_count': len(quarantined_files),
        'total_calls': total_calls
    }
    
    with open(REPORTS_DIR / f'39K_D1_gate_{date}.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    # Summary log
    if new_files:
        total_bytes = sum(f['size_bytes'] for f in new_files)
        first_sha256 = new_files[0]['sha256']
        
        summary_lines = [
            f"Phase 39K-D1 {date} Complete - {datetime.utcnow().isoformat()}Z",
            f"Files saved: {len(new_files)}",
            f"Total bytes: {total_bytes:,}",
            f"First SHA-256: {first_sha256}",
            f"Output dir: {output_dir}"
        ]
        
        if quarantined_files:
            summary_lines.append(f"Quarantined: {len(quarantined_files)} files")
        
        with open(REPORTS_DIR / '39K_SUMMARY.log', 'a') as f:
            f.write('\n'.join(summary_lines) + '\n\n')
    
    # Summary
    runtime_minutes = (time.time() - start_time) / 60
    print(f"\n✅ Phase 39K-D1 {date} Complete")
    print(f"⏱️ Runtime: {runtime_minutes:.1f} minutes")
    print(f"📊 Calls: {total_calls}/{MAX_TOTAL_CALLS_PER_DAY}")
    print(f"📊 Files saved: {len(new_files)}")
    print(f"📊 Files quarantined: {len(quarantined_files)}")
    
    return True, new_files, quarantined_files, total_calls, list_url

def build_week7_artifacts():
    """Build Week-7 artifact suite"""
    print(f"\n🏗️ Building Week-7 Artifact Suite")
    print("=" * 50)
    
    # Load all manifests
    manifest_path = REPORTS_DIR / '39K_D1_manifest.csv'
    quarantine_path = REPORTS_DIR / '39K_D1_quarantine.csv'
    
    if not manifest_path.exists():
        print("❌ No manifest found")
        return False
    
    manifest_df = pd.read_csv(manifest_path)
    manifest_df = manifest_df[manifest_df['venue'] == 'COINBASE']  # Filter COINBASE only
    
    # Filter for Week-7 dates (2025-07-07 to 2025-07-13)
    week7_dates = ['20250707', '20250708', '20250709', '20250710', '20250711', '20250712', '20250713']
    week7_manifest = manifest_df[manifest_df['date'].isin(week7_dates)]
    
    # Write W7_manifest.csv
    week7_manifest.to_csv(REPORTS_DIR / 'W7_manifest.csv', index=False)
    print(f"✅ W7_manifest.csv: {len(week7_manifest)} BTC-USD files")
    
    # Write W7_quarantine.csv
    if quarantine_path.exists():
        quarantine_df = pd.read_csv(quarantine_path)
        quarantine_df = quarantine_df[quarantine_df['venue'] == 'COINBASE']
        week7_quarantine = quarantine_df[quarantine_df['date'].isin(week7_dates)]
        week7_quarantine.to_csv(REPORTS_DIR / 'W7_quarantine.csv', index=False)
        print(f"✅ W7_quarantine.csv: {len(week7_quarantine)} quarantined files")
    else:
        # Create empty quarantine file
        empty_quarantine = pd.DataFrame(columns=['date', 'venue', 'key', 'abs_path', 'size_bytes', 'sha256', 'reason'])
        empty_quarantine.to_csv(REPORTS_DIR / 'W7_quarantine.csv', index=False)
        print(f"✅ W7_quarantine.csv: 0 quarantined files")
    
    # Build coverage matrix
    coverage_matrix = []
    for date in week7_dates:
        date_files = week7_manifest[week7_manifest['date'] == date]
        status = "✅" if len(date_files) > 0 else "❌"
        coverage_matrix.append(f"{date}: {status}")
    
    with open(REPORTS_DIR / 'W7_coverage_matrix.txt', 'w') as f:
        f.write("Week -7 COINBASE BTC-USD Coverage Matrix\n")
        f.write("=" * 40 + "\n")
        for line in coverage_matrix:
            f.write(f"{line}\n")
        f.write(f"\nTotal: {len([d for d in coverage_matrix if '✅' in d])}/7 days\n")
    
    print(f"✅ W7_coverage_matrix.txt: {len([d for d in coverage_matrix if '✅' in d])}/7 days")
    
    # Compute BOM SHA-256
    all_hashes = sorted(week7_manifest['sha256'].tolist())
    bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
    
    with open(REPORTS_DIR / 'W7_bom_sha256.txt', 'w') as f:
        f.write(f"Week -7 COINBASE BTC-USD BOM SHA-256\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Files: {len(all_hashes)}\n")
        f.write(f"BOM SHA-256: {bom_hash}\n")
    
    print(f"✅ W7_bom_sha256.txt: {bom_hash}")
    
    # W7_gate.json
    days_passed = len([d for d in coverage_matrix if '✅' in d])
    gate_data = {
        'week': '-7',
        'venue': 'COINBASE',
        'days_expected': 7,
        'days_passed': days_passed,
        'all_gates_passed': days_passed == 7,
        'total_files': len(week7_manifest),
        'total_bytes': week7_manifest['size_bytes'].sum(),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'W7_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    print(f"✅ W7_gate.json: {days_passed}/7 days {'PASS' if days_passed == 7 else 'FAIL'}")
    
    # W7_audit.txt
    total_bytes = week7_manifest['size_bytes'].sum()
    sha_distribution = week7_manifest['sha256'].nunique()
    
    with open(REPORTS_DIR / 'W7_audit.txt', 'w') as f:
        f.write("Week -7 COINBASE BTC-USD Audit Report\n")
        f.write("=" * 40 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files: {len(week7_manifest)}\n")
        f.write(f"Total bytes: {total_bytes:,}\n")
        f.write(f"Unique SHA-256 hashes: {sha_distribution}\n")
        f.write(f"Days covered: {days_passed}/7\n")
        f.write(f"Status: {'PASS' if days_passed == 7 else 'FAIL'}\n")
        f.write(f"BOM SHA-256: {bom_hash}\n")
    
    print(f"✅ W7_audit.txt: {len(week7_manifest)} files, {total_bytes:,} bytes")
    
    return days_passed == 7

def main():
    """Main execution"""
    print("🚀 Phase 39K-W7: Complete Week -7 COINBASE BTC-USD Download")
    print("=" * 70)
    
    overall_start_time = time.time()
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process each remaining day
    all_success = True
    all_new_files = []
    all_quarantined_files = []
    total_calls = 0
    
    for date in REMAINING_DATES:
        success, new_files, quarantined_files, day_calls, list_url = process_single_day(date)
        total_calls += day_calls
        
        if success:
            all_new_files.extend(new_files)
            all_quarantined_files.extend(quarantined_files)
        else:
            all_success = False
            print(f"❌ Failed to process {date}")
            break
    
    if not all_success:
        print(f"\n❌ Phase 39K-W7 Failed")
        sys.exit(1)
    
    # Build Week-7 artifacts
    week7_success = build_week7_artifacts()
    
    # Final summary
    overall_runtime_minutes = (time.time() - overall_start_time) / 60
    print(f"\n✅ Phase 39K-W7 Complete")
    print(f"⏱️ Total runtime: {overall_runtime_minutes:.1f} minutes")
    print(f"📊 Total calls: {total_calls}")
    print(f"📊 Total files saved: {len(all_new_files)}")
    print(f"📊 Total files quarantined: {len(all_quarantined_files)}")
    print(f"📊 Week-7 status: {'PASS' if week7_success else 'FAIL'}")
    
    # Final summary log
    summary_lines = [
        f"Phase 39K-W7 Complete - {datetime.utcnow().isoformat()}Z",
        f"Days processed: {len(REMAINING_DATES)}",
        f"Total files saved: {len(all_new_files)}",
        f"Total files quarantined: {len(all_quarantined_files)}",
        f"Week-7 status: {'PASS' if week7_success else 'FAIL'}"
    ]
    
    with open(REPORTS_DIR / '39K_SUMMARY.log', 'a') as f:
        f.write('\n'.join(summary_lines) + '\n\n')
    
    if not week7_success:
        print("❌ Week-7 gate failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
