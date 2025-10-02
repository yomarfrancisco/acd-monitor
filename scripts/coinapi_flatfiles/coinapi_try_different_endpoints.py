#!/usr/bin/env python3
"""
CoinAPI Flat Files - Try Different Endpoints

Test various CoinAPI endpoint formats to find the correct Flat Files API.
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

def test_different_api_versions(api_key: str):
    """Test different API versions and endpoints."""
    headers = {"X-CoinAPI-Key": api_key}
    
    # Test different API versions
    api_versions = ["v1", "v2", "v3"]
    base_urls = [
        "https://rest.coinapi.io",
        "https://api.coinapi.io", 
        "https://data.coinapi.io"
    ]
    
    test_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"🔍 Testing different API versions and base URLs")
    print("="*80)
    
    for base_url in base_urls:
        for version in api_versions:
            # Test basic endpoints
            basic_endpoints = [
                f"{base_url}/{version}/exchanges",
                f"{base_url}/{version}/symbols",
                f"{base_url}/{version}/assets"
            ]
            
            for endpoint in basic_endpoints:
                try:
                    print(f"\n🔍 Testing: {endpoint}")
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    print(f"   Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"   ✅ SUCCESS: {endpoint}")
                        data = response.json()
                        if isinstance(data, list):
                            print(f"   Response: {len(data)} items")
                        else:
                            print(f"   Response: {type(data).__name__}")
                    else:
                        print(f"   ❌ Error {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Exception: {e}")

def test_flatfiles_alternative_formats(api_key: str):
    """Test alternative Flat Files endpoint formats."""
    headers = {"X-CoinAPI-Key": api_key}
    
    test_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y%m%d")
    
    # Alternative Flat Files formats
    flatfiles_formats = [
        # Format 1: Different base URLs
        f"https://data.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        f"https://api.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        
        # Format 2: Different API versions
        f"https://rest.coinapi.io/v2/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v3/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        
        # Format 3: Different endpoint structures
        f"https://rest.coinapi.io/v1/data/flatfiles/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v1/files/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v1/datasets/trades/BINANCE_SPOT_BTC_USDT/{test_date}",
        
        # Format 4: Different date formats
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/2025-09-25",
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/20250925",
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC_USDT/25-09-2025",
        
        # Format 5: Different symbol formats
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_BTC_USDT/{test_date}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTCUSDT/{test_date}",
        f"https://rest.coinapi.io/v1/flatfiles/trades/BINANCE_SPOT_BTC-USDT/{test_date}",
    ]
    
    print(f"\n🔍 Testing alternative Flat Files formats")
    print("="*80)
    
    for endpoint in flatfiles_formats:
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

def test_coinapi_documentation_endpoints(api_key: str):
    """Test endpoints that might be documented in CoinAPI docs."""
    headers = {"X-CoinAPI-Key": api_key}
    
    # Try to find documentation or available endpoints
    doc_endpoints = [
        "https://rest.coinapi.io/v1/",
        "https://rest.coinapi.io/v1/docs",
        "https://rest.coinapi.io/v1/endpoints",
        "https://rest.coinapi.io/v1/status",
        "https://rest.coinapi.io/v1/health",
        "https://rest.coinapi.io/v1/limits",
        "https://rest.coinapi.io/v1/usage",
    ]
    
    print(f"\n🔍 Testing documentation and status endpoints")
    print("="*80)
    
    for endpoint in doc_endpoints:
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
    print("🔍 COINAPI ALTERNATIVE ENDPOINTS TEST")
    print("="*80)
    
    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    test_different_api_versions(api_key)
    test_flatfiles_alternative_formats(api_key)
    test_coinapi_documentation_endpoints(api_key)

if __name__ == "__main__":
    main()
