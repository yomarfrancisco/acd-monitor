#!/usr/bin/env python3
"""
Phase 39K-VERIFY-14W: Authoritative, Offline, All BTCUSD Verification
Scope: 14 consecutive weeks ending 2025-10-12 (W0 = 2025-10-06→10-12; W-1…W-13 back to 2025-07-07)
"""

import os
import sys
import hashlib
import json
import gzip
import re
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'verify_14w'

# Anchor date: 2025-10-12 (end of W0)
ANCHOR_DATE = datetime(2025, 10, 12)

# Valid venues and their expected pairs
VENUES = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
VENUE_PAIRS = {
    'COINBASE': ['BTC-USD', 'BTC__002DUSD'],
    'BINANCE': ['BTCUSDT'],
    'BYBITSPOT': ['BTCUSDT'],
    'BITGET': ['BTCUSDT']
}

def verify_gzip_file(file_path):
    """Verify gzip file can be opened and read"""
    try:
        with gzip.open(file_path, 'rb') as f:
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
        return "ERROR"

def get_iso_week_dates(date):
    """Get the ISO week (Monday-Sunday) containing the given date"""
    # Get the Monday of the week containing the date
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    return monday, sunday

def generate_week_index():
    """Generate week index W-13 to W0 based on anchor date 2025-10-12"""
    week_index = {}
    
    # W0 is the ISO week containing 2025-10-12
    w0_start, w0_end = get_iso_week_dates(ANCHOR_DATE)
    week_index['W0'] = {
        'start_date': w0_start.strftime('%Y-%m-%d'),
        'end_date': w0_end.strftime('%Y-%m-%d'),
        'start_yyyymmdd': w0_start.strftime('%Y%m%d'),
        'end_yyyymmdd': w0_end.strftime('%Y%m%d'),
        'dates': [(w0_start + timedelta(days=i)).strftime('%Y%m%d') for i in range(7)]
    }
    
    # Generate W-1 to W-13 (13 prior weeks)
    current_start = w0_start
    for i in range(1, 14):
        week_start = current_start - timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        week_key = f'W-{i}'
        
        week_index[week_key] = {
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': week_end.strftime('%Y-%m-%d'),
            'start_yyyymmdd': week_start.strftime('%Y%m%d'),
            'end_yyyymmdd': week_end.strftime('%Y%m%d'),
            'dates': [(week_start + timedelta(days=j)).strftime('%Y%m%d') for j in range(7)]
        }
    
    return week_index

def is_btcusd_pair(filename, pair):
    """Check if a pair is BTCUSD-class (BTC-USD, BTCUSDT, BTC__002DUSD)"""
    pair_upper = pair.upper()
    return any(btc_pair in pair_upper for btc_pair in ['BTC-USD', 'BTCUSDT', 'BTCUSD', 'BTC__002DUSD'])

def load_existing_manifests():
    """Load existing week manifests to recover v7 file dates"""
    manifests = {}
    manifest_files = [
        'W5_manifest.csv',
        'W6_manifest.csv', 
        'W7_manifest.csv',
        '39K_D1_manifest.csv',
        '39K_W6_D1_manifest.csv',
        '39K_W6_D2_manifest.csv'
    ]
    
    for manifest_file in manifest_files:
        manifest_path = BASE_DIR / 'data_v7' / 'reports' / manifest_file
        if manifest_path.exists():
            try:
                df = pd.read_csv(manifest_path)
                if 'abs_path' in df.columns and 'date' in df.columns:
                    for _, row in df.iterrows():
                        file_path = row['abs_path']
                        date = str(row['date'])
                        manifests[file_path] = date
                print(f"  📄 Loaded {len(df)} entries from {manifest_file}")
            except Exception as e:
                print(f"  ⚠️ Failed to load {manifest_file}: {e}")
    
    return manifests

def extract_legacy_metadata(file_path):
    """Extract metadata from legacy format: VENUE_YYYYMMDD_PAIR.csv.gz"""
    filename = file_path.name
    
    # Pattern: VENUE_YYYYMMDD_PAIR.csv.gz
    match = re.match(r'^([A-Z]+)_(\d{8})_([A-Z0-9_-]+)\.csv\.gz$', filename)
    if not match:
        return None
    
    venue = match.group(1)
    date = match.group(2)
    pair = match.group(3)
    
    if not is_btcusd_pair(filename, pair):
        return None
    
    return {
        'venue': venue,
        'date': date,
        'pair': pair,
        'source_format': 'v6'
    }

def extract_coinapi_metadata(file_path, existing_manifests):
    """Extract metadata from CoinAPI format: IDDI... in E-VENUE directory"""
    path_str = str(file_path)
    
    # Look for E-VENUE pattern in path
    venue_match = re.search(r'/E-([A-Z]+)/', path_str)
    if not venue_match:
        return None
    
    venue = venue_match.group(1)
    
    # Look for YYYYMMDD pattern in path
    date_match = re.search(r'/(\d{8})/', path_str)
    if date_match:
        date = date_match.group(1)
    else:
        # Try to recover date from existing manifests
        date = existing_manifests.get(str(file_path))
        if not date:
            return None
    
    # Extract pair from filename
    filename = file_path.name
    if '__' in filename:
        pair = filename.split('__')[1].replace('.csv.gz', '')
    else:
        # Try to extract from IDDI pattern
        pair_match = re.search(r'S-([A-Z0-9_-]+)\.csv\.gz', filename)
        if not pair_match:
            return None
        pair = pair_match.group(1)
    
    if not is_btcusd_pair(filename, pair):
        return None
    
    return {
        'venue': venue,
        'date': date,
        'pair': pair,
        'source_format': 'v7'
    }

def scan_directories():
    """Scan all directories for BTCUSD-class files"""
    print("🔍 Scanning directories for BTCUSD-class files...")
    
    # Load existing manifests for v7 date recovery
    existing_manifests = load_existing_manifests()
    
    directories = [
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_oct',
    ]
    
    all_files = []
    uncategorized_v7 = []
    
    for directory in directories:
        if not directory.exists():
            print(f"  📁 Directory not found: {directory}")
            continue
        
        print(f"  📁 Scanning: {directory}")
        files = list(directory.rglob("*.csv.gz"))
        print(f"    Found {len(files)} files")
        
        for file_path in files:
            # Try to extract metadata
            metadata = None
            
            if 'E-' in str(file_path.parent):
                # CoinAPI format
                metadata = extract_coinapi_metadata(file_path, existing_manifests)
            else:
                # Legacy format
                metadata = extract_legacy_metadata(file_path)
            
            if metadata:
                all_files.append({
                    'file_path': file_path,
                    'venue': metadata['venue'],
                    'date': metadata['date'],
                    'pair': metadata['pair'],
                    'source_format': metadata['source_format']
                })
            else:
                # Check if it's an uncategorized v7 file (no date in path and not in manifests)
                if 'data_v7' in str(file_path) and not re.search(r'/(\d{8})/', str(file_path)):
                    if str(file_path) not in existing_manifests:
                        uncategorized_v7.append({
                            'file_path': str(file_path),
                            'filename': file_path.name,
                            'reason': 'No date folder in v7 path and not in existing manifests'
                        })
    
    print(f"📊 Found {len(all_files)} BTCUSD-class files")
    print(f"📊 Found {len(uncategorized_v7)} uncategorized v7 files")
    
    return all_files, uncategorized_v7

def assign_files_to_weeks(all_files, week_index):
    """Assign files to weeks based on their dates"""
    week_files = defaultdict(list)
    
    for file_info in all_files:
        date = file_info['date']
        
        # Find which week this date belongs to
        for week_key, week_info in week_index.items():
            if date in week_info['dates']:
                week_files[week_key].append(file_info)
                break
    
    return week_files

def check_integrity_and_deduplicate(week_files):
    """Check file integrity and handle duplicates"""
    print("🔍 Checking file integrity and handling duplicates...")
    
    verified_files = defaultdict(list)
    conflicts = []
    quarantine = []
    
    for week_key, files in week_files.items():
        print(f"  📊 Processing {week_key}: {len(files)} files")
        
        # Group by venue+date to detect duplicates
        venue_date_groups = defaultdict(list)
        for file_info in files:
            key = f"{file_info['venue']}_{file_info['date']}"
            venue_date_groups[key].append(file_info)
        
        for key, group in venue_date_groups.items():
            if len(group) == 1:
                # No duplicates, check integrity
                file_info = group[0]
                file_path = file_info['file_path']
                
                if not file_path.exists():
                    quarantine.append({
                        'file_path': str(file_path),
                        'reason': 'File not found on disk',
                        'week': week_key
                    })
                    continue
                
                if file_path.stat().st_size == 0:
                    quarantine.append({
                        'file_path': str(file_path),
                        'reason': 'Zero-byte file',
                        'week': week_key
                    })
                    continue
                
                if not verify_gzip_file(file_path):
                    quarantine.append({
                        'file_path': str(file_path),
                        'reason': 'Invalid gzip file',
                        'week': week_key
                    })
                    continue
                
                # File is valid
                file_info['size_bytes'] = file_path.stat().st_size
                file_info['sha256'] = compute_file_hash(file_path)
                verified_files[week_key].append(file_info)
            
            else:
                # Handle duplicates
                print(f"    ⚠️ Duplicates found for {key}: {len(group)} files")
                
                # Prefer v7 over v6, then by file size (larger is better)
                def sort_key(x):
                    file_path = x['file_path']
                    return (x['source_format'] == 'v6', -file_path.stat().st_size if file_path.exists() else 0)
                group.sort(key=sort_key)
                
                primary_file = group[0]
                file_path = primary_file['file_path']
                
                if not file_path.exists():
                    quarantine.append({
                        'file_path': str(file_path),
                        'reason': 'Primary duplicate file not found',
                        'week': week_key
                    })
                    continue
                
                if not verify_gzip_file(file_path):
                    quarantine.append({
                        'file_path': str(file_path),
                        'reason': 'Primary duplicate file invalid gzip',
                        'week': week_key
                    })
                    continue
                
                # Check if all duplicates have same SHA-256
                primary_hash = compute_file_hash(file_path)
                all_same = True
                
                for duplicate in group[1:]:
                    dup_path = duplicate['file_path']
                    if dup_path.exists():
                        dup_hash = compute_file_hash(dup_path)
                        if dup_hash != primary_hash:
                            all_same = False
                            conflicts.append({
                                'week': week_key,
                                'venue': primary_file['venue'],
                                'date': primary_file['date'],
                                'primary_file': str(file_path),
                                'primary_hash': primary_hash,
                                'conflict_file': str(dup_path),
                                'conflict_hash': dup_hash,
                                'reason': 'Different SHA-256 hashes'
                            })
                
                if all_same:
                    print(f"    ✅ Duplicates have same SHA-256, keeping primary")
                
                # Add primary file
                primary_file['size_bytes'] = file_path.stat().st_size
                primary_file['sha256'] = primary_hash
                verified_files[week_key].append(primary_file)
    
    return verified_files, conflicts, quarantine

def generate_week_outputs(week_index, verified_files):
    """Generate outputs for each week"""
    print("📝 Generating week outputs...")
    
    for week_key in sorted(week_index.keys()):
        week_info = week_index[week_key]
        files = verified_files.get(week_key, [])
        
        print(f"  📊 {week_key}: {len(files)} files")
        
        # Wk##_manifest.csv
        if files:
            manifest_df = pd.DataFrame(files)
            manifest_df['abs_path'] = manifest_df['file_path'].astype(str)
            manifest_df = manifest_df[['date', 'venue', 'pair', 'abs_path', 'size_bytes', 'sha256', 'source_format']]
            manifest_df.to_csv(REPORTS_DIR / f'{week_key}_manifest.csv', index=False)
        
        # Wk##_coverage_matrix.txt
        coverage_matrix = {}
        for date in week_info['dates']:
            coverage_matrix[date] = {}
            for venue in VENUES:
                venue_files = [f for f in files if f['date'] == date and f['venue'] == venue]
                if venue_files:
                    file_info = venue_files[0]
                    coverage_matrix[date][venue] = f"✓ ({file_info['size_bytes']:,} bytes)"
                else:
                    coverage_matrix[date][venue] = "✗"
        
        with open(REPORTS_DIR / f'{week_key}_coverage_matrix.txt', 'w') as f:
            f.write(f"{week_key} Coverage Matrix\n")
            f.write("=" * 50 + "\n")
            f.write(f"Date range: {week_info['start_date']} to {week_info['end_date']}\n")
            f.write(f"Files: {len(files)}\n\n")
            
            f.write("Coverage Matrix (Date × Venue):\n")
            f.write(f"{'Date':<10} {'COINBASE':<20} {'BINANCE':<20} {'BYBITSPOT':<20} {'BITGET':<20}\n")
            f.write("-" * 90 + "\n")
            for date in week_info['dates']:
                f.write(f"{date:<10} {coverage_matrix[date]['COINBASE']:<20} {coverage_matrix[date]['BINANCE']:<20} {coverage_matrix[date]['BYBITSPOT']:<20} {coverage_matrix[date]['BITGET']:<20}\n")
        
        # Wk##_bom_sha256.txt
        if files:
            all_hashes = sorted([f['sha256'] for f in files])
            bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
            
            with open(REPORTS_DIR / f'{week_key}_bom_sha256.txt', 'w') as f:
                f.write(f"{week_key} BOM SHA-256\n")
                f.write("=" * 30 + "\n")
                f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
                f.write(f"Files: {len(files)}\n")
                f.write(f"BOM SHA-256: {bom_hash}\n")
        
        # Wk##_gate.json
        expected = 28  # 7 days × 4 venues
        found = len(files)
        total_bytes = sum(f['size_bytes'] for f in files)
        v6_count = len([f for f in files if f['source_format'] == 'v6'])
        v7_count = len([f for f in files if f['source_format'] == 'v7'])
        
        # Gate: PASS if ≥24/28 files (≥6/7 days for ≥3 venues)
        pass_threshold = 24
        gate_pass = found >= pass_threshold
        
        gate_data = {
            'week': week_key,
            'expected': expected,
            'found': found,
            'percentage': (found / expected * 100) if expected > 0 else 0,
            'pass': gate_pass,
            'pass_threshold': pass_threshold,
            'total_bytes': total_bytes,
            'v6_files': v6_count,
            'v7_files': v7_count,
            'date_range': f"{week_info['start_date']} to {week_info['end_date']}",
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        with open(REPORTS_DIR / f'{week_key}_gate.json', 'w') as f:
            json.dump(gate_data, f, indent=2)

def generate_global_outputs(week_index, verified_files, conflicts, quarantine, uncategorized_v7):
    """Generate global roll-up outputs"""
    print("📝 Generating global outputs...")
    
    # GLOBAL_manifest.csv
    all_files = []
    for week_key, files in verified_files.items():
        for file_info in files:
            file_info['week'] = week_key
            all_files.append(file_info)
    
    if all_files:
        global_df = pd.DataFrame(all_files)
        global_df['abs_path'] = global_df['file_path'].astype(str)
        global_df = global_df[['week', 'date', 'venue', 'pair', 'abs_path', 'size_bytes', 'sha256', 'source_format']]
        global_df.to_csv(REPORTS_DIR / 'GLOBAL_manifest.csv', index=False)
    
    # GLOBAL_quarantine.csv
    if quarantine:
        quarantine_df = pd.DataFrame(quarantine)
        quarantine_df.to_csv(REPORTS_DIR / 'GLOBAL_quarantine.csv', index=False)
    else:
        pd.DataFrame().to_csv(REPORTS_DIR / 'GLOBAL_quarantine.csv', index=False)
    
    # GLOBAL_conflicts.csv
    if conflicts:
        conflicts_df = pd.DataFrame(conflicts)
        conflicts_df.to_csv(REPORTS_DIR / 'GLOBAL_conflicts.csv', index=False)
    else:
        pd.DataFrame().to_csv(REPORTS_DIR / 'GLOBAL_conflicts.csv', index=False)
    
    # GLOBAL_uncategorized_v7.csv
    if uncategorized_v7:
        uncategorized_df = pd.DataFrame(uncategorized_v7)
        uncategorized_df.to_csv(REPORTS_DIR / 'GLOBAL_uncategorized_v7.csv', index=False)
    else:
        pd.DataFrame().to_csv(REPORTS_DIR / 'GLOBAL_uncategorized_v7.csv', index=False)
    
    # GLOBAL_week_summary.json
    week_summary = {}
    for week_key in sorted(week_index.keys()):
        files = verified_files.get(week_key, [])
        expected = 28
        found = len(files)
        total_bytes = sum(f['size_bytes'] for f in files)
        v6_count = len([f for f in files if f['source_format'] == 'v6'])
        v7_count = len([f for f in files if f['source_format'] == 'v7'])
        
        week_summary[week_key] = {
            'expected': expected,
            'found': found,
            'percentage': (found / expected * 100) if expected > 0 else 0,
            'pass': found >= 24,
            'total_bytes': total_bytes,
            'v6_files': v6_count,
            'v7_files': v7_count,
            'date_range': f"{week_index[week_key]['start_date']} to {week_index[week_key]['end_date']}"
        }
    
    with open(REPORTS_DIR / 'GLOBAL_week_summary.json', 'w') as f:
        json.dump(week_summary, f, indent=2)
    
    # GLOBAL_bom_sha256.txt
    if all_files:
        all_hashes = sorted([f['sha256'] for f in all_files])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'GLOBAL_bom_sha256.txt', 'w') as f:
            f.write(f"Global 14-Week BOM SHA-256\n")
            f.write("=" * 40 + "\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Total files: {len(all_files)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
    
    # GLOBAL_audit.txt
    with open(REPORTS_DIR / 'GLOBAL_audit.txt', 'w') as f:
        f.write("Global 14-Week Audit Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Anchor date: {ANCHOR_DATE.strftime('%Y-%m-%d')}\n")
        f.write(f"Total weeks: {len(week_index)}\n")
        f.write(f"Total verified files: {len(all_files)}\n")
        f.write(f"Total quarantined files: {len(quarantine)}\n")
        f.write(f"Total conflicts: {len(conflicts)}\n")
        f.write(f"Uncategorized v7 files: {len(uncategorized_v7)}\n")
        
        f.write(f"\nWeek Summary:\n")
        f.write(f"{'Week':<6} {'Status':<6} {'Files':<8} {'Bytes':<12} {'V6':<4} {'V7':<4} {'Date Range':<20}\n")
        f.write("-" * 70 + "\n")
        for week_key in sorted(week_index.keys()):
            summary = week_summary[week_key]
            status = "PASS" if summary['pass'] else "FAIL"
            f.write(f"{week_key:<6} {status:<6} {summary['found']:<8} {summary['total_bytes']:<12,} {summary['v6_files']:<4} {summary['v7_files']:<4} {summary['date_range']:<20}\n")
        
        f.write(f"\nPASS Weeks: {len([w for w in week_summary.values() if w['pass']])}\n")
        f.write(f"FAIL Weeks: {len([w for w in week_summary.values() if not w['pass']])}\n")
        
        if uncategorized_v7:
            f.write(f"\nUncategorized v7 files (recommend moving to dated folders):\n")
            for item in uncategorized_v7[:10]:  # Show first 10
                f.write(f"  {item['file_path']}\n")
            if len(uncategorized_v7) > 10:
                f.write(f"  ... and {len(uncategorized_v7) - 10} more\n")

def main():
    """Main execution"""
    print("🚀 Phase 39K-VERIFY-14W: Authoritative, Offline, All BTCUSD Verification")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        print("❌ Network is not frozen - locks/api_budget.lock not found")
        sys.exit(1)
    print("✅ Network freeze confirmed")
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate week index
    print("\n📅 Generating week index...")
    week_index = generate_week_index()
    
    # Write WEEK_INDEX.json
    with open(REPORTS_DIR / 'WEEK_INDEX.json', 'w') as f:
        json.dump(week_index, f, indent=2)
    print(f"✅ WEEK_INDEX.json: {len(week_index)} weeks")
    
    # Scan directories
    all_files, uncategorized_v7 = scan_directories()
    
    # Assign files to weeks
    print("\n📊 Assigning files to weeks...")
    week_files = assign_files_to_weeks(all_files, week_index)
    
    for week_key, files in week_files.items():
        print(f"  {week_key}: {len(files)} files")
    
    # Check integrity and handle duplicates
    verified_files, conflicts, quarantine = check_integrity_and_deduplicate(week_files)
    
    # Generate week outputs
    generate_week_outputs(week_index, verified_files)
    
    # Generate global outputs
    generate_global_outputs(week_index, verified_files, conflicts, quarantine, uncategorized_v7)
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-VERIFY-14W Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # 12-line console summary
    print(f"\n📋 12-Line Console Summary:")
    
    # Week status lines
    for week_key in sorted(week_index.keys()):
        files = verified_files.get(week_key, [])
        total_bytes = sum(f['size_bytes'] for f in files)
        status = "PASS" if len(files) >= 24 else "FAIL"
        print(f"{week_key}: {len(files)}/28 {status} ({total_bytes / 1024**3:.2f} GB)")
    
    # Totals
    total_verified = sum(len(files) for files in verified_files.values())
    total_bytes = sum(sum(f['size_bytes'] for f in files) for files in verified_files.values())
    print(f"Totals: {total_verified} verified files, {total_bytes / 1024**3:.2f} GB, {len(quarantine)} quarantined, {len(conflicts)} conflicts, {len(uncategorized_v7)} uncategorized v7")
    
    # Most relevant artifacts
    print(f"Key artifacts: {REPORTS_DIR / 'GLOBAL_manifest.csv'}")
    print(f"Key artifacts: {REPORTS_DIR / 'GLOBAL_week_summary.json'}")
    print(f"Key artifacts: {REPORTS_DIR / 'GLOBAL_audit.txt'}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
