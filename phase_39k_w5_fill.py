#!/usr/bin/env python3
"""
Phase 39K-W5-FILL: Download Missing Week-5 BTCUSD-class Files
"""

import os
import sys
import hashlib
import json
import gzip
import time
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports'
OUTPUT_DIR = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5'

# API Configuration
API_KEY = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
LIST_BASE_URL = "https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/"
GET_BASE_URL = "https://s3.flatfiles.coinapi.io/coinapi/{key}"
HEADERS = {
    "X-CoinAPI-Key": API_KEY,
    "User-Agent": "ACD-Monitor/1.0"
}

# Target files to download
MISSING_FILES = [
    # July 21st - all venues
    {"date": "20250721", "venue": "COINBASE", "pair": "BTC-USD"},
    {"date": "20250721", "venue": "BINANCE", "pair": "BTCUSDT"},
    {"date": "20250721", "venue": "BYBITSPOT", "pair": "BTCUSDT"},
    {"date": "20250721", "venue": "BITGET", "pair": "BTCUSDT"},
    # July 22-27 - COINBASE only
    {"date": "20250722", "venue": "COINBASE", "pair": "BTC-USD"},
    {"date": "20250723", "venue": "COINBASE", "pair": "BTC-USD"},
    {"date": "20250724", "venue": "COINBASE", "pair": "BTC-USD"},
    {"date": "20250725", "venue": "COINBASE", "pair": "BTC-USD"},
    {"date": "20250726", "venue": "COINBASE", "pair": "BTC-USD"},
    {"date": "20250727", "venue": "COINBASE", "pair": "BTC-USD"},
]

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
        print(f"⚠️ Error computing hash for {file_path}: {e}")
        return "ERROR"

def list_available_files(date, venue):
    """List available files for a specific date/venue"""
    list_url = LIST_BASE_URL.format(date=date, venue=venue)
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        files = []
        
        for contents in root.findall('.//Contents'):
            key_elem = contents.find('Key')
            if key_elem is not None:
                key = key_elem.text
                files.append(key)
        
        return files
    except Exception as e:
        print(f"⚠️ Error listing files for {date}/{venue}: {e}")
        return []

def download_file(key, output_path):
    """Download a file with atomic write"""
    get_url = GET_BASE_URL.format(key=key)
    temp_path = output_path.with_suffix(output_path.suffix + '.part')
    
    try:
        response = requests.get(get_url, headers=HEADERS, timeout=120, stream=True)
        response.raise_for_status()
        
        # Atomic write
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        
        # Verify content length
        if response.headers.get('Content-Length'):
            expected_size = int(response.headers['Content-Length'])
            actual_size = temp_path.stat().st_size
            if actual_size != expected_size:
                temp_path.unlink()
                return False, f"Size mismatch: expected {expected_size}, got {actual_size}"
        
        # Verify gzip header
        if not verify_gzip_file(temp_path):
            temp_path.unlink()
            return False, "Invalid gzip file"
        
        # Atomic rename
        temp_path.rename(output_path)
        return True, "Success"
        
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return False, str(e)

def main():
    """Main execution"""
    print("🚀 Phase 39K-W5-FILL: Download Missing Week-5 BTCUSD-class Files")
    print("=" * 70)
    
    start_time = time.time()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if network is frozen
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if lock_file.exists():
        print("🔒 Network is frozen. Removing lock for download...")
        lock_file.unlink()
    
    downloaded_files = []
    failed_downloads = []
    total_calls = 0
    
    print(f"📋 Target: {len(MISSING_FILES)} missing files")
    
    for i, target in enumerate(MISSING_FILES, 1):
        date = target['date']
        venue = target['venue']
        pair = target['pair']
        
        print(f"\n[{i}/{len(MISSING_FILES)}] Processing {date}/{venue}/{pair}")
        
        # Create output directory for this date/venue
        date_dir = OUTPUT_DIR / date / f"E-{venue}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # List available files
        print(f"  🔍 Listing files for {date}/{venue}...")
        available_files = list_available_files(date, venue)
        total_calls += 1
        
        if not available_files:
            print(f"  ❌ No files found for {date}/{venue}")
            failed_downloads.append({
                'date': date,
                'venue': venue,
                'pair': pair,
                'reason': 'No files found in listing'
            })
            continue
        
        # Find matching file
        target_file = None
        for file_key in available_files:
            if pair in file_key or pair.replace('-', '_') in file_key:
                target_file = file_key
                break
        
        if not target_file:
            print(f"  ❌ No matching file found for {pair}")
            failed_downloads.append({
                'date': date,
                'venue': venue,
                'pair': pair,
                'reason': f'No matching file found for {pair}'
            })
            continue
        
        print(f"  📁 Found: {target_file}")
        
        # Generate output filename
        output_filename = f"IDDI_{hashlib.md5(target_file.encode()).hexdigest()[:8]}__{pair.replace('-', '_')}.csv.gz"
        output_path = date_dir / output_filename
        
        # Check if file already exists
        if output_path.exists():
            print(f"  ⚠️ File already exists: {output_path}")
            # Verify existing file
            if verify_gzip_file(output_path):
                downloaded_files.append({
                    'date': date,
                    'venue': venue,
                    'pair': pair,
                    'file_path': str(output_path),
                    'size_bytes': output_path.stat().st_size,
                    'gzip_valid': True,
                    'sha256': compute_file_hash(output_path),
                    'status': 'already_exists'
                })
                continue
            else:
                print(f"  🗑️ Removing corrupted file: {output_path}")
                output_path.unlink()
        
        # Download file
        print(f"  ⬇️ Downloading to: {output_path}")
        success, message = download_file(target_file, output_path)
        total_calls += 1
        
        if success:
            # Verify downloaded file
            if verify_gzip_file(output_path):
                file_size = output_path.stat().st_size
                file_hash = compute_file_hash(output_path)
                
                downloaded_files.append({
                    'date': date,
                    'venue': venue,
                    'pair': pair,
                    'file_path': str(output_path),
                    'size_bytes': file_size,
                    'gzip_valid': True,
                    'sha256': file_hash,
                    'status': 'downloaded'
                })
                
                print(f"  ✅ Downloaded: {file_size:,} bytes, SHA-256: {file_hash[:16]}...")
            else:
                print(f"  ❌ Downloaded file is corrupted")
                output_path.unlink()
                failed_downloads.append({
                    'date': date,
                    'venue': venue,
                    'pair': pair,
                    'reason': 'Downloaded file is corrupted'
                })
        else:
            print(f"  ❌ Download failed: {message}")
            failed_downloads.append({
                'date': date,
                'venue': venue,
                'pair': pair,
                'reason': message
            })
        
        # Rate limiting
        time.sleep(1)
    
    # Re-freeze network
    print(f"\n🔒 Re-freezing network...")
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(f"Network frozen after Phase 39K-W5-FILL\nTimestamp: {datetime.utcnow().isoformat()}Z\n")
    
    # Generate reports
    print(f"\n📝 Generating reports...")
    
    # Write download manifest
    if downloaded_files:
        manifest_df = pd.DataFrame(downloaded_files)
        manifest_df.to_csv(REPORTS_DIR / 'W5_FILL_manifest.csv', index=False)
        print(f"✅ W5_FILL_manifest.csv: {len(downloaded_files)} files")
    
    # Write failed downloads
    if failed_downloads:
        failed_df = pd.DataFrame(failed_downloads)
        failed_df.to_csv(REPORTS_DIR / 'W5_FILL_failed.csv', index=False)
        print(f"✅ W5_FILL_failed.csv: {len(failed_downloads)} failed downloads")
    
    # Re-run Week-5 verification
    print(f"\n🔍 Re-running Week-5 verification...")
    
    # Scan for all Week-5 files (including newly downloaded)
    all_week5_files = []
    week5_dates = ['20250721', '20250722', '20250723', '20250724', '20250725', '20250726', '20250727']
    venues = ['COINBASE', 'BINANCE', 'BYBITSPOT', 'BITGET']
    venue_symbols = {
        'COINBASE': 'BTC-USD',
        'BINANCE': 'BTCUSDT',
        'BYBITSPOT': 'BTCUSDT',
        'BITGET': 'BTCUSDT'
    }
    
    for date in week5_dates:
        for venue in venues:
            target_symbol = venue_symbols[venue]
            
            # Check new format (v7)
            new_path = OUTPUT_DIR / date / f'E-{venue}' / f'IDDI_*__{target_symbol.replace("-", "_")}.csv.gz'
            for path in BASE_DIR.glob(f'data_v7/raw/coinapi_jul_w5/{date}/E-{venue}/IDDI_*__{target_symbol.replace("-", "_")}.csv.gz'):
                if path.exists():
                    all_week5_files.append({
                        'date': date,
                        'venue': venue,
                        'pair': target_symbol,
                        'file_path': str(path),
                        'format': 'new_v7',
                        'size_bytes': path.stat().st_size,
                        'gzip_valid': verify_gzip_file(path),
                        'sha256': compute_file_hash(path)
                    })
            
            # Check legacy format (v6)
            legacy_path = BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul' / f'{venue}_{date}_{target_symbol}.csv.gz'
            if legacy_path.exists():
                all_week5_files.append({
                    'date': date,
                    'venue': venue,
                    'pair': target_symbol,
                    'file_path': str(legacy_path),
                    'format': 'legacy_v6',
                    'size_bytes': legacy_path.stat().st_size,
                    'gzip_valid': verify_gzip_file(legacy_path),
                    'sha256': compute_file_hash(legacy_path)
                })
    
    # Build coverage matrix
    coverage_matrix = {}
    for date in week5_dates:
        coverage_matrix[date] = {}
        for venue in venues:
            venue_files = [f for f in all_week5_files if f['date'] == date and f['venue'] == venue]
            if venue_files:
                valid_file = next((f for f in venue_files if f['gzip_valid']), None)
                coverage_matrix[date][venue] = '✅' if valid_file else '⚠️'
            else:
                coverage_matrix[date][venue] = '❌'
    
    # Write updated W5_manifest.csv
    if all_week5_files:
        manifest_df = pd.DataFrame(all_week5_files)
        manifest_df.to_csv(REPORTS_DIR / 'W5_manifest.csv', index=False)
        print(f"✅ W5_manifest.csv: {len(all_week5_files)} files")
    
    # Compute BOM SHA-256
    if all_week5_files:
        valid_files = [f for f in all_week5_files if f['gzip_valid']]
        all_hashes = sorted([f['sha256'] for f in valid_files])
        bom_hash = hashlib.sha256('\n'.join(all_hashes).encode()).hexdigest()
        
        with open(REPORTS_DIR / 'W5_bom_sha256.txt', 'w') as f:
            f.write(f"Week -5 BTCUSD-class BOM SHA-256\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write(f"Files: {len(all_hashes)}\n")
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        print(f"✅ W5_bom_sha256.txt: {bom_hash}")
    
    # Write updated W5_gate.json
    total_expected = len(week5_dates) * len(venues)  # 7 days * 4 venues = 28
    coverage_percentage = len(valid_files) / total_expected * 100
    
    gate_data = {
        'week': '-5',
        'days_expected': len(week5_dates),
        'venues_expected': len(venues),
        'total_expected': total_expected,
        'files_found': len(all_week5_files),
        'files_valid': len(valid_files),
        'files_missing': total_expected - len(valid_files),
        'coverage_percentage': coverage_percentage,
        'all_gates_passed': len(valid_files) >= total_expected,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(REPORTS_DIR / 'W5_gate.json', 'w') as f:
        json.dump(gate_data, f, indent=2)
    
    print(f"✅ W5_gate.json: {len(valid_files)}/{total_expected} files ({coverage_percentage:.1f}%)")
    
    # Write updated W5_audit.txt
    total_bytes = sum(f['size_bytes'] for f in valid_files)
    unique_hashes = len(set(f['sha256'] for f in valid_files))
    
    with open(REPORTS_DIR / 'W5_audit.txt', 'w') as f:
        f.write("Week -5 BTCUSD-class Audit Report (Updated)\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files found: {len(all_week5_files)}\n")
        f.write(f"Total files valid: {len(valid_files)}\n")
        f.write(f"Total files missing: {total_expected - len(valid_files)}\n")
        f.write(f"Total bytes: {total_bytes:,}\n")
        f.write(f"Unique SHA-256 hashes: {unique_hashes}\n")
        f.write(f"Coverage: {coverage_percentage:.1f}%\n")
        f.write(f"Status: {'PASS' if gate_data['all_gates_passed'] else 'FAIL'}\n")
        if all_week5_files:
            f.write(f"BOM SHA-256: {bom_hash}\n")
        
        f.write(f"\nCoverage Matrix (7 days × 4 venues):\n")
        f.write(f"{'Date':<10} {'COINBASE':<10} {'BINANCE':<10} {'BYBITSPOT':<10} {'BITGET':<10}\n")
        f.write("-" * 50 + "\n")
        for date in week5_dates:
            f.write(f"{date:<10} {coverage_matrix[date]['COINBASE']:<10} {coverage_matrix[date]['BINANCE']:<10} {coverage_matrix[date]['BYBITSPOT']:<10} {coverage_matrix[date]['BITGET']:<10}\n")
        
        f.write(f"\nPer-venue totals:\n")
        for venue in venues:
            venue_files = [f for f in valid_files if f['venue'] == venue]
            venue_dates = set(f['date'] for f in venue_files)
            f.write(f"{venue}: {len(venue_files)} files, {len(venue_dates)} days\n")
    
    print(f"✅ W5_audit.txt: {len(valid_files)} files, {total_bytes:,} bytes")
    
    # Summary
    runtime_minutes = (time.time() - start_time) / 60
    print(f"\n✅ Phase 39K-W5-FILL Complete")
    print(f"⏱️ Runtime: {runtime_minutes:.1f} minutes")
    print(f"📊 API calls made: {total_calls}")
    print(f"📊 Files downloaded: {len([f for f in downloaded_files if f['status'] == 'downloaded'])}")
    print(f"📊 Files already existed: {len([f for f in downloaded_files if f['status'] == 'already_exists'])}")
    print(f"📊 Failed downloads: {len(failed_downloads)}")
    print(f"📊 Total Week-5 files: {len(valid_files)}/{total_expected} ({coverage_percentage:.1f}%)")
    print(f"📊 Status: {'PASS' if gate_data['all_gates_passed'] else 'FAIL'}")
    
    if valid_files:
        first_sha256 = valid_files[0]['sha256']
        print(f"📊 First SHA-256: {first_sha256}")
        print(f"📊 BOM SHA-256: {bom_hash}")
        
        print(f"\n📋 5-Line Summary:")
        print(f"  Files downloaded: {len([f for f in downloaded_files if f['status'] == 'downloaded'])}")
        print(f"  Total Week-5 files: {len(valid_files)}")
        print(f"  Total bytes: {total_bytes:,}")
        print(f"  First SHA-256: {first_sha256}")
        print(f"  BOM SHA-256: {bom_hash}")
        
        print(f"\n📊 Updated Coverage Table (7 days × 4 venues):")
        print(f"  Date      COINBASE  BINANCE   BYBITSPOT BITGET")
        print(f"  --------- --------- --------- --------- ---------")
        for date in week5_dates:
            print(f"  {date} {coverage_matrix[date]['COINBASE']:<9} {coverage_matrix[date]['BINANCE']:<9} {coverage_matrix[date]['BYBITSPOT']:<9} {coverage_matrix[date]['BITGET']}")
        
        print(f"\n🔒 Network Status: FROZEN")
    else:
        print("❌ No valid files found")
        sys.exit(1)

if __name__ == "__main__":
    main()
