#!/usr/bin/env python3
"""
Phase 39K-REALIGN-CALENDAR: Authoritative Week Alignment and Full Inventory
Replace relative week numbering with absolute calendar map anchored to real ISO weeks
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

# Fixed week boundaries (Monday-Sunday)
WEEK_BOUNDARIES = {
    'W-7': {'start': '2025-07-07', 'end': '2025-07-13', 'label': 'Jul 7–13, 2025'},
    'W-6': {'start': '2025-07-14', 'end': '2025-07-20', 'label': 'Jul 14–20, 2025'},
    'W-5': {'start': '2025-07-21', 'end': '2025-07-27', 'label': 'Jul 21–27, 2025'},
    'W-4': {'start': '2025-07-28', 'end': '2025-08-03', 'label': 'Jul 28–Aug 3, 2025'},
    'W-3': {'start': '2025-08-04', 'end': '2025-08-10', 'label': 'Aug 4–10, 2025'},
    'W-2': {'start': '2025-08-11', 'end': '2025-08-17', 'label': 'Aug 11–17, 2025'},
    'W-1': {'start': '2025-08-18', 'end': '2025-08-24', 'label': 'Aug 18–24, 2025'},
    'W0': {'start': '2025-08-25', 'end': '2025-08-31', 'label': 'Aug 25–31, 2025'},
    'W+1': {'start': '2025-09-01', 'end': '2025-09-07', 'label': 'Sep 1–7, 2025'},
    'W+2': {'start': '2025-09-08', 'end': '2025-09-14', 'label': 'Sep 8–14, 2025'},
    'W+3': {'start': '2025-09-15', 'end': '2025-09-21', 'label': 'Sep 15–21, 2025'},
    'W+4': {'start': '2025-09-22', 'end': '2025-09-28', 'label': 'Sep 22–28, 2025'},
    'W+5': {'start': '2025-09-29', 'end': '2025-10-05', 'label': 'Sep 29–Oct 5, 2025'},
    'W+6': {'start': '2025-10-06', 'end': '2025-10-12', 'label': 'Oct 6–12, 2025'}
}

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
        'pair': pair
    }

def extract_coinapi_metadata(file_path):
    """Extract metadata from CoinAPI format: IDDI... in E-VENUE directory"""
    path_str = str(file_path)
    
    # Look for E-VENUE pattern in path
    venue_match = re.search(r'/E-([A-Z]+)/', path_str)
    if not venue_match:
        return None
    
    venue = venue_match.group(1)
    
    # Look for YYYYMMDD pattern in path
    date_match = re.search(r'/(\d{8})/', path_str)
    if not date_match:
        return None
    
    date = date_match.group(1)
    
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
        'pair': pair
    }

def get_week_for_date(date_str):
    """Get the week label for a given date string (YYYYMMDD)"""
    try:
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        date_str_formatted = date_obj.strftime('%Y-%m-%d')
        
        for week_label, week_info in WEEK_BOUNDARIES.items():
            start_date = datetime.strptime(week_info['start'], '%Y-%m-%d')
            end_date = datetime.strptime(week_info['end'], '%Y-%m-%d')
            
            if start_date <= date_obj <= end_date:
                return week_label
        
        return None
    except Exception:
        return None

def scan_all_directories():
    """Scan all directories for BTCUSD-class files"""
    print("🔍 Scanning all directories for BTCUSD-class files...")
    
    directories = [
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_oct',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
        BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw',
    ]
    
    all_files = []
    
    for directory in directories:
        if not directory.exists():
            print(f"  📁 Directory not found: {directory}")
            continue
        
        print(f"  📁 Scanning: {directory}")
        files = list(directory.rglob("*.csv.gz"))
        print(f"    Found {len(files)} files")
        
        for file_path in files:
            # Determine source format
            if 'data_v6' in str(file_path):
                source_format = 'v6'
            elif 'data_v7' in str(file_path):
                source_format = 'v7'
            elif 'analysis' in str(file_path):
                source_format = 'v4'
            else:
                source_format = 'unknown'
            
            # Try to extract metadata
            metadata = None
            
            if 'E-' in str(file_path.parent):
                # CoinAPI format
                metadata = extract_coinapi_metadata(file_path)
            else:
                # Legacy format
                metadata = extract_legacy_metadata(file_path)
            
            if metadata:
                # Get week for this date
                week_label = get_week_for_date(metadata['date'])
                
                if week_label:
                    all_files.append({
                        'file_path': file_path,
                        'venue': metadata['venue'],
                        'date': metadata['date'],
                        'pair': metadata['pair'],
                        'source_format': source_format,
                        'week_label': week_label
                    })
    
    print(f"📊 Found {len(all_files)} BTCUSD-class files")
    return all_files

def verify_files(all_files):
    """Verify file integrity and compute hashes"""
    print("🔍 Verifying file integrity and computing hashes...")
    
    verified_files = []
    
    for file_info in all_files:
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
        verified_files.append(file_info)
    
    return verified_files

def generate_week_inventory(verified_files):
    """Generate unified week inventory table"""
    print("📝 Generating unified week inventory...")
    
    # Group files by week
    week_files = defaultdict(list)
    for file_info in verified_files:
        week_files[file_info['week_label']].append(file_info)
    
    # Create inventory table
    inventory_data = []
    
    for week_label in sorted(WEEK_BOUNDARIES.keys()):
        week_info = WEEK_BOUNDARIES[week_label]
        files = week_files.get(week_label, [])
        
        # Count files by source format
        v4_count = len([f for f in files if f['source_format'] == 'v4'])
        v6_count = len([f for f in files if f['source_format'] == 'v6'])
        v7_count = len([f for f in files if f['source_format'] == 'v7'])
        
        # Calculate total size
        total_bytes = sum(f['size_bytes'] for f in files)
        total_mb = total_bytes / (1024 * 1024)
        
        # Coverage percentage
        expected = 28  # 7 days × 4 venues
        coverage_pct = (len(files) / expected * 100) if expected > 0 else 0
        
        # Source directories
        sources = []
        if v4_count > 0:
            sources.append(f"v4({v4_count})")
        if v6_count > 0:
            sources.append(f"v6({v6_count})")
        if v7_count > 0:
            sources.append(f"v7({v7_count})")
        source_dirs = ", ".join(sources) if sources else "none"
        
        inventory_data.append({
            'Week_Label': week_label,
            'Date_Range': week_info['label'],
            'Files_Found': len(files),
            'Expected_Files': expected,
            'Coverage_%': round(coverage_pct, 1),
            'Source_Directories': source_dirs,
            'Data_Size_MB': round(total_mb, 1)
        })
    
    return inventory_data

def generate_availability_matrix(inventory_data):
    """Generate week availability matrix"""
    print("📝 Generating week availability matrix...")
    
    # Categorize weeks by coverage
    categories = {
        '100%': [],
        '90-99%': [],
        '50-89%': [],
        '<50%': []
    }
    
    for item in inventory_data:
        coverage = item['Coverage_%']
        if coverage >= 100:
            categories['100%'].append(item['Week_Label'])
        elif coverage >= 90:
            categories['90-99%'].append(item['Week_Label'])
        elif coverage >= 50:
            categories['50-89%'].append(item['Week_Label'])
        else:
            categories['<50%'].append(item['Week_Label'])
    
    return categories

def export_results(inventory_data, availability_matrix, verified_files):
    """Export all results"""
    print("📝 Exporting results...")
    
    # GLOBAL_week_inventory.csv
    inventory_df = pd.DataFrame(inventory_data)
    inventory_df.to_csv(REPORTS_DIR / 'GLOBAL_week_inventory.csv', index=False)
    print(f"✅ GLOBAL_week_inventory.csv: {len(inventory_data)} weeks")
    
    # GLOBAL_week_matrix.txt
    with open(REPORTS_DIR / 'GLOBAL_week_matrix.txt', 'w') as f:
        f.write("Week Availability Matrix\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
        
        for category, weeks in availability_matrix.items():
            f.write(f"{category} Coverage ({len(weeks)} weeks):\n")
            if weeks:
                f.write(f"  {', '.join(weeks)}\n")
            else:
                f.write("  (none)\n")
            f.write("\n")
        
        f.write("Summary:\n")
        total_weeks = len(inventory_data)
        f.write(f"  Total weeks: {total_weeks}\n")
        f.write(f"  100% coverage: {len(availability_matrix['100%'])} weeks\n")
        f.write(f"  90-99% coverage: {len(availability_matrix['90-99%'])} weeks\n")
        f.write(f"  50-89% coverage: {len(availability_matrix['50-89%'])} weeks\n")
        f.write(f"  <50% coverage: {len(availability_matrix['<50%'])} weeks\n")
    
    print(f"✅ GLOBAL_week_matrix.txt: Availability matrix")
    
    # GLOBAL_week_alignment.json
    alignment_data = {
        'week_boundaries': WEEK_BOUNDARIES,
        'inventory': inventory_data,
        'availability_matrix': availability_matrix,
        'summary': {
            'total_weeks': len(inventory_data),
            'total_files': len(verified_files),
            'total_size_mb': round(sum(item['Data_Size_MB'] for item in inventory_data), 1),
            'coverage_100pct': len(availability_matrix['100%']),
            'coverage_90_99pct': len(availability_matrix['90-99%']),
            'coverage_50_89pct': len(availability_matrix['50-89%']),
            'coverage_lt50pct': len(availability_matrix['<50%'])
        },
        'generated': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'GLOBAL_week_alignment.json', 'w') as f:
        json.dump(alignment_data, f, indent=2)
    print(f"✅ GLOBAL_week_alignment.json: Complete alignment data")

def main():
    """Main execution"""
    print("🚀 Phase 39K-REALIGN-CALENDAR: Authoritative Week Alignment and Full Inventory")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if not lock_file.exists():
        print("❌ Network is not frozen - locks/api_budget.lock not found")
        sys.exit(1)
    print("✅ Network freeze confirmed")
    
    # Scan all directories
    all_files = scan_all_directories()
    
    # Verify files
    verified_files = verify_files(all_files)
    
    # Generate week inventory
    inventory_data = generate_week_inventory(verified_files)
    
    # Generate availability matrix
    availability_matrix = generate_availability_matrix(inventory_data)
    
    # Export results
    export_results(inventory_data, availability_matrix, verified_files)
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-REALIGN-CALENDAR Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # Summary statistics
    total_files = len(verified_files)
    total_size_mb = sum(item['Data_Size_MB'] for item in inventory_data)
    total_weeks = len(inventory_data)
    
    print(f"\n📋 Final Inventory Summary:")
    print(f"Total weeks: {total_weeks}")
    print(f"Total files: {total_files}")
    print(f"Total size: {total_size_mb:.1f} MB")
    print(f"100% coverage: {len(availability_matrix['100%'])} weeks")
    print(f"90-99% coverage: {len(availability_matrix['90-99%'])} weeks")
    print(f"50-89% coverage: {len(availability_matrix['50-89%'])} weeks")
    print(f"<50% coverage: {len(availability_matrix['<50%'])} weeks")
    
    print(f"\nKey artifacts:")
    print(f"  {REPORTS_DIR / 'GLOBAL_week_inventory.csv'}")
    print(f"  {REPORTS_DIR / 'GLOBAL_week_matrix.txt'}")
    print(f"  {REPORTS_DIR / 'GLOBAL_week_alignment.json'}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
