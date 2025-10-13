#!/usr/bin/env python3
"""
🧭 Week -2 Raw Rebuild (Aug 18→24), Day-by-Day, Week-1 Method
Raw file download only - no transforms, no dedup, no parquet
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import json
from datetime import datetime, timedelta

def load_env_file():
    """Load environment variables from .env file"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables
load_env_file()

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    key = os.getenv('COINAPI_KEY')
    if not key:
        print("❌ HALT: COINAPI_KEY environment variable not set")
        return None
    return key

def list_coinapi_files(date, venue):
    """List files from CoinAPI S3 bucket for a specific date and venue"""
    coinapi_key = get_coinapi_key()
    if not coinapi_key:
        return None, "No API key"
    
    # List files from CoinAPI
    list_url = f"https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    try:
        response = requests.get(list_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return None, f"List failed: HTTP {response.status_code}"
        
        # Parse XML response
        root = ET.fromstring(response.content)
        
        files = []
        for content in root.findall('.//Contents'):
            key_elem = content.find('Key')
            size_elem = content.find('Size')
            
            if key_elem is not None and size_elem is not None:
                key = key_elem.text
                size = int(size_elem.text)
                files.append({'key': key, 'size': size})
        
        return files, None
        
    except Exception as e:
        return None, f"Error listing files: {e}"

def find_exact_symbol_match(files, venue):
    """Find exact symbol match based on venue"""
    if venue == 'COINBASE':
        # COINBASE: look for +S-BTC__002DUSD.csv.gz
        exact_matches = [f for f in files if f['key'].endswith('+S-BTC__002DUSD.csv.gz')]
    else:
        # BINANCE, BYBITSPOT, BITGET: look for +S-BTCUSDT.csv.gz
        exact_matches = [f for f in files if f['key'].endswith('+S-BTCUSDT.csv.gz')]
    
    if not exact_matches:
        # Check what BTC files exist for debugging
        btc_files = [f for f in files if 'BTC' in f['key'].upper()]
        return None, f"No exact symbol matches found. BTC files available: {[f['key'] for f in btc_files[:3]]}"
    
    # If multiple matches, pick the largest
    if len(exact_matches) > 1:
        exact_matches.sort(key=lambda x: x['size'], reverse=True)
    
    return exact_matches[0], None

def download_coinapi_file(file_key, local_path):
    """Download file from CoinAPI S3 bucket"""
    coinapi_key = get_coinapi_key()
    if not coinapi_key:
        return False, "No API key"
    
    # Use the correct URL pattern from week1_download.py
    download_url = f"https://s3.flatfiles.coinapi.io/coinapi/{file_key}"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    try:
        response = requests.get(download_url, headers=headers, timeout=60, stream=True)
        
        if response.status_code != 200:
            return False, f"Download failed: HTTP {response.status_code}"
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True, None
        
    except Exception as e:
        return False, f"Download error: {e}"

def calculate_sha256(file_path):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def process_venue(date, venue):
    """Process a single venue for a given date"""
    print(f"  🔍 {venue}...")
    
    # List files
    files, error = list_coinapi_files(date, venue)
    if error:
        return None, f"List error: {error}"
    
    if not files:
        return None, "No files found"
    
    # Find exact symbol match
    file_info, error = find_exact_symbol_match(files, venue)
    if error:
        return None, error
    
    file_key = file_info['key']
    expected_size = file_info['size']
    
    # Determine filename
    if venue == 'COINBASE':
        filename = f"{venue}_{date}_BTCUSD.csv.gz"
    else:
        filename = f"{venue}_{date}_BTCUSDT.csv.gz"
    
    local_path = f"analysis/flatfiles_ticks_v4/raw/{filename}"
    
    # Download file
    success, error = download_coinapi_file(file_key, local_path)
    if not success:
        return None, f"Download error: {error}"
    
    # Check file size
    actual_size = os.path.getsize(local_path)
    if actual_size != expected_size:
        os.remove(local_path)
        return None, f"Size mismatch: expected {expected_size}, got {actual_size}"
    
    # Calculate SHA256
    sha256_hash = calculate_sha256(local_path)
    
    return {
        'venue': venue,
        'key': file_key,
        'size': actual_size,
        'sha256': sha256_hash,
        'status': 'OK'
    }, None

def process_day(date):
    """Process a single day for all venues"""
    print(f"\n📅 Day Summary ({date[:4]}-{date[4:6]}-{date[6:8]}):")
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    results = []
    successful_venues = 0
    
    for venue in venues:
        result, error = process_venue(date, venue)
        if result:
            print(f"  • {venue}: key={result['key'][:50]}... size={result['size']:,} sha256={result['sha256'][:8]}... (OK)")
            results.append(result)
            successful_venues += 1
        else:
            print(f"  • {venue}: (FAIL: {error})")
            results.append({
                'venue': venue,
                'key': 'N/A',
                'size': 0,
                'sha256': 'N/A',
                'status': 'FAIL',
                'error': error
            })
    
    # Determine day status
    if successful_venues == 4:
        day_status = "FULL"
    elif successful_venues > 0:
        day_status = "PARTIAL"
    else:
        day_status = "FAIL"
    
    print(f"Day status: {day_status}")
    
    return results, day_status

def main():
    """Main function"""
    print("🧭 Week -2 Raw Rebuild (Aug 18→24), Day-by-Day, Week-1 Method")
    print("=" * 80)
    
    # Create output directory
    os.makedirs('analysis/flatfiles_ticks_v4/raw', exist_ok=True)
    
    # Week -2 dates in descending order: 2025-08-24 → 2025-08-18
    start_date = datetime(2025, 8, 24)
    end_date = datetime(2025, 8, 18)
    
    dates = []
    current_date = start_date
    while current_date >= end_date:
        dates.append(current_date.strftime("%Y%m%d"))
        current_date -= timedelta(days=1)
    
    print(f"📅 Week -2 dates (descending): {dates}")
    print(f"🎯 Raw files only - no transforms, no dedup, no parquet")
    print(f"🔍 Strict symbol filters, /coinapi/ path, size/sha logging only")
    
    # Process each day
    all_results = []
    week_summary = []
    
    for date in dates:
        day_results, day_status = process_day(date)
        all_results.extend(day_results)
        
        # Count successful venues
        ok_venues = [r['venue'] for r in day_results if r['status'] == 'OK']
        fail_venues = [r['venue'] for r in day_results if r['status'] == 'FAIL']
        
        week_summary.append({
            'date': date,
            'status': day_status,
            'ok_venues': ok_venues,
            'fail_venues': fail_venues,
            'notes': f"{len(ok_venues)}/4 venues successful"
        })
    
    # Print compact table
    print(f"\n📊 Week -2 Summary Table:")
    print("=" * 80)
    print(f"{'Date':<12} {'Status':<8} {'OK Venues':<20} {'Fail Venues':<20} {'Notes'}")
    print("-" * 80)
    
    for day in week_summary:
        ok_str = ', '.join(day['ok_venues']) if day['ok_venues'] else 'None'
        fail_str = ', '.join(day['fail_venues']) if day['fail_venues'] else 'None'
        print(f"{day['date']:<12} {day['status']:<8} {ok_str:<20} {fail_str:<20} {day['notes']}")
    
    # Print JSON blob for audit
    print(f"\n📋 JSON Audit Data:")
    print("=" * 80)
    audit_data = {
        'week': 'Week -2 (2025-08-18 to 2025-08-24)',
        'method': 'Week-1 raw rebuild (no transforms)',
        'results': all_results
    }
    print(json.dumps(audit_data, indent=2))
    
    print(f"\n✅ Week -2 raw rebuild completed!")

if __name__ == "__main__":
    main()




