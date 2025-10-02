#!/usr/bin/env python3
"""
CoinAPI Check Historical Data Availability

Check how much historical data is available from CoinAPI for extending the timeseries.
"""

import requests
import json
from datetime import datetime, timezone, timedelta
import pandas as pd

def check_historical_availability():
    """Check historical data availability for different time periods."""
    api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"
    
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    
    # Test different time periods going back in time
    test_periods = [
        ("1 hour ago", 1, "hour"),
        ("6 hours ago", 6, "hour"),
        ("12 hours ago", 12, "hour"),
        ("1 day ago", 1, "day"),
        ("2 days ago", 2, "day"),
        ("3 days ago", 3, "day"),
        ("1 week ago", 7, "day"),
        ("2 weeks ago", 14, "day"),
        ("1 month ago", 30, "day"),
        ("2 months ago", 60, "day"),
        ("3 months ago", 90, "day"),
        ("6 months ago", 180, "day"),
        ("1 year ago", 365, "day")
    ]
    
    print("🔍 COINAPI HISTORICAL DATA AVAILABILITY CHECK")
    print("="*80)
    print("Testing 1-second candle availability for different time periods...")
    print()
    
    availability_results = {}
    
    for period_name, period_value, period_unit in test_periods:
        print(f"📊 Testing {period_name}...")
        
        # Calculate target date
        if period_unit == "hour":
            target_time = datetime.now(timezone.utc) - timedelta(hours=period_value)
        elif period_unit == "day":
            target_time = datetime.now(timezone.utc) - timedelta(days=period_value)
        
        target_date = target_time.strftime("%Y-%m-%d")
        time_start = f"{target_date}T00:00:00"
        time_end = f"{target_date}T23:59:59"
        
        period_results = {
            "target_date": target_date,
            "target_time": target_time.isoformat(),
            "venues": {}
        }
        
        for symbol in symbols:
            print(f"   🔍 Testing {symbol} for {target_date}...")
            
            url = f"{base_url}/ohlcv/{symbol}/history"
            params = {
                "period_id": "1SEC",
                "time_start": time_start,
                "time_end": time_end,
                "limit": 100  # Just check availability, not full data
            }
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        # Get actual time range from data
                        actual_start = pd.to_datetime(data[0]['time_period_start'])
                        actual_end = pd.to_datetime(data[-1]['time_period_start'])
                        actual_duration = (actual_end - actual_start).total_seconds()
                        
                        period_results["venues"][symbol] = {
                            "status": "available",
                            "n_candles": len(data),
                            "actual_start": actual_start.isoformat(),
                            "actual_end": actual_end.isoformat(),
                            "duration_hours": actual_duration / 3600,
                            "coverage_pct": (len(data) / 86400) * 100  # Assuming 24h day
                        }
                        print(f"      ✅ {len(data)} candles, {actual_duration/3600:.1f}h span")
                    else:
                        period_results["venues"][symbol] = {
                            "status": "no_data",
                            "message": "Empty response"
                        }
                        print(f"      ❌ No data")
                elif response.status_code == 400:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get('error', 'Bad Request')
                    period_results["venues"][symbol] = {
                        "status": "error",
                        "message": error_msg
                    }
                    print(f"      ❌ Bad Request: {error_msg}")
                elif response.status_code == 404:
                    period_results["venues"][symbol] = {
                        "status": "not_found",
                        "message": "Not found"
                    }
                    print(f"      ❌ Not found")
                else:
                    period_results["venues"][symbol] = {
                        "status": "error",
                        "message": f"HTTP {response.status_code}"
                    }
                    print(f"      ❌ Error {response.status_code}")
                    
            except Exception as e:
                period_results["venues"][symbol] = {
                    "status": "error",
                    "message": str(e)
                }
                print(f"      ❌ Exception: {e}")
        
        availability_results[period_name] = period_results
        print()
    
    # Analyze results
    print("📊 HISTORICAL AVAILABILITY SUMMARY")
    print("="*80)
    
    for period_name, results in availability_results.items():
        available_venues = [symbol for symbol, venue_data in results["venues"].items() 
                          if venue_data["status"] == "available"]
        
        print(f"{period_name}:")
        print(f"   Available venues: {len(available_venues)}/{len(symbols)}")
        
        if available_venues:
            for symbol in available_venues:
                venue_data = results["venues"][symbol]
                print(f"   {symbol}: {venue_data['n_candles']} candles, {venue_data['duration_hours']:.1f}h")
        else:
            print(f"   ❌ No venues available")
        print()
    
    # Find the furthest back we can go with all venues
    print("📊 MAXIMUM HISTORICAL REACH")
    print("="*80)
    
    max_reach = None
    for period_name, results in availability_results.items():
        available_venues = [symbol for symbol, venue_data in results["venues"].items() 
                          if venue_data["status"] == "available"]
        
        if len(available_venues) == len(symbols):
            max_reach = period_name
            print(f"✅ All venues available: {period_name}")
        elif len(available_venues) > 0:
            print(f"⚠️  Partial availability: {period_name} ({len(available_venues)}/{len(symbols)} venues)")
        else:
            print(f"❌ No availability: {period_name}")
    
    if max_reach:
        print(f"\n🎯 RECOMMENDATION: Can extend timeseries back to {max_reach}")
        print(f"   📊 This would provide much longer panel data for ACD analysis")
        print(f"   📊 Could analyze coordination patterns over days/weeks/months")
    else:
        print(f"\n⚠️  LIMITED HISTORICAL DATA")
        print(f"   📊 May need to use shorter timeframes or different data sources")
    
    return availability_results

def check_data_limits():
    """Check if there are any API limits on data retrieval."""
    api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"
    
    print("\n🔍 CHECKING API LIMITS")
    print("="*80)
    
    # Test with a recent date to see limits
    test_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    time_start = f"{test_date}T00:00:00"
    time_end = f"{test_date}T23:59:59"
    
    symbol = "BINANCE_SPOT_BTC_USDT"
    
    # Test different limit values
    limits_to_test = [100, 1000, 5000, 10000, 50000]
    
    for limit in limits_to_test:
        print(f"📊 Testing limit={limit}...")
        
        url = f"{base_url}/ohlcv/{symbol}/history"
        params = {
            "period_id": "1SEC",
            "time_start": time_start,
            "time_end": time_end,
            "limit": limit
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success: {len(data)} candles returned")
            elif response.status_code == 400:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('error', 'Bad Request')
                print(f"   ❌ Bad Request: {error_msg}")
            else:
                print(f"   ❌ Error {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    availability_results = check_historical_availability()
    check_data_limits()
