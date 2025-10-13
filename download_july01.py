#!/usr/bin/env python3
"""
Download July 1st, 2025 data for all venues
"""

import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import gzip
from datetime import datetime

def download_july01():
    """Download July 1st, 2025 data for all venues"""
    print("🔍 Downloading July 1st, 2025 data")
    print("=" * 60)
    
    # Check environment variables
    coinapi_key = os.getenv('COINAPI_KEY')
    
    if not coinapi_key:
        print('❌ COINAPI_KEY not found in environment')
        return False
    
    # July 1st, 2025
    target_date = '20250701'
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    print(f"📊 Target date: {target_date}")
    print(f"📊 Venues: {venues}")
    
    # Create output directory
    output_dir = 'data_v7/raw/coinapi_jul_extension'
    os.makedirs(output_dir, exist_ok=True)
    
    # Base URL
    base_url = "https://s3.flatfiles.coinapi.io/"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'Mozilla/5.0 (compatible; DataDownloader/1.0)'
    }
    
    success_count = 0
    total_count = len(venues)
    
    for venue in venues:
        print(f"📊 Downloading {venue}...")
        
        try:
            # List objects in the bucket
            list_url = f"{base_url}bucket/?prefix=T-TRADES/D-{target_date}/E-{venue}/"
            
            response = requests.get(list_url, headers=headers, timeout=120)
            
            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                
                # Find the actual file URL
                file_url = None
                for elem in root.iter():
                    if elem.tag.endswith('Key') and elem.text and elem.text.endswith('.gz'):
                        file_url = f"{base_url}{elem.text}"
                        break
                
                if file_url:
                    print(f"   Found file: {file_url}")
                    
                    # Download the file
                    file_response = requests.get(file_url, headers=headers, timeout=120)
                    
                    if file_response.status_code == 200:
                        # Save the file
                        output_path = os.path.join(output_dir, f"2025-07-01_{venue}.gz")
                        
                        with open(output_path, 'wb') as f:
                            f.write(file_response.content)
                        
                        file_size = len(file_response.content)
                        
                        # Compute SHA-256
                        with open(output_path, 'rb') as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                        
                        print(f"   ✅ {venue}: {file_size:,} bytes, SHA256: {file_hash[:16]}...")
                        success_count += 1
                        
                    else:
                        print(f"   ❌ {venue}: HTTP {file_response.status_code}")
                else:
                    print(f"   ❌ {venue}: No .gz file found in listing")
            else:
                print(f"   ❌ {venue}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ {venue}: Timeout")
        except Exception as e:
            print(f"   ❌ {venue}: {e}")
    
    print(f"\n📊 Download Summary:")
    print(f"   Success: {success_count}/{total_count}")
    print(f"   Coverage: {success_count/total_count:.1%}")
    
    return success_count == total_count

if __name__ == '__main__':
    success = download_july01()
    if success:
        print("✅ All files downloaded successfully")
    else:
        print("❌ Some files failed to download")
