#!/usr/bin/env python3
"""
CoinAPI Phase 4 - Small Trades Sanity Probe

If trades are available for the same window, analyze trade-level characteristics.
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

def load_coinapi_trades(s3_client, bucket: str, date: str, symbol: str) -> Optional[pd.DataFrame]:
    """Load CoinAPI trades data from S3."""
    key = f"coinapi_bf1/trades/{date}/{symbol}/part-0000.parquet"
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

def analyze_trades_quality(df: pd.DataFrame, symbol: str, window_start: str, window_end: str) -> Dict[str, Any]:
    """Analyze trades data quality and characteristics."""
    if df.empty:
        return {
            "venue": symbol,
            "status": "empty",
            "message": "No trades data"
        }
    
    # Convert timestamps to UTC
    df['time_exchange'] = pd.to_datetime(df['time_exchange'], utc=True)
    df['time_coinapi'] = pd.to_datetime(df['time_coinapi'], utc=True)
    
    # Filter to window if specified
    if window_start and window_end:
        window_start_dt = pd.to_datetime(window_start, utc=True)
        window_end_dt = pd.to_datetime(window_end, utc=True)
        
        window_trades = df[
            (df['time_exchange'] >= window_start_dt) & 
            (df['time_exchange'] < window_end_dt)
        ]
    else:
        window_trades = df
    
    if window_trades.empty:
        return {
            "venue": symbol,
            "status": "no_window_data",
            "message": f"No trades in window {window_start} to {window_end}"
        }
    
    # Basic statistics
    n_trades = len(window_trades)
    time_span = (window_trades['time_exchange'].max() - window_trades['time_exchange'].min()).total_seconds()
    
    # Count trades per minute
    window_trades['minute'] = window_trades['time_exchange'].dt.floor('T')
    trades_per_minute = window_trades.groupby('minute').size()
    
    # Inter-arrival analysis
    time_diffs = window_trades['time_exchange'].diff().dt.total_seconds().dropna()
    
    # Duplicate timestamp analysis
    timestamp_duplicates = window_trades['time_exchange'].duplicated().sum()
    duplicate_pct = timestamp_duplicates / n_trades if n_trades > 0 else 0
    
    # Price analysis
    price_stats = {
        "mean": float(window_trades['price'].mean()),
        "std": float(window_trades['price'].std()),
        "min": float(window_trades['price'].min()),
        "max": float(window_trades['price'].max()),
        "cv": float(window_trades['price'].std() / window_trades['price'].mean()) if window_trades['price'].mean() > 0 else 0
    }
    
    # Volume analysis
    volume_stats = {
        "mean": float(window_trades['size'].mean()),
        "std": float(window_trades['size'].std()),
        "total": float(window_trades['size'].sum()),
        "median": float(window_trades['size'].median())
    }
    
    # Timing analysis
    timing_stats = {
        "time_span_seconds": time_span,
        "time_span_hours": time_span / 3600,
        "trades_per_minute_mean": float(trades_per_minute.mean()),
        "trades_per_minute_std": float(trades_per_minute.std()),
        "trades_per_minute_cv": float(trades_per_minute.std() / trades_per_minute.mean()) if trades_per_minute.mean() > 0 else 0,
        "inter_arrival_mean": float(time_diffs.mean()),
        "inter_arrival_std": float(time_diffs.std()),
        "inter_arrival_cv": float(time_diffs.std() / time_diffs.mean()) if time_diffs.mean() > 0 else 0
    }
    
    # Quality assessment
    quality_issues = []
    
    # Check for regular intervals (synthetic data indicator)
    if timing_stats["inter_arrival_cv"] < 0.05 and timing_stats["inter_arrival_mean"] > 0:
        quality_issues.append("Regular intervals detected (possible synthetic data)")
    
    # Check for too few trades
    if n_trades < 10:
        quality_issues.append(f"Very few trades: {n_trades}")
    
    # Check for duplicate timestamps
    if duplicate_pct > 0.1:  # More than 10% duplicates
        quality_issues.append(f"High duplicate timestamps: {duplicate_pct:.1%}")
    
    # Check for constant prices
    if price_stats["cv"] < 0.001:  # Very low coefficient of variation
        quality_issues.append("Near-constant prices detected")
    
    # Check for zero time span
    if time_span < 1:  # Less than 1 second
        quality_issues.append("Zero or near-zero time span")
    
    # Overall quality assessment
    if len(quality_issues) == 0:
        quality_status = "good"
    elif len(quality_issues) <= 2:
        quality_status = "acceptable"
    else:
        quality_status = "poor"
    
    # Data type assessment
    if timing_stats["inter_arrival_cv"] < 0.05 and timing_stats["inter_arrival_mean"] > 0:
        data_type = "likely_aggregated"
    elif n_trades < 50:
        data_type = "sparse"
    elif duplicate_pct > 0.05:
        data_type = "duplicate_heavy"
    else:
        data_type = "likely_ticks"
    
    return {
        "venue": symbol,
        "status": "success",
        "n_trades": n_trades,
        "time_span_hours": timing_stats["time_span_hours"],
        "price_stats": price_stats,
        "volume_stats": volume_stats,
        "timing_stats": timing_stats,
        "duplicate_pct": float(duplicate_pct),
        "quality_issues": quality_issues,
        "quality_status": quality_status,
        "data_type": data_type,
        "trades_per_minute_stats": {
            "mean": float(trades_per_minute.mean()),
            "std": float(trades_per_minute.std()),
            "min": int(trades_per_minute.min()),
            "max": int(trades_per_minute.max())
        }
    }

def main():
    print("🔍 COINAPI PHASE 4 - SMALL TRADES SANITY PROBE")
    print("="*80)
    
    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    # Use the same window as OHLCV analysis
    window_start = "2025-09-25T00:00:00+00:00"
    window_end = "2025-09-25T01:00:00+00:00"
    
    s3_client = boto3.client('s3')
    
    print(f"📊 Analyzing trades for window: {window_start} to {window_end}")
    
    # Load and analyze trades data
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    trades_analysis = {}
    
    print(f"\n📊 Loading trades data...")
    for symbol in symbols:
        print(f"   📊 Analyzing {symbol}...")
        
        # Load trades data
        df = load_coinapi_trades(s3_client, bucket, date, symbol)
        if df is None:
            print(f"      ❌ No trades data")
            trades_analysis[symbol] = {
                "venue": symbol,
                "status": "no_data",
                "message": "No trades data available"
            }
            continue
        
        # Analyze trades quality
        analysis = analyze_trades_quality(df, symbol, window_start, window_end)
        trades_analysis[symbol] = analysis
        
        if analysis["status"] == "success":
            print(f"      ✅ {analysis['n_trades']} trades, {analysis['time_span_hours']:.1f}h span")
            print(f"      📊 Quality: {analysis['quality_status']}")
            print(f"      📊 Data type: {analysis['data_type']}")
            if analysis['quality_issues']:
                print(f"      ⚠️  Issues: {', '.join(analysis['quality_issues'])}")
        else:
            print(f"      ❌ {analysis['message']}")
    
    # Generate summary
    valid_trades = [symbol for symbol, analysis in trades_analysis.items() 
                   if analysis["status"] == "success"]
    
    print(f"\n📊 TRADES ANALYSIS SUMMARY")
    print("="*80)
    print(f"Valid venues with trades: {len(valid_trades)}")
    
    if valid_trades:
        print(f"\n📊 Trades characteristics:")
        for symbol in valid_trades:
            analysis = trades_analysis[symbol]
            print(f"   {symbol}:")
            print(f"      Trades: {analysis['n_trades']}")
            print(f"      Time span: {analysis['time_span_hours']:.1f}h")
            print(f"      Quality: {analysis['quality_status']}")
            print(f"      Data type: {analysis['data_type']}")
            print(f"      Trades/min: {analysis['trades_per_minute_stats']['mean']:.1f} ± {analysis['trades_per_minute_stats']['std']:.1f}")
            print(f"      Duplicates: {analysis['duplicate_pct']:.1%}")
    else:
        print(f"   ❌ No valid trades data found")
    
    # Save trades quality report
    trades_qc_data = {
        "window": {
            "start": window_start,
            "end": window_end
        },
        "venues": trades_analysis,
        "valid_venues": valid_trades,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    trades_qc_key = f"analysis/coinapi/_sig/trades_qc.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=trades_qc_key,
        Body=json.dumps(trades_qc_data, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    print(f"\n💾 Saved trades QC: s3://{bucket}/{trades_qc_key}")
    
    # Generate conclusions
    print(f"\n📊 TRADES DATA CONCLUSIONS:")
    if len(valid_trades) == 0:
        print("   ❌ No trades data available for analysis")
        print("   📊 Proceeding with OHLCV-only conclusions")
    else:
        print(f"   ✅ {len(valid_trades)} venues have trades data")
        
        # Check if trades are obviously aggregated or too sparse
        aggregated_venues = [symbol for symbol, analysis in trades_analysis.items() 
                           if analysis["status"] == "success" and analysis["data_type"] == "likely_aggregated"]
        sparse_venues = [symbol for symbol, analysis in trades_analysis.items() 
                        if analysis["status"] == "success" and analysis["data_type"] == "sparse"]
        
        if aggregated_venues:
            print(f"   ⚠️  Aggregated trades detected: {', '.join(aggregated_venues)}")
        if sparse_venues:
            print(f"   ⚠️  Sparse trades data: {', '.join(sparse_venues)}")
        
        if len(aggregated_venues) + len(sparse_venues) >= len(valid_trades):
            print("   📊 Trades data appears to be aggregated or sparse")
            print("   📊 Proceeding with OHLCV-only conclusions")
        else:
            print("   📊 Trades data appears to be genuine tick data")
            print("   📊 Can be used for additional ACD analysis")
    
    print(f"\n✅ PHASE 4 COMPLETE")
    print("="*80)
    print("📁 Generated artifacts:")
    print(f"  - Trades QC report: s3://{bucket}/{trades_qc_key}")

if __name__ == "__main__":
    main()
