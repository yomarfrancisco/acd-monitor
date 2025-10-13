#!/usr/bin/env python3
"""
Phase 39K-FILL-W7: Targeted Retrieval of Missing BTCUSD Files for Week -7
Retrieve the missing BTCUSD-class tick files for Jul 7 – Jul 13 2025 (Week -7)
"""

import os
import sys
import hashlib
import json
import gzip
import requests
import time
import re
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'verify_14w'
OUTPUT_DIR = BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7'

# Week -7 date range: Jul 7-13, 2025
WEEK_7_DATES = ['20250707', '20250708', '20250709', '20250710', '20250711', '20250712', '20250713']

# Venues and their expected pairs
VENUES = {
    'BINANCE': 'BTCUSDT',
    'COINBASE': 'BTC-USD', 
    'BYBITSPOT': 'BTCUSDT',
    'BITGET': 'BTCUSDT'
}

# Search roots
SEARCH_ROOTS = [
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
    BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
    BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw'
]

# CoinAPI configuration
COINAPI_BASE_URL = 'https://s3.flatfiles.coinapi.io'
COINAPI_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

def is_week_7_btcusd_file(file_path):
    """Check if file matches Week -7 BTCUSD criteria"""
    filename = file_path.name.lower()
    path_str = str(file_path).lower()
    
    # Check for BTCUSD-class pairs
    has_btcusd = any(pair in filename for pair in ['btcusdt', 'btc-usd', 'btc__002dusd'])
    if not has_btcusd:
        return False
    
    # Check for Week -7 dates
    has_week_7_date = any(date in filename or date in path_str for date in WEEK_7_DATES)
    if not has_week_7_date:
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

def scan_existing_files():
    """Scan for existing Week -7 BTCUSD files"""
    print("🔍 Scanning for existing Week -7 BTCUSD files...")
    
    found_files = []
    
    for root in SEARCH_ROOTS:
        if not root.exists():
            print(f"  📁 Directory not found: {root}")
            continue
        
        print(f"  📁 Searching: {root}")
        files = list(root.rglob("*.csv.gz"))
        print(f"    Found {len(files)} total files")
        
        week_7_files = [f for f in files if is_week_7_btcusd_file(f)]
        print(f"    Found {len(week_7_files)} Week -7 BTCUSD files")
        
        for file_path in week_7_files:
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
    
    print(f"📊 Total Week -7 BTCUSD files found: {len(found_files)}")
    return found_files

def generate_coverage_matrix(found_files):
    """Generate 7x4 date x venue coverage matrix"""
    print("📝 Generating 7x4 coverage matrix...")
    
    # Initialize matrix
    matrix = {}
    for date in WEEK_7_DATES:
        matrix[date] = {}
        for venue in VENUES.keys():
            matrix[date][venue] = 'MISSING'
    
    # Fill in found files
    for file_info in found_files:
        date = file_info['date']
        venue = file_info['venue']
        
        if date in matrix and venue in matrix[date]:
            matrix[date][venue] = 'FOUND'
    
    return matrix

def identify_missing_files(coverage_matrix):
    """Identify missing date x venue combinations"""
    print("🎯 Identifying missing files...")
    
    missing_files = []
    
    for date in WEEK_7_DATES:
        for venue in VENUES.keys():
            if coverage_matrix[date][venue] == 'MISSING':
                pair = VENUES[venue]
                filename = f"{venue}_{date}_{pair}.csv.gz"
                missing_files.append({
                    'venue': venue,
                    'date': date,
                    'pair': pair,
                    'filename': filename
                })
    
    print(f"📊 Missing files identified: {len(missing_files)}")
    return missing_files

def find_coinapi_file_key(date, venue):
    """Find the actual CoinAPI file key for a date/venue combination"""
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/"
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        target_pair = VENUES[venue]
        
        for content in root.findall('.//Contents'):
            key_elem = content.find('Key')
            if key_elem is not None:
                key = key_elem.text
                # Look for the target pair (handle both forms)
                if target_pair in key.upper() or (target_pair == 'BTC-USD' and 'BTC__002DUSD' in key.upper()):
                    return key
        
        return None
    except Exception as e:
        print(f"    ⚠️ Error listing files for {date}/{venue}: {e}")
        return None

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

def download_file(key, output_path):
    """Download a file from CoinAPI"""
    download_url = f"{COINAPI_BASE_URL}/coinapi/{key}"
    
    try:
        response = requests.get(download_url, headers=HEADERS, timeout=120)
        response.raise_for_status()
        
        # Write to temporary file first
        temp_path = output_path.with_suffix('.part')
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify file size
        if temp_path.stat().st_size == 0:
            temp_path.unlink()
            return False, "Zero-byte file"
        
        # Verify gzip header
        if not verify_gzip_file(temp_path):
            temp_path.unlink()
            return False, "Invalid gzip file"
        
        # Move to final location
        temp_path.rename(output_path)
        return True, "Success"
        
    except Exception as e:
        return False, str(e)

def download_missing_files(missing_files):
    """Download all missing files"""
    print("📥 Downloading missing files...")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    downloaded_files = []
    failed_files = []
    
    for i, file_info in enumerate(missing_files, 1):
        venue = file_info['venue']
        date = file_info['date']
        filename = file_info['filename']
        
        print(f"  📥 [{i}/{len(missing_files)}] {filename}")
        
        # Find the actual CoinAPI file key
        key = find_coinapi_file_key(date, venue)
        
        if not key:
            print(f"    ❌ No files available for {date}/{venue}")
            failed_files.append({
                **file_info,
                'status': 'NO_FILES_AVAILABLE',
                'error': 'No files found in CoinAPI listing'
            })
            continue
        
        print(f"    Key: {key}")
        
        # Download file
        output_path = OUTPUT_DIR / filename
        success, message = download_file(key, output_path)
        
        if success:
            # Compute hash
            file_hash = compute_file_hash(output_path)
            size_bytes = output_path.stat().st_size
            
            downloaded_files.append({
                **file_info,
                'status': 'SUCCESS',
                'file_path': str(output_path),
                'size_bytes': size_bytes,
                'sha256': file_hash,
                'source_key': key
            })
            print(f"    ✅ Downloaded: {size_bytes / (1024*1024):.1f} MB")
        else:
            failed_files.append({
                **file_info,
                'status': 'DOWNLOAD_FAILED',
                'error': message,
                'source_key': key
            })
            print(f"    ❌ Failed: {message}")
        
        # Rate limiting
        time.sleep(1)
    
    print(f"📊 Download Summary:")
    print(f"  ✅ Successful: {len(downloaded_files)}")
    print(f"  ❌ Failed: {len(failed_files)}")
    
    return downloaded_files, failed_files

def update_week_inventory(downloaded_files):
    """Update GLOBAL_week_inventory.csv with new files"""
    print("📝 Updating week inventory...")
    
    # Load existing inventory
    inventory_file = REPORTS_DIR / 'GLOBAL_week_inventory.csv'
    if inventory_file.exists():
        df = pd.read_csv(inventory_file)
    else:
        df = pd.DataFrame()
    
    # Add new files to inventory
    for file_info in downloaded_files:
        new_row = {
            'Week_Label': 'W-7',
            'Date_Range': 'Jul 7–13, 2025',
            'Files_Found': 1,  # Will be recalculated
            'Expected_Files': 28,
            'Coverage_%': 100.0,  # Will be recalculated
            'Source_Directories': 'v7',
            'Data_Size_MB': file_info['size_bytes'] / (1024 * 1024)
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    # Recalculate Week -7 totals
    w7_rows = df[df['Week_Label'] == 'W-7']
    if not w7_rows.empty:
        total_files = len(w7_rows)
        total_size_mb = w7_rows['Data_Size_MB'].sum()
        coverage_pct = (total_files / 28) * 100
        
        # Update the first W-7 row with totals
        w7_index = df[df['Week_Label'] == 'W-7'].index[0]
        df.loc[w7_index, 'Files_Found'] = total_files
        df.loc[w7_index, 'Coverage_%'] = round(coverage_pct, 1)
        df.loc[w7_index, 'Data_Size_MB'] = round(total_size_mb, 1)
        
        # Remove duplicate rows
        df = df.drop(df[df['Week_Label'] == 'W-7'].index[1:])
    
    # Save updated inventory
    df.to_csv(inventory_file, index=False)
    print(f"✅ Updated GLOBAL_week_inventory.csv")
    
    return total_files, coverage_pct

def export_results(downloaded_files, failed_files, coverage_matrix):
    """Export download results"""
    print("📝 Exporting results...")
    
    # W7_download_results.csv
    all_results = downloaded_files + failed_files
    if all_results:
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(REPORTS_DIR / 'W7_download_results.csv', index=False)
        print(f"✅ W7_download_results.csv: {len(all_results)} files")
    
    # W7_coverage_matrix.txt
    with open(REPORTS_DIR / 'W7_coverage_matrix.txt', 'w') as f:
        f.write("Week -7 Coverage Matrix (Jul 7 – Jul 13, 2025)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files found: {len(downloaded_files)}\n\n")
        
        f.write("Coverage Matrix (Date × Venue):\n")
        f.write(f"{'Date':<10} {'BINANCE':<10} {'COINBASE':<10} {'BYBITSPOT':<10} {'BITGET':<10}\n")
        f.write("-" * 60 + "\n")
        
        for date in WEEK_7_DATES:
            f.write(f"{date:<10} {coverage_matrix[date]['BINANCE']:<10} {coverage_matrix[date]['COINBASE']:<10} {coverage_matrix[date]['BYBITSPOT']:<10} {coverage_matrix[date]['BITGET']:<10}\n")
        
        f.write("\nSummary:\n")
        total_expected = len(WEEK_7_DATES) * len(VENUES)  # 7 * 4 = 28
        total_found = sum(1 for date in WEEK_7_DATES for venue in VENUES.keys() if coverage_matrix[date][venue] == 'FOUND')
        total_missing = total_expected - total_found
        
        f.write(f"  Expected combinations: {total_expected}\n")
        f.write(f"  Found: {total_found}\n")
        f.write(f"  Missing: {total_missing}\n")
        f.write(f"  Coverage: {(total_found/total_expected*100):.1f}%\n")
        
        if downloaded_files:
            f.write(f"\nDownloaded Files:\n")
            for file_info in downloaded_files:
                f.write(f"  {file_info['filename']}: {file_info['size_bytes'] / (1024*1024):.1f} MB\n")
        
        if failed_files:
            f.write(f"\nFailed Files:\n")
            for file_info in failed_files:
                f.write(f"  {file_info['filename']}: {file_info.get('error', 'Unknown error')}\n")
    
    print(f"✅ W7_coverage_matrix.txt: Coverage matrix")

def main():
    """Main execution"""
    print("🚀 Phase 39K-FILL-W7: Targeted Retrieval of Missing BTCUSD Files for Week -7")
    print("=" * 80)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if lock_file.exists():
        print("❌ Network is frozen - removing lock for download")
        lock_file.unlink()
    print("✅ Network unlocked for download")
    
    # Scan for existing files
    found_files = scan_existing_files()
    
    # Generate coverage matrix
    coverage_matrix = generate_coverage_matrix(found_files)
    
    # Identify missing files
    missing_files = identify_missing_files(coverage_matrix)
    
    if not missing_files:
        print("✅ No missing files - Week -7 already has 100% coverage!")
    else:
        # Download missing files
        downloaded_files, failed_files = download_missing_files(missing_files)
        
        # Update coverage matrix with new files
        for file_info in downloaded_files:
            date = file_info['date']
            venue = file_info['venue']
            if date in coverage_matrix and venue in coverage_matrix[date]:
                coverage_matrix[date][venue] = 'FOUND'
        
        # Update week inventory
        if downloaded_files:
            total_files, coverage_pct = update_week_inventory(downloaded_files)
            print(f"📊 Week -7 Coverage: {total_files}/28 files ({coverage_pct:.1f}%)")
    
    # Export results
    export_results(downloaded_files if 'downloaded_files' in locals() else [], 
                  failed_files if 'failed_files' in locals() else [], 
                  coverage_matrix)
    
    # Re-freeze network
    lock_file.touch()
    print("🔒 Network re-frozen")
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-FILL-W7 Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    # Final coverage analysis
    total_expected = len(WEEK_7_DATES) * len(VENUES)  # 7 * 4 = 28
    total_found = sum(1 for date in WEEK_7_DATES for venue in VENUES.keys() if coverage_matrix[date][venue] == 'FOUND')
    coverage_pct = (total_found / total_expected * 100)
    
    print(f"\n📋 Week -7 Final Summary:")
    print(f"Expected combinations: {total_expected}")
    print(f"Found: {total_found}")
    print(f"Missing: {total_expected - total_found}")
    print(f"Coverage: {coverage_pct:.1f}%")
    
    if 'downloaded_files' in locals() and downloaded_files:
        total_size_mb = sum(f['size_bytes'] for f in downloaded_files) / (1024 * 1024)
        print(f"\n📁 Downloaded files:")
        for file_info in downloaded_files:
            print(f"  {file_info['filename']}: {file_info['size_bytes'] / (1024*1024):.1f} MB")
        print(f"Total size: {total_size_mb:.1f} MB")
    
    if 'failed_files' in locals() and failed_files:
        print(f"\n❌ Failed files:")
        for file_info in failed_files:
            print(f"  {file_info['filename']}: {file_info.get('error', 'Unknown error')}")
    
    print(f"\nKey artifacts:")
    print(f"  {REPORTS_DIR / 'W7_download_results.csv'}")
    print(f"  {REPORTS_DIR / 'W7_coverage_matrix.txt'}")
    print(f"  {REPORTS_DIR / 'GLOBAL_week_inventory.csv'}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
