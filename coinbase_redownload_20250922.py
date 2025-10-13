#!/usr/bin/env python3
"""
🔄 COINBASE Redownload (2025-09-22 only)
Reattempt download with retry logic for transient network errors
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time

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

def download_coinapi_file_with_retry(file_key, local_path, max_retries=3):
    """Download file from CoinAPI S3 bucket with retry logic"""
    coinapi_key = get_coinapi_key()
    if not coinapi_key:
        return False, "No API key"
    
    # Use the correct URL pattern from week1_download.py
    download_url = f"https://s3.flatfiles.coinapi.io/coinapi/{file_key}"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'ACD-Monitor/1.0'
    }
    
    for attempt in range(max_retries):
        try:
            print(f"  📥 Attempt {attempt + 1}/{max_retries}: {download_url}")
            
            response = requests.get(download_url, headers=headers, timeout=120, stream=True)
            
            if response.status_code != 200:
                return False, f"Download failed: HTTP {response.status_code}"
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True, None
            
        except (requests.exceptions.IncompleteRead, 
                requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout) as e:
            print(f"  ⚠️ Network error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"  🔄 Retrying in 2 seconds...")
                time.sleep(2)
                continue
            else:
                return False, f"Download failed after {max_retries} attempts: {e}"
        except Exception as e:
            return False, f"Download error: {e}"
    
    return False, "Max retries exceeded"

def calculate_sha256(file_path):
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def main():
    """Main function"""
    print("🔄 COINBASE Redownload (2025-09-22 only)")
    print("=" * 60)
    
    date = "20250922"
    venue = "COINBASE"
    
    # Create output directory
    os.makedirs('analysis/flatfiles_ticks_v4/raw', exist_ok=True)
    
    print(f"📅 Date: {date}")
    print(f"🏢 Venue: {venue}")
    print(f"🎯 Target: BTC__002DUSD.csv.gz")
    
    # List files
    print(f"\n🔍 Listing files...")
    files, error = list_coinapi_files(date, venue)
    if error:
        print(f"❌ List error: {error}")
        return
    
    if not files:
        print("❌ No files found")
        return
    
    # Find exact symbol match
    print(f"🔍 Finding exact symbol match...")
    file_info, error = find_exact_symbol_match(files, venue)
    if error:
        print(f"❌ Symbol match error: {error}")
        return
    
    file_key = file_info['key']
    expected_size = file_info['size']
    
    print(f"✅ Found file: {file_key}")
    print(f"📏 Expected size: {expected_size:,} bytes")
    
    # Download file with retry
    filename = f"{venue}_{date}_BTCUSD.csv.gz"
    local_path = f"analysis/flatfiles_ticks_v4/raw/{filename}"
    
    print(f"\n📥 Downloading to: {local_path}")
    success, error = download_coinapi_file_with_retry(file_key, local_path)
    
    if not success:
        print(f"❌ Download failed: {error}")
        return
    
    # Check file size
    actual_size = os.path.getsize(local_path)
    print(f"📏 Actual size: {actual_size:,} bytes")
    
    if actual_size != expected_size:
        os.remove(local_path)
        print(f"❌ Size mismatch: expected {expected_size:,}, got {actual_size:,}")
        return
    
    # Calculate SHA256
    print(f"🔐 Computing SHA256...")
    sha256_hash = calculate_sha256(local_path)
    
    # Print summary
    print(f"\n📊 Download Summary:")
    print("=" * 60)
    print(f"Download URL: https://s3.flatfiles.coinapi.io/coinapi/{file_key}")
    print(f"File size: {actual_size:,} bytes (expected: {expected_size:,})")
    print(f"SHA256 hash: {sha256_hash}")
    print(f"Status: SUCCESS")
    
    print(f"\n✅ COINBASE 2025-09-22 download completed successfully!")
    print(f"🎯 Week 4 is now 28/28 venue-days complete!")

if __name__ == "__main__":
    main()




