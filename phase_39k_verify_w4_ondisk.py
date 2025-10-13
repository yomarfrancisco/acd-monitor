#!/usr/bin/env python3
"""
Phase 39K-VERIFY-W4-ONDISK: Manifest-Independent Audit of Week -4
Confirm whether the 12 presumed-missing BTCUSD-class files for Jul 28 – Aug 3 2025 truly don't exist anywhere on disk
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'verify_14w'

# Week -4 date range: Jul 28 – Aug 3, 2025
WEEK_4_DATES = [
    '20250728', '20250729', '20250730', '20250731',
    '20250801', '20250802', '20250803'
]

# Valid venues
VENUES = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']

# Search roots
SEARCH_ROOTS = [
    BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw',
    BASE_DIR / 'data_v6' / 'raw',
    BASE_DIR / 'data_v7' / 'raw'
]

def is_week_4_btcusd_file(file_path):
    """Check if file matches Week -4 BTCUSD criteria"""
    filename = file_path.name.lower()
    path_str = str(file_path).lower()
    
    # Check for BTCUSD-class pairs
    has_btcusd = any(pair in filename for pair in ['btcusdt', 'btc-usd', 'btc__002dusd'])
    if not has_btcusd:
        return False
    
    # Check for Week -4 dates
    has_week_4_date = any(date in filename or date in path_str for date in WEEK_4_DATES)
    if not has_week_4_date:
        return False
    
    return True

def extract_venue_from_path(file_path):
    """Extract venue from file path or filename"""
    filename = file_path.name.upper()
    path_str = str(file_path).upper()
    
    # Check filename first
    for venue in VENUES:
        if venue in filename:
            return venue
    
    # Check path
    for venue in VENUES:
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

def search_week_4_files():
    """Perform recursive filesystem search for Week -4 BTCUSD files"""
    print("🔍 Performing recursive filesystem search for Week -4 BTCUSD files...")
    print(f"📅 Target dates: {', '.join(WEEK_4_DATES)}")
    print(f"📁 Search roots: {len(SEARCH_ROOTS)} directories")
    
    found_files = []
    
    for root in SEARCH_ROOTS:
        if not root.exists():
            print(f"  📁 Directory not found: {root}")
            continue
        
        print(f"  📁 Searching: {root}")
        files = list(root.rglob("*.csv.gz"))
        print(f"    Found {len(files)} total files")
        
        week_4_files = [f for f in files if is_week_4_btcusd_file(f)]
        print(f"    Found {len(week_4_files)} Week -4 BTCUSD files")
        
        for file_path in week_4_files:
            try:
                venue = extract_venue_from_path(file_path)
                date = extract_date_from_path(file_path)
                size_mb = file_path.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                found_files.append({
                    'full_path': str(file_path),
                    'venue': venue,
                    'date': date,
                    'size_mb': round(size_mb, 2),
                    'last_modified': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                    'source_root': str(root)
                })
            except Exception as e:
                print(f"    ⚠️ Error processing {file_path}: {e}")
    
    print(f"📊 Total Week -4 BTCUSD files found: {len(found_files)}")
    return found_files

def generate_coverage_matrix(found_files):
    """Generate 7x4 date x venue coverage matrix"""
    print("📝 Generating 7x4 coverage matrix...")
    
    # Initialize matrix
    matrix = {}
    for date in WEEK_4_DATES:
        matrix[date] = {}
        for venue in VENUES:
            matrix[date][venue] = 'MISSING'
    
    # Fill in found files
    for file_info in found_files:
        date = file_info['date']
        venue = file_info['venue']
        
        if date in matrix and venue in matrix[date]:
            matrix[date][venue] = 'FOUND'
    
    return matrix

def export_results(found_files, coverage_matrix):
    """Export audit results"""
    print("📝 Exporting audit results...")
    
    # W4_ondisk_audit.csv
    if found_files:
        audit_df = pd.DataFrame(found_files)
        audit_df = audit_df[['full_path', 'venue', 'date', 'size_mb', 'last_modified', 'source_root']]
        audit_df.to_csv(REPORTS_DIR / 'W4_ondisk_audit.csv', index=False)
        print(f"✅ W4_ondisk_audit.csv: {len(found_files)} files")
    else:
        pd.DataFrame().to_csv(REPORTS_DIR / 'W4_ondisk_audit.csv', index=False)
        print(f"✅ W4_ondisk_audit.csv: 0 files")
    
    # W4_coverage_matrix.txt
    with open(REPORTS_DIR / 'W4_coverage_matrix.txt', 'w') as f:
        f.write("Week -4 Coverage Matrix (Jul 28 – Aug 3, 2025)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files found: {len(found_files)}\n\n")
        
        f.write("Coverage Matrix (Date × Venue):\n")
        f.write(f"{'Date':<10} {'BINANCE':<10} {'COINBASE':<10} {'BYBITSPOT':<10} {'BITGET':<10}\n")
        f.write("-" * 60 + "\n")
        
        for date in WEEK_4_DATES:
            f.write(f"{date:<10} {coverage_matrix[date]['BINANCE']:<10} {coverage_matrix[date]['COINBASE']:<10} {coverage_matrix[date]['BYBITSPOT']:<10} {coverage_matrix[date]['BITGET']:<10}\n")
        
        f.write("\nSummary:\n")
        total_expected = len(WEEK_4_DATES) * len(VENUES)  # 7 * 4 = 28
        total_found = sum(1 for date in WEEK_4_DATES for venue in VENUES if coverage_matrix[date][venue] == 'FOUND')
        total_missing = total_expected - total_found
        
        f.write(f"  Expected combinations: {total_expected}\n")
        f.write(f"  Found: {total_found}\n")
        f.write(f"  Missing: {total_missing}\n")
        f.write(f"  Coverage: {(total_found/total_expected*100):.1f}%\n")
        
        if found_files:
            f.write(f"\nFiles found:\n")
            for file_info in found_files:
                f.write(f"  {file_info['date']} {file_info['venue']}: {file_info['size_mb']:.1f} MB - {file_info['full_path']}\n")
    
    print(f"✅ W4_coverage_matrix.txt: Coverage matrix")

def main():
    """Main execution"""
    print("🚀 Phase 39K-VERIFY-W4-ONDISK: Manifest-Independent Audit of Week -4")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        print("❌ Network is not frozen - locks/api_budget.lock not found")
        sys.exit(1)
    print("✅ Network freeze confirmed")
    
    # Search for Week -4 files
    found_files = search_week_4_files()
    
    # Generate coverage matrix
    coverage_matrix = generate_coverage_matrix(found_files)
    
    # Export results
    export_results(found_files, coverage_matrix)
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-VERIFY-W4-ONDISK Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # Analysis
    total_expected = len(WEEK_4_DATES) * len(VENUES)  # 7 * 4 = 28
    total_found = sum(1 for date in WEEK_4_DATES for venue in VENUES if coverage_matrix[date][venue] == 'FOUND')
    total_missing = total_expected - total_found
    
    print(f"\n📋 Week -4 Audit Summary:")
    print(f"Expected combinations: {total_expected}")
    print(f"Files found: {total_found}")
    print(f"Files missing: {total_missing}")
    print(f"Coverage: {(total_found/total_expected*100):.1f}%")
    
    if found_files:
        print(f"\n📁 Files found by venue:")
        venue_counts = {}
        for file_info in found_files:
            venue = file_info['venue']
            venue_counts[venue] = venue_counts.get(venue, 0) + 1
        
        for venue, count in sorted(venue_counts.items()):
            print(f"  {venue}: {count} files")
        
        print(f"\n📁 Files found by date:")
        date_counts = {}
        for file_info in found_files:
            date = file_info['date']
            date_counts[date] = date_counts.get(date, 0) + 1
        
        for date in sorted(date_counts.keys()):
            print(f"  {date}: {date_counts[date]} files")
    
    print(f"\nKey artifacts:")
    print(f"  {REPORTS_DIR / 'W4_ondisk_audit.csv'}")
    print(f"  {REPORTS_DIR / 'W4_coverage_matrix.txt'}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
