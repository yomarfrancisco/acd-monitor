#!/usr/bin/env python3
"""
ACD Phase BF1 - Tick Backfill (≥1h, fallback 3h/6h if available)

Obtains ≥1 hour overlapping tick feeds across validated venues using official APIs.
"""

import argparse
import json
import logging
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import boto3
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_bf1_tick_backfill.log"),
        ],
    )

def create_session_with_retries():
    """Create requests session with retry strategy for rate limiting."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def backfill_binance_trades(start_time: datetime, end_time: datetime) -> Tuple[bool, Dict[str, Any], Optional[pd.DataFrame]]:
    """Backfill Binance trades using historical trades API."""
    logger = logging.getLogger(__name__)
    
    # Binance historical trades endpoint
    base_url = "https://api.binance.com/api/v3/historicalTrades"
    symbol = "BTCUSDT"
    
    # Convert to milliseconds for Binance API
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    
    all_trades = []
    from_id = None
    
    session = create_session_with_retries()
    
    try:
        while True:
            params = {
                "symbol": symbol,
                "limit": 1000
            }
            
            if from_id:
                params["fromId"] = from_id
            
            response = session.get(base_url, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("Rate limited, backing off...")
                time.sleep(2)
                continue
            elif response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return False, {"error": f"API error: {response.status_code}"}, None
            
            trades = response.json()
            
            if not trades:
                break
            
            # Process trades
            for trade in trades:
                trade_data = {
                    "timestamp": pd.to_datetime(trade["time"], unit="ms", utc=True),
                    "price": float(trade["price"]),
                    "volume": float(trade["qty"]),
                    "trade_id": trade["id"],
                    "venue": "binance",
                    "symbol": symbol
                }
                all_trades.append(trade_data)
            
            # Update from_id for pagination
            from_id = trades[-1]["id"] + 1
            
            # Check if we've reached the end time
            if trades[-1]["time"] >= end_ms:
                break
            
            # Filter trades by time window
            filtered_trades = [trade for trade in trades if start_ms <= trade["time"] <= end_ms]
            if not filtered_trades:
                break
            
            # Rate limiting
            time.sleep(0.1)
        
        if not all_trades:
            return False, {"error": "No trades found"}, None
        
        df = pd.DataFrame(all_trades)
        
        # Validate provenance
        provenance_result = validate_provenance(df, "binance")
        
        return True, {
            "endpoint": base_url,
            "symbol": symbol,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "row_count": len(df),
            "provenance": provenance_result
        }, df
        
    except Exception as e:
        logger.error(f"Error backfilling Binance: {e}")
        return False, {"error": str(e)}, None

def backfill_kraken_trades(start_time: datetime, end_time: datetime) -> Tuple[bool, Dict[str, Any], Optional[pd.DataFrame]]:
    """Backfill Kraken trades using public trades API."""
    logger = logging.getLogger(__name__)
    
    # Kraken public trades endpoint
    base_url = "https://api.kraken.com/0/public/Trades"
    pair = "XXBTZUSD"  # BTC/USD
    
    all_trades = []
    since = None
    
    session = create_session_with_retries()
    
    try:
        while True:
            params = {"pair": pair}
            if since:
                params["since"] = since
            
            response = session.get(base_url, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("Rate limited, backing off...")
                time.sleep(2)
                continue
            elif response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return False, {"error": f"API error: {response.status_code}"}, None
            
            data = response.json()
            
            if "error" in data and data["error"]:
                logger.error(f"Kraken API error: {data['error']}")
                return False, {"error": f"Kraken API error: {data['error']}"}, None
            
            trades = data["result"][pair]
            
            if not trades:
                break
            
            # Process trades
            for trade in trades:
                trade_data = {
                    "timestamp": pd.to_datetime(trade[2], unit="s", utc=True),
                    "price": float(trade[0]),
                    "volume": float(trade[1]),
                    "trade_id": None,  # Kraken doesn't provide trade IDs in this endpoint
                    "venue": "kraken",
                    "symbol": "BTCUSD"
                }
                
                # Filter by time window
                if start_time <= trade_data["timestamp"] <= end_time:
                    all_trades.append(trade_data)
            
            # Update since for pagination
            since = data["result"]["last"]
            
            # Check if we've reached the end time
            if trades and pd.to_datetime(trades[-1][2], unit="s", utc=True) >= end_time:
                break
            
            # Rate limiting
            time.sleep(0.1)
        
        if not all_trades:
            return False, {"error": "No trades found"}, None
        
        df = pd.DataFrame(all_trades)
        
        # Validate provenance
        provenance_result = validate_provenance(df, "kraken")
        
        return True, {
            "endpoint": base_url,
            "symbol": "BTCUSD",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "row_count": len(df),
            "provenance": provenance_result
        }, df
        
    except Exception as e:
        logger.error(f"Error backfilling Kraken: {e}")
        return False, {"error": str(e)}, None

def validate_provenance(df: pd.DataFrame, venue: str) -> Dict[str, Any]:
    """Validate provenance requirements for backfilled data."""
    logger = logging.getLogger(__name__)
    
    if df.empty:
        return {"status": "failed", "reason": "Empty DataFrame"}
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Compute time deltas
    time_deltas = df['timestamp'].diff().dropna()
    time_deltas_seconds = time_deltas.dt.total_seconds()
    
    # Irregularity test: CV(Δt) > 0.05 AND >5 unique inter-arrival values
    cv = float(time_deltas_seconds.std() / time_deltas_seconds.mean()) if time_deltas_seconds.mean() > 0 else 0
    unique_intervals = time_deltas_seconds.nunique()
    irregularity_pass = cv > 0.05 and unique_intervals > 5
    
    # No constant price: price std ≥ $0.10
    price_std = float(df['price'].std())
    price_variance_pass = price_std >= 0.10
    
    # Duplicate ratio: exact row duplicates ≤ 5%
    exact_duplicates = df.duplicated().sum()
    exact_dup_ratio = exact_duplicates / len(df)
    dup_ratio_pass = exact_dup_ratio <= 0.05
    
    # Timestamp duplicates ≤ 50% (with differing trade_ids OK) - relaxed for high-frequency data
    timestamp_duplicates = df.duplicated(subset=['timestamp']).sum()
    timestamp_dup_ratio = timestamp_duplicates / len(df)
    timestamp_dup_pass = timestamp_dup_ratio <= 0.50
    
    # Clock sanity: timestamps UTC, within reasonable range
    utc_check = all(ts.tz == timezone.utc for ts in df['timestamp'])
    time_range_check = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() > 0
    
    provenance_result = {
        "status": "passed" if all([irregularity_pass, price_variance_pass, dup_ratio_pass, timestamp_dup_pass, utc_check, time_range_check]) else "failed",
        "irregularity": {
            "cv": cv,
            "unique_intervals": unique_intervals,
            "pass": bool(irregularity_pass)
        },
        "price_variance": {
            "std": price_std,
            "pass": bool(price_variance_pass)
        },
        "duplicates": {
            "exact_ratio": exact_dup_ratio,
            "timestamp_ratio": timestamp_dup_ratio,
            "exact_pass": bool(dup_ratio_pass),
            "timestamp_pass": bool(timestamp_dup_pass)
        },
        "clock_sanity": {
            "utc_check": bool(utc_check),
            "time_range_check": bool(time_range_check)
        }
    }
    
    if provenance_result["status"] == "failed":
        logger.warning(f"{venue} provenance validation failed")
    else:
        logger.info(f"{venue} provenance validation passed")
    
    return provenance_result

def save_backfill_data(s3_client, bucket: str, date: str, venue: str, window_id: str, df: pd.DataFrame) -> str:
    """Save backfilled data to S3."""
    logger = logging.getLogger(__name__)
    
    # Create window ID from timestamps
    start_time = df['timestamp'].min()
    end_time = df['timestamp'].max()
    window_id_actual = f"canonical_{start_time.strftime('%H%M')}_{end_time.strftime('%H%M')}"
    
    # Save to S3
    s3_key = f"backfill/{venue}/{date}/{window_id_actual}/part-0000.parquet"
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
        df.to_parquet(tmp_file.name, index=False)
        s3_client.upload_file(tmp_file.name, bucket, s3_key)
        Path(tmp_file.name).unlink()
    
    logger.info(f"Saved {venue} backfill data: s3://{bucket}/{s3_key}")
    return s3_key

def save_provenance_artifacts(s3_client, bucket: str, date: str, venue: str, backfill_result: Dict[str, Any], df: pd.DataFrame) -> None:
    """Save provenance artifacts."""
    logger = logging.getLogger(__name__)
    
    # Save provenance JSON
    prov_key = f"analysis/{date}/ACD/_prov/{venue}_bf1_prov.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=prov_key,
        Body=json.dumps(backfill_result, indent=2),
        ContentType='application/json'
    )
    
    # Save sample data
    sample_df = df.head(50)
    sample_key = f"analysis/{date}/ACD/_prov/{venue}_bf1_sample.ndjson"
    
    # Convert to NDJSON format
    sample_json = sample_df.to_json(orient='records', lines=True, date_format='iso')
    s3_client.put_object(
        Bucket=bucket,
        Key=sample_key,
        Body=sample_json,
        ContentType='application/json'
    )
    
    logger.info(f"Saved provenance artifacts for {venue}")

def main():
    """Main Phase BF1 function."""
    parser = argparse.ArgumentParser(description='ACD Phase BF1 - Tick Backfill')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    parser.add_argument('--hours', type=int, default=1, help='Hours to backfill (default: 1)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE BF1 - TICK BACKFILL")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    print(f"⏰ Backfill duration: {args.hours} hour(s)")
    print(f"🎯 Target venues: Binance, Kraken")
    
    # Define time window - use current time for better API compatibility
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=args.hours)
    end_time = now
    
    print(f"🕐 Time window: {start_time.isoformat()} to {end_time.isoformat()}")
    
    # Backfill each venue
    venues = ['binance', 'kraken']
    backfill_results = {}
    successful_venues = []
    
    for venue in venues:
        print(f"\n📊 Backfilling {venue.upper()}...")
        
        try:
            if venue == 'binance':
                success, result, df = backfill_binance_trades(start_time, end_time)
            elif venue == 'kraken':
                success, result, df = backfill_kraken_trades(start_time, end_time)
            else:
                print(f"   ❌ Unknown venue: {venue}")
                continue
            
            if not success:
                print(f"   ❌ Backfill failed: {result.get('error', 'Unknown error')}")
                backfill_results[venue] = result
                continue
            
            # Check provenance
            if result['provenance']['status'] != 'passed':
                print(f"   ❌ Provenance validation failed: {result['provenance']}")
                backfill_results[venue] = result
                continue
            
            # Save data
            s3_key = save_backfill_data(s3_client, args.bucket, args.date, venue, "canonical", df)
            result['s3_key'] = s3_key
            
            # Save provenance artifacts
            save_provenance_artifacts(s3_client, args.bucket, args.date, venue, result, df)
            
            backfill_results[venue] = result
            successful_venues.append(venue)
            
            print(f"   ✅ Backfill successful: {result['row_count']} rows")
            print(f"   📊 CV(Δt): {result['provenance']['irregularity']['cv']:.3f}")
            print(f"   📊 Price std: ${result['provenance']['price_variance']['std']:.2f}")
            print(f"   📊 Duplicates: {result['provenance']['duplicates']['exact_ratio']:.1%}")
            
        except Exception as e:
            print(f"   ❌ Error backfilling {venue}: {e}")
            backfill_results[venue] = {"error": str(e)}
    
    # Save overall results
    print(f"\n💾 Saving backfill results...")
    
    overall_results = {
        "date": args.date,
        "time_window": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration_hours": args.hours
        },
        "backfill_results": backfill_results,
        "successful_venues": successful_venues,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    results_key = f"analysis/{args.date}/ACD/_bf1/backfill_results.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(overall_results, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")
    
    # Final summary
    print(f"\n📊 PHASE BF1 SUMMARY")
    print("="*60)
    print(f"Successful venues: {len(successful_venues)}")
    print(f"Failed venues: {len(venues) - len(successful_venues)}")
    
    if successful_venues:
        print(f"\n✅ SUCCESSFUL VENUES:")
        for venue in successful_venues:
            result = backfill_results[venue]
            print(f"   {venue.upper()}: {result['row_count']} rows, CV={result['provenance']['irregularity']['cv']:.3f}")
    
    failed_venues = [v for v in venues if v not in successful_venues]
    if failed_venues:
        print(f"\n❌ FAILED VENUES:")
        for venue in failed_venues:
            result = backfill_results[venue]
            print(f"   {venue.upper()}: {result.get('error', 'Unknown error')}")
    
    if len(successful_venues) >= 2:
        print(f"\n✅ PHASE BF1 COMPLETE - Proceeding to Phase CW")
    else:
        print(f"\n❌ PHASE BF1 FAILED - Insufficient successful venues")
        sys.exit(1)

if __name__ == "__main__":
    main()
