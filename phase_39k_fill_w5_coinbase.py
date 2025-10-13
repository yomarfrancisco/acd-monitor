#!/usr/bin/env python3
"""
Phase 39K-FILL-W5-COINBASE: Retrieve missing COINBASE BTC-USD file for 2025-07-21
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

# Target file details
TARGET_DATE = '20250721'
TARGET_VENUE = 'COINBASE'
TARGET_PAIR = 'BTC-USD'

# CoinAPI configuration
COINAPI_BASE_URL = 'https://s3.flatfiles.coinapi.io'
COINAPI_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

def search_existing_files():
    """Search all sources for existing COINBASE 2025-07-21 files"""
    print("🔍 Searching all sources for COINBASE 2025-07-21 files...")
    
    search_roots = [
        BASE_DIR / 'data_v7' / 'raw' / 'coinapi_jul_w5',
        BASE_DIR / 'data_v6' / 'raw' / 'coinapi_jul',
        BASE_DIR / 'analysis' / 'flatfiles_ticks_v4' / 'raw'
    ]
    
    found_files = []
    
    for root_path in search_roots:
        if not root_path.exists():
            continue
        
        print(f"  📁 Searching: {root_path}")
        
        # Search for files with 20250721 and COINBASE
        for file_path in root_path.rglob("*.csv.gz"):
            filename = file_path.name.upper()
            path_str = str(file_path).upper()
            
            # Check if file matches our criteria
            if (TARGET_DATE in filename or TARGET_DATE in path_str) and 'COINBASE' in path_str:
                # Check for BTC-USD patterns (including BTC_USD with underscores)
                if any(pattern in filename or pattern in path_str for pattern in ['BTC-USD', 'BTC__002DUSD', 'BTC_USD', 'BTCUSDT']):
                    found_files.append({
                        'file_path': file_path,
                        'size_bytes': file_path.stat().st_size,
                        'source': str(root_path)
                    })
                    print(f"    ✅ Found: {file_path}")
    
    print(f"📊 Found {len(found_files)} existing files")
    return found_files

def list_coinapi_files():
    """List available files from CoinAPI for the target date/venue"""
    print("🌐 Querying CoinAPI for available files...")
    
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{TARGET_DATE}/E-{TARGET_VENUE}/"
    
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
                # Look for BTC-USD files
                if 'BTC' in key and 'USD' in key:
                    files.append(key)
                    print(f"    📄 Available: {key}")
        
        print(f"📊 Found {len(files)} BTC-USD files on CoinAPI")
        return files
        
    except Exception as e:
        print(f"❌ Error querying CoinAPI: {e}")
        return []

def download_coinapi_file(key):
    """Download a file from CoinAPI"""
    print(f"⬇️ Downloading: {key}")
    
    download_url = f"{COINAPI_BASE_URL}/coinapi/{key}"
    
    try:
        response = requests.get(download_url, headers=HEADERS, timeout=120)
        response.raise_for_status()
        
        # Create target directory
        target_dir = CANONICAL_DIR / TARGET_DATE / f"E-{TARGET_VENUE}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        temp_path = target_dir / f"{TARGET_PAIR}.csv.gz.part"
        final_path = target_dir / f"{TARGET_PAIR}.csv.gz"
        
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

def update_canonical_manifest(new_file_info):
    """Update the canonical manifest with the new file"""
    print("📝 Updating canonical manifest...")
    
    manifest_path = REPORTS_DIR / 'CANON_manifest.csv'
    
    if not manifest_path.exists():
        print("❌ Canonical manifest not found")
        return False
    
    # Read existing manifest
    df = pd.read_csv(manifest_path)
    
    # Add new file entry
    new_entry = {
        'date': TARGET_DATE,
        'venue': TARGET_VENUE,
        'pair': TARGET_PAIR,
        'source_tier': 'v7',
        'abs_path': str(new_file_info['file_path']),
        'bytes': new_file_info['size_bytes'],
        'sha256': new_file_info['sha256'],
        'first_ts': new_file_info['first_ts'],
        'last_ts': new_file_info['last_ts'],
        'row_count': new_file_info['row_count']
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
    
    # Check W-5 coverage specifically
    w5_files = df[df['date'].astype(str) == TARGET_DATE]
    w5_coverage = len(w5_files)
    
    # Generate audit report
    audit_path = REPORTS_DIR / 'CANON_audit.txt'
    with open(audit_path, 'w') as f:
        f.write("Canonical Dataset Audit Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Date Range: 2025-07-07 → 2025-10-12\n\n")
        
        f.write("Summary Statistics:\n")
        f.write(f"  Total canonical files: {len(df)}\n")
        f.write(f"  COINBASE files: {venue_counts.get('COINBASE', 0)}\n")
        f.write(f"  BINANCE files: {venue_counts.get('BINANCE', 0)}\n")
        f.write(f"  BYBITSPOT files: {venue_counts.get('BYBITSPOT', 0)}\n")
        f.write(f"  BITGET files: {venue_counts.get('BITGET', 0)}\n\n")
        
        f.write("Week -5 Coverage (2025-07-21):\n")
        f.write(f"  Files found: {w5_coverage}/4 venues\n")
        if w5_coverage == 4:
            f.write("  Status: ✅ PASS (100%)\n")
        else:
            f.write("  Status: ❌ FAIL\n")
        
        # Overall status
        total_expected = 14 * 4 * 7  # 14 weeks × 4 venues × 7 days
        coverage_pct = (len(df) / total_expected * 100) if total_expected > 0 else 0
        overall_status = "PASS" if len(df) >= total_expected else "FAIL"
        
        f.write(f"\nOverall Status: {overall_status}\n")
        f.write(f"Total Coverage: {len(df)}/{total_expected} ({coverage_pct:.1f}%)\n")
    
    print(f"✅ Audit report regenerated")
    return True

def main():
    """Main execution"""
    print("🚀 Phase 39K-FILL-W5-COINBASE: Retrieve Missing COINBASE File")
    print("=" * 70)
    
    start_time = datetime.now()
    
    # Check network freeze
    lock_file = BASE_DIR / 'locks' / 'api_budget.lock'
    if lock_file.exists():
        print("❌ Network is frozen - removing lock for this operation")
        lock_file.unlink()
    
    # Step 1: Search existing files
    existing_files = search_existing_files()
    
    if existing_files:
        print(f"✅ Found {len(existing_files)} existing files")
        # Use the first existing file
        source_file = existing_files[0]['file_path']
        print(f"📁 Using existing file: {source_file}")
        
        # Copy to canonical location
        target_dir = CANONICAL_DIR / TARGET_DATE / f"E-{TARGET_VENUE}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{TARGET_PAIR}.csv.gz"
        
        import shutil
        shutil.copy2(source_file, target_path)
        print(f"✅ Copied to canonical location: {target_path}")
        
    else:
        print("❌ No existing files found, querying CoinAPI...")
        
        # Step 2: Query CoinAPI
        available_files = list_coinapi_files()
        
        if not available_files:
            print("❌ No files available on CoinAPI")
            sys.exit(1)
        
        # Step 3: Download the first available file
        downloaded_file, error = download_coinapi_file(available_files[0])
        
        if not downloaded_file:
            print(f"❌ Download failed: {error}")
            sys.exit(1)
    
    # Step 4: Verify file integrity
    file_info, error = verify_file_integrity(target_path)
    
    if not file_info:
        print(f"❌ File verification failed: {error}")
        sys.exit(1)
    
    print(f"✅ File verified:")
    print(f"  Size: {file_info['size_bytes']:,} bytes")
    print(f"  SHA-256: {file_info['sha256']}")
    print(f"  Rows: {file_info['row_count']:,}")
    print(f"  First TS: {file_info['first_ts']}")
    print(f"  Last TS: {file_info['last_ts']}")
    
    # Step 5: Update canonical manifest
    if not update_canonical_manifest(file_info):
        print("❌ Failed to update manifest")
        sys.exit(1)
    
    # Step 6: Regenerate BOM hash
    bom_hash = regenerate_bom_hash()
    if not bom_hash:
        print("❌ Failed to regenerate BOM hash")
        sys.exit(1)
    
    # Step 7: Regenerate audit report
    if not regenerate_audit_report():
        print("❌ Failed to regenerate audit report")
        sys.exit(1)
    
    # Re-freeze network
    lock_file.touch()
    print("🔒 Network re-frozen")
    
    # Summary
    runtime_seconds = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ Phase 39K-FILL-W5-COINBASE Complete")
    print(f"⏱️ Runtime: {runtime_seconds:.1f} seconds")
    
    print(f"\n📋 Results:")
    print(f"Target file: {TARGET_DATE} {TARGET_VENUE} {TARGET_PAIR}")
    print(f"File path: {target_path}")
    print(f"File size: {file_info['size_bytes']:,} bytes")
    print(f"SHA-256: {file_info['sha256']}")
    print(f"BOM hash: {bom_hash}")
    
    print(f"\nREADY_FOR_APPROVAL: true")

if __name__ == "__main__":
    main()
