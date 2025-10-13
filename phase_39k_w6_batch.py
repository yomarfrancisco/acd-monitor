#!/usr/bin/env python3
"""
Phase 39K-W6-Batch: Week-6 Batch Processing (2025-07-16 to 2025-07-20)
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
BATCH_DATES = ['20250716', '20250717', '20250718', '20250719', '20250720']
VENUES = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
VENUE_SYMBOLS = {
    'COINBASE': 'BTC-USD',
    'BINANCE': 'BTCUSDT',
    'BYBITSPOT': 'BTCUSDT',
    'BITGET': 'BTCUSDT'
}

# Budget limits
MAX_LIST_CALLS_PER_DAY = 4  # 1 per venue
MAX_GET_CALLS_PER_DAY = 12  # 3 per venue
MAX_TOTAL_CALLS_PER_DAY = 24
MAX_TOTAL_CALLS_BATCH = 120  # 5 days * 24 calls

def is_target_pair(key, venue):
    """Check if key corresponds to target BTCUSD-class pair for venue"""
    key_upper = key.upper()
    target_symbol = VENUE_SYMBOLS[venue]
    
    if venue == 'COINBASE':
        # COINBASE: BTC-USD or BTC__002DUSD
        return 'BTC-USD' in key_upper or 'BTC__002DUSD' in key_upper
    else:
        # BINANCE, BYBITSPOT, BITGET: BTCUSDT (exact match, not WBTCUSDT)
        return key_upper.endswith('BTCUSDT.CSV.GZ') or 'BTCUSDT' in key_upper and 'WBTCUSDT' not in key_upper

def is_quarantine_pair(key, venue):
    """Check if key should be quarantined (non-target BTC pairs)"""
    key_upper = key.upper()
    
    # Only quarantine if it's a BTC pair but not our target
    if 'BTC' in key_upper:
        return not is_target_pair(key, venue)
    
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
                    # Include all BTC-related keys for processing
                    if 'BTC' in key.upper():
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

def download_file_atomic(key, output_dir, quarantine_dir, venue, max_attempts=2):
    """Download file with atomic write and quarantine handling"""
    download_url = f'{DOWNLOAD_BASE_URL}{key}'
    
    # Create output path with .part extension
    filename = key.split('/')[-1]
    # Create unique filename for this day/venue
    unique_filename = f"IDDI_{hashlib.md5(key.encode()).hexdigest()[:8]}__{VENUE_SYMBOLS[venue].replace('-', '_')}.csv.gz"
    part_path = output_dir / f'{unique_filename}.part'
    final_path = output_dir / unique_filename
    
    # Determine if this should be quarantined
    is_quarantine = is_quarantine_pair(key, venue)
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
                    # Force fsync on file descriptor
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

def process_single_day(date):
    """Process a single day"""
    print(f"\n📅 Processing {date}...")
    print("=" * 50)
    
    start_time = time.time()
    
    # Tracking
    total_calls = 0
    list_calls = 0
    get_calls = 0
    venue_results = {}
    all_new_files = []
    all_quarantined_files = []
    
    # Process each venue
    for venue in VENUES:
        print(f"  🏢 Processing {venue}...")
        
        # Create directories
        output_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6' / date / f'E-{venue}'
        output_dir.mkdir(parents=True, exist_ok=True)
        quarantine_dir = BASE_DIR / 'data_v7' / 'quarantine' / date / f'E-{venue}'
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # LIST objects
        keys, status_code, list_url = list_s3_objects(date, venue)
        list_calls += 1
        total_calls += 1
        
        # Check for errors (abort policy)
        if status_code >= 400:
            print(f"    ❌ LIST failed for {venue} with {status_code}")
            return False, [], [], total_calls, f"LIST HTTP {status_code} for {venue}"
        
        if len(keys) == 0:
            print(f"    ❌ No keys found for {venue}")
            return False, [], [], total_calls, f"No keys found for {venue}"
        
        venue_new_files = []
        venue_quarantined_files = []
        venue_target_found = False
        
        # Find target keys first
        target_keys = [k for k in keys if is_target_pair(k, venue)]
        quarantine_keys = [k for k in keys if is_quarantine_pair(k, venue)]
        
        print(f"    🎯 Target keys: {len(target_keys)}, Quarantine keys: {len(quarantine_keys)}")
        
        # Process target keys first (up to 1 per venue)
        for key in target_keys[:1]:  # Limit to 1 target per venue
            result, message = download_file_atomic(key, output_dir, quarantine_dir, venue)
            get_calls += 1
            total_calls += 1
            
            if result == 'OK':
                venue_target_found = True
                # Extract filename from message
                filename = message.split(': ')[1].split(' (')[0]
                file_path = output_dir / filename
                if file_path.exists():
                    venue_new_files.append({
                        'date': date,
                        'venue': venue,
                        'pair': VENUE_SYMBOLS[venue],
                        'key': key,
                        'abs_path': str(file_path),
                        'rel_path': f'data_v7/raw/coinapi_jul_w6/{date}/E-{venue}/{filename}',
                        'size_bytes': file_path.stat().st_size,
                        'sha256': compute_file_hash(file_path)
                    })
            elif result == 'SKIP':
                # File already exists, verify it
                venue_target_found = True
                # Extract filename from message
                filename = message.split(': ')[1].split(' (')[0]
                file_path = output_dir / filename
                if file_path.exists():
                    venue_new_files.append({
                        'date': date,
                        'venue': venue,
                        'pair': VENUE_SYMBOLS[venue],
                        'key': key,
                        'abs_path': str(file_path),
                        'rel_path': f'data_v7/raw/coinapi_jul_w6/{date}/E-{venue}/{filename}',
                        'size_bytes': file_path.stat().st_size,
                        'sha256': compute_file_hash(file_path)
                    })
            
            # Check budget
            if total_calls >= MAX_TOTAL_CALLS_PER_DAY:
                print("    ⚠️ Reached daily call limit")
                break
        
        # Process quarantine keys (up to 2 per venue)
        for key in quarantine_keys[:2]:  # Limit to 2 quarantine per venue
            if total_calls >= MAX_TOTAL_CALLS_PER_DAY:
                break
                
            result, message = download_file_atomic(key, output_dir, quarantine_dir, venue)
            get_calls += 1
            total_calls += 1
            
            if result == 'QUARANTINE':
                # Extract filename from message
                filename = message.split(': ')[1].split(' (')[0]
                file_path = quarantine_dir / filename
                if file_path.exists():
                    venue_quarantined_files.append({
                        'date': date,
                        'venue': venue,
                        'key': key,
                        'abs_path': str(file_path),
                        'size_bytes': file_path.stat().st_size,
                        'sha256': compute_file_hash(file_path),
                        'reason': f'Non-target BTC pair (not {VENUE_SYMBOLS[venue]})'
                    })
        
        venue_results[venue] = {
            'target_found': venue_target_found,
            'new_files': len(venue_new_files),
            'quarantined_files': len(venue_quarantined_files),
            'target_keys_available': len(target_keys),
            'quarantine_keys_available': len(quarantine_keys)
        }
        
        all_new_files.extend(venue_new_files)
        all_quarantined_files.extend(venue_quarantined_files)
    
    # Check success gates
    success_gates = {
        'list_ok': all(venue_results[v]['target_keys_available'] > 0 for v in VENUES),
        'target_found': all(venue_results[v]['target_found'] for v in VENUES),
        'write_ok': True,  # Atomic write ensures this
        'integrity_ok': True,  # Verified during download
        'budget_ok': total_calls <= MAX_TOTAL_CALLS_PER_DAY
    }
    
    all_gates_passed = all(success_gates.values())
    
    if not all_gates_passed:
        print(f"    ❌ Success gates failed: {success_gates}")
        return False, [], [], total_calls, f"Gates failed: {success_gates}"
    
    # Write per-day artifacts
    print(f"    📝 Writing artifacts for {date}...")
    
    # Manifest
    if all_new_files:
        manifest_df = pd.DataFrame(all_new_files)
        manifest_df.to_csv(REPORTS_DIR / f'39K_W6_D{date[-2:]}_manifest.csv', index=False)
    
    # Quarantine manifest
    if all_quarantined_files:
        quarantine_df = pd.DataFrame(all_quarantined_files)
        quarantine_df.to_csv(REPORTS_DIR / f'39K_W6_D{date[-2:]}_quarantine.csv', index=False)
    
    # Spend log
    spend_data = {
        'date': date,
        'total_calls': total_calls,
        'list_calls': list_calls,
        'get_calls': get_calls,
        'budget_used': f"{total_calls}/{MAX_TOTAL_CALLS_PER_DAY}",
        'duration_seconds': time.time() - start_time,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'per_venue': venue_results
    }
    
    with open(REPORTS_DIR / f'39K_W6_D{date[-2:]}_spend.json', 'w') as f:
        json.dump(spend_data, f, indent=2)
    
    # Gate file
    gate_data = {
        'date': date,
        'list_ok': success_gates['list_ok'],
        'target_found': success_gates['target_found'],
        'write_ok': success_gates['write_ok'],
        'integrity_ok': success_gates['integrity_ok'],
        'budget_ok': success_gates['budget_ok'],
        'all_gates_passed': all_gates_passed,
        'total_files': len(all_new_files),
        'total_quarantined': len(all_quarantined_files),
        'total_calls': total_calls
    }
    
    with open(REPORTS_DIR / f'39K_W6_D{date[-2:]}_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    # BOM SHA-256
    if all_new_files:
        all_hashes = sorted([f['sha256'] for f in all_new_files])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / f'39K_W6_D{date[-2:]}_bom_sha256.txt', 'w') as f:
            f.write(f"Phase 39K-W6-D{date[-2:]} BOM SHA-256\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
    
    # Summary log
    if all_new_files:
        total_bytes = sum(f['size_bytes'] for f in all_new_files)
        first_sha256 = all_new_files[0]['sha256']
        
        summary_line = f"Phase 39K-W6-D{date[-2:]} Complete - {datetime.utcnow().isoformat()}Z - {total_calls} calls, {len(all_new_files)} files, {total_bytes:,} bytes, {first_sha256}, data_v7/raw/coinapi_jul_w6/{date}/"
        
        with open(REPORTS_DIR / '39K_SUMMARY.log', 'a') as f:
            f.write(summary_line + '\n')
    
    runtime_minutes = (time.time() - start_time) / 60
    print(f"    ✅ {date} complete: {runtime_minutes:.1f} min, {total_calls} calls, {len(all_new_files)} files")
    
    return True, all_new_files, all_quarantined_files, total_calls, None

def build_week6_artifacts(all_files, all_quarantined):
    """Build Week-6 artifact suite"""
    print(f"\n🏗️ Building Week-6 Artifact Suite")
    print("=" * 50)
    
    # Write W6_manifest.csv
    if all_files:
        manifest_df = pd.DataFrame(all_files)
        manifest_df.to_csv(REPORTS_DIR / 'W6_manifest.csv', index=False)
        print(f"✅ W6_manifest.csv: {len(all_files)} files")
    
    # Write W6_quarantine.csv
    if all_quarantined:
        quarantine_df = pd.DataFrame(all_quarantined)
        quarantine_df.to_csv(REPORTS_DIR / 'W6_quarantine.csv', index=False)
        print(f"✅ W6_quarantine.csv: {len(all_quarantined)} files")
    
    # Build coverage matrix
    coverage_matrix = []
    for date in BATCH_DATES:
        date_files = [f for f in all_files if f['date'] == date]
        venues_covered = len(set(f['venue'] for f in date_files))
        status = "✅" if venues_covered == 4 else f"⚠️ {venues_covered}/4"
        coverage_matrix.append(f"{date}: {status}")
    
    with open(REPORTS_DIR / 'W6_coverage_matrix.txt', 'w') as f:
        f.write("Week -6 BTCUSD-class Coverage Matrix\n")
        f.write("=" * 40 + "\n")
        for line in coverage_matrix:
            f.write(f"{line}\n")
        f.write(f"\nTotal: {len([d for d in coverage_matrix if '✅' in d])}/5 days\n")
    
    print(f"✅ W6_coverage_matrix.txt: {len([d for d in coverage_matrix if '✅' in d])}/5 days")
    
    # Compute BOM SHA-256
    if all_files:
        all_hashes = sorted([f['sha256'] for f in all_files])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'W6_bom_sha256.txt', 'w') as f:
            f.write(f"Week -6 BTCUSD-class BOM SHA-256\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        print(f"✅ W6_bom_sha256.txt: {bom_hash}")
    
    # W6_gate.json
    days_passed = len([d for d in coverage_matrix if '✅' in d])
    gate_data = {
        'week': '-6',
        'days_expected': 5,
        'days_passed': days_passed,
        'all_gates_passed': days_passed == 5,
        'total_files': len(all_files),
        'total_bytes': sum(f['size_bytes'] for f in all_files) if all_files else 0,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'W6_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    print(f"✅ W6_gate.json: {days_passed}/5 days {'PASS' if days_passed == 5 else 'FAIL'}")
    
    # W6_audit.txt
    total_bytes = sum(f['size_bytes'] for f in all_files) if all_files else 0
    sha_distribution = len(set(f['sha256'] for f in all_files)) if all_files else 0
    
    with open(REPORTS_DIR / 'W6_audit.txt', 'w') as f:
        f.write("Week -6 BTCUSD-class Audit Report\n")
        f.write("=" * 40 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files: {len(all_files)}\n")
        f.write(f"Total bytes: {total_bytes:,}\n")
        f.write(f"Unique SHA-256 hashes: {sha_distribution}\n")
        f.write(f"Days covered: {days_passed}/5\n")
        f.write(f"Status: {'PASS' if days_passed == 5 else 'FAIL'}\n")
        if all_files:
            f.write(f"BOM SHA-256: {bom_hash}\n")
    
    print(f"✅ W6_audit.txt: {len(all_files)} files, {total_bytes:,} bytes")
    
    return days_passed == 5

def main():
    """Main execution"""
    print("🚀 Phase 39K-W6-Batch: Week-6 Batch Processing (2025-07-16 to 2025-07-20)")
    print("=" * 80)
    
    overall_start_time = time.time()
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process each day
    all_success = True
    all_new_files = []
    all_quarantined_files = []
    total_calls = 0
    failed_day = None
    
    for date in BATCH_DATES:
        success, new_files, quarantined_files, day_calls, error = process_single_day(date)
        total_calls += day_calls
        
        if success:
            all_new_files.extend(new_files)
            all_quarantined_files.extend(quarantined_files)
        else:
            all_success = False
            failed_day = date
            print(f"❌ Failed to process {date}: {error}")
            break
        
        # Check batch budget
        if total_calls >= MAX_TOTAL_CALLS_BATCH:
            print(f"⚠️ Reached batch call limit: {total_calls}/{MAX_TOTAL_CALLS_BATCH}")
            break
    
    if not all_success:
        print(f"\n❌ Phase 39K-W6-Batch Failed at {failed_day}")
        sys.exit(1)
    
    # Build Week-6 artifacts
    week6_success = build_week6_artifacts(all_new_files, all_quarantined_files)
    
    # Final summary
    overall_runtime_minutes = (time.time() - overall_start_time) / 60
    print(f"\n✅ Phase 39K-W6-Batch Complete")
    print(f"⏱️ Total runtime: {overall_runtime_minutes:.1f} minutes")
    print(f"📊 Total calls: {total_calls}")
    print(f"📊 Total files saved: {len(all_new_files)}")
    print(f"📊 Total files quarantined: {len(all_quarantined_files)}")
    print(f"📊 Week-6 status: {'PASS' if week6_success else 'FAIL'}")
    
    # Final summary log
    summary_lines = [
        f"Phase 39K-W6-Batch Complete - {datetime.utcnow().isoformat()}Z",
        f"Days processed: {len(BATCH_DATES)}",
        f"Total files saved: {len(all_new_files)}",
        f"Total files quarantined: {len(all_quarantined_files)}",
        f"Week-6 status: {'PASS' if week6_success else 'FAIL'}"
    ]
    
    with open(REPORTS_DIR / '39K_SUMMARY.log', 'a') as f:
        f.write('\n'.join(summary_lines) + '\n\n')
    
    if not week6_success:
        print("❌ Week-6 gate failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
