#!/usr/bin/env python3
"""
Comprehensive Week Verification: Check all weeks for BTCUSD-class coverage
"""

import os
import sys
import hashlib
import json
import gzip
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

def scan_week_files(week_id, dates):
    """Scan for files in a specific week"""
    print(f"🔍 Scanning {week_id}: {WEEKS[week_id]['name']}")
    
    found_files = []
    missing_files = []
    
    for date in dates:
        for venue in VENUES:
            target_symbol = VENUE_SYMBOLS[venue]
            found = False
            
            # Check multiple possible locations
            search_paths = [
                # New format (v7)
                BASE_DIR / 'data_v7' / 'raw' / f'coinapi_{week_id.lower().replace("-", "w")}' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_aug' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_sep' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_oct' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz',
                # Legacy format (v6)
                BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul' / f'{venue}_{date}_{target_symbol}.csv.gz',
                BASE_DIR / 'data_v6' / 'raw' / 'coinapi_aug' / f'{venue}_{date}_{target_symbol}.csv.gz',
                BASE_DIR / 'data_v6' / 'raw' / 'coinapi_sep' / f'{venue}_{date}_{target_symbol}.csv.gz',
                BASE_DIR / 'data_v6' / 'raw' / 'coinapi_oct' / f'{venue}_{date}_{target_symbol}.csv.gz',
                # Extension directories
                BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_extension' / f'{venue}_{date}_{target_symbol}.csv.gz',
            ]
            
            for search_path in search_paths:
                if '*' in str(search_path):
                    # Handle glob patterns - convert to relative path
                    relative_path = str(search_path).replace(str(BASE_DIR) + '/', '')
                    for path in BASE_DIR.glob(relative_path):
                        if path.exists():
                            found_files.append({
                                'week': week_id,
                                'date': date,
                                'venue': venue,
                                'pair': target_symbol,
                                'file_path': str(path),
                                'size_bytes': path.stat().st_size,
                                'gzip_valid': verify_gzip_file(path),
                                'sha256': compute_file_hash(path)
                            })
                            found = True
                            break
                else:
                    # Handle direct paths
                    if search_path.exists():
                        found_files.append({
                            'week': week_id,
                            'date': date,
                            'venue': venue,
                            'pair': target_symbol,
                            'file_path': str(search_path),
                            'size_bytes': search_path.stat().st_size,
                            'gzip_valid': verify_gzip_file(search_path),
                            'sha256': compute_file_hash(search_path)
                        })
                        found = True
                        break
                
                if found:
                    break
            
            if not found:
                missing_files.append({
                    'week': week_id,
                    'date': date,
                    'venue': venue,
                    'pair': target_symbol,
                    'reason': 'File not found in any directory'
                })
    
    return found_files, missing_files

def main():
    """Main execution"""
    print("🚀 Comprehensive Week Verification: All Weeks BTCUSD-class Coverage")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    all_found_files = []
    all_missing_files = []
    week_summaries = {}
    
    # Scan each week
    for week_id, week_info in WEEKS.items():
        found_files, missing_files = scan_week_files(week_id, week_info['dates'])
        
        all_found_files.extend(found_files)
        all_missing_files.extend(missing_files)
        
        # Calculate week statistics
        total_expected = len(week_info['dates']) * len(VENUES)  # 7 days * 4 venues
        valid_files = [f for f in found_files if f['gzip_valid']]
        coverage_percentage = len(valid_files) / total_expected * 100
        
        week_summaries[week_id] = {
            'name': week_info['name'],
            'dates': week_info['dates'],
            'total_expected': total_expected,
            'files_found': len(found_files),
            'files_valid': len(valid_files),
            'files_missing': len(missing_files),
            'coverage_percentage': coverage_percentage,
            'total_bytes': sum(f['size_bytes'] for f in valid_files),
            'status': 'COMPLETE' if coverage_percentage >= 90 else 'PARTIAL' if coverage_percentage >= 50 else 'MISSING'
        }
        
        print(f"  📊 {week_id}: {len(valid_files)}/{total_expected} files ({coverage_percentage:.1f}%) - {week_summaries[week_id]['status']}")
    
    # Generate comprehensive report
    print(f"\n📝 Generating comprehensive report...")
    
    # Write all files manifest
    if all_found_files:
        manifest_df = pd.DataFrame(all_found_files)
        manifest_df.to_csv(REPORTS_DIR / 'ALL_WEEKS_manifest.csv', index=False)
        print(f"✅ ALL_WEEKS_manifest.csv: {len(all_found_files)} files")
    
    # Write missing files manifest
    if all_missing_files:
        missing_df = pd.DataFrame(all_missing_files)
        missing_df.to_csv(REPORTS_DIR / 'ALL_WEEKS_missing.csv', index=False)
        print(f"✅ ALL_WEEKS_missing.csv: {len(all_missing_files)} missing files")
    
    # Write week summary
    summary_data = []
    for week_id, summary in week_summaries.items():
        summary_data.append({
            'week': week_id,
            'name': summary['name'],
            'total_expected': summary['total_expected'],
            'files_found': summary['files_found'],
            'files_valid': summary['files_valid'],
            'files_missing': summary['files_missing'],
            'coverage_percentage': summary['coverage_percentage'],
            'total_bytes': summary['total_bytes'],
            'status': summary['status']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(REPORTS_DIR / 'ALL_WEEKS_summary.csv', index=False)
    print(f"✅ ALL_WEEKS_summary.csv: {len(week_summaries)} weeks")
    
    # Compute overall BOM SHA-256
    if all_found_files:
        valid_files = [f for f in all_found_files if f['gzip_valid']]
        all_hashes = sorted([f['sha256'] for f in valid_files])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'ALL_WEEKS_bom_sha256.txt', 'w') as f:
            f.write(f"All Weeks BTCUSD-class BOM SHA-256\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Total files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        print(f"✅ ALL_WEEKS_bom_sha256.txt: {bom_hash}")
    
    # Write comprehensive audit
    total_expected = sum(s['total_expected'] for s in week_summaries.values())
    total_valid = sum(s['files_valid'] for s in week_summaries.values())
    total_bytes = sum(s['total_bytes'] for s in week_summaries.values())
    overall_coverage = total_valid / total_expected * 100
    
    with open(REPORTS_DIR / 'ALL_WEEKS_audit.txt', 'w') as f:
        f.write("All Weeks BTCUSD-class Comprehensive Audit Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total weeks analyzed: {len(WEEKS)}\n")
        f.write(f"Total files expected: {total_expected}\n")
        f.write(f"Total files found: {len(all_found_files)}\n")
        f.write(f"Total files valid: {total_valid}\n")
        f.write(f"Total files missing: {len(all_missing_files)}\n")
        f.write(f"Overall coverage: {overall_coverage:.1f}%\n")
        f.write(f"Total bytes: {total_bytes:,}\n")
        f.write(f"BOM SHA-256: {bom_hash}\n")
        
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
    
    print(f"✅ ALL_WEEKS_audit.txt: {len(WEEKS)} weeks analyzed")
    
    # Print summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Comprehensive Week Verification Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    print(f"📊 Total weeks analyzed: {len(WEEKS)}")
    print(f"📊 Total files expected: {total_expected}")
    print(f"📊 Total files valid: {total_valid}")
    print(f"📊 Overall coverage: {overall_coverage:.1f}%")
    print(f"📊 Total bytes: {total_bytes:,}")
    
    print(f"\n📊 Week Status Summary:")
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
    
    return week_summaries, total_valid, total_expected, overall_coverage

if __name__ == "__main__":
    week_summaries, total_valid, total_expected, overall_coverage = main()
