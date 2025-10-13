#!/usr/bin/env python3
"""
Phase 39H — Validate Method, Recover Missing Files, Make Overwrites Impossible
Objective: Recover missing files using proven Week-7 method with atomic writes and cryptographic verification
"""

import os
import sys
import hashlib
import json
import shutil
import gzip
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
import psutil

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports'
LOCK_FILE = BASE_DIR / 'locks' / 'api_budget.lock'

# API Configuration (from DOWNLOAD_METHOD.md)
API_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
BASE_URL = 'https://s3.flatfiles.coinapi.io/'
DOWNLOAD_BASE_URL = 'https://s3.flatfiles.coinapi.io/coinapi/'
HEADERS = {
    'X-CoinAPI-Key': API_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

# Target configuration
TARGET_VENUES = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
TARGET_PAIRS = ['BTC-USD', 'BTCUSD', 'BTCUSDT']

# Date ranges
W7_DATES = [20250707, 20250708, 20250709, 20250710, 20250711, 20250712, 20250713]
W6_DATES = [20250714, 20250715, 20250716, 20250717, 20250718, 20250719, 20250720]

# Expected script hash from proven Week-7 success
EXPECTED_SCRIPT_HASH = '6716384d2c6c2210f706265afcbbb5e7cfca92c765a50953ad059969d5c173b3'

def check_network_freeze():
    """Ensure network is frozen initially"""
    print("🔒 Checking initial network freeze status...")
    
    if not LOCK_FILE.exists():
        print("⚠️ API lock missing - creating it")
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write(f"""API_BUDGET_LOCK
Created: {datetime.utcnow().isoformat()}Z
Reason: Phase 39H - Initial freeze check
Status: ACTIVE
Network calls: BLOCKED
""")
        print("🔒 API lock created")
    else:
        print("✅ API lock exists - network frozen")
    
    return True

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

def extract_venue_date_pair_coinapi(file_path):
    """Extract venue, date, and pair from CoinAPI style path"""
    path_parts = file_path.parts
    venue = None
    date = None
    pair = None
    
    # Look for venue in path
    for part in path_parts:
        if part in TARGET_VENUES:
            venue = part
            break
    
    # Look for date in path (YYYYMMDD format)
    for part in path_parts:
        if part.startswith('202507') and len(part) == 8:
            try:
                date = int(part)
                break
            except ValueError:
                continue
    
    # Extract pair from filename
    filename = file_path.name
    if 'BTCUSDT' in filename:
        pair = 'BTCUSDT'
    elif 'BTC__002DUSD' in filename:  # COINBASE format
        pair = 'BTC-USD'
    elif 'BTCUSD' in filename and 'BTCUSDT' not in filename and 'BTC__002D' not in filename:
        pair = 'BTCUSD'
    
    return venue, date, pair

def extract_venue_date_pair_legacy(file_path):
    """Extract venue, date, and pair from legacy style path"""
    filename = file_path.name
    
    # Legacy format: VENUE_YYYYMMDD_PAIR.csv.gz
    parts = filename.replace('.csv.gz', '').split('_')
    if len(parts) >= 3:
        venue = parts[0]
        try:
            date = int(parts[1])
        except ValueError:
            date = None
        pair = parts[2]
        
        # Validate venue
        if venue not in TARGET_VENUES:
            venue = None
        
        return venue, date, pair
    
    return None, None, None

def build_disk_inventory():
    """Build fresh disk inventory"""
    print("📊 Building fresh disk inventory...")
    
    # Load 39F manifest for date mapping
    f39_manifest_path = REPORTS_DIR / '39F_manifest.csv'
    f39_date_map = {}
    if f39_manifest_path.exists():
        try:
            f39_df = pd.read_csv(f39_manifest_path)
            for _, row in f39_df.iterrows():
                filename = row['filename']
                date = row['date']
                venue = row['venue']
                path = row['path']
                f39_date_map[path] = {'date': date, 'venue': venue, 'filename': filename}
            print(f"📋 Loaded 39F manifest: {len(f39_date_map)} files")
        except Exception as e:
            print(f"⚠️ Error reading 39F manifest: {e}")
    
    # Directories to scan
    scan_dirs = [
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul'
    ]
    
    inventory_data = []
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            print(f"⚠️ Directory not found: {scan_dir}")
            continue
        
        print(f"📁 Scanning: {scan_dir}")
        
        for file_path in scan_dir.rglob('*.csv.gz'):
            try:
                size = file_path.stat().st_size
                sha256 = compute_file_hash(file_path)
                
                # Try CoinAPI format first
                venue, date, pair = extract_venue_date_pair_coinapi(file_path)
                
                # If that failed, try legacy format
                if not venue or not date or not pair:
                    venue, date, pair = extract_venue_date_pair_legacy(file_path)
                
                # Use 39F manifest for date mapping if available
                file_path_str = str(file_path)
                if file_path_str in f39_date_map:
                    date = f39_date_map[file_path_str]['date']
                    venue = f39_date_map[file_path_str]['venue']
                
                inventory_data.append({
                    'path': str(file_path),
                    'fname': file_path.name,
                    'bytes': size,
                    'sha256': sha256,
                    'venue': venue,
                    'date': date,
                    'pair': pair
                })
                
            except Exception as e:
                print(f"⚠️ Error processing {file_path}: {e}")
    
    df = pd.DataFrame(inventory_data)
    print(f"📊 Total files found: {len(df)}")
    
    return df

def create_gap_list(inventory_df):
    """Create gap list of missing files"""
    print("🔍 Creating gap list...")
    
    # Define target grid
    target_grid = []
    
    # W-7: COINBASE only
    for date in W7_DATES:
        target_grid.append({
            'date': date,
            'venue': 'COINBASE',
            'pair': 'BTC-USD',
            'week': 'W-7'
        })
    
    # W-6: All venues
    for date in W6_DATES:
        for venue in TARGET_VENUES:
            target_grid.append({
                'date': date,
                'venue': venue,
                'pair': 'BTCUSDT',  # Most common pair
                'week': 'W-6'
            })
    
    print(f"📋 Target grid: {len(target_grid)} slots")
    
    # Find gaps
    gap_list = []
    for target in target_grid:
        # Check if this slot exists in inventory
        existing = inventory_df[
            (inventory_df['date'] == target['date']) &
            (inventory_df['venue'] == target['venue']) &
            (inventory_df['pair'].isin(TARGET_PAIRS))
        ]
        
        if len(existing) == 0:
            gap_list.append(target)
    
    print(f"📊 Gaps found: {len(gap_list)}")
    
    # Write gap list
    if gap_list:
        gap_df = pd.DataFrame(gap_list)
        gap_path = REPORTS_DIR / '39H_gaplist.csv'
        gap_df.to_csv(gap_path, index=False)
        print(f"✅ Gap list written: {gap_path}")
    else:
        print("✅ No gaps found - all target files exist")
    
    return gap_list

def validate_method():
    """Validate method against proven Week-7 success"""
    print("🔍 Validating method...")
    
    # Check script hash
    script_path = BASE_DIR / 'phase_39f_validation_first.py'
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    with open(script_path, 'rb') as f:
        content = f.read()
    actual_hash = hashlib.sha256(content).hexdigest()
    
    print(f"📄 Script: {script_path}")
    print(f"🔐 Expected hash: {EXPECTED_SCRIPT_HASH}")
    print(f"🔐 Actual hash:   {actual_hash}")
    
    if actual_hash != EXPECTED_SCRIPT_HASH:
        print("❌ Script hash mismatch!")
        return False
    
    # Write downloader SHA
    with open(REPORTS_DIR / '39H_downloader_sha.txt', 'w') as f:
        f.write(f"DOWNLOADER_SCRIPT_SHA256: {actual_hash}\n")
        f.write(f"SCRIPT_PATH: {script_path}\n")
        f.write(f"VALIDATED: {datetime.utcnow().isoformat()}Z\n")
    
    print("✅ Method validation passed")
    return True

def is_btcusd_class(filename):
    """Check if filename indicates BTCUSD-class pair"""
    filename_upper = filename.upper()
    
    # Standard patterns
    if any(pair in filename_upper for pair in TARGET_PAIRS):
        return True
    
    # COINBASE specific patterns
    if 'BTC__002D' in filename_upper:
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

def download_file_atomic(date, venue, key, output_dir, max_attempts=3):
    """Download file with atomic write and verification"""
    download_url = f'{DOWNLOAD_BASE_URL}{key}'
    
    # Create output path with .part extension
    filename = key.split('/')[-1]
    part_path = output_dir / f'{filename}.part'
    final_path = output_dir / filename
    
    # Skip if final file already exists (no-clobber)
    if final_path.exists():
        return 'SKIP', f'File already exists: {final_path}'
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(download_url, headers=HEADERS, timeout=120)
            if response.status_code == 200:
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
                
                return 'OK', f'Downloaded: {filename} ({final_path.stat().st_size} bytes, SHA-256: {sha256})'
            else:
                if attempt < max_attempts - 1:
                    time.sleep(60 * (attempt + 1))  # Exponential backoff
                return 'FAIL', f'HTTP {response.status_code}'
        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(60 * (attempt + 1))
            print(f"⚠️ Download error {date}/{venue}/{filename}: {e}")
            return 'FAIL', str(e)
    
    return 'FAIL', 'Max attempts exceeded'

def controlled_recovery(gap_list):
    """Execute controlled recovery with atomic writes"""
    print("🚀 Starting controlled recovery...")
    
    # Remove lock temporarily
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print("🔓 Temporarily removed API lock")
    
    # Create output directories
    w7_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7'
    w6_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6'
    w7_dir.mkdir(parents=True, exist_ok=True)
    w6_dir.mkdir(parents=True, exist_ok=True)
    
    # Tracking
    total_calls = 0
    list_calls = 0
    get_calls = 0
    results = []
    
    # Process gaps
    for gap in gap_list:
        date = gap['date']
        venue = gap['venue']
        week = gap['week']
        
        print(f"📅 Processing {week} {date}/{venue}")
        
        # Determine output directory
        if week == 'W-7':
            output_dir = w7_dir / str(date) / venue
        else:  # W-6
            output_dir = w6_dir / str(date) / venue
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # LIST objects
        keys, status_code = list_s3_objects(date, venue)
        list_calls += 1
        total_calls += 1
        
        if keys:
            for key in keys[:3]:  # Max 3 files per day/venue
                result, message = download_file_atomic(date, venue, key, output_dir)
                get_calls += 1
                total_calls += 1
                
                results.append({
                    'date': date,
                    'venue': venue,
                    'key': key,
                    'result': result,
                    'message': message
                })
                
                print(f"    {result}: {message}")
        
        # Check limits
        if total_calls >= 120:
            print("⚠️ Reached call limit (120)")
            break
    
    # Recreate lock
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'w') as f:
        f.write(f"""API_BUDGET_LOCK
Recreated: {datetime.utcnow().isoformat()}Z
Reason: Phase 39H Complete
Status: ACTIVE
Network calls: BLOCKED
""")
    print("🔒 API lock recreated")
    
    # Write run log
    with open(REPORTS_DIR / '39H_runlog.txt', 'w') as f:
        f.write(f"""Phase 39H Run Log
==================
Start: {datetime.utcnow().isoformat()}Z
Total calls: {total_calls}
List calls: {list_calls}
Get calls: {get_calls}
Gaps processed: {len(gap_list)}

Results:
""")
        for result in results:
            f.write(f"{result['result']}: {result['date']}/{result['venue']} - {result['message']}\n")
    
    return {
        'total_calls': total_calls,
        'list_calls': list_calls,
        'get_calls': get_calls,
        'results': results
    }

def post_download_audit():
    """Post-download audit and refreeze"""
    print("📊 Post-download audit...")
    
    # Rebuild inventory
    inventory_df = build_disk_inventory()
    
    # Filter to BTCUSD-class only
    btcusd_df = inventory_df[inventory_df['pair'].isin(TARGET_PAIRS)]
    
    # Build coverage matrices
    coverage_data = {}
    
    for week_name, dates in [('W-7', W7_DATES), ('W-6', W6_DATES)]:
        week_df = btcusd_df[btcusd_df['date'].isin(dates)]
        
        # Build matrix
        matrix = []
        for date in dates:
            day_name = f"Jul {int(str(date)[6:8])}"
            row = [day_name]
            
            for venue in TARGET_VENUES:
                venue_date_files = week_df[(week_df['venue'] == venue) & (week_df['date'] == date)]
                if len(venue_date_files) > 0:
                    row.append('✓')
                else:
                    row.append('✗')
            matrix.append(row)
        
        # Add venue totals
        venue_totals = ['TOTAL']
        for venue in TARGET_VENUES:
            venue_files = week_df[week_df['venue'] == venue]
            venue_dates = venue_files['date'].nunique()
            venue_totals.append(f"{venue_dates}/7")
        matrix.append(venue_totals)
        
        coverage_data[week_name] = {
            'matrix': matrix,
            'total_files': len(week_df),
            'total_slots': len(week_df)
        }
    
    # Write coverage matrix
    with open(REPORTS_DIR / '39H_coverage_matrix.txt', 'w') as f:
        f.write("COVERAGE MATRIX - Week -7, -6\n")
        f.write("=" * 50 + "\n\n")
        
        for week_name, data in coverage_data.items():
            f.write(f"{week_name}:\n")
            f.write("-" * 30 + "\n")
            
            # Header
            f.write("Day".ljust(8))
            for venue in TARGET_VENUES:
                f.write(f"{venue[:4]}".ljust(6))
            f.write("\n")
            
            # Matrix rows
            for row in data['matrix']:
                f.write(f"{row[0]}".ljust(8))
                for cell in row[1:]:
                    f.write(f"{cell}".ljust(6))
                f.write("\n")
            
            f.write(f"\nSummary: {data['total_files']} files\n\n")
    
    # Run gate checks
    gates = {}
    
    # W-7 COINBASE gate: ≥ 5/7 dates filled
    w7_df = btcusd_df[btcusd_df['date'].isin(W7_DATES)]
    w7_coinbase_df = w7_df[w7_df['venue'] == 'COINBASE']
    w7_coinbase_dates = w7_coinbase_df['date'].nunique()
    gates['w7_coinbase'] = {
        'condition': '≥ 5/7 dates filled',
        'actual': f"{w7_coinbase_dates}/7",
        'passed': w7_coinbase_dates >= 5
    }
    
    # W-6 aggregate gate: ≥ 20/28 slots
    w6_df = btcusd_df[btcusd_df['date'].isin(W6_DATES)]
    w6_total_slots = len(w6_df)
    gates['w6_aggregate'] = {
        'condition': '≥ 20/28 slots',
        'actual': f"{w6_total_slots}/28",
        'passed': w6_total_slots >= 20
    }
    
    # Overall gate status
    all_passed = all(gate['passed'] for gate in gates.values())
    gates['overall'] = {
        'status': 'PASS' if all_passed else 'FAIL',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    # Write gates JSON
    with open(REPORTS_DIR / '39H_gates.json', 'w') as f:
        json.dump(gates, f, indent=2)
    
    # Create manifest
    manifest_data = []
    for _, row in btcusd_df.iterrows():
        manifest_data.append({
            'path': row['path'],
            'date': row['date'],
            'venue': row['venue'],
            'pair': row['pair'],
            'size': row['bytes'],
            'sha256': row['sha256'],
            'source_key': 'RECOVERED'  # Placeholder
        })
    
    manifest_df = pd.DataFrame(manifest_data)
    manifest_path = REPORTS_DIR / '39H_manifest.csv'
    manifest_df.to_csv(manifest_path, index=False)
    
    # Create BOM hash
    btcusd_hashes = sorted(btcusd_df['sha256'].tolist())
    bom_content = '\n'.join(btcusd_hashes)
    bom_hash = hashlib.sha256(bom_content.encode()).hexdigest()
    
    with open(REPORTS_DIR / '39H_bom_sha256.txt', 'w') as f:
        f.write(f"BOM_SHA256: {bom_hash}\n")
        f.write(f"FILES_COUNT: {len(btcusd_df)}\n")
        f.write(f"CREATED: {datetime.utcnow().isoformat()}Z\n")
    
    print(f"✅ Post-download audit complete")
    print(f"📊 Gate checks: {gates['overall']['status']}")
    for gate_name, gate_data in gates.items():
        if gate_name != 'overall':
            status = "✅ PASS" if gate_data['passed'] else "❌ FAIL"
            print(f"  {gate_name}: {status} ({gate_data['actual']})")
    
    return gates

def main():
    """Main execution"""
    print("🚀 Phase 39H — Validate Method, Recover Missing Files, Make Overwrites Impossible")
    print("=" * 80)
    
    start_time = time.time()
    
    # Create directories
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # H0: Disk truth & gap list
    print("\n📋 H0: Disk truth & gap list")
    if not check_network_freeze():
        print("❌ Network freeze check failed")
        sys.exit(1)
    
    inventory_df = build_disk_inventory()
    gap_list = create_gap_list(inventory_df)
    
    if not gap_list:
        print("✅ No gaps found - all target files exist")
        print("🔒 Refreezing network...")
        sys.exit(0)
    
    # H1: Validation of method
    print("\n🔍 H1: Validation of method")
    if not validate_method():
        print("❌ Method validation failed")
        sys.exit(1)
    
    # H2: Controlled recovery
    print("\n🚀 H2: Controlled recovery")
    recovery_results = controlled_recovery(gap_list)
    
    # H3: Post-download audit & refreeze
    print("\n📊 H3: Post-download audit & refreeze")
    gates = post_download_audit()
    
    # Check runtime
    runtime_minutes = (time.time() - start_time) / 60
    print(f"⏱️ Runtime: {runtime_minutes:.1f} minutes")
    
    # Final status
    if gates['overall']['status'] == 'PASS':
        print("\n✅ Phase 39H Complete - All gates passed")
        sys.exit(0)
    else:
        print("\n❌ Phase 39H Failed - Some gates failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
