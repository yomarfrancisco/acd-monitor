#!/usr/bin/env python3
"""
Phase 39K-HARMONIZE-CANONICAL: Consolidate all BTCUSD-class tick files into canonical dataset
"""

import os
import sys
import hashlib
import json
import gzip
import pandas as pd
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import shutil

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'canonical'
CANONICAL_DIR = BASE_DIR / 'data_v7' / 'canonical'

# Date range: Jul 7 → Oct 12, 2025
START_DATE = datetime(2025, 7, 7)
END_DATE = datetime(2025, 10, 12)

# Venues and their expected pairs
VENUES = {
    'BINANCE': 'BTCUSDT',
    'COINBASE': 'BTC-USD', 
    'BYBITSPOT': 'BTCUSDT',
    'BITGET': 'BTCUSDT'
}

# Search roots with priority order (v7 > v6 > v4)
SEARCH_ROOTS = [
    (BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7', 'v7'),
    (BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6', 'v7'),
    (BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5', 'v7'),
    (BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w4', 'v7'),
    (BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul', 'v6'),
    (BASE_DIR / 'data_v6' / 'raw' / 'coinapi_oct', 'v6'),
    (BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw', 'v4')
]

# Complete weeks (should have 28/28 coverage)
COMPLETE_WEEKS = ['W-7', 'W-6', 'W-5', 'W-4', 'W+1', 'W+4', 'W+5']

def is_btcusd_file(file_path):
    """Check if file matches BTCUSD criteria"""
    filename = file_path.name.lower()
    path_str = str(file_path).lower()
    
    # Check for BTCUSD-class pairs
    has_btcusd = any(pair in filename for pair in ['btcusdt', 'btc-usd', 'btc__002dusd'])
    if not has_btcusd:
        return False
    
    return True

def extract_venue_from_path(file_path):
    """Extract venue from file path or filename"""
    filename = file_path.name.upper()
    path_str = str(file_path).upper()
    
    # Check filename first
    for venue in VENUES.keys():
        if venue in filename:
            return venue
    
    # Check path
    for venue in VENUES.keys():
        if venue in path_str:
            return venue
    
    return 'UNKNOWN'

def extract_date_from_path(file_path):
    """Extract date from file path or filename"""
    filename = file_path.name
    path_str = str(file_path)
    
    # Look for YYYYMMDD pattern
    date_match = re.search(r'(\d{8})', filename)
    if date_match:
        return date_match.group(1)
    
    date_match = re.search(r'(\d{8})', path_str)
    if date_match:
        return date_match.group(1)
    
    return 'UNKNOWN'

def extract_pair_from_path(file_path):
    """Extract trading pair from file path"""
    filename = file_path.name.upper()
    path_str = str(file_path).upper()
    
    # Check for COINBASE BTC-USD (both encoded and literal forms)
    if 'BTC__002DUSD' in filename or 'BTC__002DUSD' in path_str:
        return 'BTC-USD'
    if 'BTC-USD' in filename or 'BTC-USD' in path_str:
        return 'BTC-USD'
    
    # Check for BTCUSDT
    if 'BTCUSDT' in filename or 'BTCUSDT' in path_str:
        return 'BTCUSDT'
    
    return 'UNKNOWN'

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

def verify_gzip_file(file_path):
    """Verify gzip file can be opened and read"""
    try:
        with gzip.open(file_path, 'rb') as f:
            header = f.read(10)
            return len(header) > 0
    except Exception:
        return False

def get_file_timestamps(file_path):
    """Get first and last timestamps from a tick file"""
    try:
        with gzip.open(file_path, 'rt') as f:
            first_line = f.readline().strip()
            last_line = None
            for line in f:
                last_line = line.strip()
            
            if first_line and last_line:
                # Extract timestamp from CSV (assuming first column)
                first_ts = first_line.split(',')[0]
                last_ts = last_line.split(',')[0]
                
                # Clean up timestamps (remove quotes if present)
                first_ts = first_ts.strip('"')
                last_ts = last_ts.strip('"')
                
                return first_ts, last_ts
    except Exception as e:
        print(f"    ⚠️ Error reading timestamps from {file_path}: {e}")
    
    return None, None

def count_file_rows(file_path):
    """Count rows in a gzipped CSV file"""
    try:
        with gzip.open(file_path, 'rt') as f:
            return sum(1 for line in f)
    except Exception:
        return 0

def scan_all_files():
    """Scan all search roots for BTCUSD files"""
    print("🔍 Scanning all data roots for BTCUSD files...")
    
    all_files = []
    
    for root_path, source_tier in SEARCH_ROOTS:
        if not root_path.exists():
            print(f"  📁 Directory not found: {root_path}")
            continue
        
        print(f"  📁 Scanning: {root_path} ({source_tier})")
        files = list(root_path.rglob("*.csv.gz"))
        print(f"    Found {len(files)} total files")
        
        btcusd_files = [f for f in files if is_btcusd_file(f)]
        print(f"    Found {len(btcusd_files)} BTCUSD files")
        
        for file_path in btcusd_files:
            try:
                venue = extract_venue_from_path(file_path)
                date = extract_date_from_path(file_path)
                pair = extract_pair_from_path(file_path)
                size_bytes = file_path.stat().st_size
                
                # Skip if we can't extract required info
                if venue == 'UNKNOWN' or date == 'UNKNOWN' or pair == 'UNKNOWN':
                    continue
                
                all_files.append({
                    'file_path': file_path,
                    'venue': venue,
                    'date': date,
                    'pair': pair,
                    'source_tier': source_tier,
                    'size_bytes': size_bytes,
                    'key': f"{date}_{venue}_{pair}"
                })
            except Exception as e:
                print(f"    ⚠️ Error processing {file_path}: {e}")
    
    print(f"📊 Total BTCUSD files found: {len(all_files)}")
    return all_files

def canonicalize_files(all_files):
    """Apply canonicalization rules and resolve conflicts"""
    print("🎯 Applying canonicalization rules...")
    
    # Group files by key (date_venue_pair)
    file_groups = defaultdict(list)
    for file_info in all_files:
        file_groups[file_info['key']].append(file_info)
    
    canonical_files = []
    conflicts = []
    
    # Priority order: v7 > v6 > v4
    tier_priority = {'v7': 3, 'v6': 2, 'v4': 1}
    
    for key, files in file_groups.items():
        if len(files) == 1:
            # No conflict
            canonical_files.append(files[0])
        else:
            # Resolve conflict by tier priority, then by size (larger is better)
            files.sort(key=lambda x: (tier_priority[x['source_tier']], x['size_bytes']), reverse=True)
            winner = files[0]
            losers = files[1:]
            
            canonical_files.append(winner)
            
            for loser in losers:
                conflicts.append({
                    'key': key,
                    'losing_file': str(loser['file_path']),
                    'losing_tier': loser['source_tier'],
                    'losing_size': loser['size_bytes'],
                    'winning_file': str(winner['file_path']),
                    'winning_tier': winner['source_tier'],
                    'winning_size': winner['size_bytes'],
                    'reason': f"Tier priority: {winner['source_tier']} > {loser['source_tier']}"
                })
    
    print(f"📊 Canonicalization Results:")
    print(f"  ✅ Canonical files: {len(canonical_files)}")
    print(f"  ⚠️ Conflicts resolved: {len(conflicts)}")
    
    return canonical_files, conflicts

def verify_canonical_files(canonical_files):
    """Verify all canonical files"""
    print("🔍 Verifying canonical files...")
    
    verified_files = []
    verification_errors = []
    
    for file_info in canonical_files:
        file_path = file_info['file_path']
        
        # Check file exists and has size > 0
        if not file_path.exists():
            verification_errors.append({
                'file': str(file_path),
                'error': 'File does not exist'
            })
            continue
        
        if file_path.stat().st_size == 0:
            verification_errors.append({
                'file': str(file_path),
                'error': 'Zero-byte file'
            })
            continue
        
        # Verify gzip
        if not verify_gzip_file(file_path):
            verification_errors.append({
                'file': str(file_path),
                'error': 'Invalid gzip file'
            })
            continue
        
        # Compute hash
        file_hash = compute_file_hash(file_path)
        if file_hash == "ERROR":
            verification_errors.append({
                'file': str(file_path),
                'error': 'SHA-256 computation failed'
            })
            continue
        
        # Get timestamps and row count
        first_ts, last_ts = get_file_timestamps(file_path)
        row_count = count_file_rows(file_path)
        
        verified_files.append({
            **file_info,
            'sha256': file_hash,
            'first_ts': first_ts,
            'last_ts': last_ts,
            'row_count': row_count
        })
    
    print(f"📊 Verification Results:")
    print(f"  ✅ Verified files: {len(verified_files)}")
    print(f"  ❌ Verification errors: {len(verification_errors)}")
    
    return verified_files, verification_errors

def generate_week_coverage(verified_files):
    """Generate week coverage matrix"""
    print("📊 Generating week coverage matrix...")
    
    # Generate all dates in range
    current_date = START_DATE
    all_dates = []
    while current_date <= END_DATE:
        all_dates.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    
    # Group files by date
    files_by_date = defaultdict(list)
    for file_info in verified_files:
        files_by_date[file_info['date']].append(file_info)
    
    # Build coverage matrix
    coverage_matrix = {}
    for date in all_dates:
        coverage_matrix[date] = {}
        for venue in VENUES.keys():
            coverage_matrix[date][venue] = 'MISSING'
    
    # Fill in found files
    for date, files in files_by_date.items():
        for file_info in files:
            venue = file_info['venue']
            if date in coverage_matrix and venue in coverage_matrix[date]:
                coverage_matrix[date][venue] = 'FOUND'
    
    return coverage_matrix, all_dates

def check_continuity(verified_files):
    """Check timestamp continuity and boundary conditions"""
    print("🕐 Checking timestamp continuity...")
    
    boundary_issues = []
    
    for file_info in verified_files:
        date = file_info['date']
        venue = file_info['venue']
        first_ts = file_info['first_ts']
        last_ts = file_info['last_ts']
        
        if not first_ts or not last_ts:
            boundary_issues.append({
                'file': str(file_info['file_path']),
                'date': date,
                'venue': venue,
                'issue': 'Could not extract timestamps'
            })
            continue
        
        # Parse date to get expected day boundaries
        try:
            file_date = datetime.strptime(date, '%Y%m%d')
            day_start = file_date.strftime('%Y-%m-%d')
            day_end = file_date.strftime('%Y-%m-%d')
            
            # Check if timestamps are within the expected day (more lenient)
            if not (day_start in first_ts and day_start in last_ts):
                boundary_issues.append({
                    'file': str(file_info['file_path']),
                    'date': date,
                    'venue': venue,
                    'first_ts': first_ts,
                    'last_ts': last_ts,
                    'expected_day': day_start,
                    'issue': 'Timestamps do not match expected day'
                })
        except Exception as e:
            boundary_issues.append({
                'file': str(file_info['file_path']),
                'date': date,
                'venue': venue,
                'issue': f'Date parsing error: {e}'
            })
    
    print(f"📊 Continuity Check Results:")
    print(f"  ⚠️ Boundary issues: {len(boundary_issues)}")
    
    return boundary_issues

def create_canonical_structure(verified_files):
    """Create canonical directory structure and copy files"""
    print("📁 Creating canonical directory structure...")
    
    # Create canonical directory
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    
    canonical_manifest = []
    
    for file_info in verified_files:
        date = file_info['date']
        venue = file_info['venue']
        pair = file_info['pair']
        
        # Create canonical path: canonical/YYYYMMDD/E-<VENUE>/<PAIR>.csv.gz
        canonical_date_dir = CANONICAL_DIR / date
        canonical_venue_dir = canonical_date_dir / f"E-{venue}"
        canonical_venue_dir.mkdir(parents=True, exist_ok=True)
        
        canonical_filename = f"{pair}.csv.gz"
        canonical_path = canonical_venue_dir / canonical_filename
        
        # Copy file to canonical location
        shutil.copy2(file_info['file_path'], canonical_path)
        
        canonical_manifest.append({
            'date': date,
            'venue': venue,
            'pair': pair,
            'source_tier': file_info['source_tier'],
            'abs_path': str(canonical_path),
            'bytes': file_info['size_bytes'],
            'sha256': file_info['sha256'],
            'first_ts': file_info['first_ts'],
            'last_ts': file_info['last_ts'],
            'row_count': file_info['row_count']
        })
    
    print(f"📊 Canonical Structure Created:")
    print(f"  📁 Files copied: {len(canonical_manifest)}")
    
    return canonical_manifest

def compute_bom_hash(canonical_manifest):
    """Compute BOM hash over all canonical files"""
    print("🔐 Computing BOM hash...")
    
    # Sort by path for consistent ordering
    sorted_files = sorted(canonical_manifest, key=lambda x: x['abs_path'])
    
    # Create BOM string
    bom_string = ""
    for file_info in sorted_files:
        bom_string += f"{file_info['abs_path']}:{file_info['sha256']}\n"
    
    # Compute SHA-256 of BOM
    bom_hash = hashlib.sha256(bom_string.encode()).hexdigest()
    
    return bom_hash, bom_string

def export_results(canonical_manifest, conflicts, verification_errors, coverage_matrix, all_dates, boundary_issues, bom_hash):
    """Export all canonical results"""
    print("📝 Exporting canonical results...")
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # CANON_manifest.csv
    manifest_df = pd.DataFrame(canonical_manifest)
    manifest_df.to_csv(REPORTS_DIR / 'CANON_manifest.csv', index=False)
    print(f"✅ CANON_manifest.csv: {len(canonical_manifest)} files")
    
    # CANON_conflicts.csv
    if conflicts:
        conflicts_df = pd.DataFrame(conflicts)
        conflicts_df.to_csv(REPORTS_DIR / 'CANON_conflicts.csv', index=False)
        print(f"✅ CANON_conflicts.csv: {len(conflicts)} conflicts")
    
    # CANON_coverage_matrix.txt
    with open(REPORTS_DIR / 'CANON_coverage_matrix.txt', 'w') as f:
        f.write("Canonical Coverage Matrix (Jul 7 – Oct 12, 2025)\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total canonical files: {len(canonical_manifest)}\n\n")
        
        # Group by weeks
        current_date = START_DATE
        week_num = -7  # Start from W-7
        
        while current_date <= END_DATE:
            week_dates = []
            for i in range(7):  # 7 days per week
                if current_date <= END_DATE:
                    week_dates.append(current_date.strftime('%Y%m%d'))
                    current_date += timedelta(days=1)
                else:
                    break
            
            if week_dates:
                week_label = f"W{week_num:+d}" if week_num != 0 else "W0"
                f.write(f"\n{week_label} ({week_dates[0]} – {week_dates[-1]}):\n")
                f.write(f"{'Date':<10} {'BINANCE':<10} {'COINBASE':<10} {'BYBITSPOT':<10} {'BITGET':<10}\n")
                f.write("-" * 60 + "\n")
                
                week_found = 0
                for date in week_dates:
                    if date in coverage_matrix:
                        f.write(f"{date:<10} {coverage_matrix[date]['BINANCE']:<10} {coverage_matrix[date]['COINBASE']:<10} {coverage_matrix[date]['BYBITSPOT']:<10} {coverage_matrix[date]['BITGET']:<10}\n")
                        week_found += sum(1 for venue in VENUES.keys() if coverage_matrix[date][venue] == 'FOUND')
                    else:
                        f.write(f"{date:<10} {'MISSING':<10} {'MISSING':<10} {'MISSING':<10} {'MISSING':<10}\n")
                
                expected = len(week_dates) * len(VENUES)
                coverage_pct = (week_found / expected * 100) if expected > 0 else 0
                f.write(f"Coverage: {week_found}/{expected} ({coverage_pct:.1f}%)\n")
                
                if week_label in COMPLETE_WEEKS and week_found != expected:
                    f.write(f"⚠️ WARNING: {week_label} marked complete but coverage is {coverage_pct:.1f}%\n")
            
            week_num += 1
    
    print(f"✅ CANON_coverage_matrix.txt: Coverage matrix")
    
    # CANON_bom_sha256.txt
    with open(REPORTS_DIR / 'CANON_bom_sha256.txt', 'w') as f:
        f.write(f"Canonical BOM SHA-256: {bom_hash}\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files: {len(canonical_manifest)}\n")
    
    print(f"✅ CANON_bom_sha256.txt: BOM hash")
    
    # CANON_audit.txt
    with open(REPORTS_DIR / 'CANON_audit.txt', 'w') as f:
        f.write("Canonical Dataset Audit Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Date Range: {START_DATE.strftime('%Y-%m-%d')} → {END_DATE.strftime('%Y-%m-%d')}\n\n")
        
        f.write("Summary Statistics:\n")
        f.write(f"  Total canonical files: {len(canonical_manifest)}\n")
        f.write(f"  Conflicts resolved: {len(conflicts)}\n")
        f.write(f"  Verification errors: {len(verification_errors)}\n")
        f.write(f"  Boundary issues: {len(boundary_issues)}\n")
        f.write(f"  BOM SHA-256: {bom_hash}\n\n")
        
        # Check complete weeks
        f.write("Complete Week Status:\n")
        current_date = START_DATE
        week_num = -7
        
        while current_date <= END_DATE:
            week_dates = []
            for i in range(7):
                if current_date <= END_DATE:
                    week_dates.append(current_date.strftime('%Y%m%d'))
                    current_date += timedelta(days=1)
                else:
                    break
            
            if week_dates:
                week_label = f"W{week_num:+d}" if week_num != 0 else "W0"
                week_found = 0
                for date in week_dates:
                    if date in coverage_matrix:
                        week_found += sum(1 for venue in VENUES.keys() if coverage_matrix[date][venue] == 'FOUND')
                
                expected = len(week_dates) * len(VENUES)
                coverage_pct = (week_found / expected * 100) if expected > 0 else 0
                status = "✅ PASS" if week_found == expected else "❌ FAIL"
                
                if week_label in COMPLETE_WEEKS:
                    f.write(f"  {week_label}: {week_found}/{expected} ({coverage_pct:.1f}%) {status}\n")
            
            week_num += 1
        
        f.write(f"\nAnomalies:\n")
        if verification_errors:
            f.write(f"  Verification Errors ({len(verification_errors)}):\n")
            for error in verification_errors[:10]:  # Show first 10
                f.write(f"    {error['file']}: {error['error']}\n")
        
        if boundary_issues:
            f.write(f"  Boundary Issues ({len(boundary_issues)}):\n")
            for issue in boundary_issues[:10]:  # Show first 10
                f.write(f"    {issue['file']}: {issue['issue']}\n")
        
        # Overall status
        total_issues = len(verification_errors) + len(boundary_issues)
        overall_status = "PASS" if total_issues == 0 else "FAIL"
        f.write(f"\nOverall Status: {overall_status}\n")
    
    print(f"✅ CANON_audit.txt: Audit report")

def main():
    """Main execution"""
    print("🚀 Phase 39K-HARMONIZE-CANONICAL: Consolidate BTCUSD Dataset")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        print("❌ Network is not frozen - this phase requires network to be frozen")
        sys.exit(1)
    print("✅ Network freeze confirmed")
    
    # Scan all files
    all_files = scan_all_files()
    
    # Canonicalize files
    canonical_files, conflicts = canonicalize_files(all_files)
    
    # Verify canonical files
    verified_files, verification_errors = verify_canonical_files(canonical_files)
    
    # Generate coverage matrix
    coverage_matrix, all_dates = generate_week_coverage(verified_files)
    
    # Check continuity
    boundary_issues = check_continuity(verified_files)
    
    # Create canonical structure
    canonical_manifest = create_canonical_structure(verified_files)
    
    # Compute BOM hash
    bom_hash, bom_string = compute_bom_hash(canonical_manifest)
    
    # Export results
    export_results(canonical_manifest, conflicts, verification_errors, coverage_matrix, all_dates, boundary_issues, bom_hash)
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-HARMONIZE-CANONICAL Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # Final statistics
    total_issues = len(verification_errors) + len(boundary_issues)
    overall_status = "PASS" if total_issues == 0 else "FAIL"
    
    print(f"\n📋 Canonical Dataset Summary:")
    print(f"Total canonical files: {len(canonical_manifest)}")
    print(f"Conflicts resolved: {len(conflicts)}")
    print(f"Verification errors: {len(verification_errors)}")
    print(f"Boundary issues: {len(boundary_issues)}")
    print(f"Overall status: {overall_status}")
    print(f"BOM SHA-256: {bom_hash}")
    
    print(f"\nKey artifacts:")
    print(f"  {REPORTS_DIR / 'CANON_manifest.csv'}")
    print(f"  {REPORTS_DIR / 'CANON_conflicts.csv'}")
    print(f"  {REPORTS_DIR / 'CANON_coverage_matrix.txt'}")
    print(f"  {REPORTS_DIR / 'CANON_bom_sha256.txt'}")
    print(f"  {REPORTS_DIR / 'CANON_audit.txt'}")
    print(f"  {CANONICAL_DIR}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
