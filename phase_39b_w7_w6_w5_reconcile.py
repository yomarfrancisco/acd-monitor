#!/usr/bin/env python3
"""
Phase 39B — W−7/−6/−5 Reconcile, Lock & BTC-Only Purge (No Network)
Freeze network I/O and produce authoritative BTC-only inventory
"""

import os
import sys
import hashlib
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import random

# Configuration
TARGET_PAIRS = {'BTCUSDT', 'BTC-USD', 'BTCUSD'}
TARGET_VENUES = {'BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET'}
MAX_RAM_GB = 1.0
MAX_RUNTIME_MIN = 30

# Date ranges
W7_DATES = ['20250707', '20250708', '20250709', '20250710', '20250711', '20250712', '20250713']
W6_DATES = ['20250714', '20250715', '20250716', '20250717', '20250718', '20250719', '20250720']
W5_DATES = ['20250721', '20250722', '20250723', '20250724', '20250725', '20250726', '20250727']

# Paths
LOCK_FILE = Path('locks/api_budget.lock')
REPORTS_DIR = Path('data_v7/reports')
QUARANTINE_DIR = Path('data_v7/quarantine/w7_w6_w5_other_pairs')
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
Path('locks').mkdir(parents=True, exist_ok=True)

# Set deterministic seed
random.seed(39)

def check_network_lock():
    """Check if network is locked and abort if so"""
    if LOCK_FILE.exists():
        print(f"LOCKED: network disabled (see {LOCK_FILE})")
        sys.exit(1)

def create_network_lock():
    """Create network lock file"""
    now_utc = datetime.utcnow().isoformat() + 'Z'
    with open(LOCK_FILE, 'w') as f:
        f.write("reason=W7-W6-W5 forensic freeze\n")
        f.write(f"created_utc={now_utc}\n")
        f.write("guard=no network I/O\n")
    print(f"LOCK: present with path {LOCK_FILE}")

def write_download_methodology():
    """Write methodology disclosure"""
    method_file = REPORTS_DIR / 'DOWNLOAD_METHOD.md'
    
    content = """# Download Methodology - Weeks -7/-6/-5

## LIST URL Patterns Used

### Correct Pattern (Working)
```
https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-YYYYMMDD/E-VENUE/
```

### Incorrect Pattern (Failed)
```
https://s3.flatfiles.coinapi.io/?prefix=T-TRADES/D-YYYYMMDD/E-VENUE/
```

## DOWNLOAD URL Patterns Used

### Correct Pattern (Working)
```
https://s3.flatfiles.coinapi.io/coinapi/{key}
```

### Incorrect Pattern (Failed)
```
https://s3.flatfiles.coinapi.io/{key}
```

## Authentication Mechanism
- Header: `X-CoinAPI-Key: 7f036b38-38d6-4ed6-9fce-00a06280a0f6`
- Header: `User-Agent: ACD-Monitor/1.0`
- TLS: Default Python requests settings

## XML Parsing
- Namespace: None (no namespace in actual XML)
- Tag paths: `.//Contents` and `Key` (not `{http://s3.amazonaws.com/doc/2006-03-01/}Contents`)
- Pagination: Not handled (assumed single page results)

## Rate/Budget Controls
- Max calls per run: 80
- Backoff: Exponential (30s, 60s, 120s) with ±5s jitter
- Retries: 3 attempts per file
- Concurrency: 2 workers max
- Timeout: 120s per request

## Disk Write Policy
- Target folders: `data_v7/raw/coinapi_jul_w7/` and `data_v6/raw/coinapi_jul/`
- Atomic move: Direct write to final location
- Temp naming: None (direct write)

## CLI Invocations Executed

### Week -7 (July 7-13)
```bash
python3 phase_42a_v7f_jul_w7_download.py
python3 phase_42a_v7f_retry_jul_w7.py
```

### Week -6 (July 14-20) 
```bash
python3 phase_42a_v7e_jul_w6b_download_fixed.py
```

### Week -5 (July 21-27)
```bash
# Used existing data from data_v6/raw/coinapi_jul/
```

## Environment Variables
- COINAPI_KEY=7f036b38-38d6-4ed6-9fce-00a06280a0f6
"""
    
    with open(method_file, 'w') as f:
        f.write(content)
    
    return method_file

def extract_venue_date_pair_legacy(filename):
    """Extract venue/date/pair from legacy format: VENUE_YYYYMMDD_PAIR.csv.gz"""
    pattern = r'(?P<venue>[A-Z]+)_(?P<date>\d{8})_(?P<pair>[A-Z\-]+)\.csv\.gz'
    match = re.match(pattern, filename)
    if match:
        return match.group('venue'), match.group('date'), match.group('pair')
    return None, None, None

def extract_venue_date_pair_coinapi(file_path):
    """Extract venue/date/pair from CoinAPI format using path segments"""
    path_parts = file_path.parts
    
    # Extract venue from path
    venue = None
    for part in path_parts:
        if part in TARGET_VENUES:
            venue = part
            break
    
    # Extract date from path
    date = None
    for part in path_parts:
        if part.startswith('202507'):
            date = part
            break
    
    # Extract pair from filename
    filename = file_path.name
    pair = None
    if 'BTCUSDT' in filename.upper():
        pair = 'BTCUSDT'
    elif 'BTC-USD' in filename.upper() or 'BTC__002DUSD' in filename.upper():
        pair = 'BTC-USD'
    elif 'BTCUSD' in filename.upper() and 'BTCUSDT' not in filename.upper():
        pair = 'BTCUSD'
    
    return venue, date, pair

def canonicalize_pair(pair):
    """Canonicalize pair names"""
    if pair in {'BTC-USD', 'BTCUSD'}:
        return 'BTCUSD'
    return pair

def is_target_file(file_path):
    """Check if file matches target criteria"""
    filename = file_path.name
    
    # Try legacy format first
    venue, date, pair = extract_venue_date_pair_legacy(filename)
    
    # If not legacy, try CoinAPI format
    if not venue:
        venue, date, pair = extract_venue_date_pair_coinapi(file_path)
    
    if not venue or not date or not pair:
        return False, None, None, None
    
    # Check if in target date ranges
    if date not in W7_DATES + W6_DATES + W5_DATES:
        return False, None, None, None
    
    # Check venue and pair
    if venue not in TARGET_VENUES:
        return False, None, None, None
    
    canonical_pair = canonicalize_pair(pair)
    if canonical_pair not in TARGET_PAIRS:
        return False, None, None, None
    
    return True, venue, date, canonical_pair

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

def scan_data_roots():
    """Scan both data roots for files"""
    roots = [
        Path('data_v7/raw/coinapi_jul_w7/'),
        Path('data_v6/raw/coinapi_jul/')
    ]
    
    all_files = []
    for root in roots:
        if root.exists():
            for file_path in root.rglob('*.csv.gz'):
                all_files.append((file_path, root))
    
    return all_files

def generate_coverage_matrix(dates, btc_files):
    """Generate coverage matrix for a week"""
    matrix = {}
    for date in dates:
        matrix[date] = {}
        for venue in TARGET_VENUES:
            matrix[date][venue] = '✗'
    
    # Mark filled slots
    for file_info in btc_files:
        date = file_info['date']
        venue = file_info['venue']
        if date in dates:
            matrix[date][venue] = '✓'
    
    return matrix

def print_coverage_matrix(week_name, dates, matrix):
    """Print coverage matrix"""
    print(f"\n📊 {week_name} Coverage Matrix:")
    print("Date       | BINANCE | COINBASE | BYBITSPOT | BITGET")
    print("-" * 50)
    for date in dates:
        row = f"{date} |"
        for venue in TARGET_VENUES:
            row += f"    {matrix[date][venue]}    |"
        print(row)

def main():
    print("🔍 Phase 39B — W−7/−6/−5 Reconcile, Lock & BTC-Only Purge")
    print("🚫 NO NETWORK I/O")
    print()
    
    start_time = datetime.now()
    
    # A) Freeze network spend
    create_network_lock()
    
    # B) Write methodology disclosure
    method_file = write_download_methodology()
    print(f"📄 DOWNLOAD_METHOD.md: {method_file}")
    
    # C) Scan data roots
    print("\n📂 Scanning data roots...")
    all_files = scan_data_roots()
    print(f"Found {len(all_files)} total files")
    
    # D) Process files
    btc_files = []
    other_files = []
    zero_byte_files = []
    small_files = []
    
    for file_path, root in all_files:
        is_target, venue, date, pair = is_target_file(file_path)
        
        try:
            file_size = file_path.stat().st_size
            
            if file_size == 0:
                zero_byte_files.append(str(file_path))
            
            if file_size < 50 * 1024:  # 50 KB
                small_files.append((str(file_path), file_size))
            
            if is_target:
                file_hash = compute_file_hash(file_path)
                relpath = file_path.relative_to(root)
                
                btc_files.append({
                    'relpath': str(relpath),
                    'root': str(root),
                    'venue': venue,
                    'date': date,
                    'pair': pair,
                    'bytes': file_size,
                    'sha256': file_hash
                })
            else:
                file_hash = compute_file_hash(file_path)
                relpath = file_path.relative_to(root)
                
                other_files.append({
                    'relpath': str(relpath),
                    'root': str(root),
                    'venue': venue or 'UNKNOWN',
                    'date': date or 'UNKNOWN',
                    'pair': pair or 'UNKNOWN',
                    'bytes': file_size,
                    'sha256': file_hash,
                    'moved_utc': datetime.utcnow().isoformat() + 'Z'
                })
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    # Quarantine non-target files
    print(f"\n📦 Quarantining {len(other_files)} non-target files...")
    quarantine_manifest = []
    
    for file_info in other_files:
        try:
            original_path = Path(file_info['root']) / file_info['relpath']
            quarantine_path = QUARANTINE_DIR / file_info['relpath']
            quarantine_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(original_path), str(quarantine_path))
            quarantine_manifest.append(file_info)
            
        except Exception as e:
            print(f"❌ Error moving {file_info['relpath']}: {e}")
    
    # Write manifests
    btc_manifest_file = REPORTS_DIR / 'w7_w6_w5_btc_manifest.csv'
    with open(btc_manifest_file, 'w', newline='') as f:
        if btc_files:
            writer = csv.DictWriter(f, fieldnames=btc_files[0].keys())
            writer.writeheader()
            writer.writerows(btc_files)
    
    quarantine_manifest_file = REPORTS_DIR / 'w7_w6_w5_quarantine_manifest.csv'
    with open(quarantine_manifest_file, 'w', newline='') as f:
        if quarantine_manifest:
            writer = csv.DictWriter(f, fieldnames=quarantine_manifest[0].keys())
            writer.writeheader()
            writer.writerows(quarantine_manifest)
    
    # Generate BOM hashes
    btc_hashes = sorted([f['sha256'] for f in btc_files if f['sha256']])
    btc_bom_input = '\n'.join(btc_hashes)
    btc_bom_hash = hashlib.sha256(btc_bom_input.encode('utf-8')).hexdigest()
    
    quarantine_hashes = sorted([f['sha256'] for f in quarantine_manifest if f['sha256']])
    quarantine_bom_input = '\n'.join(quarantine_hashes)
    quarantine_bom_hash = hashlib.sha256(quarantine_bom_input.encode('utf-8')).hexdigest()
    
    btc_bom_file = REPORTS_DIR / 'btc_manifest_bom_sha256.txt'
    with open(btc_bom_file, 'w') as f:
        f.write(btc_bom_hash)
    
    quarantine_bom_file = REPORTS_DIR / 'quarantine_bom_sha256.txt'
    with open(quarantine_bom_file, 'w') as f:
        f.write(quarantine_bom_hash)
    
    # E) Generate coverage matrices
    w7_matrix = generate_coverage_matrix(W7_DATES, btc_files)
    w6_matrix = generate_coverage_matrix(W6_DATES, btc_files)
    w5_matrix = generate_coverage_matrix(W5_DATES, btc_files)
    
    print_coverage_matrix("W−7", W7_DATES, w7_matrix)
    print_coverage_matrix("W−6", W6_DATES, w6_matrix)
    print_coverage_matrix("W−5", W5_DATES, w5_matrix)
    
    # Count coverage
    w7_filled = sum(1 for date in W7_DATES for venue in TARGET_VENUES if w7_matrix[date][venue] == '✓')
    w6_filled = sum(1 for date in W6_DATES for venue in TARGET_VENUES if w6_matrix[date][venue] == '✓')
    w5_filled = sum(1 for date in W5_DATES for venue in TARGET_VENUES if w5_matrix[date][venue] == '✓')
    
    # F) Gates
    w7_pass = w7_filled >= 12
    w6_pass = w6_filled >= 12
    w5_pass = w5_filled >= 20
    
    # G) Required console summary
    print(f"\n🎯 REQUIRED CONSOLE SUMMARY:")
    print(f"1. LOCK: present with path {LOCK_FILE}")
    print(f"2. Paths to:")
    print(f"   • DOWNLOAD_METHOD.md: {method_file}")
    print(f"   • w7_w6_w5_btc_manifest.csv: {btc_manifest_file}")
    print(f"   • btc_manifest_bom_sha256.txt: {btc_bom_file}")
    print(f"   • w7_w6_w5_quarantine_manifest.csv: {quarantine_manifest_file} (with count {len(quarantine_manifest)})")
    print(f"   • quarantine_bom_sha256.txt: {quarantine_bom_file}")
    
    print(f"3. Three coverage matrices (W−7, W−6, W−5) - see above")
    
    # Counts
    total_bytes = sum(f['bytes'] for f in btc_files)
    bytes_list = [f['bytes'] for f in btc_files]
    bytes_list.sort()
    
    print(f"4. Counts:")
    print(f"   • Valid BTC files: {len(btc_files)}")
    print(f"   • Quarantined files: {len(quarantine_manifest)}")
    print(f"   • Zero-byte count: {len(zero_byte_files)}")
    print(f"   • Min/median/max bytes: {min(bytes_list) if bytes_list else 0}/{bytes_list[len(bytes_list)//2] if bytes_list else 0}/{max(bytes_list) if bytes_list else 0}")
    
    print(f"5. Gate lines:")
    print(f"   • W−7: {'PASS' if w7_pass else 'FAIL'} ({w7_filled}/28)")
    print(f"   • W−6: {'PASS' if w6_pass else 'FAIL'} ({w6_filled}/28)")
    print(f"   • W−5: {'PASS' if w5_pass else 'FAIL'} ({w5_filled}/28)")
    
    # Check for zero-byte files (fail phase if >0)
    if zero_byte_files:
        print(f"\n❌ FAIL: {len(zero_byte_files)} zero-byte files found")
        for f in zero_byte_files[:5]:
            print(f"  {f}")
        return False
    
    # Overall pass/fail
    if w7_pass and w6_pass and w5_pass:
        print(f"\n✅ OVERALL PASS: All weeks meet coverage requirements")
        return True
    else:
        print(f"\n❌ OVERALL FAIL: One or more weeks fail coverage requirements")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        sys.exit(1)
