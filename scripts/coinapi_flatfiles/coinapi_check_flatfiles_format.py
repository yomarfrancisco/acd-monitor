#!/usr/bin/env python3
"""
CoinAPI Flat Files - Check Correct Format

Test different Flat Files API endpoint formats to find the correct one.
"""

import os
import requests
import json
from datetime import datetime, timezone, timedelta

def get_coinapi_key() -> str:
    """Get CoinAPI key from environment variable."""
    api_key = os.getenv('COINAPI_KEY')
    if not api_key:
        raise ValueError("COINAPI_KEY environment variable not set")
    return api_key

def test_flatfiles_formats(api_key: str):
    """Test different Flat Files API endpoint formats."""
    headers = {"X-CoinAPI-Key": api_key}
    
    # Test different date formats
    test_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y%m%d")
    
    # Different endpoint formats to try
    formats_to_test = [
        # Format 1: /v1/flatfiles/trades/{exchange}_{symbol}/{date}
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/KRAKEN_SPOT_BTC_USD/{test_date}",
        
        # Format 2: /v1/flatfiles/trades/{exchange}/{symbol}/{date}
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE/BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/KRAKEN/BTC_USD/{test_date}",
        
        # Format 3: /v1/flatfiles/trades/{exchange}_{symbol}_{date}
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT_{test_date}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/KRAKEN_SPOT_BTC_USD_{test_date}",
        
        # Format 4: /v1/flatfiles/{exchange}_{symbol}/{date}
        f"https://rest.coinapi.io/v1/flatfiles/BINANCE_SPOT_BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v1/flatfiles/KRAKEN_SPOT_BTC_USD/{test_date}",
        
        # Format 5: /v1/flatfiles/trades/{exchange}_{symbol}
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT",
        f"https://rest.coinapi.io/v1/flatfiles/trades/KRAKEN_SPOT_BTC_USD",
    ]
    
    print(f"🔍 Testing Flat Files API formats for date: {test_date}")
    print("="*80)
    
    for endpoint in formats_to_test:
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS: {endpoint}")
                print(f"   Content-Type: {response.headers.get('content-type', '')}")
                print(f"   Content-Length: {response.headers.get('content-length', '')}")
                
                # Try to read a bit of content
                try:
                    content_preview = response.text[:200]
                    print(f"   Content Preview: {content_preview}...")
                except:
                    print(f"   Content: Binary data")
                    
            elif response.status_code == 404:
                print(f"   ❌ Not Found: {endpoint}")
            elif response.status_code == 403:
                print(f"   ❌ Forbidden: {response.text[:100]}...")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def test_available_datasets(api_key: str):
    """Test what datasets are available."""
    headers = {"X-CoinAPI-Key": api_key}
    
    # Try to list available datasets
    dataset_endpoints = [
        "https://rest.coinapi.io/v1/flatfiles",
        "https://rest.coinapi.io/v1/flatfiles/",
        "https://rest.coinapi.io/v1/flatfiles/trades",
        "https://rest.coinapi.io/v1/flatfiles/trades/",
    ]
    
    print(f"\n🔍 Testing dataset listing endpoints")
    print("="*80)
    
    for endpoint in dataset_endpoints:
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS: {endpoint}")
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=2)[:500]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def main():
    print("🔍 COINAPI FLAT FILES FORMAT CHECK")
    print("="*80)
    
    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    test_flatfiles_formats(api_key)
    test_available_datasets(api_key)

if __name__ == "__main__":
    main()
