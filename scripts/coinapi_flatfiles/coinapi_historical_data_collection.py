#!/usr/bin/env python3
"""
CoinAPI Historical Data Collection

Use available CoinAPI endpoints to collect historical data for ACD analysis.
"""

import os
import requests
import json
import pandas as pd
import boto3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

def get_coinapi_key() -> str:
    """Get CoinAPI key from environment variable or use provided key."""
    api_key = os.getenv('COINAPI_KEY')
    if not api_key:
        # Use the provided key as fallback
        api_key = "7f036b38-38d6-4ed6-9fce-00a06280a0f6"
    return api_key

def collect_historical_ohlcv_data(api_key: str, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Collect historical OHLCV data."""
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"
    
    # Convert dates to proper format
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    
    all_data = []
    
    # Collect data day by day to avoid timeouts
    current_date = start_dt
    while current_date <= end_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        time_start = f"{date_str}T00:00:00"
        time_end = f"{date_str}T23:59:59"
        
        url = f"{base_url}/ohlcv/{symbol}/history"
        params = {
            "period_id": "1MIN",
            "time_start": time_start,
            "time_end": time_end,
            "limit": 1000
        }
        
        print(f"📊 Collecting OHLCV data for {date_str}...")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    all_data.extend(data)
                    print(f"   ✅ Collected {len(data)} OHLCV records for {date_str}")
                else:
                    print(f"   ⚠️  No data for {date_str}")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Exception for {date_str}: {e}")
        
        current_date += timedelta(days=1)
        
        # Rate limiting
        import time
        time.sleep(1)
    
    if all_data:
        df = pd.DataFrame(all_data)
        # Convert time columns to datetime
        df['time_period_start'] = pd.to_datetime(df['time_period_start'])
        df['time_period_end'] = pd.to_datetime(df['time_period_end'])
        df['time_open'] = pd.to_datetime(df['time_open'])
        df['time_close'] = pd.to_datetime(df['time_close'])
        
        # Add venue information
        df['venue'] = symbol.split('_')[0].lower()
        df['symbol'] = symbol
        
        return df
    else:
        return None

def collect_latest_trades_data(api_key: str, symbol: str, limit: int = 1000) -> Optional[pd.DataFrame]:
    """Collect latest trades data."""
    headers = {"X-CoinAPI-Key": api_key}
    base_url = "https://rest.coinapi.io/v1"
    
    url = f"{base_url}/trades/{symbol}/latest"
    params = {"limit": limit}
    
    print(f"📊 Collecting latest trades for {symbol}...")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                # Convert time columns to datetime
                df['time_exchange'] = pd.to_datetime(df['time_exchange'])
                df['time_coinapi'] = pd.to_datetime(df['time_coinapi'])
                
                # Add venue information
                df['venue'] = symbol.split('_')[0].lower()
                df['symbol'] = symbol
                
                print(f"   ✅ Collected {len(df)} trade records")
                return df
            else:
                print(f"   ⚠️  No data returned")
                return None
        else:
            print(f"   ❌ Error {response.status_code}: {response.text[:100]}...")
            return None
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None

def save_data_to_s3(df: pd.DataFrame, bucket: str, key: str):
    """Save DataFrame to S3 as parquet."""
    s3_client = boto3.client('s3')
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
        df.to_parquet(tmp_file.name, index=False)
        s3_client.upload_file(tmp_file.name, bucket, key)
        Path(tmp_file.name).unlink()
    
    print(f"💾 Saved data to s3://{bucket}/{key}")

def main():
    print("🔍 COINAPI HISTORICAL DATA COLLECTION")
    print("="*80)
    
    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    # Symbols to collect
    symbols = [
        "BINANCE_SPOT_BTC_USDT",
        "KRAKEN_SPOT_BTC_USD", 
        "COINBASE_SPOT_BTC_USD",
        "OKX_SPOT_BTC_USDT",
        "BYBIT_SPOT_BTC_USDT"
    ]
    
    # Date range (last 7 days)
    end_date = date
    start_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"📅 Date range: {start_date} to {end_date}")
    print(f"🎯 Symbols: {', '.join(symbols)}")
    
    # Collect data for each symbol
    all_results = {}
    
    for symbol in symbols:
        print(f"\n📊 Processing {symbol}...")
        
        # Try to collect historical OHLCV data
        ohlcv_df = collect_historical_ohlcv_data(api_key, symbol, start_date, end_date)
        
        # Try to collect latest trades data
        trades_df = collect_latest_trades_data(api_key, symbol, limit=1000)
        
        symbol_results = {
            "symbol": symbol,
            "ohlcv_count": 0,
            "trades_count": 0,
            "ohlcv_s3_key": None,
            "trades_s3_key": None
        }
        
        if ohlcv_df is not None:
            symbol_results["ohlcv_count"] = len(ohlcv_df)
            
            # Save OHLCV data
            ohlcv_key = f"coinapi_bf1/ohlcv/{date}/{symbol.replace('_', '_')}/part-0000.parquet"
            save_data_to_s3(ohlcv_df, bucket, ohlcv_key)
            symbol_results["ohlcv_s3_key"] = ohlcv_key
        
        if trades_df is not None:
            symbol_results["trades_count"] = len(trades_df)
            
            # Save trades data
            trades_key = f"coinapi_bf1/trades/{date}/{symbol.replace('_', '_')}/part-0000.parquet"
            save_data_to_s3(trades_df, bucket, trades_key)
            symbol_results["trades_s3_key"] = trades_key
        
        all_results[symbol] = symbol_results
        
        print(f"   📊 OHLCV: {symbol_results['ohlcv_count']} records")
        print(f"   📊 Trades: {symbol_results['trades_count']} records")
    
    # Save summary
    summary = {
        "date": date,
        "start_date": start_date,
        "end_date": end_date,
        "symbols": symbols,
        "results": all_results,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    s3_client = boto3.client('s3')
    summary_key = f"coinapi_bf1/summary/{date}/collection_summary.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=summary_key,
        Body=json.dumps(summary, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    print(f"\n💾 Saved summary to s3://{bucket}/{summary_key}")
    
    # Print final summary
    print(f"\n📊 COLLECTION SUMMARY")
    print("="*80)
    for symbol, results in all_results.items():
        print(f"{symbol}:")
        print(f"   OHLCV: {results['ohlcv_count']} records")
        print(f"   Trades: {results['trades_count']} records")

if __name__ == "__main__":
    main()
