#!/usr/bin/env python3
"""
CoinAPI - Check Available Endpoints

Check what endpoints are actually available with the current API key.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import requests


def get_coinapi_key() -> str:
    """Get CoinAPI key from environment variable."""
    api_key = os.getenv("COINAPI_KEY")
    if not api_key:
        raise ValueError("COINAPI_KEY environment variable not set")
    return api_key


def check_available_endpoints(api_key: str):
    """Check what endpoints are available."""
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"

    # List of endpoints to test
    endpoints_to_test = [
        # Basic endpoints
        "/exchanges",
        "/symbols",
        "/assets",
        # Historical data endpoints
        "/ohlcv/BINANCE_SPOT_BTC_USDT/latest",
        "/ohlcv/BINANCE_SPOT_BTC_USDT/history",
        "/trades/BINANCE_SPOT_BTC_USDT/latest",
        "/trades/BINANCE_SPOT_BTC_USDT/history",
        "/quotes/BINANCE_SPOT_BTC_USDT/latest",
        "/quotes/BINANCE_SPOT_BTC_USDT/history",
        "/orderbooks/BINANCE_SPOT_BTC_USDT/latest",
        "/orderbooks/BINANCE_SPOT_BTC_USDT/history",
        # Alternative data endpoints
        "/exchangerate/BTC/USD",
        "/exchangerate/BTC/USD/history",
        # Flat files alternatives
        "/data/trades/BINANCE_SPOT_BTC_USDT/latest",
        "/data/ohlcv/BINANCE_SPOT_BTC_USDT/latest",
        "/files/trades/BINANCE_SPOT_BTC_USDT/latest",
        "/datasets/trades/BINANCE_SPOT_BTC_USDT/latest",
        # Bulk data endpoints
        "/bulk/trades/BINANCE_SPOT_BTC_USDT",
        "/bulk/ohlcv/BINANCE_SPOT_BTC_USDT",
        # Alternative formats
        "/trades/BINANCE_SPOT_BTC_USDT/2025-09-25",
        "/trades/BINANCE_SPOT_BTC_USDT/20250925",
    ]

    print(f"🔍 Testing available endpoints")
    print("=" * 80)

    available_endpoints = []

    for endpoint in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ SUCCESS: {endpoint}")
                available_endpoints.append(endpoint)

                # Try to get some info about the response
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   Response: {len(data)} items")
                        if len(data) > 0:
                            print(f"   Sample: {json.dumps(data[0], indent=2)[:200]}...")
                    else:
                        print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")

            elif response.status_code == 400:
                print(f"   ⚠️  Bad Request: {response.text[:100]}...")
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized: {response.text[:100]}...")
            elif response.status_code == 403:
                print(f"   ❌ Forbidden: {response.text[:100]}...")
            elif response.status_code == 404:
                print(f"   ❌ Not Found: {endpoint}")
            elif response.status_code == 429:
                print(f"   ⚠️  Rate Limited: {response.text[:100]}...")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")

        except Exception as e:
            print(f"   ❌ Exception: {e}")

    print(f"\n📊 SUMMARY")
    print("=" * 80)
    print(f"Total endpoints tested: {len(endpoints_to_test)}")
    print(f"Available endpoints: {len(available_endpoints)}")

    if available_endpoints:
        print(f"\n✅ Available endpoints:")
        for endpoint in available_endpoints:
            print(f"   - {endpoint}")
    else:
        print(f"\n❌ No additional endpoints found beyond basic ones")


def check_historical_data_access(api_key: str):
    """Check if we can access historical data through standard endpoints."""
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"

    # Test historical data access
    test_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    historical_endpoints = [
        f"/ohlcv/BINANCE_SPOT_BTC_USDT/history?period_id=1MIN&time_start={test_date}T00:00:00&time_end={test_date}T23:59:59&limit=100",
        f"/trades/BINANCE_SPOT_BTC_USDT/history?time_start={test_date}T00:00:00&time_end={test_date}T23:59:59&limit=100",
        f"/quotes/BINANCE_SPOT_BTC_USDT/history?time_start={test_date}T00:00:00&time_end={test_date}T23:59:59&limit=100",
    ]

    print(f"\n🔍 Testing historical data access")
    print("=" * 80)

    for endpoint in historical_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            print(f"\n🔍 Testing: {endpoint}")
            response = requests.get(url, headers=headers, timeout=30)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ SUCCESS: {endpoint}")
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   Response: {len(data)} items")
                        if len(data) > 0:
                            print(f"   Sample: {json.dumps(data[0], indent=2)[:300]}...")
                    else:
                        print(f"   Response: {json.dumps(data, indent=2)[:300]}...")
                except:
                    print(f"   Response: {response.text[:300]}...")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")

        except Exception as e:
            print(f"   ❌ Exception: {e}")


def main():
    print("🔍 COINAPI AVAILABLE ENDPOINTS CHECK")
    print("=" * 80)

    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return

    check_available_endpoints(api_key)
    check_historical_data_access(api_key)


if __name__ == "__main__":
    main()
