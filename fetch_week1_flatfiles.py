#!/usr/bin/env python3
"""
Fetch Week-1 CoinAPI Flat Files for ACD analysis
Week 1: 2025-08-01 to 2025-08-07
Venues: BINANCE, COINBASE, BYBITSPOT, BITGET
"""

import os
import requests
import xml.etree.ElementTree as ET
import gzip
import pandas as pd
from pathlib import Path
import time
import json
from datetime import datetime

# Configuration
COINAPI_KEY = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
BASE_URL = "https://s3.flatfiles.coinapi.io/"
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY
}

# Week 1 dates
WEEK1_DATES = [
    "20250801", "20250802", "20250803", "20250804", 
    "20250805", "20250806", "20250807"
]

# Venues to fetch
VENUES = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]

# BTC symbols to look for
BTC_SYMBOLS = ["BTCUSDT", "BTCUSD", "XBTUSD", "XBTUSDT"]

def list_files_for_venue_date(venue, date):
    """List all files for a specific venue and date"""
    url = f"{BASE_URL}bucket/?prefix=T-TRADES/D-{date}/E-{venue}/"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        files = []
        for contents in root.findall('.//Contents'):
            key = contents.find('Key').text
            size = int(contents.find('Size').text)
            last_modified = contents.find('LastModified').text
            
            files.append({
                'key': key,
                'size': size,
                'last_modified': last_modified
            })
        
        return files
    
    except Exception as e:
        print(f"Error listing files for {venue} {date}: {e}")
        return []

def find_btc_files(files):
    """Find BTC-related files from the file list"""
    btc_files = []
    
    for file_info in files:
        key = file_info['key']
        
        # Check if this is a BTC file
        for symbol in BTC_SYMBOLS:
            if symbol in key.upper():
                btc_files.append(file_info)
                break
    
    return btc_files

def download_file(file_key, local_path):
    """Download a file from CoinAPI S3"""
    url = f"{BASE_URL}{file_key}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Write file
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        return True, len(response.content)
    
    except Exception as e:
        print(f"Error downloading {file_key}: {e}")
        return False, 0

def validate_file(file_path):
    """Validate a downloaded file"""
    try:
        # Try to read as gzipped CSV
        with gzip.open(file_path, 'rt') as f:
            # Read first few lines to check format
            lines = []
            for i, line in enumerate(f):
                lines.append(line.strip())
                if i >= 4:  # Read first 5 lines
                    break
        
        # Check if it looks like trade data
        if len(lines) > 0:
            # Look for common trade data columns
            header = lines[0].lower()
            has_timestamp = any(col in header for col in ['time', 'timestamp', 'date'])
            has_price = any(col in header for col in ['price', 'rate'])
            has_volume = any(col in header for col in ['volume', 'size', 'amount', 'base_amount'])
            
            if has_timestamp and has_price and has_volume:
                return True, f"Valid trade data format. Header: {lines[0]}"
            else:
                return False, f"Invalid format. Header: {lines[0]}"
        else:
            return False, "Empty file"
    
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    """Main function to fetch and validate Week-1 files"""
    print("🚀 Starting Week-1 CoinAPI Flat Files fetch...")
    print(f"📅 Dates: {WEEK1_DATES}")
    print(f"🏢 Venues: {VENUES}")
    
    # Create base directory
    base_dir = Path("data/flatfiles_v5")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Track results
    results = {
        'successful_downloads': 0,
        'failed_downloads': 0,
        'valid_files': 0,
        'invalid_files': 0,
        'files': []
    }
    
    for date in WEEK1_DATES:
        print(f"\n📅 Processing date: {date}")
        
        for venue in VENUES:
            print(f"  🏢 Processing venue: {venue}")
            
            # List files for this venue/date
            files = list_files_for_venue_date(venue, date)
            print(f"    Found {len(files)} total files")
            
            # Find BTC files
            btc_files = find_btc_files(files)
            print(f"    Found {len(btc_files)} BTC-related files")
            
            if not btc_files:
                print(f"    ⚠️  No BTC files found for {venue} {date}")
                continue
            
            # Download the largest BTC file (likely the main one)
            btc_files.sort(key=lambda x: x['size'], reverse=True)
            main_file = btc_files[0]
            
            print(f"    📥 Downloading: {main_file['key']} ({main_file['size']} bytes)")
            
            # Create local path
            local_path = base_dir / venue / date / f"{venue}_{date}.csv.gz"
            
            # Download file
            success, size = download_file(main_file['key'], str(local_path))
            
            if success:
                print(f"    ✅ Downloaded {size} bytes")
                results['successful_downloads'] += 1
                
                # Validate file
                is_valid, message = validate_file(str(local_path))
                
                if is_valid:
                    print(f"    ✅ File is valid: {message}")
                    results['valid_files'] += 1
                else:
                    print(f"    ❌ File is invalid: {message}")
                    results['invalid_files'] += 1
                
                # Record file info
                results['files'].append({
                    'venue': venue,
                    'date': date,
                    'file_key': main_file['key'],
                    'local_path': str(local_path),
                    'size': size,
                    'valid': is_valid,
                    'message': message
                })
                
            else:
                print(f"    ❌ Failed to download")
                results['failed_downloads'] += 1
            
            # Rate limiting
            time.sleep(1)
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"  ✅ Successful downloads: {results['successful_downloads']}")
    print(f"  ❌ Failed downloads: {results['failed_downloads']}")
    print(f"  ✅ Valid files: {results['valid_files']}")
    print(f"  ❌ Invalid files: {results['invalid_files']}")
    
    # Save results
    results_file = base_dir / "fetch_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Print file list
    print(f"\n📁 Downloaded files:")
    for file_info in results['files']:
        status = "✅" if file_info['valid'] else "❌"
        print(f"  {status} {file_info['venue']} {file_info['date']}: {file_info['local_path']}")

if __name__ == "__main__":
    main()