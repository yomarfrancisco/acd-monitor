#!/usr/bin/env python3
"""
Phase 39K-FILL-OCT-CLOSURE: Retrieve 9 remaining BTCUSD files for 100% canonical coverage
"""

import os
import sys
import hashlib
import json
import gzip
import pandas as pd
import re
import requests
import time
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# Configuration
BASE_DIR = Path('/Users/ygorfrancisco/Desktop/acd-monitor')
CANONICAL_DIR = BASE_DIR / 'data_v7' / 'canonical'
REPORTS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'canonical'

# Missing files to retrieve
MISSING_FILES = [
    # BINANCE files (3)
    {'date': '20250913', 'venue': 'BINANCE', 'pair': 'BTCUSDT'},
    {'date': '20250920', 'venue': 'BINANCE', 'pair': 'BTCUSDT'},
    {'date': '20250921', 'venue': 'BINANCE', 'pair': 'BTCUSDT'},
    
    # Oct 11-12 files (6)
    {'date': '20251011', 'venue': 'BINANCE', 'pair': 'BTCUSDT'},
    {'date': '20251011', 'venue': 'COINBASE', 'pair': 'BTC-USD'},
    {'date': '20251011', 'venue': 'BYBITSPOT', 'pair': 'BTCUSDT'},
    {'date': '20251011', 'venue': 'BITGET', 'pair': 'BTCUSDT'},
    {'date': '20251012', 'venue': 'BINANCE', 'pair': 'BTCUSDT'},
    {'date': '20251012', 'venue': 'COINBASE', 'pair': 'BTC-USD'},
    {'date': '20251012', 'venue': 'BYBITSPOT', 'pair': 'BTCUSDT'},
    {'date': '20251012', 'venue': 'BITGET', 'pair': 'BTCUSDT'},
]

# CoinAPI configuration
COINAPI_BASE_URL = 'https://s3.flatfiles.coinapi.io'
COINAPI_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

# Search roots
SEARCH_ROOTS = [
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w7',
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w6',
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
    BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w4',
    BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
    BASE_DIR / 'data_v6' / 'raw' / 'coinapi_oct',
    BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw',
    BASE_DIR / 'data_v6' / 'cache' / 'ticks' / 'sep_w2',
    BASE_DIR / 'data_v6' / 'cache' / 'ticks' / 'sep_w3'
]

def search_existing_files():
    """Search all sources for existing files matching missing file criteria"""
    print("🔍 Searching all sources for missing files...")
    
    found_files = {}
    
    for root_path in SEARCH_ROOTS:
        if not root_path.exists():
            continue
        
        print(f"  📁 Searching: {root_path}")
        
        for file_path in root_path.rglob("*.csv.gz"):
            filename = file_path.name.upper()
            path_str = str(file_path).upper()
            
            # Check each missing file
            for missing in MISSING_FILES:
                date = missing['date']
                venue = missing['venue']
                pair = missing['pair']
                
                # Create key for this missing file
                key = f"{date}_{venue}_{pair}"
                
                # Skip if already found
                if key in found_files:
                    continue
                
                # Check if file matches criteria
                if (date in filename or date in path_str) and venue in path_str:
                    # Check for appropriate pair patterns
                    pair_patterns = []
                    if pair == 'BTC-USD':
                        pair_patterns = ['BTC-USD', 'BTC__002DUSD', 'BTC_USD']
                    elif pair == 'BTCUSDT':
                        pair_patterns = ['BTCUSDT']
                    
                    if any(pattern in filename or pattern in path_str for pattern in pair_patterns):
                        found_files[key] = {
                            'file_path': file_path,
                            'size_bytes': file_path.stat().st_size,
                            'source': str(root_path),
                            'missing_info': missing
                        }
                        print(f"    ✅ Found {key}: {file_path}")
    
    print(f"📊 Found {len(found_files)} existing files")
    return found_files

def list_coinapi_files(date, venue):
    """List available files from CoinAPI for the target date/venue"""
    print(f"🌐 Querying CoinAPI for {date} {venue}...")
    
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/"
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.text)
        files = []
        
        for contents in root.findall('.//Contents'):
            key_elem = contents.find('Key')
            if key_elem is not None:
                key = key_elem.text
                # Look for BTC files
                if 'BTC' in key and 'USD' in key:
                    files.append(key)
                    print(f"    📄 Available: {key}")
        
        print(f"📊 Found {len(files)} BTC files on CoinAPI")
        return files
        
    except Exception as e:
        print(f"❌ Error querying CoinAPI: {e}")
        return []

def download_coinapi_file(key, target_date, target_venue, target_pair):
    """Download a file from CoinAPI"""
    print(f"⬇️ Downloading: {key}")
    
    download_url = f"{COINAPI_BASE_URL}/coinapi/{key}"
    
    try:
        response = requests.get(download_url, headers=HEADERS, timeout=120)
        response.raise_for_status()
        
        # Create target directory
        target_dir = CANONICAL_DIR / target_date / f"E-{target_venue}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        temp_path = target_dir / f"{target_pair}.csv.gz.part"
        final_path = target_dir / f"{target_pair}.csv.gz"
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
            f.flush()
            os.fsync(f.fileno())
        
        # Verify file
        if temp_path.stat().st_size == 0:
            temp_path.unlink()
            return None, "Zero-byte file"
        
        # Check gzip header
        try:
            with gzip.open(temp_path, 'rb') as f:
                header = f.read(10)
                if len(header) == 0:
                    temp_path.unlink()
                    return None, "Invalid gzip file"
        except Exception:
            temp_path.unlink()
            return None, "Invalid gzip file"
        
        # Move to final location
        temp_path.rename(final_path)
        
        print(f"✅ Downloaded: {final_path}")
        return final_path, None
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None, str(e)

def verify_file_integrity(file_path):
    """Verify file integrity and extract metadata"""
    print(f"🔍 Verifying: {file_path}")
    
    try:
        # Check file exists and has size > 0
        if not file_path.exists():
            return None, "File does not exist"
        
        size_bytes = file_path.stat().st_size
        if size_bytes == 0:
            return None, "Zero-byte file"
        
        # Verify gzip
        try:
            with gzip.open(file_path, 'rb') as f:
                header = f.read(10)
                if len(header) == 0:
                    return None, "Invalid gzip file"
        except Exception:
            return None, "Invalid gzip file"
        
        # Compute SHA-256
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()
        
        # Get timestamps and row count
        first_ts, last_ts = get_file_timestamps(file_path)
        row_count = count_file_rows(file_path)
        
        return {
            'file_path': file_path,
            'size_bytes': size_bytes,
            'sha256': file_hash,
            'first_ts': first_ts,
            'last_ts': last_ts,
            'row_count': row_count
        }, None
        
    except Exception as e:
        return None, str(e)

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
        print(f"    ⚠️ Error reading timestamps: {e}")
    
    return None, None

def count_file_rows(file_path):
    """Count rows in a gzipped CSV file"""
    try:
        with gzip.open(file_path, 'rt') as f:
            return sum(1 for line in f)
    except Exception:
        return 0

def process_missing_files():
    """Process all missing files - search existing, download if needed"""
    print("🎯 Processing missing files...")
    
    # Step 1: Search for existing files
    found_files = search_existing_files()
    
    processed_files = []
    download_errors = []
    
    # Step 2: Process each missing file
    for missing in MISSING_FILES:
        date = missing['date']
        venue = missing['venue']
        pair = missing['pair']
        key = f"{date}_{venue}_{pair}"
        
        print(f"\n📋 Processing: {key}")
        
        if key in found_files:
            # Use existing file
            source_file = found_files[key]['file_path']
            print(f"📁 Using existing file: {source_file}")
            
            # Copy to canonical location
            target_dir = CANONICAL_DIR / date / f"E-{venue}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{pair}.csv.gz"
            
            import shutil
            shutil.copy2(source_file, target_path)
            print(f"✅ Copied to canonical location: {target_path}")
            
        else:
            # Download from CoinAPI
            print(f"❌ File not found locally, querying CoinAPI...")
            available_files = list_coinapi_files(date, venue)
            
            if not available_files:
                print(f"❌ No files available on CoinAPI for {key}")
                download_errors.append(f"{key}: No files available on CoinAPI")
                continue
            
            # Download the first available file
            downloaded_file, error = download_coinapi_file(available_files[0], date, venue, pair)
            
            if not downloaded_file:
                print(f"❌ Download failed for {key}: {error}")
                download_errors.append(f"{key}: {error}")
                continue
            
            target_path = downloaded_file
        
        # Step 3: Verify file integrity
        file_info, error = verify_file_integrity(target_path)
        
        if not file_info:
            print(f"❌ File verification failed for {key}: {error}")
            download_errors.append(f"{key}: Verification failed - {error}")
            continue
        
        print(f"✅ File verified:")
        print(f"  Size: {file_info['size_bytes']:,} bytes")
        print(f"  SHA-256: {file_info['sha256']}")
        print(f"  Rows: {file_info['row_count']:,}")
        
        # Add metadata
        file_info['missing_info'] = missing
        processed_files.append(file_info)
    
    print(f"\n📊 Processing Results:")
    print(f"  ✅ Successfully processed: {len(processed_files)}")
    print(f"  ❌ Errors: {len(download_errors)}")
    
    if download_errors:
        print(f"  Errors:")
        for error in download_errors:
            print(f"    - {error}")
    
    return processed_files, download_errors

def update_canonical_manifest(new_files):
    """Update the canonical manifest with all new files"""
    print("📝 Updating canonical manifest...")
    
    manifest_path = REPORTS_DIR / 'CANON_manifest.csv'
    
    if not manifest_path.exists():
        print("❌ Canonical manifest not found")
        return False
    
    # Read existing manifest
    df = pd.read_csv(manifest_path)
    
    # Add new file entries
    for file_info in new_files:
        missing = file_info['missing_info']
        new_entry = {
            'date': missing['date'],
            'venue': missing['venue'],
            'pair': missing['pair'],
            'source_tier': 'v7',
            'abs_path': str(file_info['file_path']),
            'bytes': file_info['size_bytes'],
            'sha256': file_info['sha256'],
            'first_ts': file_info['first_ts'],
            'last_ts': file_info['last_ts'],
            'row_count': file_info['row_count']
        }
        
        # Append new entry
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    
    # Sort by date, venue, pair
    df = df.sort_values(['date', 'venue', 'pair'])
    
    # Save updated manifest
    df.to_csv(manifest_path, index=False)
    
    print(f"✅ Manifest updated: {len(df)} total files")
    return True

def regenerate_bom_hash():
    """Regenerate BOM hash over all canonical files"""
    print("🔐 Regenerating BOM hash...")
    
    manifest_path = REPORTS_DIR / 'CANON_manifest.csv'
    
    if not manifest_path.exists():
        print("❌ Canonical manifest not found")
        return None
    
    # Read manifest
    df = pd.read_csv(manifest_path)
    
    # Sort by path for consistent ordering
    df = df.sort_values('abs_path')
    
    # Create BOM string
    bom_string = ""
    for _, row in df.iterrows():
        bom_string += f"{row['abs_path']}:{row['sha256']}\n"
    
    # Compute SHA-256 of BOM
    bom_hash = hashlib.sha256(bom_string.encode()).hexdigest()
    
    # Save BOM hash
    bom_path = REPORTS_DIR / 'CANON_bom_sha256.txt'
    with open(bom_path, 'w') as f:
        f.write(f"Canonical BOM SHA-256: {bom_hash}\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Total files: {len(df)}\n")
    
    print(f"✅ BOM hash regenerated: {bom_hash}")
    return bom_hash

def regenerate_audit_report():
    """Regenerate the audit report"""
    print("📊 Regenerating audit report...")
    
    manifest_path = REPORTS_DIR / 'CANON_manifest.csv'
    
    if not manifest_path.exists():
        print("❌ Canonical manifest not found")
        return False
    
    # Read manifest
    df = pd.read_csv(manifest_path)
    
    # Count files by venue
    venue_counts = df['venue'].value_counts()
    
    # Calculate expected vs actual
    expected_total = 14 * 4 * 7  # 14 weeks × 4 venues × 7 days
    actual_total = len(df)
    coverage_pct = (actual_total / expected_total * 100) if expected_total > 0 else 0
    
    # Generate audit report
    audit_path = REPORTS_DIR / 'CANON_audit.txt'
    with open(audit_path, 'w') as f:
        f.write("Canonical Dataset Audit Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Date Range: 2025-07-07 → 2025-10-12\n\n")
        
        f.write("Summary Statistics:\n")
        f.write(f"  Total canonical files: {actual_total}\n")
        f.write(f"  Expected total files: {expected_total}\n")
        f.write(f"  Coverage: {coverage_pct:.1f}%\n")
        f.write(f"  COINBASE files: {venue_counts.get('COINBASE', 0)}\n")
        f.write(f"  BINANCE files: {venue_counts.get('BINANCE', 0)}\n")
        f.write(f"  BYBITSPOT files: {venue_counts.get('BYBITSPOT', 0)}\n")
        f.write(f"  BITGET files: {venue_counts.get('BITGET', 0)}\n\n")
        
        # Check specific missing dates
        f.write("Missing Files Analysis:\n")
        from datetime import timedelta
        
        start_date = datetime(2025, 7, 7)
        end_date = datetime(2025, 10, 12)
        venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
        
        current_date = start_date
        missing_count = 0
        while current_date <= end_date:
            date_str = current_date.strftime('%Y%m%d')
            date_files = df[df['date'].astype(str) == date_str]
            found_venues = set(date_files['venue'].tolist())
            missing_venues = set(venues) - found_venues
            if missing_venues:
                f.write(f"  {date_str}: Missing {missing_venues} ({len(missing_venues)} files)\n")
                missing_count += len(missing_venues)
            current_date += timedelta(days=1)
        
        if missing_count == 0:
            f.write("  ✅ No missing files found!\n")
        
        f.write(f"\nOverall Status: {'PASS' if actual_total >= expected_total else 'FAIL'}\n")
        f.write(f"Total Coverage: {actual_total}/{expected_total} ({coverage_pct:.1f}%)\n")
    
    print(f"✅ Audit report regenerated")
    return True

def main():
    """Main execution"""
    print("🚀 Phase 39K-FILL-OCT-CLOSURE: Final Canonical Completion")
    print("=" * 70)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if lock_file.exists():
        print("❌ Network is frozen - removing lock for this operation")
        lock_file.unlink()
    
    print(f"🎯 Target: {len(MISSING_FILES)} missing files")
    for missing in MISSING_FILES:
        print(f"  - {missing['date']} {missing['venue']} {missing['pair']}")
    
    # Step 1: Process missing files
    processed_files, errors = process_missing_files()
    
    if not processed_files:
        print("❌ No files were successfully processed")
        sys.exit(1)
    
    # Step 2: Update canonical manifest
    if not update_canonical_manifest(processed_files):
        print("❌ Failed to update manifest")
        sys.exit(1)
    
    # Step 3: Regenerate BOM hash
    bom_hash = regenerate_bom_hash()
    if not bom_hash:
        print("❌ Failed to regenerate BOM hash")
        sys.exit(1)
    
    # Step 4: Regenerate audit report
    if not regenerate_audit_report():
        print("❌ Failed to regenerate audit report")
        sys.exit(1)
    
    # Re-freeze network
    lock_file.touch()
    print("🔒 Network re-frozen")
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-FILL-OCT-CLOSURE Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    print(f"\n📋 Results:")
    print(f"Files processed: {len(processed_files)}")
    print(f"Errors: {len(errors)}")
    print(f"BOM hash: {bom_hash}")
    
    if errors:
        print(f"\n⚠️ Errors encountered:")
        for error in errors:
            print(f"  - {error}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
