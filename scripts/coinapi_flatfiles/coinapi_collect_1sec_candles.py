#!/usr/bin/env python3
"""
CoinAPI Collect 1-Second Candles

Collect 1-second granular candle data for better ACD analysis.
"""

import os
import json
import pandas as pd
import boto3
import tempfile
import numpy as np
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

def get_coinapi_key() -> str:
    """Get CoinAPI key."""
    return "7f036b38-38d6-4ed6-9fce-00a06280a0f6"

def collect_1sec_candles(symbol: str, start_date: str, end_date: str) -> Tuple[bool, Dict[str, Any], Optional[pd.DataFrame]]:
    """Collect 1-second candles for a symbol."""
    api_key = get_coinapi_key()
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"
    
    url = f"{base_url}/ohlcv/{symbol}/history"
    params = {
        "period_id": "1SEC",
        "time_start": start_date,
        "time_end": end_date,
        "limit": 1000
    }
    
    all_candles = []
    current_start = start_date
    
    try:
        while current_start < end_date:
            params["time_start"] = current_start
            
            response = requests.get(url, headers=headers, params=params, timeout=60)
            
            if response.status_code == 200:
                candles = response.json()
                if candles:
                    all_candles.extend(candles)
                    # Move to next batch
                    last_time = candles[-1]['time_period_start']
                    current_start = (pd.to_datetime(last_time) + timedelta(seconds=1)).isoformat()
                else:
                    break
            elif response.status_code == 429:
                print(f"   Rate limited, waiting...")
                time.sleep(2)
                continue
            else:
                print(f"   Error {response.status_code}: {response.text[:100]}...")
                break
            
            # Rate limiting
            time.sleep(0.1)
        
        if all_candles:
            df = pd.DataFrame(all_candles)
            # Convert timestamps
            df['time_period_start'] = pd.to_datetime(df['time_period_start'], utc=True)
            df['time_period_end'] = pd.to_datetime(df['time_period_end'], utc=True)
            df['time_open'] = pd.to_datetime(df['time_open'], utc=True)
            df['time_close'] = pd.to_datetime(df['time_close'], utc=True)
            
            # Add venue info
            df['venue'] = symbol.split('_')[0].lower()
            df['symbol'] = symbol
            
            return True, {"message": f"Collected {len(df)} 1-second candles"}, df
        else:
            return False, {"message": "No candles collected"}, None
            
    except Exception as e:
        return False, {"message": f"Error: {e}"}, None

def main():
    print("🔍 COINAPI COLLECT 1-SECOND CANDLES")
    print("="*80)
    
    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    # Use the same 1-hour window as before
    window_start = "2025-09-25T00:00:00"
    window_end = "2025-09-25T01:00:00"
    
    s3_client = boto3.client('s3')
    
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    
    print(f"📊 Collecting 1-second candles for 1-hour window...")
    print(f"   Window: {window_start} to {window_end}")
    print(f"   Expected: ~3,600 candles per venue")
    
    all_results = {}
    
    for symbol in symbols:
        print(f"\n📊 Collecting {symbol}...")
        
        success, message, df = collect_1sec_candles(symbol, window_start, window_end)
        
        if success and df is not None:
            print(f"   ✅ {message['message']}")
            print(f"   📊 Time span: {df['time_period_start'].min()} to {df['time_period_start'].max()}")
            print(f"   📊 Price range: ${df['price_close'].min():.2f} - ${df['price_close'].max():.2f}")
            
            # Save to S3
            s3_key = f"coinapi_bf1/ohlcv_1sec/{date}/{symbol}/part-0000.parquet"
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                df.to_parquet(tmp_file.name, index=False)
                s3_client.upload_file(tmp_file.name, bucket, s3_key)
                Path(tmp_file.name).unlink()
            
            print(f"   💾 Saved: s3://{bucket}/{s3_key}")
            
            all_results[symbol] = {
                "status": "success",
                "n_candles": len(df),
                "time_span_hours": (df['time_period_start'].max() - df['time_period_start'].min()).total_seconds() / 3600,
                "price_stats": {
                    "mean": float(df['price_close'].mean()),
                    "std": float(df['price_close'].std()),
                    "min": float(df['price_close'].min()),
                    "max": float(df['price_close'].max())
                },
                "s3_key": s3_key
            }
        else:
            print(f"   ❌ {message['message']}")
            all_results[symbol] = {
                "status": "failed",
                "message": message['message']
            }
    
    # Save collection summary
    summary = {
        "window": {
            "start": window_start,
            "end": window_end
        },
        "granularity": "1SEC",
        "expected_candles_per_hour": 3600,
        "results": all_results,
        "collection_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    summary_key = f"coinapi_bf1/ohlcv_1sec/{date}/collection_summary.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=summary_key,
        Body=json.dumps(summary, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    print(f"\n💾 Saved collection summary: s3://{bucket}/{summary_key}")
    
    # Print final summary
    print(f"\n📊 COLLECTION SUMMARY")
    print("="*80)
    successful_venues = [symbol for symbol, result in all_results.items() if result["status"] == "success"]
    print(f"Successful venues: {len(successful_venues)}")
    
    for symbol, result in all_results.items():
        if result["status"] == "success":
            print(f"   {symbol}: {result['n_candles']} candles, {result['time_span_hours']:.1f}h")
        else:
            print(f"   {symbol}: {result['message']}")
    
    if len(successful_venues) >= 2:
        print(f"\n✅ Ready for 1-second ACD analysis!")
        print(f"   📊 {len(successful_venues)} venues with 1-second granularity")
        print(f"   📊 Expected ~3,600 data points per venue")
        print(f"   📊 Much finer granularity for lead-lag analysis")
    else:
        print(f"\n❌ Insufficient data for 1-second ACD analysis")

if __name__ == "__main__":
    import time
    main()
