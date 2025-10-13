#!/usr/bin/env python3
"""
Phase 39K-REVERIFY-FIX: Single Source of Truth Coverage Verification
"""

import os
import sys
import hashlib
import json
import gzip
import re
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports'

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

def load_weekly_manifest(week_label, manifest_path):
    """Load a weekly manifest and add week label"""
    if not manifest_path.exists():
        print(f"⚠️ Weekly manifest not found: {manifest_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(manifest_path)
        df['week_label'] = week_label
        return df
    except Exception as e:
        print(f"⚠️ Error loading manifest {manifest_path}: {e}")
        return pd.DataFrame()

def main():
    """Main execution"""
    print("🚀 Phase 39K-REVERIFY-FIX: Single Source of Truth Coverage Verification")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # 1. Freeze check
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        print("❌ Network is not frozen - locks/api_budget.lock not found")
        sys.exit(1)
    print("✅ Network freeze confirmed")
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Load weekly manifests
    print("\n📋 Loading weekly manifests...")
    
    # Primary weekly manifests
    weekly_manifests = [
        ('W7', REPORTS_DIR / 'W7_manifest.csv'),
        ('W6', REPORTS_DIR / 'W6_manifest.csv'),
        ('W5', REPORTS_DIR / 'W5_manifest.csv'),
    ]
    
    # Fallback manifests (39K_*_manifest.csv)
    fallback_manifests = [
        ('W7', REPORTS_DIR / '39K_D1_manifest.csv'),
        ('W6', REPORTS_DIR / '39K_W6_D1_manifest.csv'),
        ('W6', REPORTS_DIR / '39K_W6_D2_manifest.csv'),
        ('W5', REPORTS_DIR / 'W5_FILL_manifest.csv'),
    ]
    
    all_manifests = []
    
    # Load primary manifests
    for week_label, manifest_path in weekly_manifests:
        df = load_weekly_manifest(week_label, manifest_path)
        if not df.empty:
            all_manifests.append(df)
            print(f"✅ Loaded {week_label}: {len(df)} files from {manifest_path.name}")
        else:
            # Try fallback manifests
            fallback_found = False
            for fallback_week, fallback_path in fallback_manifests:
                if fallback_week == week_label and fallback_path.exists():
                    df = load_weekly_manifest(week_label, fallback_path)
                    if not df.empty:
                        all_manifests.append(df)
                        print(f"✅ Loaded {week_label} (fallback): {len(df)} files from {fallback_path.name}")
                        fallback_found = True
                        break
            
            if not fallback_found:
                print(f"❌ No manifest found for {week_label}")
    
    if not all_manifests:
        print("❌ No weekly manifests found")
        sys.exit(1)
    
    # Union all manifests
    global_df = pd.concat(all_manifests, ignore_index=True)
    print(f"📊 Total files in global manifest: {len(global_df)}")
    
    # Standardize column names
    if 'file_path' in global_df.columns:
        global_df['abs_path'] = global_df['file_path']
    if 'size_bytes' in global_df.columns:
        global_df['bytes'] = global_df['size_bytes']
    
    # Ensure required columns exist
    required_columns = ['week_label', 'date', 'venue', 'pair', 'abs_path', 'bytes', 'sha256']
    for col in required_columns:
        if col not in global_df.columns:
            print(f"⚠️ Missing column: {col}")
            global_df[col] = None
    
    # Clean up data types and remove rows with missing critical data
    global_df = global_df.dropna(subset=['abs_path', 'sha256'])
    global_df['abs_path'] = global_df['abs_path'].astype(str)
    global_df['sha256'] = global_df['sha256'].astype(str)
    
    # 3. Disk assertion and integrity checks
    print(f"\n🔍 Performing disk assertion and integrity checks...")
    
    integrity_issues = []
    valid_files = []
    
    for idx, row in global_df.iterrows():
        if pd.isna(row['abs_path']):
            continue
        file_path = Path(row['abs_path'])
        
        # Check if file exists
        if not file_path.exists():
            integrity_issues.append({
                'week_label': row['week_label'],
                'date': row['date'],
                'venue': row['venue'],
                'pair': row['pair'],
                'abs_path': str(file_path),
                'issue': 'File not found on disk',
                'expected_sha256': row['sha256'],
                'actual_sha256': 'N/A'
            })
            continue
        
        # Check file size
        actual_size = file_path.stat().st_size
        expected_size = row['bytes']
        if actual_size != expected_size:
            integrity_issues.append({
                'week_label': row['week_label'],
                'date': row['date'],
                'venue': row['venue'],
                'pair': row['pair'],
                'abs_path': str(file_path),
                'issue': f'Size mismatch: expected {expected_size}, got {actual_size}',
                'expected_sha256': row['sha256'],
                'actual_sha256': 'N/A'
            })
            continue
        
        # Check gzip validity
        if not verify_gzip_file(file_path):
            integrity_issues.append({
                'week_label': row['week_label'],
                'date': row['date'],
                'venue': row['venue'],
                'pair': row['pair'],
                'abs_path': str(file_path),
                'issue': 'Invalid gzip file',
                'expected_sha256': row['sha256'],
                'actual_sha256': 'N/A'
            })
            continue
        
        # Check SHA-256 hash
        actual_hash = compute_file_hash(file_path)
        expected_hash = row['sha256']
        if actual_hash != expected_hash:
            integrity_issues.append({
                'week_label': row['week_label'],
                'date': row['date'],
                'venue': row['venue'],
                'pair': row['pair'],
                'abs_path': str(file_path),
                'issue': 'SHA-256 hash mismatch',
                'expected_sha256': expected_hash,
                'actual_sha256': actual_hash
            })
            continue
        
        # File is valid
        valid_files.append(row)
    
    print(f"✅ Integrity check complete: {len(valid_files)} valid files, {len(integrity_issues)} issues")
    
    # 4. Build coverage matrix and week summary
    print(f"\n📊 Building coverage matrix and week summary...")
    
    # Coverage matrix
    all_dates = sorted(set([f['date'] for f in valid_files]))
    all_venues = sorted(set([f['venue'] for f in valid_files]))
    
    coverage_matrix = {}
    for date in all_dates:
        coverage_matrix[date] = {}
        for venue in all_venues:
            venue_files = [f for f in valid_files if f['date'] == date and f['venue'] == venue]
            coverage_matrix[date][venue] = '✅' if venue_files else '❌'
    
    # Week summary
    week_summary = {}
    for week_label in ['W5', 'W6', 'W7']:
        week_files = [f for f in valid_files if f['week_label'] == week_label]
        
        if week_label == 'W7':
            # W7 is COINBASE BTC-USD only
            expected = 7  # 7 days
            coinbase_files = [f for f in week_files if f['venue'] == 'COINBASE' and 'BTC-USD' in f['pair']]
            found = len(coinbase_files)
            week_summary[week_label] = {
                'expected': expected,
                'found': found,
                'percentage': (found / expected * 100) if expected > 0 else 0,
                'pass': found >= expected and len(integrity_issues) == 0,
                'type': 'COINBASE BTC-USD only'
            }
        else:
            # W5 and W6 are all venues
            expected = 28  # 7 days * 4 venues
            found = len(week_files)
            week_summary[week_label] = {
                'expected': expected,
                'found': found,
                'percentage': (found / expected * 100) if expected > 0 else 0,
                'pass': found >= expected and len(integrity_issues) == 0,
                'type': 'All venues'
            }
    
    # 5. Handle mixed v7 layout - find uncategorized v7 files
    print(f"\n🔍 Scanning for uncategorized v7 files...")
    
    uncategorized_v7 = []
    v7_dirs = [
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
    ]
    
    for v7_dir in v7_dirs:
        if v7_dir.exists():
            for file_path in v7_dir.rglob("*.csv.gz"):
                # Check if this file is already in our global manifest
                file_str = str(file_path)
                if not any(f['abs_path'] == file_str for f in valid_files):
                    # Check if it has date information
                    has_date = False
                    path_str = str(file_path)
                    
                    # Check for YYYYMMDD pattern in the path
                    date_match = re.search(r'/(\d{8})/', path_str)
                    if date_match:
                        date_part = date_match.group(1)
                        if date_part.isdigit() and len(date_part) == 8:
                            has_date = True
                    
                    if not has_date:
                        uncategorized_v7.append({
                            'file_path': str(file_path),
                            'filename': file_path.name,
                            'directory': str(file_path.parent),
                            'size_bytes': file_path.stat().st_size,
                            'reason': 'No unambiguous YYYYMMDD in path or filename'
                        })
    
    print(f"📊 Found {len(uncategorized_v7)} uncategorized v7 files")
    
    # 6. Write outputs
    print(f"\n📝 Writing outputs...")
    
    # GLOBAL_manifest.csv
    if valid_files:
        manifest_df = pd.DataFrame(valid_files)
        manifest_df.to_csv(REPORTS_DIR / 'GLOBAL_manifest.csv', index=False)
        print(f"✅ GLOBAL_manifest.csv: {len(valid_files)} files")
    
    # GLOBAL_coverage_matrix.txt
    with open(REPORTS_DIR / 'GLOBAL_coverage_matrix.txt', 'w') as f:
        f.write("Global Coverage Matrix\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files: {len(valid_files)}\n")
        f.write(f"Integrity issues: {len(integrity_issues)}\n")
        f.write(f"Uncategorized v7 files: {len(uncategorized_v7)}\n\n")
        
        f.write("Coverage Matrix (Date × Venue):\n")
        f.write(f"{'Date':<10} {'COINBASE':<10} {'BINANCE':<10} {'BYBITSPOT':<10} {'BITGET':<10}\n")
        f.write("-" * 50 + "\n")
        for date in all_dates:
            f.write(f"{date:<10} {coverage_matrix[date]['COINBASE']:<10} {coverage_matrix[date]['BINANCE']:<10} {coverage_matrix[date]['BYBITSPOT']:<10} {coverage_matrix[date]['BITGET']:<10}\n")
    
    print(f"✅ GLOBAL_coverage_matrix.txt")
    
    # GLOBAL_week_summary.json
    with open(REPORTS_DIR / 'GLOBAL_week_summary.json', 'w') as f:
        json.dump(week_summary, f, indent=2)
    print(f"✅ GLOBAL_week_summary.json")
    
    # GLOBAL_integrity_issues.csv
    if integrity_issues:
        integrity_df = pd.DataFrame(integrity_issues)
        integrity_df.to_csv(REPORTS_DIR / 'GLOBAL_integrity_issues.csv', index=False)
        print(f"✅ GLOBAL_integrity_issues.csv: {len(integrity_issues)} issues")
    else:
        # Create empty file
        pd.DataFrame().to_csv(REPORTS_DIR / 'GLOBAL_integrity_issues.csv', index=False)
        print(f"✅ GLOBAL_integrity_issues.csv: 0 issues (PASS)")
    
    # GLOBAL_uncategorized_v7.csv
    if uncategorized_v7:
        uncategorized_df = pd.DataFrame(uncategorized_v7)
        uncategorized_df.to_csv(REPORTS_DIR / 'GLOBAL_uncategorized_v7.csv', index=False)
        print(f"✅ GLOBAL_uncategorized_v7.csv: {len(uncategorized_v7)} files")
    else:
        # Create empty file
        pd.DataFrame().to_csv(REPORTS_DIR / 'GLOBAL_uncategorized_v7.csv', index=False)
        print(f"✅ GLOBAL_uncategorized_v7.csv: 0 files")
    
    # GLOBAL_bom_sha256.txt
    if valid_files:
        all_hashes = sorted([f['sha256'] for f in valid_files])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'GLOBAL_bom_sha256.txt', 'w') as f:
            f.write(f"Global BTCUSD-class BOM SHA-256\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Total files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        print(f"✅ GLOBAL_bom_sha256.txt: {bom_hash}")
    
    # GLOBAL_gate.json
    gate_data = {
        'W5_gate': week_summary.get('W5', {}).get('pass', False),
        'W6_gate': week_summary.get('W6', {}).get('pass', False),
        'W7_coinbase_gate': week_summary.get('W7', {}).get('pass', False),
        'week_summary': week_summary,
        'integrity_issues_count': len(integrity_issues),
        'uncategorized_v7_count': len(uncategorized_v7),
        'total_valid_files': len(valid_files),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'GLOBAL_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    print(f"✅ GLOBAL_gate.json")
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-REVERIFY-FIX Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # 10-line summary
    print(f"\n📋 10-Line Summary:")
    print(f"1. W5_gate: {'PASS' if week_summary.get('W5', {}).get('pass', False) else 'FAIL'}")
    print(f"2. W6_gate: {'PASS' if week_summary.get('W6', {}).get('pass', False) else 'FAIL'}")
    print(f"3. W7_coinbase_gate: {'PASS' if week_summary.get('W7', {}).get('pass', False) else 'FAIL'}")
    print(f"4. W5 count: {week_summary.get('W5', {}).get('found', 0)}/{week_summary.get('W5', {}).get('expected', 0)} files")
    print(f"5. W6 count: {week_summary.get('W6', {}).get('found', 0)}/{week_summary.get('W6', {}).get('expected', 0)} files")
    print(f"6. W7 count: {week_summary.get('W7', {}).get('found', 0)}/{week_summary.get('W7', {}).get('expected', 0)} COINBASE files")
    print(f"7. Integrity mismatches: {len(integrity_issues)} (should be 0)")
    print(f"8. Uncategorized v7 files: {len(uncategorized_v7)}")
    print(f"9. Total valid files: {len(valid_files)}")
    print(f"10. Network I/O: NONE (frozen)")

if __name__ == "__main__":
    main()
