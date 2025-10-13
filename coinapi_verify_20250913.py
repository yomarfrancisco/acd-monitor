#!/usr/bin/env python3
"""
CoinAPI Verification for 2025-09-13
Check BINANCE and BITGET data availability and authenticity
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

def download_coinapi_file(venue, date, object_key):
    """Download a file from CoinAPI"""
    base_url = "https://s3.flatfiles.coinapi.io"
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    try:
        response = requests.get(f"{base_url}/{object_key}", headers=headers, timeout=60)
        return response.status_code, response.content
    except Exception as e:
        return None, str(e)

def compute_file_hash(content):
    """Compute SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()

def analyze_csv_content(content, venue):
    """Analyze CSV content for row count and price range"""
    try:
        # Decompress if gzipped
        if content.startswith(b'\x1f\x8b'):
            content = gzip.decompress(content)
        
        # Convert to string and split lines
        lines = content.decode('utf-8').strip().split('\n')
        
        # Skip header
        data_lines = lines[1:] if len(lines) > 1 else []
        row_count = len(data_lines)
        
        if row_count == 0:
            return row_count, None, None
        
        # Parse first few lines to get price range
        prices = []
        for line in data_lines[:1000]:  # Sample first 1000 rows
            try:
                parts = line.split(';')
                if len(parts) >= 4:
                    price = float(parts[3])  # price column
                    prices.append(price)
            except:
                continue
        
        if prices:
            price_min = min(prices)
            price_max = max(prices)
        else:
            price_min = price_max = None
        
        return row_count, price_min, price_max
        
    except Exception as e:
        return 0, None, None

def compare_with_existing(venue, date, coinapi_content):
    """Compare CoinAPI data with existing raw files"""
    # Find existing raw file
    pattern = f"analysis/flatfiles_ticks_v4/raw/*{venue}*{date}*.csv.gz"
    existing_files = glob.glob(pattern)
    
    if not existing_files:
        return None, "No existing file found"
    
    existing_file = existing_files[0]
    
    try:
        # Read existing file
        with open(existing_file, 'rb') as f:
            existing_content = f.read()
        
        # Compare hashes
        existing_hash = compute_file_hash(existing_content)
        coinapi_hash = compute_file_hash(coinapi_content)
        
        hash_match = existing_hash == coinapi_hash
        
        # Compare row counts
        existing_rows, existing_price_min, existing_price_max = analyze_csv_content(existing_content, venue)
        coinapi_rows, coinapi_price_min, coinapi_price_max = analyze_csv_content(coinapi_content, venue)
        
        row_count_match = abs(existing_rows - coinapi_rows) <= max(1, existing_rows * 0.01)  # 1% tolerance
        
        # Compare price ranges (1 bp tolerance)
        price_match = True
        if existing_price_min and coinapi_price_min:
            price_match = price_match and abs(existing_price_min - coinapi_price_min) <= 0.01
        if existing_price_max and coinapi_price_max:
            price_match = price_match and abs(existing_price_max - coinapi_price_max) <= 0.01
        
        return {
            'hash_match': hash_match,
            'row_count_match': row_count_match,
            'price_match': price_match,
            'existing_rows': existing_rows,
            'coinapi_rows': coinapi_rows,
            'existing_price_range': f"{existing_price_min:.2f}→{existing_price_max:.2f}" if existing_price_min and existing_price_max else "N/A",
            'coinapi_price_range': f"{coinapi_price_min:.2f}→{coinapi_price_max:.2f}" if coinapi_price_min and coinapi_price_max else "N/A"
        }, None
        
    except Exception as e:
        return None, f"Error comparing files: {e}"

def main():
    """Main verification function"""
    print("🧩 2025-09-13 CoinAPI Verification")
    print("=" * 50)
    
    date = "20250913"
    venues = ["BINANCE", "BITGET"]
    results = []
    
    for venue in venues:
        print(f"\n🔍 Checking {venue}...")
        
        # List objects in CoinAPI
        status_code, xml_content = list_coinapi_objects(venue, date)
        
        if status_code != 200:
            print(f"❌ HTTP {status_code}: {xml_content}")
            results.append({
                'venue': venue,
                'http_status': status_code,
                'objects': 0,
                'size_mb': 0,
                'match': False,
                'row_count': "N/A",
                'price_range': "N/A",
                'action': "ERROR"
            })
            continue
        
        # Parse objects
        objects = parse_s3_listing(xml_content)
        
        if not objects:
            print(f"❌ No objects found for {venue}")
            results.append({
                'venue': venue,
                'http_status': status_code,
                'objects': 0,
                'size_mb': 0,
                'match': False,
                'row_count': "N/A",
                'price_range': "N/A",
                'action': "NO_DATA"
            })
            continue
        
        print(f"✅ Found {len(objects)} objects")
        
        # Find BTC-related file (largest one)
        btc_objects = [obj for obj in objects if 'BTC' in obj['key'].upper()]
        if not btc_objects:
            btc_objects = objects  # Use all if no BTC filter
        
        target_object = max(btc_objects, key=lambda x: x['size'])
        print(f"📁 Target file: {target_object['key']} ({target_object['size']:,} bytes)")
        
        # Download file
        print("⬇️  Downloading...")
        download_status, content = download_coinapi_file(venue, date, target_object['key'])
        
        if download_status != 200:
            print(f"❌ Download failed: HTTP {download_status}")
            results.append({
                'venue': venue,
                'http_status': status_code,
                'objects': len(objects),
                'size_mb': target_object['size'] / 1024 / 1024,
                'match': False,
                'row_count': "N/A",
                'price_range': "N/A",
                'action': "DOWNLOAD_FAILED"
            })
            continue
        
        print(f"✅ Downloaded {len(content):,} bytes")
        
        # Analyze content
        row_count, price_min, price_max = analyze_csv_content(content, venue)
        price_range = f"{price_min:.2f}→{price_max:.2f}" if price_min and price_max else "N/A"
        
        print(f"📊 Rows: {row_count:,}, Price range: {price_range}")
        
        # Compare with existing
        comparison, error = compare_with_existing(venue, date, content)
        
        if error:
            print(f"❌ Comparison error: {error}")
            results.append({
                'venue': venue,
                'http_status': status_code,
                'objects': len(objects),
                'size_mb': target_object['size'] / 1024 / 1024,
                'match': False,
                'row_count': f"{row_count:,}",
                'price_range': price_range,
                'action': "COMPARISON_ERROR"
            })
            continue
        
        # Determine action
        if comparison['hash_match'] and comparison['row_count_match'] and comparison['price_match']:
            action = "PERFECT_MATCH"
            match_status = "✅"
        elif comparison['row_count_match'] and comparison['price_match']:
            action = "CONTENT_MATCH"
            match_status = "✅"
        else:
            action = "MISMATCH"
            match_status = "❌"
        
        print(f"{match_status} Hash match: {comparison['hash_match']}")
        print(f"{match_status} Row count match: {comparison['row_count_match']} ({comparison['existing_rows']:,} vs {comparison['coinapi_rows']:,})")
        print(f"{match_status} Price match: {comparison['price_match']}")
        print(f"📈 Existing price range: {comparison['existing_price_range']}")
        print(f"📈 CoinAPI price range: {comparison['coinapi_price_range']}")
        
        results.append({
            'venue': venue,
            'http_status': status_code,
            'objects': len(objects),
            'size_mb': target_object['size'] / 1024 / 1024,
            'match': comparison['hash_match'] and comparison['row_count_match'] and comparison['price_match'],
            'row_count': f"{comparison['existing_rows']:,} vs {comparison['coinapi_rows']:,}",
            'price_range': f"{comparison['existing_price_range']} vs {comparison['coinapi_price_range']}",
            'action': action
        })
    
    # Print results table
    print(f"\n## 🧩 2025-09-13 CoinAPI Verification")
    print("| Venue | HTTP | Objects | Size MB | Match? | Row Count (raw vs CoinAPI) | Price Min→Max | Action |")
    print("|-------|------|---------|---------|--------|----------------------------|---------------|--------|")
    
    for result in results:
        match_symbol = "✅" if result['match'] else "❌"
        print(f"| {result['venue']} | {result['http_status']} | {result['objects']} | {result['size_mb']:.1f} | {match_symbol} | {result['row_count']} | {result['price_range']} | {result['action']} |")
    
    # Final assessment
    print(f"\n## 📋 Assessment")
    
    binance_result = next((r for r in results if r['venue'] == 'BINANCE'), None)
    bitget_result = next((r for r in results if r['venue'] == 'BITGET'), None)
    
    if bitget_result and bitget_result['match']:
        print("✅ **BITGET data matches perfectly** - existing Week 2 data can be trusted overall")
    elif bitget_result and bitget_result['action'] in ['PERFECT_MATCH', 'CONTENT_MATCH']:
        print("✅ **BITGET data matches** - existing Week 2 data can be trusted overall")
    else:
        print("⚠️ **BITGET data mismatch** - existing Week 2 data may need verification")
    
    if binance_result and binance_result['match']:
        print("✅ **BINANCE data matches** - no additional action needed")
    elif binance_result and binance_result['action'] in ['PERFECT_MATCH', 'CONTENT_MATCH']:
        print("✅ **BINANCE data available and matches** - no additional action needed")
    elif binance_result and binance_result['action'] == 'MISMATCH':
        print("⚠️ **BINANCE data available but differs** - manual review recommended")
    else:
        print("❌ **BINANCE data not available** - missing data confirmed")

if __name__ == "__main__":
    main()




