#!/usr/bin/env python3
"""
CoinAPI Flat Files - Check API Access

Test CoinAPI access and available endpoints.
"""

import os
import requests
import json

def get_coinapi_key() -> str:
    """Get CoinAPI key from environment variable."""
    api_key = os.getenv('COINAPI_KEY')
    if not api_key:
        raise ValueError("COINAPI_KEY environment variable not set")
    return api_key

def test_endpoints(api_key: str):
    """Test various CoinAPI endpoints."""
    headers = {"X-CoinAPI-Key": api_key}
    
    endpoints = [
        "https://rest.coinapi.io/v1/exchanges",
        "https://rest.coinapi.io/v1/symbols", 
        "https://rest.coinapi.io/v1/assets",
        "https://rest.coinapi.io/v1/exchangerate/BTC/USD",
        "https://rest.coinapi.io/v1/ohlcv/BINANCE_SPOT_BTC_USDT/latest?period_id=1DAY"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"   Response: {len(data)} items")
                else:
                    print(f"   Response: {type(data).__name__}")
            else:
                print(f"   Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   Exception: {e}")

def test_flat_files_access(api_key: str):
    """Test Flat Files API access."""
    headers = {"X-CoinAPI-Key": api_key}
    
    # Try to access flat files for a recent date
    from datetime import datetime, timezone, timedelta
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = yesterday.strftime("%Y%m%d")
    
    # Try different flat file endpoints
    flat_file_endpoints = [
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{date_str}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/KRAKEN_SPOT_BTC_USD/{date_str}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/COINBASE_SPOT_BTC_USD/{date_str}"
    ]
    
    for endpoint in flat_file_endpoints:
        try:
            print(f"\n🔍 Testing Flat File: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   Success: Flat file accessible")
            else:
                print(f"   Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   Exception: {e}")

def main():
    print("🔍 COINAPI ACCESS CHECK")
    print("="*50)
    
    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    print(f"\n🔍 Testing REST API endpoints...")
    test_endpoints(api_key)
    
    print(f"\n🔍 Testing Flat Files API...")
    test_flat_files_access(api_key)

if __name__ == "__main__":
    main()
