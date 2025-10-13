#!/usr/bin/env python3
"""
Phase 39K-W5-VERIFY: Week-5 Coverage Verification (July 21-27)
"""

import os
import sys
import hashlib
import json
import gzip
import time
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports'

# Target configuration
WEEK5_DATES = ['20250721', '20250722', '20250723', '20250724', '20250725', '20250726', '20250727']
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
            # Try to read first few bytes
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
        print(f"⚠️ Error computing hash for {file_path}: {e}")
        return "ERROR"

def scan_week5_files():
    """Scan for Week-5 files in both v6 and v7 directories"""
    print("🔍 Scanning for Week-5 files...")
    
    # Check both v6 and v7 directories
    search_paths = [
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_extension'
    ]
    
    found_files = []
    missing_files = []
    
    for date in WEEK5_DATES:
        for venue in VENUES:
            target_symbol = VENUE_SYMBOLS[venue]
            found = False
            
            # Check legacy format (v6)
            legacy_path = BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul' / f'{venue}_{date}_{target_symbol}.csv.gz'
            if legacy_path.exists():
                found_files.append({
                    'date': date,
                    'venue': venue,
                    'pair': target_symbol,
                    'file_path': str(legacy_path),
                    'format': 'legacy_v6',
                    'size_bytes': legacy_path.stat().st_size,
                    'gzip_valid': verify_gzip_file(legacy_path),
                    'sha256': compute_file_hash(legacy_path)
                })
                found = True
            
            # Check new format (v7)
            new_path = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5' / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz'
            for path in BASE_DIR.glob(f'data_v7/raw/coinapi_jul_w5/{date}/E-{venue}/IDDI_*__{target_symbol.replace("-", "_")}.csv.gz'):
                if path.exists():
                    found_files.append({
                        'date': date,
                        'venue': venue,
                        'pair': target_symbol,
                        'file_path': str(path),
                        'format': 'new_v7',
                        'size_bytes': path.stat().st_size,
                        'gzip_valid': verify_gzip_file(path),
                        'sha256': compute_file_hash(path)
                    })
                    found = True
            
            # Check extension directory
            ext_path = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_extension' / f'{venue}_{date}_{target_symbol}.csv.gz'
            if ext_path.exists():
                found_files.append({
                    'date': date,
                    'venue': venue,
                    'pair': target_symbol,
                    'file_path': str(ext_path),
                    'format': 'extension_v7',
                    'size_bytes': ext_path.stat().st_size,
                    'gzip_valid': verify_gzip_file(ext_path),
                    'sha256': compute_file_hash(ext_path)
                })
                found = True
            
            if not found:
                missing_files.append({
                    'date': date,
                    'venue': venue,
                    'pair': target_symbol,
                    'reason': 'File not found in any directory'
                })
    
    return found_files, missing_files

def scan_quarantine_files():
    """Scan for non-BTCUSD files that should be quarantined"""
    print("🔍 Scanning for quarantine candidates...")
    
    quarantine_files = []
    search_paths = [
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_extension'
    ]
    
    for date in WEEK5_DATES:
        for venue in VENUES:
            target_symbol = VENUE_SYMBOLS[venue]
            
            # Check legacy format for non-target files
            legacy_dir = BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul'
            if legacy_dir.exists():
                for file_path in legacy_dir.glob(f'{venue}_{date}_*.csv.gz'):
                    if target_symbol not in file_path.name:
                        quarantine_files.append({
                            'date': date,
                            'venue': venue,
                            'file_path': str(file_path),
                            'filename': file_path.name,
                            'size_bytes': file_path.stat().st_size,
                            'sha256': compute_file_hash(file_path),
                            'reason': f'Non-target pair (not {target_symbol})'
                        })
            
            # Check new format for non-target files
            new_dir = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5' / date / f'E-{venue}'
            if new_dir.exists():
                for file_path in new_dir.glob('*.csv.gz'):
                    if target_symbol.replace('-', '_') not in file_path.name:
                        quarantine_files.append({
                            'date': date,
                            'venue': venue,
                            'file_path': str(file_path),
                            'filename': file_path.name,
                            'size_bytes': file_path.stat().st_size,
                            'sha256': compute_file_hash(file_path),
                            'reason': f'Non-target pair (not {target_symbol})'
                        })
    
    return quarantine_files

def build_coverage_matrix(found_files):
    """Build coverage matrix for Week-5"""
    matrix = {}
    
    for date in WEEK5_DATES:
        matrix[date] = {}
        for venue in VENUES:
            # Check if file exists for this date/venue
            venue_files = [f for f in found_files if f['date'] == date and f['venue'] == venue]
            if venue_files:
                # Use the first valid file
                valid_file = next((f for f in venue_files if f['gzip_valid']), None)
                matrix[date][venue] = '✅' if valid_file else '⚠️'
            else:
                matrix[date][venue] = '❌'
    
    return matrix

def main():
    """Main execution"""
    print("🚀 Phase 39K-W5-VERIFY: Week-5 Coverage Verification (July 21-27)")
    print("=" * 70)
    
    start_time = time.time()
    
    # Create reports directory
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Scan for files
    found_files, missing_files = scan_week5_files()
    quarantine_files = scan_quarantine_files()
    
    print(f"📊 Found {len(found_files)} target files")
    print(f"📊 Missing {len(missing_files)} target files")
    print(f"📊 Found {len(quarantine_files)} quarantine candidates")
    
    # Build coverage matrix
    coverage_matrix = build_coverage_matrix(found_files)
    
    # Write W5_manifest.csv
    if found_files:
        manifest_df = pd.DataFrame(found_files)
        manifest_df.to_csv(REPORTS_DIR / 'W5_manifest.csv', index=False)
        print(f"✅ W5_manifest.csv: {len(found_files)} files")
    
    # Write W5_missing.csv
    if missing_files:
        missing_df = pd.DataFrame(missing_files)
        missing_df.to_csv(REPORTS_DIR / 'W5_missing.csv', index=False)
        print(f"✅ W5_missing.csv: {len(missing_files)} missing files")
    
    # Write W5_quarantine.csv
    if quarantine_files:
        quarantine_df = pd.DataFrame(quarantine_files)
        quarantine_df.to_csv(REPORTS_DIR / 'W5_quarantine.csv', index=False)
        print(f"✅ W5_quarantine.csv: {len(quarantine_files)} quarantine files")
    
    # Compute BOM SHA-256
    if found_files:
        all_hashes = sorted([f['sha256'] for f in found_files if f['gzip_valid']])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'W5_bom_sha256.txt', 'w') as f:
            f.write(f"Week -5 BTCUSD-class BOM SHA-256\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        print(f"✅ W5_bom_sha256.txt: {bom_hash}")
    
    # Write W5_gate.json
    valid_files = [f for f in found_files if f['gzip_valid']]
    total_expected = len(WEEK5_DATES) * len(VENUES)  # 7 days * 4 venues = 28
    coverage_percentage = len(valid_files) / total_expected * 100
    
    gate_data = {
        'week': '-5',
        'days_expected': len(WEEK5_DATES),
        'venues_expected': len(VENUES),
        'total_expected': total_expected,
        'files_found': len(found_files),
        'files_valid': len(valid_files),
        'files_missing': len(missing_files),
        'quarantine_files': len(quarantine_files),
        'coverage_percentage': coverage_percentage,
        'all_gates_passed': len(valid_files) >= total_expected * 0.8,  # 80% threshold
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'W5_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    print(f"✅ W5_gate.json: {len(valid_files)}/{total_expected} files ({coverage_percentage:.1f}%)")
    
    # Write W5_audit.txt
    total_bytes = sum(f['size_bytes'] for f in valid_files)
    unique_hashes = len(set(f['sha256'] for f in valid_files))
    
    with open(REPORTS_DIR / 'W5_audit.txt', 'w') as f:
        f.write("Week -5 BTCUSD-class Audit Report\n")
        f.write("=" * 40 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files found: {len(found_files)}\n")
        f.write(f"Total files valid: {len(valid_files)}\n")
        f.write(f"Total files missing: {len(missing_files)}\n")
        f.write(f"Quarantine files: {len(quarantine_files)}\n")
        f.write(f"Total bytes: {total_bytes:,}\n")
        f.write(f"Unique SHA-256 hashes: {unique_hashes}\n")
        f.write(f"Coverage: {coverage_percentage:.1f}%\n")
        f.write(f"Status: {'PASS' if gate_data['all_gates_passed'] else 'FAIL'}\n")
        if found_files:
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        f.write(f"\nCoverage Matrix (7 days × 4 venues):\n")
        f.write(f"{'Date':<10} {'COINBASE':<10} {'BINANCE':<10} {'BYBITSPOT':<10} {'BITGET':<10}\n")
        f.write("-" * 50 + "\n")
        for date in WEEK5_DATES:
            f.write(f"{date:<10} {coverage_matrix[date]['COINBASE']:<10} {coverage_matrix[date]['BINANCE']:<10} {coverage_matrix[date]['BYBITSPOT']:<10} {coverage_matrix[date]['BITGET']:<10}\n")
        
        f.write(f"\nPer-venue totals:\n")
        for venue in VENUES:
            venue_files = [f for f in valid_files if f['venue'] == venue]
            venue_dates = set(f['date'] for f in venue_files)
            f.write(f"{venue}: {len(venue_files)} files, {len(venue_dates)} days\n")
    
    print(f"✅ W5_audit.txt: {len(valid_files)} files, {total_bytes:,} bytes")
    
    # Summary
    runtime_minutes = (time.time() - start_time) / 60
    print(f"\n✅ Phase 39K-W5-VERIFY Complete")
    print(f"⏱️ Runtime: {runtime_minutes:.1f} minutes")
    print(f"📊 Files validated: {len(valid_files)}")
    print(f"📊 Files missing: {len(missing_files)}")
    print(f"📊 Total bytes: {total_bytes:,}")
    
    if valid_files:
        first_sha256 = valid_files[0]['sha256']
        print(f"📊 First SHA-256: {first_sha256}")
        print(f"📊 BOM SHA-256: {bom_hash}")
        
        print(f"\n📋 5-Line Summary:")
        print(f"  Files validated: {len(valid_files)}")
        print(f"  Files missing: {len(missing_files)}")
        print(f"  Total bytes: {total_bytes:,}")
        print(f"  First SHA-256: {first_sha256}")
        print(f"  BOM SHA-256: {bom_hash}")
        
        print(f"\n📊 Coverage Table (7 days × 4 venues):")
        print(f"  Date      COINBASE  BINANCE   BYBITSPOT BITGET")
        print(f"  --------- --------- --------- --------- ---------")
        for date in WEEK5_DATES:
            print(f"  {date} {coverage_matrix[date]['COINBASE']:<9} {coverage_matrix[date]['BINANCE']:<9} {coverage_matrix[date]['BYBITSPOT']:<9} {coverage_matrix[date]['BITGET']}")
        
        print(f"\n🔒 Network Status: FROZEN (no downloads performed)")
    else:
        print("❌ No valid files found")
        sys.exit(1)

if __name__ == "__main__":
    main()
