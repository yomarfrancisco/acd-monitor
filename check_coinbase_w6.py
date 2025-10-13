#!/usr/bin/env python3
"""
Check what COINBASE files are actually available for Week -6 dates
"""

import requests
import xml.etree.ElementTree as ET
import re

# CoinAPI configuration
COINAPI_BASE_URL = 'https://s3.flatfiles.coinapi.io'
COINAPI_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

# Week -6 dates
WEEK_6_DATES = ['20250714', '20250715', '20250716', '20250717', '20250718', '20250719', '20250720']

def check_coinbase_files(date_str):
    """Check what COINBASE files are available for a specific date"""
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{date_str}/E-COINBASE/"
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            btc_files = []
            
            for content in root.findall('.//Contents'):
                key_elem = content.find('Key')
                if key_elem is not None:
                    key = key_elem.text
                    # Look for BTC files
                    if 'BTC' in key.upper():
                        btc_files.append(key)
            
            return btc_files
        else:
            return []
    except Exception as e:
        print(f"Error checking {date_str}: {e}")
        return []

def main():
    """Check COINBASE availability for Week -6"""
    print("🔍 Checking COINBASE file availability for Week -6...")
    
    for date_str in WEEK_6_DATES:
        print(f"\n📅 {date_str}:")
        files = check_coinbase_files(date_str)
        
        if files:
            print(f"  Found {len(files)} BTC files:")
            for file in files:
                print(f"    {file}")
        else:
            print(f"  No BTC files found")

if __name__ == "__main__":
    main()
