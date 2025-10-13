#!/usr/bin/env python3
"""
Fix Symbol Mismatch for Day 1 (2025-09-08)
Re-download BINANCE and COINBASE with correct symbols
"""

import os
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import hashlib
import shutil
from datetime import datetime

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    return os.environ.get('COINAPI_KEY', '7f036b38-38d6-4ed6-9fce-00a06280a0f6')

def list_coinapi_objects(venue, date):
    """List objects for venue/date"""
    list_url = f'https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/'
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key(),
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    try:
        response = requests.get(list_url, headers=headers, timeout=30)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

def download_coinapi_file(key, output_path):
    """Download file using Week 1 URL pattern"""
    full_url = f'https://s3.flatfiles.coinapi.io/coinapi/{key}'
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key(),
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    try:
        response = requests.get(full_url, headers=headers, timeout=60)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True, None, response.status_code
        else:
            return False, f"HTTP {response.status_code}", response.status_code
    except Exception as e:
        return False, str(e), None

def find_correct_symbol_file(venue, date, expected_symbol):
    """Find file with correct symbol"""
    status_code, xml_content = list_coinapi_objects(venue, date)
    if status_code != 200:
        return None, f"Failed to list objects: {status_code}"
    
    try:
        root = ET.fromstring(xml_content)
        
        # Find files with correct symbol
        correct_objects = []
        for content in root.findall('.//Contents'):
            key = content.find('Key').text
            size = int(content.find('Size').text)
            
            # Check for exact symbol match
            if expected_symbol in key.upper():
                correct_objects.append((key, size))
        
        if not correct_objects:
            return None, f"No files found with symbol {expected_symbol}"
        
        # Get the largest correct file
        largest_obj = max(correct_objects, key=lambda x: x[1])
        return largest_obj, None
        
    except Exception as e:
        return None, f"Error parsing XML: {e}"

def canonicalize_venue_data(file_path, venue, date):
    """Canonicalize venue data"""
    try:
        # Load and process in chunks
        chunk_size = 50000
        all_chunks = []
        
        for chunk in pd.read_csv(file_path, sep=';', compression='gzip', chunksize=chunk_size):
            # Convert to canonical format
            canonical_chunk = pd.DataFrame({
                'ts': pd.to_datetime(chunk['time_exchange'], utc=True),
                'price': pd.to_numeric(chunk['price'], errors='coerce'),
                'size': pd.to_numeric(chunk['base_amount'], errors='coerce'),
                'venue': venue
            })
            
            # Filter valid data
            canonical_chunk = canonical_chunk.dropna()
            canonical_chunk = canonical_chunk[
                (canonical_chunk['price'] > 0) & 
                (canonical_chunk['size'] > 0)
            ]
            
            if len(canonical_chunk) > 0:
                all_chunks.append(canonical_chunk)
        
        if not all_chunks:
            return None, "No valid data after processing"
        
        # Combine all chunks
        canonical_df = pd.concat(all_chunks, ignore_index=True)
        
        # Deduplicate
        initial_rows = len(canonical_df)
        canonical_df = canonical_df.drop_duplicates(subset=['ts', 'price', 'size'], keep='first')
        duplicates_removed = initial_rows - len(canonical_df)
        
        return canonical_df, duplicates_removed
        
    except Exception as e:
        return None, f"Error canonicalizing: {e}"

def fix_venue_symbol(venue, date, expected_symbol):
    """Fix symbol mismatch for a venue"""
    print(f"🔧 Fixing {venue} symbol mismatch...")
    
    # 1. Find correct file
    file_info, error = find_correct_symbol_file(venue, date, expected_symbol)
    if error:
        return False, error
    
    key, size = file_info
    print(f"  📁 Found correct file: {os.path.basename(key)} ({size:,} bytes)")
    
    # 2. Download correct file
    staging_path = f"analysis/flatfiles_ticks_v4/staging/{venue}/{date}/raw/{os.path.basename(key)}"
    success, error, http_status = download_coinapi_file(key, staging_path)
    
    if not success:
        return False, f"Download failed: {error}"
    
    # Verify file size
    actual_size = os.path.getsize(staging_path)
    if actual_size != size:
        return False, f"Size mismatch: expected {size}, got {actual_size}"
    
    print(f"  ✅ Downloaded correct file: {actual_size:,} bytes")
    
    # 3. Restore backup canonical
    canonical_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    backup_dir = f"data_v6/_backup/{venue}/{date}"
    
    if os.path.exists(canonical_path):
        # Find latest backup
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('ticks_canonical_')]
        if backup_files:
            latest_backup = max(backup_files)
            backup_path = os.path.join(backup_dir, latest_backup)
            
            # Restore from backup
            shutil.copy2(backup_path, canonical_path)
            print(f"  📦 Restored backup: {latest_backup}")
    
    # 4. Canonicalize new data
    canonical_df, dups_removed = canonicalize_venue_data(staging_path, venue, date)
    if canonical_df is None:
        return False, f"Canonicalization failed: {dups_removed}"
    
    # 5. Write new canonical
    os.makedirs(os.path.dirname(canonical_path), exist_ok=True)
    canonical_df.to_parquet(canonical_path, compression='snappy', index=False)
    
    # 6. Clean up staging
    os.remove(staging_path)
    os.rmdir(os.path.dirname(staging_path))
    
    # 7. Get stats
    price_min = canonical_df['price'].min()
    price_max = canonical_df['price'].max()
    rows = len(canonical_df)
    
    print(f"  ✅ Fixed {venue}: {rows:,} rows, {dups_removed:,} dups removed, price {price_min:.0f}→{price_max:.0f}")
    
    return True, {
        'venue': venue,
        'old_symbol': 'WRONG',
        'new_symbol': expected_symbol,
        'rows': rows,
        'price_range': f"{price_min:.0f}→{price_max:.0f}",
        'duplicates_removed': dups_removed
    }

def main():
    """Main function"""
    print("🔧 Fixing Symbol Mismatches for Day 1 (2025-09-08)")
    print("=" * 60)
    
    date = "20250908"
    corrections = []
    
    # Fix BINANCE (BTCFDUSD → BTCUSDT)
    success, result = fix_venue_symbol('BINANCE', date, 'BTCUSDT')
    if success:
        corrections.append(result)
    else:
        print(f"❌ Failed to fix BINANCE: {result}")
        return
    
    # Fix COINBASE (verify BTCUSD)
    success, result = fix_venue_symbol('COINBASE', date, 'BTCUSD')
    if success:
        corrections.append(result)
    else:
        print(f"❌ Failed to fix COINBASE: {result}")
        return
    
    # Print correction table
    print(f"\n📊 Correction Results:")
    print("Venue | Old Symbol | New Symbol | Rows | Price Range | Dups Removed")
    print("-" * 80)
    
    for correction in corrections:
        print(f"{correction['venue']} | {correction['old_symbol']} | {correction['new_symbol']} | {correction['rows']:,} | {correction['price_range']} | {correction['duplicates_removed']:,}")
    
    print(f"\n✅ Symbol corrections completed")

if __name__ == "__main__":
    main()




