#!/usr/bin/env python3
"""
Find the actual BTCUSD file names for July 28-31, 2025
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

def find_btcusd_files(date_str, venue):
    """Find BTCUSD files for a specific date/venue"""
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{date_str}/E-{venue}/"
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            btcusd_files = []
            
            for content in root.findall('.//Contents'):
                key_elem = content.find('Key')
                if key_elem is not None:
                    key = key_elem.text
                    # Look for BTCUSD patterns
                    if re.search(r'BTC.*USD|BTC.*USDT', key.upper()):
                        btcusd_files.append(key)
            
            return btcusd_files
        else:
            return []
    except Exception as e:
        print(f"Error checking {date_str}/{venue}: {e}")
        return []

def main():
    """Find BTCUSD files for July 28-31, 2025"""
    print("🔍 Finding actual BTCUSD file names for July 28-31, 2025...")
    
    target_dates = ["20250728", "20250729", "20250730", "20250731"]
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    for date_str in target_dates:
        print(f"\n📅 {date_str}:")
        
        for venue in venues:
            files = find_btcusd_files(date_str, venue)
            
            if files:
                print(f"  {venue}: {len(files)} BTCUSD files")
                for file in files:
                    print(f"    {file}")
            else:
                print(f"  {venue}: No BTCUSD files found")
    
    # Also check what we expect vs what we find
    print(f"\n🎯 Expected vs Actual:")
    expected_pairs = {
        'BINANCE': 'BTCUSDT',
        'COINBASE': 'BTC-USD',
        'BYBITSPOT': 'BTCUSDT', 
        'BITGET': 'BTCUSDT'
    }
    
    for date_str in target_dates:
        print(f"\n📅 {date_str}:")
        for venue, expected_pair in expected_pairs.items():
            files = find_btcusd_files(date_str, venue)
            matching_files = [f for f in files if expected_pair in f.upper()]
            
            if matching_files:
                print(f"  {venue} ({expected_pair}): ✅ Found {len(matching_files)} files")
                for file in matching_files:
                    print(f"    {file}")
            else:
                print(f"  {venue} ({expected_pair}): ❌ Not found")
                if files:
                    print(f"    Available BTCUSD files:")
                    for file in files:
                        print(f"      {file}")

if __name__ == "__main__":
    main()
