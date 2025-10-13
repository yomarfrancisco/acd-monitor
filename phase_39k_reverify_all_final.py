#!/usr/bin/env python3
"""
Phase 39K-REVERIFY-ALL-FINAL: Comprehensive Week Verification (v6 + v7 merge) - Final
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

# Week definitions
WEEKS = {
    'W-7': {'dates': ['20250707', '20250708', '20250709', '20250710', '20250711', '20250712', '20250713'], 'name': 'Week -7 (July 7-13)'},
    'W-6': {'dates': ['20250714', '20250715', '20250716', '20250717', '20250718', '20250719', '20250720'], 'name': 'Week -6 (July 14-20)'},
    'W-5': {'dates': ['20250721', '20250722', '20250723', '20250724', '20250725', '20250726', '20250727'], 'name': 'Week -5 (July 21-27)'},
    'W-4': {'dates': ['20250728', '20250729', '20250730', '20250731', '20250801', '20250802', '20250803'], 'name': 'Week -4 (July 28 - Aug 3)'},
    'W-3': {'dates': ['20250804', '20250805', '20250806', '20250807', '20250808', '20250809', '20250810'], 'name': 'Week -3 (Aug 4-10)'},
    'W-2': {'dates': ['20250811', '20250812', '20250813', '20250814', '20250815', '20250816', '20250817'], 'name': 'Week -2 (Aug 11-17)'},
    'W-1': {'dates': ['20250818', '20250819', '20250820', '20250821', '20250822', '20250823', '20250824'], 'name': 'Week -1 (Aug 18-24)'},
    'W0': {'dates': ['20250825', '20250826', '20250827', '20250828', '20250829', '20250830', '20250831'], 'name': 'Week 0 (Aug 25-31)'},
    'W1': {'dates': ['20250901', '20250902', '20250903', '20250904', '20250905', '20250906', '20250907'], 'name': 'Week 1 (Sep 1-7)'},
    'W2': {'dates': ['20250908', '20250909', '20250910', '20250911', '20250912', '20250913', '20250914'], 'name': 'Week 2 (Sep 8-14)'},
    'W3': {'dates': ['20250915', '20250916', '20250917', '20250918', '20250919', '20250920', '20250921'], 'name': 'Week 3 (Sep 15-21)'},
    'W4': {'dates': ['20250922', '20250923', '20250924', '20250925', '20250926', '20250927', '20250928'], 'name': 'Week 4 (Sep 22-28)'},
    'W5': {'dates': ['20250929', '20250930', '20251001', '20251002', '20251003', '20251004', '20251005'], 'name': 'Week 5 (Sep 29 - Oct 5)'},
    'W6': {'dates': ['20251006', '20251007', '20251008', '20251009', '20251010', '20251011', '20251012'], 'name': 'Week 6 (Oct 6-12)'}
}

VENUES = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
VENUE_SYMBOLS = {
    'COINBASE': 'BTC-USD',
    'BINANCE': 'BTCUSDT',
    'BYBITSPOT': 'BTCUSDT',
    'BITGET': 'BTCUSDT'
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

def process_file(file_path):
    """Process a single file and extract metadata"""
    filename = file_path.name
    directory = file_path.parent
    
    # Determine format and extract metadata
    if 'E-' in str(directory):
        # New format: data_v7/raw/coinapi_*/YYYYMMDD/E-VENUE/IDDI_*__PAIR.csv.gz
        format_type = 'new_v7'
        venue = directory.name.replace('E-', '')
        date = directory.parent.name
        pair = extract_pair_from_filename(filename)
    elif filename.startswith('IDDI'):
        # New format: data_v7/raw/coinapi_*/IDDI-*+SC-VENUE_*+S-PAIR.csv.gz
        format_type = 'new_v7'
        venue, date, pair = extract_from_iddi_filename(filename)
    else:
        # Legacy format: data_v6/raw/coinapi_*/VENUE_YYYYMMDD_PAIR.csv.gz
        format_type = 'legacy_v6'
        venue = normalize_venue_name(filename)
        date = extract_date_from_filename(filename)
        pair = extract_pair_from_filename(filename)
    
    # Filter for BTC pairs only
    if not pair or not any(btc_pair in pair.upper() for btc_pair in ['BTC-USD', 'BTCUSDT', 'BTCUSD']):
        return None
    
    # Filter for valid venues
    if venue not in VENUES:
        return None
    
    # Filter for 2025 dates
    if not date or not date.startswith('2025'):
        return None
    
    # Verify file integrity
    try:
        size_bytes = file_path.stat().st_size
        gzip_valid = verify_gzip_file(file_path)
        sha256 = compute_file_hash(file_path) if gzip_valid else "INVALID"
    except Exception as e:
        return None
    
    return {
        'file_path': str(file_path),
        'filename': filename,
        'directory': str(directory),
        'format': format_type,
        'venue': venue,
        'date': date,
        'pair': pair,
        'size_bytes': size_bytes,
        'gzip_valid': gzip_valid,
        'sha256': sha256,
        'mtime': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
    }

def extract_from_iddi_filename(filename):
    """Extract venue, date, and pair from IDDI filename"""
    # Format: IDDI-*+SC-VENUE_SPOT_PAIR+S-PAIR.csv.gz
    # Example: IDDI-138123+SC-BINANCE_SPOT_BTC_USDT+S-BTCUSDT.csv.gz
    
    # Extract venue
    venue_match = re.search(r'SC-([A-Z]+)_SPOT', filename)
    venue = venue_match.group(1) if venue_match else None
    
    # Extract pair
    pair_match = re.search(r'S-([A-Z0-9_-]+)\.csv\.gz', filename)
    pair = pair_match.group(1) if pair_match else None
    
    # For date, we need to infer from directory structure or filename
    # This is a limitation - we'll need to handle this differently
    date = None
    
    return venue, date, pair

def normalize_venue_name(filename):
    """Extract and normalize venue name from filename"""
    # Legacy format: VENUE_YYYYMMDD_PAIR.csv.gz
    legacy_match = re.match(r'^([A-Z]+)_\d{8}_[A-Z0-9_-]+\.csv\.gz$', filename)
    if legacy_match:
        return legacy_match.group(1)
    return None

def extract_date_from_filename(filename):
    """Extract date from filename"""
    # Legacy format: VENUE_YYYYMMDD_PAIR.csv.gz
    date_match = re.search(r'(\d{8})', filename)
    if date_match:
        return date_match.group(1)
    return None

def extract_pair_from_filename(filename):
    """Extract trading pair from filename"""
    # Legacy format: VENUE_YYYYMMDD_PAIR.csv.gz
    parts = filename.split('_')
    if len(parts) >= 3:
        pair_part = parts[2].replace('.csv.gz', '')
        return pair_part
    
    # New format: IDDI_*__PAIR.csv.gz
    if '__' in filename:
        pair_part = filename.split('__')[1].replace('.csv.gz', '')
        return pair_part
    
    return None

def scan_all_directories():
    """Scan all v6 and v7 directories for BTC files"""
    print("🔍 Scanning all directories for BTC files...")
    
    all_files = []
    
    # Scan v6 directories
    v6_dirs = [
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_oct',
    ]
    
    for search_dir in v6_dirs:
        if search_dir.exists():
            print(f"  📁 Scanning v6: {search_dir}")
            files = list(search_dir.glob("*.csv.gz"))
            print(f"    Found {len(files)} files")
            all_files.extend(files)
        else:
            print(f"  📁 Directory not found: {search_dir}")
    
    # Scan v7 directories
    v7_dirs = [
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
    ]
    
    for search_dir in v7_dirs:
        if search_dir.exists():
            print(f"  📁 Scanning v7: {search_dir}")
            # Scan recursively for v7 structure
            files = list(search_dir.rglob("*.csv.gz"))
            print(f"    Found {len(files)} files")
            all_files.extend(files)
        else:
            print(f"  📁 Directory not found: {search_dir}")
    
    print(f"📊 Total files found: {len(all_files)}")
    return all_files

def assign_week_to_date(date):
    """Assign a date to its corresponding week"""
    for week_id, week_info in WEEKS.items():
        if date in week_info['dates']:
            return week_id
    return None

def main():
    """Main execution"""
    print("🚀 Phase 39K-REVERIFY-ALL-FINAL: Comprehensive Week Verification (v6 + v7 merge)")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Scan all directories
    all_files = scan_all_directories()
    
    # Process all files
    print(f"\n🔍 Processing {len(all_files)} files...")
    processed_files = []
    skipped_files = []
    
    for i, file_path in enumerate(all_files, 1):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(all_files)} files...")
        
        result = process_file(file_path)
        if result:
            processed_files.append(result)
        else:
            skipped_files.append(str(file_path))
    
    print(f"📊 Processed: {len(processed_files)} valid BTC files")
    print(f"📊 Skipped: {len(skipped_files)} non-BTC files")
    
    # Create DataFrame
    df = pd.DataFrame(processed_files)
    
    # Add week assignment
    df['week'] = df['date'].apply(assign_week_to_date)
    
    # Filter for valid weeks only
    df = df[df['week'].notna()]
    
    print(f"📊 Files in valid weeks: {len(df)}")
    
    # Generate reports
    print(f"\n📝 Generating reports...")
    
    # Write GLOBAL_manifest.csv
    df.to_csv(REPORTS_DIR / 'GLOBAL_manifest_FINAL.csv', index=False)
    print(f"✅ GLOBAL_manifest_FINAL.csv: {len(df)} files")
    
    # Write skipped files log
    if skipped_files:
        with open(REPORTS_DIR / 'GLOBAL_skipped_files_FINAL.txt', 'w') as f:
            f.write("Skipped files (non-BTC or invalid format):\n")
            for file_path in skipped_files:
                f.write(f"{file_path}\n")
        print(f"✅ GLOBAL_skipped_files_FINAL.txt: {len(skipped_files)} files")
    
    # Compute BOM SHA-256
    valid_files = df[df['gzip_valid'] == True]
    if len(valid_files) > 0:
        all_hashes = sorted(valid_files['sha256'].tolist())
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'GLOBAL_bom_sha256_FINAL.txt', 'w') as f:
            f.write(f"Global BTCUSD-class BOM SHA-256 (Final)\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Total files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        print(f"✅ GLOBAL_bom_sha256_FINAL.txt: {bom_hash}")
    
    # Generate week-by-week analysis
    week_summaries = {}
    for week_id, week_info in WEEKS.items():
        week_files = df[df['week'] == week_id]
        valid_week_files = week_files[week_files['gzip_valid'] == True]
        
        total_expected = len(week_info['dates']) * len(VENUES)  # 7 days * 4 venues
        coverage_percentage = len(valid_week_files) / total_expected * 100
        
        week_summaries[week_id] = {
            'name': week_info['name'],
            'dates': week_info['dates'],
            'total_expected': int(total_expected),
            'files_found': int(len(week_files)),
            'files_valid': int(len(valid_week_files)),
            'files_missing': int(total_expected - len(valid_week_files)),
            'coverage_percentage': float(coverage_percentage),
            'total_bytes': int(valid_week_files['size_bytes'].sum()) if len(valid_week_files) > 0 else 0,
            'status': 'COMPLETE' if coverage_percentage >= 90 else 'PARTIAL' if coverage_percentage >= 50 else 'MISSING'
        }
    
    # Write GLOBAL_gate.json
    total_expected = sum(s['total_expected'] for s in week_summaries.values())
    total_valid = sum(s['files_valid'] for s in week_summaries.values())
    overall_coverage = total_valid / total_expected * 100
    
    gate_data = {
        'total_weeks': int(len(WEEKS)),
        'total_expected': int(total_expected),
        'total_found': int(len(df)),
        'total_valid': int(len(valid_files)),
        'total_missing': int(total_expected - len(valid_files)),
        'overall_coverage_percentage': float(overall_coverage),
        'week_summaries': week_summaries,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'GLOBAL_gate_FINAL.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    print(f"✅ GLOBAL_gate_FINAL.json: {len(valid_files)}/{total_expected} files ({overall_coverage:.1f}%)")
    
    # Generate coverage comparison (v6 vs v7)
    v6_files = df[df['format'] == 'legacy_v6']
    v7_files = df[df['format'] == 'new_v7']
    
    comparison_data = {
        'v6_legacy': {
            'total_files': int(len(v6_files)),
            'valid_files': int(len(v6_files[v6_files['gzip_valid'] == True])),
            'total_bytes': int(v6_files['size_bytes'].sum()) if len(v6_files) > 0 else 0,
            'weeks_covered': int(len(v6_files['week'].unique())) if len(v6_files) > 0 else 0
        },
        'v7_new': {
            'total_files': int(len(v7_files)),
            'valid_files': int(len(v7_files[v7_files['gzip_valid'] == True])),
            'total_bytes': int(v7_files['size_bytes'].sum()) if len(v7_files) > 0 else 0,
            'weeks_covered': int(len(v7_files['week'].unique())) if len(v7_files) > 0 else 0
        }
    }
    
    with open(REPORTS_DIR / 'GLOBAL_comparison_FINAL.json', 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    print(f"✅ GLOBAL_comparison_FINAL.json: v6={len(v6_files)} files, v7={len(v7_files)} files")
    
    # Write comprehensive audit
    with open(REPORTS_DIR / 'GLOBAL_audit_FINAL.txt', 'w') as f:
        f.write("Global BTCUSD-class Comprehensive Audit Report (Final)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total weeks analyzed: {len(WEEKS)}\n")
        f.write(f"Total files expected: {total_expected}\n")
        f.write(f"Total files found: {len(df)}\n")
        f.write(f"Total files valid: {len(valid_files)}\n")
        f.write(f"Total files missing: {total_expected - len(valid_files)}\n")
        f.write(f"Overall coverage: {overall_coverage:.1f}%\n")
        f.write(f"Total bytes: {valid_files['size_bytes'].sum():,}\n")
        f.write(f"BOM SHA-256: {bom_hash}\n")
        
        f.write(f"\nFormat Comparison:\n")
        f.write(f"V6 Legacy: {len(v6_files)} files, {len(v6_files[v6_files['gzip_valid'] == True])} valid\n")
        f.write(f"V7 New: {len(v7_files)} files, {len(v7_files[v7_files['gzip_valid'] == True])} valid\n")
        
        f.write(f"\nWeek-by-Week Summary:\n")
        f.write(f"{'Week':<6} {'Name':<25} {'Valid':<6} {'Total':<6} {'Coverage':<10} {'Status':<10} {'Bytes':<12}\n")
        f.write("-" * 80 + "\n")
        for week_id, summary in week_summaries.items():
            f.write(f"{week_id:<6} {summary['name']:<25} {summary['files_valid']:<6} {summary['total_expected']:<6} {summary['coverage_percentage']:<9.1f}% {summary['status']:<10} {summary['total_bytes']:<12,}\n")
        
        f.write(f"\nStatus Summary:\n")
        status_counts = {}
        for summary in week_summaries.values():
            status = summary['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            f.write(f"{status}: {count} weeks\n")
    
    print(f"✅ GLOBAL_audit_FINAL.txt: {len(WEEKS)} weeks analyzed")
    
    # Print summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-REVERIFY-ALL-FINAL Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    print(f"📊 Total weeks analyzed: {len(WEEKS)}")
    print(f"📊 Total files expected: {total_expected}")
    print(f"📊 Total files found: {len(df)}")
    print(f"📊 Total files valid: {len(valid_files)}")
    print(f"📊 Overall coverage: {overall_coverage:.1f}%")
    print(f"📊 Total bytes: {valid_files['size_bytes'].sum():,}")
    
    print(f"\n📊 Format Comparison:")
    print(f"  V6 Legacy: {len(v6_files)} files, {len(v6_files[v6_files['gzip_valid'] == True])} valid")
    print(f"  V7 New: {len(v7_files)} files, {len(v7_files[v7_files['gzip_valid'] == True])} valid")
    
    print(f"\n📊 Week Status Summary:")
    status_counts = {}
    for summary in week_summaries.values():
        status = summary['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"  {status}: {count} weeks")
    
    print(f"\n📊 Complete Weeks (≥90% coverage):")
    complete_weeks = [week_id for week_id, summary in week_summaries.items() if summary['status'] == 'COMPLETE']
    for week_id in complete_weeks:
        summary = week_summaries[week_id]
        print(f"  {week_id}: {summary['files_valid']}/{summary['total_expected']} files ({summary['coverage_percentage']:.1f}%)")
    
    print(f"\n📊 Partial Weeks (50-89% coverage):")
    partial_weeks = [week_id for week_id, summary in week_summaries.items() if summary['status'] == 'PARTIAL']
    for week_id in partial_weeks:
        summary = week_summaries[week_id]
        print(f"  {week_id}: {summary['files_valid']}/{summary['total_expected']} files ({summary['coverage_percentage']:.1f}%)")
    
    print(f"\n📊 Missing Weeks (<50% coverage):")
    missing_weeks = [week_id for week_id, summary in week_summaries.items() if summary['status'] == 'MISSING']
    for week_id in missing_weeks:
        summary = week_summaries[week_id]
        print(f"  {week_id}: {summary['files_valid']}/{summary['total_expected']} files ({summary['coverage_percentage']:.1f}%)")
    
    return week_summaries, len(valid_files), total_expected, overall_coverage

if __name__ == "__main__":
    week_summaries, total_valid, total_expected, overall_coverage = main()
