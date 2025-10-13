#!/usr/bin/env python3
"""
Local verification for BITGET and BINANCE 2025-09-13 data
Source-to-canonical verification without CoinAPI calls
"""

import os
import sys
import pandas as pd
import gzip
import hashlib
import glob
from pathlib import Path

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def analyze_raw_csv(file_path):
    """Analyze raw CSV file"""
    try:
        # Get file size
        file_size_mb = os.path.getsize(file_path) / 1024 / 1024
        
        # Read CSV
        df = pd.read_csv(file_path, sep=';', compression='gzip')
        row_count = len(df)
        
        # Get timestamp range
        timestamps = pd.to_datetime(df['time_exchange'], utc=True)
        min_ts = timestamps.min()
        max_ts = timestamps.max()
        
        # Get price range
        prices = pd.to_numeric(df['price'], errors='coerce')
        min_price = prices.min()
        max_price = prices.max()
        
        # Compute SHA256
        sha256 = compute_file_hash(file_path)
        
        return {
            'file_size_mb': file_size_mb,
            'row_count': row_count,
            'min_ts': min_ts,
            'max_ts': max_ts,
            'min_price': min_price,
            'max_price': max_price,
            'sha256': sha256
        }
    except Exception as e:
        return {'error': str(e)}

def analyze_canonical_parquet(file_path):
    """Analyze canonical parquet file"""
    try:
        # Get file size
        file_size_mb = os.path.getsize(file_path) / 1024 / 1024
        
        # Read parquet
        df = pd.read_parquet(file_path)
        row_count = len(df)
        
        # Get timestamp range
        min_ts = df['ts'].min()
        max_ts = df['ts'].max()
        
        # Get price range
        min_price = df['price'].min()
        max_price = df['price'].max()
        
        # Get schema
        schema = list(df.columns)
        dtypes = df.dtypes.to_dict()
        
        return {
            'file_size_mb': file_size_mb,
            'row_count': row_count,
            'min_ts': min_ts,
            'max_ts': max_ts,
            'min_price': min_price,
            'max_price': max_price,
            'schema': schema,
            'dtypes': dtypes
        }
    except Exception as e:
        return {'error': str(e)}

def verify_bitget_20250913():
    """Verify BITGET 2025-09-13 data"""
    print("🔍 BITGET 2025-09-13 Verification")
    print("=" * 40)
    
    # Find raw file
    raw_pattern = "analysis/flatfiles_ticks_v4/raw/*BITGET*20250913*.csv.gz"
    raw_files = glob.glob(raw_pattern)
    
    if not raw_files:
        print("❌ No raw BITGET file found")
        return None
    
    raw_file = raw_files[0]
    print(f"📁 Raw file: {raw_file}")
    
    # Analyze raw file
    raw_data = analyze_raw_csv(raw_file)
    if 'error' in raw_data:
        print(f"❌ Error analyzing raw file: {raw_data['error']}")
        return None
    
    print(f"📊 Raw file analysis:")
    print(f"  Size: {raw_data['file_size_mb']:.2f} MB")
    print(f"  Rows: {raw_data['row_count']:,}")
    print(f"  Timestamps: {raw_data['min_ts']} → {raw_data['max_ts']}")
    print(f"  Price range: ${raw_data['min_price']:.2f} → ${raw_data['max_price']:.2f}")
    print(f"  SHA256: {raw_data['sha256'][:16]}...")
    
    # Find canonical file
    canonical_file = "data_v6/views/BITGET/20250913/ticks_canonical.parquet"
    
    if not os.path.exists(canonical_file):
        print("❌ No canonical BITGET file found")
        return None
    
    print(f"📁 Canonical file: {canonical_file}")
    
    # Analyze canonical file
    canonical_data = analyze_canonical_parquet(canonical_file)
    if 'error' in canonical_data:
        print(f"❌ Error analyzing canonical file: {canonical_data['error']}")
        return None
    
    print(f"📊 Canonical file analysis:")
    print(f"  Size: {canonical_data['file_size_mb']:.2f} MB")
    print(f"  Rows: {canonical_data['row_count']:,}")
    print(f"  Timestamps: {canonical_data['min_ts']} → {canonical_data['max_ts']}")
    print(f"  Price range: ${canonical_data['min_price']:.2f} → ${canonical_data['max_price']:.2f}")
    print(f"  Schema: {canonical_data['schema']}")
    
    # Compare raw vs canonical
    print(f"\n🔍 Comparison:")
    
    # Price range comparison (1 bp tolerance)
    price_min_diff = abs(raw_data['min_price'] - canonical_data['min_price'])
    price_max_diff = abs(raw_data['max_price'] - canonical_data['max_price'])
    price_match = price_min_diff <= 0.01 and price_max_diff <= 0.01
    
    print(f"  Price range match: {'✅' if price_match else '❌'} (diff: {price_min_diff:.4f}, {price_max_diff:.4f})")
    
    # Row count comparison (canonical should be <= raw)
    row_count_match = canonical_data['row_count'] <= raw_data['row_count']
    print(f"  Row count match: {'✅' if row_count_match else '❌'} (canonical ≤ raw)")
    
    # Timestamp range comparison
    ts_contained = (canonical_data['min_ts'] >= raw_data['min_ts'] and 
                   canonical_data['max_ts'] <= raw_data['max_ts'])
    print(f"  Timestamp containment: {'✅' if ts_contained else '❌'}")
    
    # Schema comparison
    expected_schema = ['ts', 'price', 'size', 'venue']
    schema_match = canonical_data['schema'] == expected_schema
    print(f"  Schema match: {'✅' if schema_match else '❌'} (expected: {expected_schema})")
    
    # Overall match
    overall_match = price_match and row_count_match and ts_contained and schema_match
    
    return {
        'raw': raw_data,
        'canonical': canonical_data,
        'price_match': price_match,
        'row_count_match': row_count_match,
        'ts_contained': ts_contained,
        'schema_match': schema_match,
        'overall_match': overall_match
    }

def check_binance_20250913():
    """Check for BINANCE 2025-09-13 data existence"""
    print(f"\n🔍 BINANCE 2025-09-13 Existence Check")
    print("=" * 40)
    
    # Search for raw files
    raw_pattern = "analysis/flatfiles_ticks_v4/raw/*BINANCE*20250913*.csv.gz"
    raw_files = glob.glob(raw_pattern)
    
    # Check canonical file
    canonical_file = "data_v6/views/BINANCE/20250913/ticks_canonical.parquet"
    canonical_exists = os.path.exists(canonical_file)
    
    results = []
    
    if raw_files:
        print(f"📁 Found {len(raw_files)} raw file(s):")
        for raw_file in raw_files:
            file_size_mb = os.path.getsize(raw_file) / 1024 / 1024
            try:
                df = pd.read_csv(raw_file, sep=';', compression='gzip')
                row_count = len(df)
            except:
                row_count = "Error reading"
            
            print(f"  {raw_file} ({file_size_mb:.2f} MB, {row_count:,} rows)")
            results.append({
                'location': 'Raw',
                'found': True,
                'size_mb': file_size_mb,
                'rows': row_count,
                'action': 'FOUND'
            })
    else:
        print("❌ No raw BINANCE files found")
        results.append({
            'location': 'Raw',
            'found': False,
            'size_mb': 0,
            'rows': 0,
            'action': 'NOT_FOUND'
        })
    
    if canonical_exists:
        canonical_size_mb = os.path.getsize(canonical_file) / 1024 / 1024
        try:
            df = pd.read_parquet(canonical_file)
            row_count = len(df)
        except:
            row_count = "Error reading"
        
        print(f"📁 Canonical file exists: {canonical_file} ({canonical_size_mb:.2f} MB, {row_count:,} rows)")
        results.append({
            'location': 'Canonical',
            'found': True,
            'size_mb': canonical_size_mb,
            'rows': row_count,
            'action': 'FOUND'
        })
    else:
        print("❌ No canonical BINANCE file found")
        results.append({
            'location': 'Canonical',
            'found': False,
            'size_mb': 0,
            'rows': 0,
            'action': 'NOT_FOUND'
        })
    
    return results

def main():
    """Main verification function"""
    print("🧩 Source-to-Canonical Verification (2025-09-13)")
    print("=" * 60)
    
    # Part 1: BITGET verification
    bitget_result = verify_bitget_20250913()
    
    if bitget_result:
        print(f"\n## BITGET 2025-09-13 Verification")
        print("| Source | Rows | Min ts | Max ts | Price Min→Max | SHA256 | Match? |")
        print("|--------|------|--------|--------|---------------|--------|--------|")
        
        raw = bitget_result['raw']
        canonical = bitget_result['canonical']
        
        print(f"| Raw | {raw['row_count']:,} | {raw['min_ts'].strftime('%H:%M:%S')} | {raw['max_ts'].strftime('%H:%M:%S')} | ${raw['min_price']:.2f}→${raw['max_price']:.2f} | {raw['sha256'][:8]}... | N/A |")
        print(f"| Canonical | {canonical['row_count']:,} | {canonical['min_ts'].strftime('%H:%M:%S')} | {canonical['max_ts'].strftime('%H:%M:%S')} | ${canonical['min_price']:.2f}→${canonical['max_price']:.2f} | N/A | {'✅' if bitget_result['overall_match'] else '❌'} |")
        
        print(f"\n**BITGET 2025-09-13 canonical = {'faithful' if bitget_result['overall_match'] else 'not faithful'} to raw source.**")
    
    # Part 2: BINANCE existence check
    binance_results = check_binance_20250913()
    
    print(f"\n## BINANCE 2025-09-13 Existence Check")
    print("| Location | Found? | Size (MB) | Rows | Action |")
    print("|----------|--------|-----------|------|--------|")
    
    for result in binance_results:
        found_symbol = "✅" if result['found'] else "❌"
        print(f"| {result['location']} | {found_symbol} | {result['size_mb']:.2f} | {result['rows']:,} | {result['action']} |")
    
    # Final summary
    raw_found = any(r['found'] for r in binance_results if r['location'] == 'Raw')
    canonical_found = any(r['found'] for r in binance_results if r['location'] == 'Canonical')
    
    if not raw_found and not canonical_found:
        print(f"\n**No BINANCE 2025-09-13 data present locally or canonically.**")
    else:
        print(f"\n**BINANCE 2025-09-13 data found in {'raw' if raw_found else ''} {'and/or' if raw_found and canonical_found else ''} {'canonical' if canonical_found else ''} form.**")

if __name__ == "__main__":
    main()




