#!/usr/bin/env python3
"""
CoinAPI ACD Analysis

Analyze the collected CoinAPI data and build canonical windows for ACD analysis.
"""

import os
import json
import pandas as pd
import boto3
import tempfile
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        print(f"Error getting S3 object {key}: {e}")
        return None

def load_coinapi_data(s3_client, bucket: str, date: str, symbol: str, data_type: str) -> Optional[pd.DataFrame]:
    """Load CoinAPI data from S3."""
    key = f"coinapi_bf1/{data_type}/{date}/{symbol}/part-0000.parquet"
    content = get_s3_object_content(s3_client, bucket, key)
    
    if content is None:
        return None
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()
        return df
    except Exception as e:
        print(f"Error loading {key}: {e}")
        return None

def analyze_ohlcv_data(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Analyze OHLCV data for ACD characteristics."""
    if df.empty:
        return {"status": "empty", "message": "No data"}
    
    # Basic stats
    n_records = len(df)
    time_span = (df['time_period_end'].max() - df['time_period_start'].min()).total_seconds()
    
    # Price analysis
    price_stats = {
        "mean": float(df['price_close'].mean()),
        "std": float(df['price_close'].std()),
        "min": float(df['price_close'].min()),
        "max": float(df['price_close'].max()),
        "cv": float(df['price_close'].std() / df['price_close'].mean()) if df['price_close'].mean() > 0 else 0
    }
    
    # Volume analysis
    volume_stats = {
        "mean": float(df['volume_traded'].mean()),
        "std": float(df['volume_traded'].std()),
        "total": float(df['volume_traded'].sum())
    }
    
    # Time analysis
    time_deltas = df['time_period_start'].diff().dt.total_seconds().dropna()
    time_stats = {
        "mean_interval": float(time_deltas.mean()),
        "std_interval": float(time_deltas.std()),
        "cv_interval": float(time_deltas.std() / time_deltas.mean()) if time_deltas.mean() > 0 else 0
    }
    
    # ACD indicators
    price_changes = df['price_close'].pct_change().dropna()
    volatility = price_changes.std()
    
    # Check for regular intervals (synthetic data indicator)
    is_regular = time_stats["cv_interval"] < 0.05 and abs(time_stats["mean_interval"] - 60) < 5
    
    return {
        "status": "success",
        "symbol": symbol,
        "n_records": n_records,
        "time_span_hours": time_span / 3600,
        "price_stats": price_stats,
        "volume_stats": volume_stats,
        "time_stats": time_stats,
        "volatility": float(volatility),
        "is_regular_intervals": bool(is_regular),
        "data_quality": "good" if not is_regular and volatility > 0.001 else "suspicious"
    }

def analyze_trades_data(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Analyze trades data for ACD characteristics."""
    if df.empty:
        return {"status": "empty", "message": "No data"}
    
    # Basic stats
    n_records = len(df)
    time_span = (df['time_exchange'].max() - df['time_exchange'].min()).total_seconds()
    
    # Price analysis
    price_stats = {
        "mean": float(df['price'].mean()),
        "std": float(df['price'].std()),
        "min": float(df['price'].min()),
        "max": float(df['price'].max()),
        "cv": float(df['price'].std() / df['price'].mean()) if df['price'].mean() > 0 else 0
    }
    
    # Volume analysis
    volume_stats = {
        "mean": float(df['size'].mean()),
        "std": float(df['size'].std()),
        "total": float(df['size'].sum())
    }
    
    # Time analysis
    time_deltas = df['time_exchange'].diff().dt.total_seconds().dropna()
    time_stats = {
        "mean_interval": float(time_deltas.mean()),
        "std_interval": float(time_deltas.std()),
        "cv_interval": float(time_deltas.std() / time_deltas.mean()) if time_deltas.mean() > 0 else 0
    }
    
    # ACD indicators
    price_changes = df['price'].pct_change().dropna()
    volatility = price_changes.std()
    
    # Check for regular intervals (synthetic data indicator)
    is_regular = time_stats["cv_interval"] < 0.05 and time_stats["mean_interval"] < 10
    
    return {
        "status": "success",
        "symbol": symbol,
        "n_records": n_records,
        "time_span_hours": time_span / 3600,
        "price_stats": price_stats,
        "volume_stats": volume_stats,
        "time_stats": time_stats,
        "volatility": float(volatility),
        "is_regular_intervals": bool(is_regular),
        "data_quality": "good" if not is_regular and volatility > 0.001 else "suspicious"
    }

def find_common_time_windows(ohlcv_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Find common time windows across venues."""
    if not ohlcv_data:
        return []
    
    # Get time ranges for each venue
    time_ranges = {}
    for symbol, df in ohlcv_data.items():
        if not df.empty:
            time_ranges[symbol] = {
                "start": df['time_period_start'].min(),
                "end": df['time_period_end'].max()
            }
    
    if len(time_ranges) < 2:
        return []
    
    # Find intersection
    common_start = max(tr["start"] for tr in time_ranges.values())
    common_end = min(tr["end"] for tr in time_ranges.values())
    
    if common_start >= common_end:
        return []
    
    # Create 1-hour windows within the common time range
    windows = []
    current_start = common_start
    
    while current_start < common_end:
        current_end = current_start + timedelta(hours=1)
        if current_end > common_end:
            current_end = common_end
        
        # Check coverage for each venue
        coverage = {}
        for symbol, df in ohlcv_data.items():
            if not df.empty:
                window_data = df[
                    (df['time_period_start'] >= current_start) & 
                    (df['time_period_end'] <= current_end)
                ]
                coverage[symbol] = {
                    "records": len(window_data),
                    "coverage_pct": len(window_data) / 60 if len(window_data) > 0 else 0  # Assuming 1-minute intervals
                }
        
        windows.append({
            "start": current_start.isoformat(),
            "end": current_end.isoformat(),
            "duration_hours": (current_end - current_start).total_seconds() / 3600,
            "coverage": coverage,
            "total_venues": len([s for s in coverage.keys() if coverage[s]["records"] > 0]),
            "usable": len([s for s in coverage.keys() if coverage[s]["records"] > 0]) >= 2
        })
        
        current_start = current_end
    
    return windows

def main():
    print("🔍 COINAPI ACD ANALYSIS")
    print("="*80)
    
    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    s3_client = boto3.client('s3')
    
    # Available symbols from collection
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    
    print(f"📅 Analyzing data for date: {date}")
    print(f"🎯 Symbols: {', '.join(symbols)}")
    
    # Load and analyze data
    ohlcv_data = {}
    trades_data = {}
    analysis_results = {}
    
    for symbol in symbols:
        print(f"\n📊 Analyzing {symbol}...")
        
        # Load OHLCV data
        ohlcv_df = load_coinapi_data(s3_client, bucket, date, symbol, "ohlcv")
        if ohlcv_df is not None:
            ohlcv_data[symbol] = ohlcv_df
            ohlcv_analysis = analyze_ohlcv_data(ohlcv_df, symbol)
            analysis_results[f"{symbol}_ohlcv"] = ohlcv_analysis
            print(f"   📊 OHLCV: {ohlcv_analysis['n_records']} records, {ohlcv_analysis['time_span_hours']:.1f}h")
            print(f"   📊 Price: ${ohlcv_analysis['price_stats']['mean']:.2f} ± ${ohlcv_analysis['price_stats']['std']:.2f}")
            print(f"   📊 Quality: {ohlcv_analysis['data_quality']}")
        
        # Load trades data
        trades_df = load_coinapi_data(s3_client, bucket, date, symbol, "trades")
        if trades_df is not None:
            trades_data[symbol] = trades_df
            trades_analysis = analyze_trades_data(trades_df, symbol)
            analysis_results[f"{symbol}_trades"] = trades_analysis
            print(f"   📊 Trades: {trades_analysis['n_records']} records, {trades_analysis['time_span_hours']:.1f}h")
            print(f"   📊 Price: ${trades_analysis['price_stats']['mean']:.2f} ± ${trades_analysis['price_stats']['std']:.2f}")
            print(f"   📊 Quality: {trades_analysis['data_quality']}")
    
    # Find common time windows
    print(f"\n🔍 Finding common time windows...")
    common_windows = find_common_time_windows(ohlcv_data)
    
    if common_windows:
        print(f"   ✅ Found {len(common_windows)} potential windows")
        usable_windows = [w for w in common_windows if w["usable"]]
        print(f"   ✅ {len(usable_windows)} usable windows (≥2 venues)")
        
        if usable_windows:
            best_window = max(usable_windows, key=lambda w: w["total_venues"])
            print(f"   🎯 Best window: {best_window['start']} to {best_window['end']}")
            print(f"   🎯 Venues: {best_window['total_venues']}")
            for symbol, coverage in best_window["coverage"].items():
                if coverage["records"] > 0:
                    print(f"      - {symbol}: {coverage['records']} records ({coverage['coverage_pct']:.1%} coverage)")
    else:
        print(f"   ❌ No common time windows found")
    
    # Save analysis results
    results = {
        "date": date,
        "symbols": symbols,
        "analysis_results": analysis_results,
        "common_windows": common_windows,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    results_key = f"coinapi_bf1/analysis/{date}/acd_analysis.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    
    print(f"\n💾 Saved analysis to s3://{bucket}/{results_key}")
    
    # Print summary
    print(f"\n📊 ANALYSIS SUMMARY")
    print("="*80)
    for symbol in symbols:
        ohlcv_key = f"{symbol}_ohlcv"
        trades_key = f"{symbol}_trades"
        
        if ohlcv_key in analysis_results:
            ohlcv = analysis_results[ohlcv_key]
            print(f"{symbol} OHLCV: {ohlcv['n_records']} records, {ohlcv['data_quality']} quality")
        
        if trades_key in analysis_results:
            trades = analysis_results[trades_key]
            print(f"{symbol} Trades: {trades['n_records']} records, {trades['data_quality']} quality")

if __name__ == "__main__":
    main()
