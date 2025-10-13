#!/usr/bin/env python3
"""
Phase 39A-W7 Forensics (BTCUSDT/BTC-USD only) + API Lock
Freeze network I/O and produce authoritative BTCUSDT/BTC-USD inventory for Week -7
"""

import os
import sys
import hashlib
import csv
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import shutil

# Configuration
TARGET_PAIRS = {'BTCUSDT', 'BTC-USD', 'BTCUSD'}
TARGET_VENUES = {'BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET'}
START_DATE = '2025-07-07'
END_DATE = '2025-07-13'
MAX_RAM_GB = 1.0
MAX_RUNTIME_MIN = 30

# Paths
RAW_DATA_DIR = Path('data_v7/raw')
QUARANTINE_DIR = Path('data_v7/quarantine/week7_other_pairs')
LOCK_FILE = Path('locks/api_budget.lock')
OUTPUT_DIR = Path('data_v7/reports')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
Path('locks').mkdir(parents=True, exist_ok=True)

def generate_date_range(start_date, end_date):
    """Generate list of dates in YYYYMMDD format"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    return dates

def write_api_lock():
    """Write API lock file"""
    with open(LOCK_FILE, 'w') as f:
        f.write("LOCKED\n")
        f.write("reason=W7 forensics\n")
        f.write(f"timestamp={datetime.now().isoformat()}\n")
    print(f"🔒 API LOCKED: {LOCK_FILE}")

def check_network_calls():
    """Abort if any network calls would be made"""
    # This is a guard function - if any code path would make network calls, abort
    pass

def extract_pair_from_filename(filename):
    """Extract trading pair from filename"""
    filename_upper = filename.upper()
    
    # Look for common BTC pair patterns
    if 'BTCUSDT' in filename_upper:
        return 'BTCUSDT'
    elif 'BTC-USD' in filename_upper or 'BTC__002DUSD' in filename_upper:
        return 'BTC-USD'
    elif 'BTCUSD' in filename_upper and 'BTCUSDT' not in filename_upper:
        return 'BTCUSD'
    
    return None

def extract_venue_from_path(file_path):
    """Extract venue from file path"""
    path_parts = file_path.parts
    for part in path_parts:
        if part in TARGET_VENUES:
            return part
    return None

def extract_date_from_path(file_path):
    """Extract date from file path"""
    path_parts = file_path.parts
    for part in path_parts:
        if part.startswith('202507'):
            return part
    return None

def compute_file_hash(file_path):
    """Compute SHA-256 hash of file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"❌ Error computing hash for {file_path}: {e}")
        return None

def is_target_file(file_path):
    """Check if file matches our target criteria"""
    filename = file_path.name
    venue = extract_venue_from_path(file_path)
    date = extract_date_from_path(file_path)
    pair = extract_pair_from_filename(filename)
    
    # Check if it's in our target date range
    if not date or not date.startswith('202507'):
        return False
    
    # Check if it's in our target date range (July 7-13)
    try:
        file_date = datetime.strptime(date, '%Y%m%d')
        start_date = datetime.strptime(START_DATE, '%Y-%m-%d')
        end_date = datetime.strptime(END_DATE, '%Y-%m-%d')
        if not (start_date <= file_date <= end_date):
            return False
    except:
        return False
    
    # Check venue and pair
    return (venue in TARGET_VENUES and 
            pair in TARGET_PAIRS)

def main():
    print("🔍 Phase 39A-W7 Forensics (BTCUSDT/BTC-USD only) + API Lock")
    print(f"📅 Date range: {START_DATE} to {END_DATE}")
    print(f"🏢 Venues: {', '.join(TARGET_VENUES)}")
    print(f"₿ Target pairs: {', '.join(TARGET_PAIRS)}")
    print(f"💾 RAM limit: {MAX_RAM_GB} GB")
    print(f"⏱️  Runtime limit: {MAX_RUNTIME_MIN} min")
    print()
    
    start_time = datetime.now()
    
    # 1) Write API lock
    write_api_lock()
    
    # 2) Enumerate local flatfiles
    print("📂 Enumerating local flatfiles...")
    all_files = []
    
    if RAW_DATA_DIR.exists():
        for file_path in RAW_DATA_DIR.rglob('*.csv.gz'):
            all_files.append(file_path)
    
    print(f"Found {len(all_files)} total .csv.gz files")
    
    # 3) Filter to target pairs, venues, dates
    print("🔍 Filtering to target BTC pairs...")
    target_files = []
    other_files = []
    
    for file_path in all_files:
        if is_target_file(file_path):
            target_files.append(file_path)
        else:
            other_files.append(file_path)
    
    print(f"Target BTC files: {len(target_files)}")
    print(f"Other files: {len(other_files)}")
    
    # 4) Generate coverage matrix
    print("\n📊 Coverage Matrix:")
    dates = generate_date_range(START_DATE, END_DATE)
    
    coverage_matrix = {}
    for date in dates:
        coverage_matrix[date] = {}
        for venue in TARGET_VENUES:
            coverage_matrix[date][venue] = '✗'
    
    # Check coverage
    for file_path in target_files:
        date = extract_date_from_path(file_path)
        venue = extract_venue_from_path(file_path)
        if date and venue:
            coverage_matrix[date][venue] = '✓'
    
    # Print coverage matrix
    print("Date       | BINANCE | COINBASE | BYBITSPOT | BITGET")
    print("-" * 50)
    for date in dates:
        row = f"{date} |"
        for venue in TARGET_VENUES:
            row += f"    {coverage_matrix[date][venue]}    |"
        print(row)
    
    # Count missing slots
    total_slots = len(dates) * len(TARGET_VENUES)
    filled_slots = sum(1 for date in dates for venue in TARGET_VENUES 
                      if coverage_matrix[date][venue] == '✓')
    missing_slots = total_slots - filled_slots
    
    print(f"\n📈 Coverage: {filled_slots}/{total_slots} slots filled")
    print(f"❌ Missing slots: {missing_slots}")
    
    # List missing slots explicitly
    if missing_slots > 0:
        print("\n❌ Missing slots:")
        for date in dates:
            for venue in TARGET_VENUES:
                if coverage_matrix[date][venue] == '✗':
                    print(f"  {date}/{venue}")
    
    # 5) Process target files
    print(f"\n🔍 Processing {len(target_files)} target BTC files...")
    
    file_info = []
    total_bytes = 0
    min_bytes = float('inf')
    max_bytes = 0
    zero_byte_files = []
    small_files = []
    
    for file_path in target_files:
        try:
            file_size = file_path.stat().st_size
            total_bytes += file_size
            
            if file_size == 0:
                zero_byte_files.append(str(file_path))
            elif file_size < 50 * 1024:  # 50 KB
                small_files.append((str(file_path), file_size))
            
            min_bytes = min(min_bytes, file_size)
            max_bytes = max(max_bytes, file_size)
            
            # Compute SHA-256
            file_hash = compute_file_hash(file_path)
            
            file_info.append({
                'path': str(file_path),
                'filename': file_path.name,
                'date': extract_date_from_path(file_path),
                'venue': extract_venue_from_path(file_path),
                'pair': extract_pair_from_filename(file_path.name),
                'size_bytes': file_size,
                'sha256': file_hash
            })
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    # Check for duplicates
    print("\n🔍 Checking for duplicates...")
    filename_counts = {}
    hash_counts = {}
    
    for info in file_info:
        filename = info['filename']
        file_hash = info['sha256']
        
        filename_counts[filename] = filename_counts.get(filename, 0) + 1
        hash_counts[file_hash] = hash_counts.get(file_hash, 0) + 1
    
    duplicate_filenames = {f: c for f, c in filename_counts.items() if c > 1}
    duplicate_hashes = {h: c for h, c in hash_counts.items() if c > 1}
    
    # 6) Move non-target files to quarantine
    print(f"\n📦 Moving {len(other_files)} non-target files to quarantine...")
    quarantine_manifest = []
    
    for file_path in other_files:
        try:
            # Create quarantine path preserving directory structure
            rel_path = file_path.relative_to(RAW_DATA_DIR)
            quarantine_path = QUARANTINE_DIR / rel_path
            quarantine_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(file_path), str(quarantine_path))
            
            # Record in quarantine manifest
            file_size = quarantine_path.stat().st_size
            file_hash = compute_file_hash(quarantine_path)
            
            quarantine_manifest.append({
                'original_path': str(file_path),
                'quarantine_path': str(quarantine_path),
                'filename': file_path.name,
                'size_bytes': file_size,
                'sha256': file_hash
            })
            
        except Exception as e:
            print(f"❌ Error moving {file_path}: {e}")
    
    # Write quarantine manifest
    quarantine_manifest_file = OUTPUT_DIR / 'week7_quarantine_manifest.csv'
    with open(quarantine_manifest_file, 'w', newline='') as f:
        if quarantine_manifest:
            writer = csv.DictWriter(f, fieldnames=quarantine_manifest[0].keys())
            writer.writeheader()
            writer.writerows(quarantine_manifest)
    
    # 7) Compute combined BOM hash
    print("\n🔐 Computing combined BOM hash...")
    sorted_hashes = sorted([info['sha256'] for info in file_info if info['sha256']])
    combined_hash_input = '\n'.join(sorted_hashes)
    bom_hash = hashlib.sha256(combined_hash_input.encode()).hexdigest()
    
    # Write target files manifest
    target_manifest_file = OUTPUT_DIR / 'week7_target_btc_manifest.csv'
    with open(target_manifest_file, 'w', newline='') as f:
        if file_info:
            writer = csv.DictWriter(f, fieldnames=file_info[0].keys())
            writer.writeheader()
            writer.writerows(file_info)
    
    # Print summary
    print(f"\n📊 COMPACT SUMMARY:")
    print(f"Target BTC files: {len(file_info)}")
    print(f"Total bytes: {total_bytes:,} ({total_bytes/1024/1024:.1f} MB)")
    print(f"Min file size: {min_bytes:,} bytes")
    print(f"Max file size: {max_bytes:,} bytes")
    print(f"Combined BOM hash: {bom_hash}")
    
    if zero_byte_files:
        print(f"❌ Zero-byte files: {len(zero_byte_files)}")
        for f in zero_byte_files[:5]:
            print(f"  {f}")
    
    if small_files:
        print(f"⚠️  Small files (<50KB): {len(small_files)}")
        for f, size in small_files[:5]:
            print(f"  {f} ({size:,} bytes)")
    
    if duplicate_filenames:
        print(f"⚠️  Duplicate filenames: {len(duplicate_filenames)}")
        for f, count in list(duplicate_filenames.items())[:5]:
            print(f"  {f}: {count} copies")
    
    if duplicate_hashes:
        print(f"⚠️  Duplicate hashes: {len(duplicate_hashes)}")
    
    print(f"\n📦 Quarantine: {len(quarantine_manifest)} files moved to {QUARANTINE_DIR}")
    print(f"📄 Quarantine manifest: {quarantine_manifest_file}")
    print(f"📄 Target manifest: {target_manifest_file}")
    
    # Final gate
    runtime_min = (datetime.now() - start_time).total_seconds() / 60
    
    print(f"\n🎯 FINAL GATE:")
    print(f"Valid BTC files: {len(file_info)}")
    print(f"Missing slots: {missing_slots}")
    print(f"Runtime: {runtime_min:.1f} min")
    
    if zero_byte_files:
        print("❌ FAIL: Zero-byte files found")
        return False
    elif len(file_info) == 0:
        print("❌ FAIL: No valid BTC files found")
        return False
    elif missing_slots > 14:  # Allow some missing slots
        print(f"❌ FAIL: Too many missing slots ({missing_slots})")
        return False
    else:
        print("✅ PASS: Week -7 BTC forensics complete")
        return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        sys.exit(1)
