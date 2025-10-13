#!/usr/bin/env python3
"""
Check what files are available for July 1st, 2025
"""

import os
import requests
import xml.etree.ElementTree as ET

def check_july01_availability():
    """Check what files are available for July 1st, 2025"""
    print("🔍 Checking July 1st, 2025 file availability")
    print("=" * 60)
    
    # Check environment variables
    coinapi_key = os.getenv('COINAPI_KEY')
    
    if not coinapi_key:
        print('❌ COINAPI_KEY not found in environment')
        return
    
    # July 1st, 2025
    target_date = '20250701'
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    print(f"📊 Target date: {target_date}")
    print(f"📊 Venues: {venues}")
    
    # Base URL
    base_url = "https://s3.flatfiles.coinapi.io/"
    
    headers = {
        'X-CoinAPI-Key': coinapi_key,
        'User-Agent': 'Mozilla/5.0 (compatible; DataDownloader/1.0)'
    }
    
    for venue in venues:
        print(f"\n📊 Checking {venue}...")
        
        try:
            # List objects in the bucket
            list_url = f"{base_url}bucket/?prefix=T-TRADES/D-{target_date}/E-{venue}/"
            
            print(f"   URL: {list_url}")
            
            response = requests.get(list_url, headers=headers, timeout=120)
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                
                # Find all files
                files_found = []
                for elem in root.iter():
                    if elem.tag.endswith('Key') and elem.text:
                        files_found.append(elem.text)
                
                print(f"   Files found: {len(files_found)}")
                
                if files_found:
                    print(f"   Sample files:")
                    for i, file_path in enumerate(files_found[:5]):  # Show first 5
                        print(f"     {i+1}. {file_path}")
                    
                    if len(files_found) > 5:
                        print(f"     ... and {len(files_found) - 5} more")
                else:
                    print(f"   No files found")
                    
            else:
                print(f"   ❌ HTTP {response.status_code}")
                if response.status_code == 403:
                    print(f"   This indicates permission/access issues")
                elif response.status_code == 404:
                    print(f"   This indicates the path doesn't exist")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    check_july01_availability()
