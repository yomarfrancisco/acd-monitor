#!/usr/bin/env python3
"""
CoinAPI Test Flat Files with New Key

Test the Flat Files API with the new API key to see if it's available.
"""

import json
from datetime import datetime, timedelta, timezone

import requests


def test_flatfiles_with_new_key():
    """Test Flat Files API with the new key."""
    api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"

    print("🔍 Testing Flat Files API with new key...")
    print("=" * 80)

    # Test different date formats and symbols
    test_dates = [
        "20250925",  # YYYYMMDD format
        "2025-09-25",  # YYYY-MM-DD format
        "20250926",
        "20250927",
    ]

    test_symbols = [
        "BINANCE_SPOT_BTC_USDT",
        "KRAKEN_SPOT_BTC_USD",
        "COINBASE_SPOT_BTC_USD",
        "OKX_SPOT_BTC_USDT",
        "BYBIT_SPOT_BTC_USDT",
    ]

    successful_requests = []

    for date in test_dates:
        print(f"\n📅 Testing date: {date}")
        for symbol in test_symbols:
            endpoint = f"/flatfiles/trades/{symbol}/{date}"
            url = f"{base_url}{endpoint}"

            try:
                print(f"   🔍 Testing: {symbol}")
                response = requests.get(url, headers=headers, timeout=30)
                print(f"      Status: {response.status_code}")

                if response.status_code == 200:
                    print(f"      ✅ SUCCESS: {symbol} for {date}")
                    successful_requests.append(
                        {
                            "symbol": symbol,
                            "date": date,
                            "endpoint": endpoint,
                            "content_type": response.headers.get("content-type", ""),
                            "content_length": response.headers.get("content-length", ""),
                            "status_code": response.status_code,
                        }
                    )

                    # Try to read a bit of content to see what we get
                    try:
                        content_preview = response.text[:500]
                        print(f"      Content preview: {content_preview}...")
                    except:
                        print(f"      Content: Binary data")

                elif response.status_code == 404:
                    print(f"      ❌ Not Found: {symbol} for {date}")
                elif response.status_code == 403:
                    print(f"      ❌ Forbidden: {response.text[:100]}...")
                elif response.status_code == 400:
                    print(f"      ❌ Bad Request: {response.text[:100]}...")
                else:
                    print(f"      ❌ Error {response.status_code}: {response.text[:100]}...")

            except Exception as e:
                print(f"      ❌ Exception: {e}")

    print(f"\n📊 SUMMARY")
    print("=" * 80)
    print(f"Total requests made: {len(test_dates) * len(test_symbols)}")
    print(f"Successful requests: {len(successful_requests)}")

    if successful_requests:
        print(f"\n✅ SUCCESSFUL FLAT FILES ACCESS:")
        for req in successful_requests:
            print(f"   - {req['symbol']} for {req['date']}")
            print(f"     Content-Type: {req['content_type']}")
            print(f"     Content-Length: {req['content_length']}")
    else:
        print(f"\n❌ NO FLAT FILES ACCESS")
        print("   Flat Files API is not available with this key")

    return successful_requests


def test_alternative_flatfiles_endpoints():
    """Test alternative Flat Files endpoint formats."""
    api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    headers = {"X-CoinAPI-Key": api_key}

    # Test different base URLs and endpoint formats
    test_configs = [
        {
            "base_url": "https://rest.coinapi.io/v1",
            "endpoint": "/flatfiles/trades/BINANCE_SPOT_BTC_USDT/20250925",
        },
        {
            "base_url": "https://api.coinapi.io/v1",
            "endpoint": "/flatfiles/trades/BINANCE_SPOT_BTC_USDT/20250925",
        },
        {
            "base_url": "https://rest.coinapi.io/v2",
            "endpoint": "/flatfiles/trades/BINANCE_SPOT_BTC_USDT/20250925",
        },
        {
            "base_url": "https://rest.coinapi.io/v1",
            "endpoint": "/data/flatfiles/trades/BINANCE_SPOT_BTC_USDT/20250925",
        },
        {
            "base_url": "https://rest.coinapi.io/v1",
            "endpoint": "/files/trades/BINANCE_SPOT_BTC_USDT/20250925",
        },
    ]

    print(f"\n🔍 Testing alternative Flat Files endpoints...")
    print("=" * 80)

    for config in test_configs:
        url = f"{config['base_url']}{config['endpoint']}"
        try:
            print(f"\n🔍 Testing: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ SUCCESS: {url}")
                print(f"   Content-Type: {response.headers.get('content-type', '')}")
                print(f"   Content-Length: {response.headers.get('content-length', '')}")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")

        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    successful_requests = test_flatfiles_with_new_key()
    test_alternative_flatfiles_endpoints()
