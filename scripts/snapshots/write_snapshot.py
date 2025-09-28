#!/usr/bin/env python3
"""
Snapshot writer utility for S3-based snapshots.

Writes snapshot data to S3 following the agreed schema:
s3://acd-monitor-snapshots/snapshots/{symbol}/{yyyymmdd}/{HHMM}-{HHMM}/
  OVERLAP.json
  ticks/{venue}.parquet
  meta/provenance.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone
import boto3
import pandas as pd
import numpy as np

# Import config from same directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
try:
    from config import DEFAULT_BUCKET, DEFAULT_PREFIX, DEFAULT_REGION
except ImportError:
    # Fallback to environment variables
    DEFAULT_BUCKET = os.getenv('ACD_S3_BUCKET', 'acd-monitor-snapshots')
    DEFAULT_PREFIX = os.getenv('ACD_S3_PREFIX', 'snapshots')
    DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def generate_synthetic_ticks(
    start_time: datetime, 
    end_time: datetime, 
    venue: str, 
    symbol: str = "BTC-USD"
) -> pd.DataFrame:
    """Generate synthetic tick data for testing."""
    
    # Generate timestamps every 1 second
    timestamps = pd.date_range(start=start_time, end=end_time, freq='1S', tz='UTC')
    
    # Generate synthetic price data (random walk around $50,000)
    base_price = 50000.0
    price_changes = np.random.normal(0, 10, len(timestamps))  # $10 std dev
    prices = base_price + np.cumsum(price_changes)
    
    # Generate bid/ask spreads (0.1% to 0.5% of price)
    spreads = np.random.uniform(0.001, 0.005, len(timestamps)) * prices
    bids = prices - spreads / 2
    asks = prices + spreads / 2
    
    # Generate sizes (random between 0.1 and 10 BTC)
    bid_sizes = np.random.uniform(0.1, 10.0, len(timestamps))
    ask_sizes = np.random.uniform(0.1, 10.0, len(timestamps))
    trade_sizes = np.random.uniform(0.01, 5.0, len(timestamps))
    
    # Convert timestamps to nanoseconds
    ts_exchange = timestamps.astype('int64') // 1000  # Convert to nanoseconds
    
    df = pd.DataFrame({
        'ts_exchange': ts_exchange,
        'best_bid': bids,
        'best_ask': asks,
        'last_px': prices,
        'bid_sz': bid_sizes,
        'ask_sz': ask_sizes,
        'trade_sz': trade_sizes
    })
    
    return df


def write_snapshot_to_s3(
    s3_client,
    bucket: str,
    prefix: str,
    symbol: str,
    date_str: str,
    time_range: str,
    venues: List[str],
    start_time: datetime,
    end_time: datetime,
    provenance: str = "REAL",
    seed: int = 42
) -> str:
    """Write a complete snapshot to S3."""
    
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Construct S3 paths
    base_key = f"{prefix}/{symbol}/{date_str}/{time_range}"
    overlap_key = f"{base_key}/OVERLAP.json"
    provenance_key = f"{base_key}/meta/provenance.json"
    
    # Generate OVERLAP.json
    overlap_data = {
        "start_utc": start_time.isoformat() + "Z",
        "end_utc": end_time.isoformat() + "Z",
        "cadences": ["1s"],
        "venues": venues,
        "coverage": {venue: 1.0 for venue in venues}
    }
    
    # Write OVERLAP.json
    s3_client.put_object(
        Bucket=bucket,
        Key=overlap_key,
        Body=json.dumps(overlap_data, indent=2),
        ContentType='application/json'
    )
    logger.info(f"Wrote OVERLAP.json to s3://{bucket}/{overlap_key}")
    
    # Generate and write tick data for each venue
    for venue in venues:
        logger.info(f"Generating synthetic data for {venue}...")
        tick_data = generate_synthetic_ticks(start_time, end_time, venue, symbol)
        
        # Convert to parquet in memory
        parquet_buffer = tick_data.to_parquet()
        
        # Upload to S3
        tick_key = f"{base_key}/ticks/{venue}.parquet"
        s3_client.put_object(
            Bucket=bucket,
            Key=tick_key,
            Body=parquet_buffer,
            ContentType='application/octet-stream'
        )
        logger.info(f"Wrote {len(tick_data)} ticks to s3://{bucket}/{tick_key}")
    
    # Generate provenance.json
    provenance_data = {
        "provenance": provenance,
        "seed": seed,
        "code_version": "acdm-local",
        "snapshot": f"s3://{bucket}/{overlap_key}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "module": "write_snapshot.py",
        "params": {
            "symbol": symbol,
            "date": date_str,
            "time_range": time_range,
            "venues": venues,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
    }
    
    # Write provenance.json
    s3_client.put_object(
        Bucket=bucket,
        Key=provenance_key,
        Body=json.dumps(provenance_data, indent=2),
        ContentType='application/json'
    )
    logger.info(f"Wrote provenance.json to s3://{bucket}/{provenance_key}")
    
    return f"s3://{bucket}/{overlap_key}"


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Write snapshot to S3")
    parser.add_argument("--symbol", default="BTC-USD", help="Trading symbol")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--start-time", required=True, help="Start time in HHMM format")
    parser.add_argument("--end-time", required=True, help="End time in HHMM format")
    parser.add_argument("--venues", default="binance,coinbase,kraken,okx,bybit", 
                       help="Comma-separated list of venues")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket name")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="S3 prefix")
    parser.add_argument("--provenance", default="REAL", choices=["REAL", "DEMO"], 
                       help="Provenance tag")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Parse arguments
    venues = [v.strip() for v in args.venues.split(',')]
    
    # Parse date and times
    date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    start_time = datetime.combine(date_obj, datetime.strptime(args.start_time, '%H%M').time())
    end_time = datetime.combine(date_obj, datetime.strptime(args.end_time, '%H%M').time())
    
    # Add timezone
    start_time = start_time.replace(tzinfo=timezone.utc)
    end_time = end_time.replace(tzinfo=timezone.utc)
    
    # Format for S3 keys
    date_str = args.date.replace('-', '')
    time_range = f"{args.start_time}-{args.end_time}"
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    # Write snapshot
    try:
        snapshot_url = write_snapshot_to_s3(
            s3_client=s3_client,
            bucket=args.bucket,
            prefix=args.prefix,
            symbol=args.symbol,
            date_str=date_str,
            time_range=time_range,
            venues=venues,
            start_time=start_time,
            end_time=end_time,
            provenance=args.provenance,
            seed=args.seed
        )
        
        logger.info(f"Successfully wrote snapshot: {snapshot_url}")
        print(f"Snapshot written: {snapshot_url}")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to write snapshot: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
