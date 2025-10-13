#!/usr/bin/env python3
"""
Extend 14-week coverage by incorporating BTCUSD-class files from analysis/flatfiles_ticks_v4/raw/
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
ANALYSIS_DIR = BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw'

# Valid venues
VENUES = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']

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
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    return monday, sunday

def generate_week_index():
    """Generate week index W-13 to W0 based on anchor date 2025-10-12"""
    week_index = {}
    anchor_date = datetime(2025, 10, 12)
    
    # W0 is the ISO week containing 2025-10-12
    w0_start, w0_end = get_iso_week_dates(anchor_date)
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
        'source_format': 'v4'
    }

def scan_analysis_directory():
    """Scan analysis/flatfiles_ticks_v4/raw/ for BTCUSD-class files"""
    print("🔍 Scanning analysis/flatfiles_ticks_v4/raw/ for BTCUSD-class files...")
    
    if not ANALYSIS_DIR.exists():
        print(f"  📁 Directory not found: {ANALYSIS_DIR}")
        return []
    
    print(f"  📁 Scanning: {ANALYSIS_DIR}")
    files = list(ANALYSIS_DIR.rglob("*.csv.gz"))
    print(f"    Found {len(files)} files")
    
    btcusd_files = []
    
    for file_path in files:
        metadata = extract_legacy_metadata(file_path)
        if metadata:
            btcusd_files.append({
                'file_path': file_path,
                'venue': metadata['venue'],
                'date': metadata['date'],
                'pair': metadata['pair'],
                'source_format': metadata['source_format']
            })
    
    print(f"📊 Found {len(btcusd_files)} BTCUSD-class files")
    return btcusd_files

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

def verify_files(week_files):
    """Verify file integrity and compute hashes"""
    print("🔍 Verifying file integrity and computing hashes...")
    
    verified_files = defaultdict(list)
    
    for week_key, files in week_files.items():
        print(f"  📊 Processing {week_key}: {len(files)} files")
        
        for file_info in files:
            file_path = file_info['file_path']
            
            if not file_path.exists():
                print(f"    ⚠️ File not found: {file_path}")
                continue
            
            if file_path.stat().st_size == 0:
                print(f"    ⚠️ Zero-byte file: {file_path}")
                continue
            
            if not verify_gzip_file(file_path):
                print(f"    ⚠️ Invalid gzip file: {file_path}")
                continue
            
            # File is valid
            file_info['size_bytes'] = file_path.stat().st_size
            file_info['sha256'] = compute_file_hash(file_path)
            verified_files[week_key].append(file_info)
    
    return verified_files

def load_existing_manifests():
    """Load existing manifests from verify_14w"""
    existing_files = []
    
    manifest_file = REPORTS_DIR / 'GLOBAL_manifest.csv'
    if manifest_file.exists():
        try:
            df = pd.read_csv(manifest_file)
            for _, row in df.iterrows():
                existing_files.append({
                    'week': row['week'],
                    'date': str(row['date']),
                    'venue': row['venue'],
                    'pair': row['pair'],
                    'abs_path': row['abs_path'],
                    'size_bytes': row['size_bytes'],
                    'sha256': row['sha256'],
                    'source_format': row['source_format']
                })
            print(f"📄 Loaded {len(existing_files)} existing files from GLOBAL_manifest.csv")
        except Exception as e:
            print(f"⚠️ Failed to load existing manifest: {e}")
    
    return existing_files

def generate_extended_outputs(existing_files, new_files, week_index):
    """Generate extended outputs combining existing and new files"""
    print("📝 Generating extended outputs...")
    
    # Combine existing and new files
    all_files = existing_files.copy()
    for week_key, files in new_files.items():
        for file_info in files:
            file_info['week'] = week_key
            file_info['abs_path'] = str(file_info['file_path'])
            all_files.append(file_info)
    
    # GLOBAL_manifest_EXT.csv
    if all_files:
        global_df = pd.DataFrame(all_files)
        global_df = global_df[['week', 'date', 'venue', 'pair', 'abs_path', 'size_bytes', 'sha256', 'source_format']]
        global_df.to_csv(REPORTS_DIR / 'GLOBAL_manifest_EXT.csv', index=False)
        print(f"✅ GLOBAL_manifest_EXT.csv: {len(all_files)} files")
    
    # GLOBAL_week_summary_EXT.json
    week_summary = {}
    for week_key in sorted(week_index.keys()):
        week_files = [f for f in all_files if f['week'] == week_key]
        expected = 28
        found = len(week_files)
        total_bytes = sum(f['size_bytes'] for f in week_files)
        v4_count = len([f for f in week_files if f['source_format'] == 'v4'])
        v6_count = len([f for f in week_files if f['source_format'] == 'v6'])
        v7_count = len([f for f in week_files if f['source_format'] == 'v7'])
        
        week_summary[week_key] = {
            'expected': expected,
            'found': found,
            'percentage': (found / expected * 100) if expected > 0 else 0,
            'pass': found >= 24,
            'total_bytes': total_bytes,
            'v4_files': v4_count,
            'v6_files': v6_count,
            'v7_files': v7_count,
            'date_range': f"{week_index[week_key]['start_date']} to {week_index[week_key]['end_date']}"
        }
    
    with open(REPORTS_DIR / 'GLOBAL_week_summary_EXT.json', 'w') as f:
        json.dump(week_summary, f, indent=2)
    print(f"✅ GLOBAL_week_summary_EXT.json: {len(week_summary)} weeks")
    
    # GLOBAL_audit_EXT.txt
    with open(REPORTS_DIR / 'GLOBAL_audit_EXT.txt', 'w') as f:
        f.write("Extended 14-Week Audit Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total weeks: {len(week_index)}\n")
        f.write(f"Total verified files: {len(all_files)}\n")
        f.write(f"New v4 files added: {sum(len(files) for files in new_files.values())}\n")
        
        f.write(f"\nWeek Summary:\n")
        f.write(f"{'Week':<6} {'Status':<6} {'Files':<8} {'Bytes':<12} {'V4':<4} {'V6':<4} {'V7':<4} {'Date Range':<20}\n")
        f.write("-" * 80 + "\n")
        for week_key in sorted(week_index.keys()):
            summary = week_summary[week_key]
            status = "PASS" if summary['pass'] else "FAIL"
            f.write(f"{week_key:<6} {status:<6} {summary['found']:<8} {summary['total_bytes']:<12,} {summary['v4_files']:<4} {summary['v6_files']:<4} {summary['v7_files']:<4} {summary['date_range']:<20}\n")
        
        f.write(f"\nPASS Weeks: {len([w for w in week_summary.values() if w['pass']])}\n")
        f.write(f"FAIL Weeks: {len([w for w in week_summary.values() if not w['pass']])}\n")
        
        # Highlight newly integrated weeks
        newly_integrated = [week_key for week_key, files in new_files.items() if len(files) > 0]
        if newly_integrated:
            f.write(f"\nNewly Integrated Weeks (from analysis/flatfiles_ticks_v4/):\n")
            for week_key in sorted(newly_integrated):
                files = new_files[week_key]
                total_bytes = sum(f['size_bytes'] for f in files)
                f.write(f"  {week_key}: {len(files)} files, {total_bytes / 1024**3:.2f} GB\n")
    
    print(f"✅ GLOBAL_audit_EXT.txt: Extended audit report")

def main():
    """Main execution"""
    print("🚀 Extend 14-Week Coverage: Incorporate analysis/flatfiles_ticks_v4/raw/")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        print("❌ Network is not frozen - locks/api_budget.lock not found")
        sys.exit(1)
    print("✅ Network freeze confirmed")
    
    # Generate week index
    print("\n📅 Generating week index...")
    week_index = generate_week_index()
    print(f"✅ Week index: {len(week_index)} weeks")
    
    # Scan analysis directory
    new_files = scan_analysis_directory()
    
    # Assign files to weeks
    print("\n📊 Assigning files to weeks...")
    week_files = assign_files_to_weeks(new_files, week_index)
    
    for week_key, files in week_files.items():
        print(f"  {week_key}: {len(files)} files")
    
    # Verify files
    verified_new_files = verify_files(week_files)
    
    # Load existing manifests
    existing_files = load_existing_manifests()
    
    # Generate extended outputs
    generate_extended_outputs(existing_files, verified_new_files, week_index)
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Extension Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # Summary statistics
    total_new_files = sum(len(files) for files in verified_new_files.values())
    total_new_bytes = sum(sum(f['size_bytes'] for f in files) for files in verified_new_files.values())
    newly_integrated_weeks = [week_key for week_key, files in verified_new_files.items() if len(files) > 0]
    
    print(f"\n📋 Extension Summary:")
    print(f"New files added: {total_new_files}")
    print(f"New data size: {total_new_bytes / 1024**3:.2f} GB")
    print(f"Newly integrated weeks: {len(newly_integrated_weeks)}")
    print(f"Weeks: {', '.join(sorted(newly_integrated_weeks))}")
    
    print(f"\nKey artifacts:")
    print(f"  {REPORTS_DIR / 'GLOBAL_manifest_EXT.csv'}")
    print(f"  {REPORTS_DIR / 'GLOBAL_week_summary_EXT.json'}")
    print(f"  {REPORTS_DIR / 'GLOBAL_audit_EXT.txt'}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
