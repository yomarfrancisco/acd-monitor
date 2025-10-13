#!/usr/bin/env python3
"""
CoinAPI Cross-Check for 2025-09-13
Verify BITGET data integrity and check BINANCE availability
"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
import gzip
import hashlib
import pandas as pd
from pathlib import Path
import glob

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    return os.environ.get('COINAPI_KEY', '7f036b38-38d6-4ed6-9fce-00a06280a0f6')

def list_coinapi_objects(venue, date):
    """List objects in CoinAPI S3 bucket for specific venue and date"""
    base_url = "https://s3.flatfiles.coinapi.io"
    prefix = f"T-TRADES/D-{date}/E-{venue}/"
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    params = {
        'list-type': '2',
        'prefix': prefix
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

def parse_s3_listing(xml_content):
    """Parse S3 XML listing response"""
    try:
        root = ET.fromstring(xml_content)
        objects = []
        
        for contents in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
            key = contents.find('{http://s3.amazonaws.com/doc/2006-03-01/}Key').text
            size = int(contents.find('{http://s3.amazonaws.com/doc/2006-03-01/}Size').text)
            objects.append({'key': key, 'size': size})
        
        return objects
    except Exception as e:
        return []

def download_coinapi_file(object_key, output_path):
    """Download a file from CoinAPI to quarantine folder"""
    base_url = "https://s3.flatfiles.coinapi.io"
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    try:
        response = requests.get(f"{base_url}/{object_key}", headers=headers, timeout=60)
        if response.status_code == 200:
            # Create quarantine directory
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write to quarantine
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True, None
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def compute_file_hash(file_path):
    """Compute SHA256 hash of a file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def analyze_file_streaming(file_path):
    """Analyze file with minimal memory usage"""
    try:
        # Get file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / 1024 / 1024
        
        # Compute SHA256
        sha256 = compute_file_hash(file_path)
        
        # Stream analyze CSV
        row_count = 0
        timestamps = []
        prices = []
        
        # Read in chunks to avoid memory issues
        chunk_size = 10000
        
        if file_path.endswith('.gz'):
            # Handle gzipped file
            with gzip.open(file_path, 'rt') as f:
                # Skip header
                header = f.readline()
                if not header:
                    return {
                        'sha256': sha256,
                        'size_bytes': file_size_bytes,
                        'size_mb': file_size_mb,
                        'row_count': 0,
                        'min_ts': None,
                        'max_ts': None,
                        'min_price': None,
                        'max_price': None
                    }
                
                # Read first chunk
                for i, line in enumerate(f):
                    if i >= chunk_size:
                        break
                    row_count += 1
                    
                    try:
                        parts = line.strip().split(';')
                        if len(parts) >= 4:
                            # Parse timestamp
                            ts = pd.to_datetime(parts[0], utc=True)
                            timestamps.append(ts)
                            
                            # Parse price
                            price = float(parts[3])
                            prices.append(price)
                    except:
                        continue
                
                # Continue reading for full count
                for line in f:
                    row_count += 1
        else:
            # Handle regular file
            with open(file_path, 'r') as f:
                # Skip header
                header = f.readline()
                if not header:
                    return {
                        'sha256': sha256,
                        'size_bytes': file_size_bytes,
                        'size_mb': file_size_mb,
                        'row_count': 0,
                        'min_ts': None,
                        'max_ts': None,
                        'min_price': None,
                        'max_price': None
                    }
                
                # Read first chunk
                for i, line in enumerate(f):
                    if i >= chunk_size:
                        break
                    row_count += 1
                    
                    try:
                        parts = line.strip().split(';')
                        if len(parts) >= 4:
                            # Parse timestamp
                            ts = pd.to_datetime(parts[0], utc=True)
                            timestamps.append(ts)
                            
                            # Parse price
                            price = float(parts[3])
                            prices.append(price)
                    except:
                        continue
                
                # Continue reading for full count
                for line in f:
                    row_count += 1
        
        # Calculate stats from sample
        min_ts = min(timestamps) if timestamps else None
        max_ts = max(timestamps) if timestamps else None
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        
        return {
            'sha256': sha256,
            'size_bytes': file_size_bytes,
            'size_mb': file_size_mb,
            'row_count': row_count,
            'min_ts': min_ts,
            'max_ts': max_ts,
            'min_price': min_price,
            'max_price': max_price
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'sha256': 'ERROR',
            'size_bytes': 0,
            'size_mb': 0,
            'row_count': 0,
            'min_ts': None,
            'max_ts': None,
            'min_price': None,
            'max_price': None
        }

def check_bitget_20250913():
    """Check BITGET 2025-09-13 data integrity"""
    print("🔍 BITGET 2025-09-13 — CoinAPI vs Local Raw")
    print("=" * 50)
    
    date = "20250913"
    venue = "BITGET"
    
    # List CoinAPI objects
    status_code, xml_content = list_coinapi_objects(venue, date)
    
    if status_code != 200:
        print(f"❌ CoinAPI listing failed: HTTP {status_code}")
        return None
    
    objects = parse_s3_listing(xml_content)
    
    if not objects:
        print("❌ BITGET: NO_DATA_AT_SOURCE")
        return None
    
    # Find largest BTCUSDT file
    btc_objects = [obj for obj in objects if 'BTCUSDT' in obj['key'].upper()]
    if not btc_objects:
        print("❌ No BTCUSDT files found for BITGET")
        return None
    
    target_object = max(btc_objects, key=lambda x: x['size'])
    print(f"📁 CoinAPI file: {target_object['key']} ({target_object['size']:,} bytes)")
    
    # Download to quarantine
    quarantine_path = f"analysis/_quarantine/coinapi_verify/2025-09-13/{venue}/{os.path.basename(target_object['key'])}"
    success, error = download_coinapi_file(target_object['key'], quarantine_path)
    
    if not success:
        print(f"❌ Download failed: {error}")
        return None
    
    print(f"✅ Downloaded to quarantine: {quarantine_path}")
    
    # Analyze CoinAPI file
    print("📊 Analyzing CoinAPI file...")
    coinapi_data = analyze_file_streaming(quarantine_path)
    
    if 'error' in coinapi_data:
        print(f"❌ Error analyzing CoinAPI file: {coinapi_data['error']}")
        return None
    
    # Find local raw file
    local_pattern = f"analysis/flatfiles_ticks_v4/raw/*BITGET*20250913*BTCUSDT*.csv.gz"
    local_files = glob.glob(local_pattern)
    
    if not local_files:
        print(f"❌ No local BITGET file found matching pattern: {local_pattern}")
        return None
    
    local_file = local_files[0]
    print(f"📁 Local file: {local_file}")
    
    # Analyze local file
    print("📊 Analyzing local file...")
    local_data = analyze_file_streaming(local_file)
    
    if 'error' in local_data:
        print(f"❌ Error analyzing local file: {local_data['error']}")
        return None
    
    # Compare results
    print(f"\n## BITGET 2025-09-13 — CoinAPI vs Local Raw")
    print("| Source     | SHA256                                  | Size (MB) | Rows    | ts_min → ts_max                 | px_min → px_max    |")
    print("|------------|------------------------------------------|-----------|---------|---------------------------------|--------------------|")
    
    coinapi_ts_range = f"{coinapi_data['min_ts'].strftime('%H:%M:%S')} → {coinapi_data['max_ts'].strftime('%H:%M:%S')}" if coinapi_data['min_ts'] and coinapi_data['max_ts'] else "N/A"
    coinapi_price_range = f"{coinapi_data['min_price']:.2f} → {coinapi_data['max_price']:.2f}" if coinapi_data['min_price'] and coinapi_data['max_price'] else "N/A"
    
    local_ts_range = f"{local_data['min_ts'].strftime('%H:%M:%S')} → {local_data['max_ts'].strftime('%H:%M:%S')}" if local_data['min_ts'] and local_data['max_ts'] else "N/A"
    local_price_range = f"{local_data['min_price']:.2f} → {local_data['max_price']:.2f}" if local_data['min_price'] and local_data['max_price'] else "N/A"
    
    print(f"| CoinAPI    | {coinapi_data['sha256'][:16]}...                        | {coinapi_data['size_mb']:.2f}    | {coinapi_data['row_count']:,}  | {coinapi_ts_range}             | {coinapi_price_range}      |")
    print(f"| Local Raw  | {local_data['sha256'][:16]}...                        | {local_data['size_mb']:.2f}    | {local_data['row_count']:,}  | {local_ts_range}             | {local_price_range}      |")
    
    # Check for match
    sha256_match = coinapi_data['sha256'] == local_data['sha256']
    size_match = coinapi_data['size_bytes'] == local_data['size_bytes']
    row_count_match = coinapi_data['row_count'] == local_data['row_count']
    
    if sha256_match and size_match and row_count_match:
        print(f"**Verdict:** BITGET: MATCH")
        # Delete quarantine file
        os.remove(quarantine_path)
        print(f"✅ Deleted quarantine file (files match)")
        return {'status': 'MATCH'}
    else:
        print(f"**Verdict:** HALT: BITGET_MISMATCH")
        print(f"⚠️  Keeping quarantine file for review")
        return {'status': 'MISMATCH', 'quarantine_path': quarantine_path}

def check_binance_20250913():
    """Check BINANCE 2025-09-13 availability"""
    print(f"\n🔍 BINANCE 2025-09-13 — Source Check")
    print("=" * 50)
    
    date = "20250913"
    venue = "BINANCE"
    
    # List CoinAPI objects
    status_code, xml_content = list_coinapi_objects(venue, date)
    
    if status_code != 200:
        print(f"❌ CoinAPI listing failed: HTTP {status_code}")
        return None
    
    objects = parse_s3_listing(xml_content)
    
    if not objects:
        print("❌ BINANCE: NO_DATA_AT_SOURCE")
        return {'status': 'NO_DATA_AT_SOURCE'}
    
    # Find largest BTCUSDT file
    btc_objects = [obj for obj in objects if 'BTCUSDT' in obj['key'].upper()]
    if not btc_objects:
        print("❌ No BTCUSDT files found for BINANCE")
        return {'status': 'NO_DATA_AT_SOURCE'}
    
    target_object = max(btc_objects, key=lambda x: x['size'])
    print(f"📁 CoinAPI file: {target_object['key']} ({target_object['size']:,} bytes)")
    
    # Download to quarantine
    quarantine_path = f"analysis/_quarantine/coinapi_verify/2025-09-13/{venue}/{os.path.basename(target_object['key'])}"
    success, error = download_coinapi_file(target_object['key'], quarantine_path)
    
    if not success:
        print(f"❌ Download failed: {error}")
        return None
    
    print(f"✅ Downloaded to quarantine: {quarantine_path}")
    
    # Analyze downloaded file
    print("📊 Analyzing downloaded BINANCE file...")
    binance_data = analyze_file_streaming(quarantine_path)
    
    if 'error' in binance_data:
        print(f"❌ Error analyzing BINANCE file: {binance_data['error']}")
        return None
    
    print(f"\n## BINANCE 2025-09-13 — Source Check")
    print(f"Result: READY_FOR_REVIEW (downloaded to quarantine)")
    print(f"SHA256={binance_data['sha256'][:16]}..., Size={binance_data['size_mb']:.2f}MB, Rows={binance_data['row_count']:,}")
    
    ts_range = f"{binance_data['min_ts'].strftime('%Y-%m-%d %H:%M:%S')} → {binance_data['max_ts'].strftime('%Y-%m-%d %H:%M:%S')}" if binance_data['min_ts'] and binance_data['max_ts'] else "N/A"
    price_range = f"{binance_data['min_price']:.2f} → {binance_data['max_price']:.2f}" if binance_data['min_price'] and binance_data['max_price'] else "N/A"
    
    print(f"ts_min={binance_data['min_ts']}, ts_max={binance_data['max_ts']}, px_min={binance_data['min_price']:.2f}, px_max={binance_data['max_price']:.2f}")
    
    return {'status': 'READY_FOR_REVIEW', 'quarantine_path': quarantine_path, 'data': binance_data}

def main():
    """Main cross-check function"""
    print("🧩 CoinAPI Cross-Check (2025-09-13)")
    print("=" * 60)
    
    # Check memory
    import psutil
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"🧠 Initial memory: {memory_mb:.1f} MB")
    
    if memory_mb > 300:
        print("⚠️  Memory warning: {memory_mb:.1f} MB")
    
    if memory_mb > 400:
        print("❌ HALT: Memory limit exceeded")
        return
    
    # Part A: BITGET verification
    bitget_result = check_bitget_20250913()
    
    # Part B: BINANCE availability check
    binance_result = check_binance_20250913()
    
    # Final memory check
    final_memory = process.memory_info().rss / 1024 / 1024
    print(f"\n🧠 Final memory: {final_memory:.1f} MB")
    
    if final_memory > 400:
        print("⚠️  Memory usage exceeded 400MB during processing")

if __name__ == "__main__":
    main()




