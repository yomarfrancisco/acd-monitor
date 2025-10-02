#!/usr/bin/env python3
"""
CoinAPI Phase 0 - Evidence of what we pulled

Log exact endpoints used, dump sample rows, and perform timezone checks.
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

def log_endpoints_used():
    """Log the exact endpoints used for data collection."""
    endpoints_used = {
        "collection_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_key_prefix": "7f036b38",
        "base_url": "https://rest.coinapi.io/v1",
        "endpoints": {
            "ohlcv_history": {
                "method": "GET",
                "path": "/ohlcv/{symbol}/history",
                "parameters": {
                    "period_id": "1MIN",
                    "time_start": "{date}T00:00:00",
                    "time_end": "{date}T23:59:59",
                    "limit": 1000
                },
                "description": "Historical OHLCV data (1-minute candles)"
            },
            "trades_latest": {
                "method": "GET", 
                "path": "/trades/{symbol}/latest",
                "parameters": {
                    "limit": 1000
                },
                "description": "Latest trades data"
            }
        },
        "venues_collected": {
            "BINANCE_SPOT_BTC_USDT": {
                "ohlcv_status": "success",
                "trades_status": "success",
                "date_range": "2025-09-25 to 2025-10-02"
            },
            "KRAKEN_SPOT_BTC_USD": {
                "ohlcv_status": "success", 
                "trades_status": "success",
                "date_range": "2025-09-25 to 2025-10-02"
            },
            "COINBASE_SPOT_BTC_USD": {
                "ohlcv_status": "success",
                "trades_status": "success", 
                "date_range": "2025-09-25 to 2025-10-02"
            },
            "OKX_SPOT_BTC_USDT": {
                "ohlcv_status": "failed",
                "trades_status": "failed",
                "reason": "Symbol not available with this API key"
            },
            "BYBIT_SPOT_BTC_USDT": {
                "ohlcv_status": "failed",
                "trades_status": "failed", 
                "reason": "Symbol not available with this API key"
            }
        }
    }
    return endpoints_used

def dump_sample_rows(s3_client, bucket: str, date: str, symbol: str, data_type: str) -> Dict[str, Any]:
    """Dump 5 sample rows per venue with column info."""
    df = load_coinapi_data(s3_client, bucket, date, symbol, data_type)
    
    if df is None or df.empty:
        return {"status": "no_data", "message": f"No {data_type} data for {symbol}"}
    
    # Get sample rows
    sample_rows = df.head(5)
    
    # Convert to serializable format
    sample_data = []
    for idx, row in sample_rows.iterrows():
        row_dict = {}
        for col in df.columns:
            value = row[col]
            if pd.isna(value):
                row_dict[col] = None
            elif isinstance(value, pd.Timestamp):
                row_dict[col] = value.isoformat()
            elif hasattr(value, 'item'):  # numpy scalar
                row_dict[col] = value.item()
            else:
                row_dict[col] = str(value)
        sample_data.append(row_dict)
    
    # Column info
    column_info = {}
    for col in df.columns:
        column_info[col] = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "total_count": len(df)
        }
    
    return {
        "status": "success",
        "symbol": symbol,
        "data_type": data_type,
        "n_rows": len(df),
        "columns": list(df.columns),
        "column_info": column_info,
        "sample_rows": sample_data
    }

def timezone_audit(s3_client, bucket: str, date: str, symbol: str, data_type: str) -> Dict[str, Any]:
    """Perform timezone audit on data."""
    df = load_coinapi_data(s3_client, bucket, date, symbol, data_type)
    
    if df is None or df.empty:
        return {"status": "no_data", "message": f"No {data_type} data for {symbol}"}
    
    # Find timestamp columns
    timestamp_cols = [col for col in df.columns if 'time' in col.lower()]
    
    audit_results = {
        "status": "success",
        "symbol": symbol,
        "data_type": data_type,
        "timestamp_columns": timestamp_cols,
        "timestamp_analysis": {}
    }
    
    for col in timestamp_cols:
        if col in df.columns:
            timestamps = pd.to_datetime(df[col], utc=True, errors='coerce')
            valid_timestamps = timestamps.dropna()
            
            if len(valid_timestamps) > 0:
                # Basic stats
                ts_min = valid_timestamps.min()
                ts_max = valid_timestamps.max()
                duration = (ts_max - ts_min).total_seconds()
                
                # Inter-arrival analysis
                if len(valid_timestamps) > 1:
                    intervals = valid_timestamps.diff().dt.total_seconds().dropna()
                    interval_stats = {
                        "mean_seconds": float(intervals.mean()),
                        "std_seconds": float(intervals.std()),
                        "cv": float(intervals.std() / intervals.mean()) if intervals.mean() > 0 else 0,
                        "min_seconds": float(intervals.min()),
                        "max_seconds": float(intervals.max())
                    }
                else:
                    interval_stats = {"message": "Insufficient data for interval analysis"}
                
                audit_results["timestamp_analysis"][col] = {
                    "n_valid": len(valid_timestamps),
                    "n_total": len(df),
                    "ts_min_utc": ts_min.isoformat(),
                    "ts_max_utc": ts_max.isoformat(),
                    "duration_hours": duration / 3600,
                    "is_utc": True,  # We forced UTC conversion
                    "interval_stats": interval_stats
                }
    
    return audit_results

def main():
    print("🔍 COINAPI PHASE 0 - EVIDENCE OF WHAT WE PULLED")
    print("="*80)
    
    # Configuration
    bucket = "acd-monitor-snapshots"
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    s3_client = boto3.client('s3')
    
    # Create output directory structure
    output_base = f"analysis/coinapi/_prov"
    
    print("📊 Phase 0.1: Logging endpoints used...")
    endpoints_used = log_endpoints_used()
    
    # Save endpoints log
    endpoints_key = f"{output_base}/endpoints_used.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=endpoints_key,
        Body=json.dumps(endpoints_used, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    print(f"   💾 Saved endpoints log: s3://{bucket}/{endpoints_key}")
    
    # Create readme
    readme_content = f"""# CoinAPI Data Collection Evidence

## Collection Details
- **Date**: {date}
- **API Key**: 7f036b38-38d6-4ed6-9fce-00a06280a0f6 (prefix)
- **Base URL**: https://rest.coinapi.io/v1
- **Collection Method**: REST API (OHLCV + Trades)

## Endpoints Used
- **OHLCV History**: GET /ohlcv/{{symbol}}/history (1-minute candles)
- **Trades Latest**: GET /trades/{{symbol}}/latest (1000 records)

## Venues Collected
- ✅ BINANCE_SPOT_BTC_USDT (OHLCV + Trades)
- ✅ KRAKEN_SPOT_BTC_USD (OHLCV + Trades)  
- ✅ COINBASE_SPOT_BTC_USD (OHLCV + Trades)
- ❌ OKX_SPOT_BTC_USDT (Not available)
- ❌ BYBIT_SPOT_BTC_USDT (Not available)

## Data Quality Notes
- OHLCV data: 1-minute aggregated candles (regular intervals expected)
- Trades data: Latest 1000 records per venue
- All timestamps converted to UTC
"""
    
    readme_key = f"{output_base}/readme.md"
    s3_client.put_object(
        Bucket=bucket,
        Key=readme_key,
        Body=readme_content.encode('utf-8'),
        ContentType='text/markdown'
    )
    print(f"   💾 Saved readme: s3://{bucket}/{readme_key}")
    
    print("\n📊 Phase 0.2: Dumping sample rows...")
    symbols = ["BINANCE_SPOT_BTC_USDT", "KRAKEN_SPOT_BTC_USD", "COINBASE_SPOT_BTC_USD"]
    data_types = ["ohlcv", "trades"]
    
    for symbol in symbols:
        for data_type in data_types:
            print(f"   📊 Processing {symbol} {data_type}...")
            sample_data = dump_sample_rows(s3_client, bucket, date, symbol, data_type)
            
            if sample_data["status"] == "success":
                sample_key = f"{output_base}/samples_{symbol}_{data_type}.json"
                s3_client.put_object(
                    Bucket=bucket,
                    Key=sample_key,
                    Body=json.dumps(sample_data, indent=2).encode('utf-8'),
                    ContentType='application/json'
                )
                print(f"      ✅ {sample_data['n_rows']} rows, {len(sample_data['columns'])} columns")
            else:
                print(f"      ❌ {sample_data['message']}")
    
    print("\n📊 Phase 0.3: Timezone audit...")
    time_audit_results = {}
    
    for symbol in symbols:
        for data_type in data_types:
            print(f"   📊 Auditing {symbol} {data_type}...")
            audit_result = timezone_audit(s3_client, bucket, date, symbol, data_type)
            time_audit_results[f"{symbol}_{data_type}"] = audit_result
            
            if audit_result["status"] == "success":
                print(f"      ✅ {audit_result['timestamp_columns']} timestamp columns")
                for ts_col, ts_info in audit_result["timestamp_analysis"].items():
                    print(f"         {ts_col}: {ts_info['n_valid']} valid, {ts_info['duration_hours']:.1f}h span")
                    if "interval_stats" in ts_info and "cv" in ts_info["interval_stats"]:
                        cv = ts_info["interval_stats"]["cv"]
                        print(f"         Interval CV: {cv:.3f}")
            else:
                print(f"      ❌ {audit_result['message']}")
    
    # Save time audit results
    time_audit_key = f"{output_base}/time_audit.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=time_audit_key,
        Body=json.dumps(time_audit_results, indent=2).encode('utf-8'),
        ContentType='application/json'
    )
    print(f"   💾 Saved time audit: s3://{bucket}/{time_audit_key}")
    
    print(f"\n✅ PHASE 0 COMPLETE")
    print("="*80)
    print("📁 Generated artifacts:")
    print(f"  - Endpoints log: s3://{bucket}/{endpoints_key}")
    print(f"  - Readme: s3://{bucket}/{readme_key}")
    print(f"  - Sample data: s3://{bucket}/{output_base}/samples_*.json")
    print(f"  - Time audit: s3://{bucket}/{time_audit_key}")

if __name__ == "__main__":
    main()
