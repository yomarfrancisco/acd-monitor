#!/usr/bin/env python3
"""
CoinAPI Test Granular Candles

Test different period_id values to see what granular candle data is available.
"""

import json
from datetime import datetime, timedelta, timezone

import requests


def test_granular_candles():
    """Test different granular candle periods."""
    api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"

    # Test different period_id values
    period_ids = [
        "1SEC",  # 1 second
        "2SEC",  # 2 seconds
        "5SEC",  # 5 seconds
        "10SEC",  # 10 seconds
        "15SEC",  # 15 seconds
        "30SEC",  # 30 seconds
        "1MIN",  # 1 minute (we know this works)
        "2MIN",  # 2 minutes
        "3MIN",  # 3 minutes
        "5MIN",  # 5 minutes
        "10MIN",  # 10 minutes
        "15MIN",  # 15 minutes
        "30MIN",  # 30 minutes
        "1HRS",  # 1 hour
        "2HRS",  # 2 hours
        "4HRS",  # 4 hours
        "6HRS",  # 6 hours
        "8HRS",  # 8 hours
        "12HRS",  # 12 hours
        "1DAY",  # 1 day
        "2DAY",  # 2 days
        "3DAY",  # 3 days
        "1WEEK",  # 1 week
        "1MTH",  # 1 month
        "1YRS",  # 1 year
    ]

    # Test with a recent date
    test_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    time_start = f"{test_date}T00:00:00"
    time_end = f"{test_date}T23:59:59"

    symbol = "BINANCE_SPOT_BTC_USDT"

    print("🔍 Testing granular candle periods...")
    print("=" * 80)
    print(f"Symbol: {symbol}")
    print(f"Date: {test_date}")
    print(f"Time range: {time_start} to {time_end}")
    print()

    available_periods = []
    unavailable_periods = []

    for period_id in period_ids:
        print(f"🔍 Testing {period_id}...")

        url = f"{base_url}/ohlcv/{symbol}/history"
        params = {
            "period_id": period_id,
            "time_start": time_start,
            "time_end": time_end,
            "limit": 10,  # Just get a few samples
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    print(f"   ✅ SUCCESS: {len(data)} candles")
                    available_periods.append(
                        {
                            "period_id": period_id,
                            "n_candles": len(data),
                            "sample_data": data[0] if data else None,
                        }
                    )

                    # Show sample data structure
                    if data:
                        sample = data[0]
                        print(
                            f"   📊 Sample: {sample.get('time_period_start', 'N/A')} - ${sample.get('price_close', 'N/A')}"
                        )
                else:
                    print(f"   ⚠️  Empty response")
                    unavailable_periods.append(period_id)
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", "Bad Request")
                print(f"   ❌ Bad Request: {error_msg}")
                unavailable_periods.append(period_id)
            elif response.status_code == 404:
                print(f"   ❌ Not Found")
                unavailable_periods.append(period_id)
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                unavailable_periods.append(period_id)

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            unavailable_periods.append(period_id)

    print(f"\n📊 SUMMARY")
    print("=" * 80)
    print(f"Available periods: {len(available_periods)}")
    print(f"Unavailable periods: {len(unavailable_periods)}")

    if available_periods:
        print(f"\n✅ AVAILABLE GRANULAR PERIODS:")
        for period in available_periods:
            print(f"   - {period['period_id']}: {period['n_candles']} candles")

    if unavailable_periods:
        print(f"\n❌ UNAVAILABLE PERIODS:")
        for period in unavailable_periods:
            print(f"   - {period}")

    # Test the most granular available period with more data
    if available_periods:
        most_granular = min(available_periods, key=lambda x: x["period_id"])
        print(f"\n🔍 Testing {most_granular['period_id']} with more data...")

        url = f"{base_url}/ohlcv/{symbol}/history"
        params = {
            "period_id": most_granular["period_id"],
            "time_start": time_start,
            "time_end": time_end,
            "limit": 1000,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Retrieved {len(data)} candles")

                if len(data) > 1:
                    # Analyze time intervals
                    timestamps = [pd.to_datetime(candle["time_period_start"]) for candle in data]
                    intervals = [
                        (timestamps[i + 1] - timestamps[i]).total_seconds()
                        for i in range(len(timestamps) - 1)
                    ]

                    print(f"   📊 Time intervals:")
                    print(f"      Mean: {np.mean(intervals):.1f} seconds")
                    print(f"      Std: {np.std(intervals):.1f} seconds")
                    print(f"      Min: {min(intervals):.1f} seconds")
                    print(f"      Max: {max(intervals):.1f} seconds")

                    # Check if intervals are regular
                    cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
                    print(f"      CV: {cv:.3f} ({'regular' if cv < 0.05 else 'irregular'})")
            else:
                print(f"   ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

    return available_periods, unavailable_periods


if __name__ == "__main__":
    import numpy as np
    import pandas as pd

    available, unavailable = test_granular_candles()
