#!/usr/bin/env python3
"""
CoinAPI Test New Key

Test the new API key to see what symbols are available.
"""

import requests
import json

def test_new_api_key():
    """Test the new API key."""
    api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"
    
    print("🔍 Testing new API key...")
    print("="*80)
    
    # Test basic endpoints
    endpoints = [
        "/exchanges",
        "/symbols",
        "/assets"
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"   ✅ SUCCESS: {len(data)} items")
                    if endpoint == "/symbols":
                        # Look for BTC symbols
                        btc_symbols = [s for s in data if "BTC" in s.get("symbol_id", "")]
                        print(f"   📊 BTC symbols found: {len(btc_symbols)}")
                        for symbol in btc_symbols[:10]:  # Show first 10
                            print(f"      - {symbol['symbol_id']}")
                else:
                    print(f"   ✅ SUCCESS: {type(data).__name__}")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_new_api_key()
