#!/usr/bin/env python3
"""
Test CoinAPI access with a known working date
"""

import requests
import xml.etree.ElementTree as ET

# Test with Aug 1, 2025 (we know this date has data)
test_date = "20250801"
test_venue = "BINANCE"

# CoinAPI configuration
COINAPI_BASE_URL = 'https://s3.flatfiles.coinapi.io'
COINAPI_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

def test_listing():
    """Test listing files for a known working date"""
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{test_date}/E-{test_venue}/"
    
    print(f"Testing API access...")
    print(f"URL: {list_url}")
    print(f"Headers: {HEADERS}")
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ API access working!")
            root = ET.fromstring(response.text)
            files = []
            for content in root.findall('.//Contents'):
                key_elem = content.find('Key')
                if key_elem is not None:
                    key = key_elem.text
                    if key.endswith('.csv.gz'):
                        files.append(key)
            
            print(f"Found {len(files)} CSV files:")
            for file in files[:5]:  # Show first 5
                print(f"  {file}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
                
        else:
            print(f"❌ API access failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_listing()