#!/usr/bin/env python3
"""
ACD Phase CLN - Canonical Clean Build

Normalizes schemas, validates monotonicity/variance/duplicates, and writes cleaned outputs.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import boto3
import pandas as pd
import numpy as np

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_cln_canonical_clean_build.log"),
        ],
    )

def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None

def load_venue_data(s3_client, bucket: str, date: str, venue: str, slice_name: str) -> Optional[pd.DataFrame]:
    """Load data for a specific venue and slice."""
    logger = logging.getLogger(__name__)
    
    # Try different data sources
    if venue == "coinbase":
        # For Coinbase, prioritize corrected data
        data_sources = [
            f"analysis/{date}/ACD/_tzfix/coinbase/corrected_{slice_name}.parquet",  # Corrected Coinbase
            f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet",
            f"backfill/{venue}/{date}/{slice_name}/part-0000.parquet"
        ]
    else:
        data_sources = [
            f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet",
            f"backfill/{venue}/{date}/{slice_name}/part-0000.parquet"
        ]
    
    for source_key in data_sources:
        parquet_data_content = get_s3_object_content(s3_client, bucket, source_key)
        if parquet_data_content:
            try:
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                    tmp_file.write(parquet_data_content)
                    tmp_file.flush()
                    df = pd.read_parquet(tmp_file.name)
                    Path(tmp_file.name).unlink()
                
                logger.info(f"Loaded {venue} {slice_name} from {source_key}: {len(df)} rows")
                return df
            except Exception as e:
                logger.warning(f"Error loading {source_key}: {e}")
                continue
    
    logger.warning(f"No data found for {venue} {slice_name}")
    return None

def normalize_schema(df: pd.DataFrame, venue: str) -> pd.DataFrame:
    """Normalize schema to standard format: timestamp, price, volume, venue, dt."""
    logger = logging.getLogger(__name__)
    
    # Create normalized dataframe
    normalized_df = pd.DataFrame()
    
    # Normalize timestamp
    if 'timestamp' in df.columns:
        if df['timestamp'].dtype == 'object':
            normalized_df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        else:
            normalized_df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    else:
        logger.error(f"No timestamp column found for {venue}")
        return pd.DataFrame()
    
    # Normalize price
    if 'price' in df.columns:
        normalized_df['price'] = pd.to_numeric(df['price'], errors='coerce')
    else:
        logger.error(f"No price column found for {venue}")
        return pd.DataFrame()
    
    # Normalize volume
    if 'volume' in df.columns:
        normalized_df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    else:
        logger.error(f"No volume column found for {venue}")
        return pd.DataFrame()
    
    # Add venue
    normalized_df['venue'] = venue
    
    # Add datetime for binning
    normalized_df['dt'] = normalized_df['timestamp'].dt.floor('1s')
    
    # Remove rows with NaN values
    normalized_df = normalized_df.dropna()
    
    logger.info(f"Normalized {venue}: {len(normalized_df)} rows")
    return normalized_df

def validate_data_quality(df: pd.DataFrame, venue: str) -> Dict[str, Any]:
    """Validate data quality: monotonicity, variance, duplicates."""
    logger = logging.getLogger(__name__)
    
    if df.empty:
        return {
            "status": "failed",
            "reason": "Empty dataframe",
            "n_rows": 0,
            "is_monotonic": False,
            "price_std": 0.0,
            "duplicate_ratio": 0.0,
            "issues": ["Empty dataframe"]
        }
    
    n_rows = len(df)
    
    # Check monotonicity
    is_monotonic = df['timestamp'].is_monotonic_increasing
    non_monotonic_count = 0
    if not is_monotonic:
        non_monotonic_count = (df['timestamp'].diff() < pd.Timedelta(0)).sum()
    
    # Check duplicates
    duplicates = df.duplicated(subset=['timestamp', 'price', 'volume']).sum()
    duplicate_ratio = duplicates / n_rows if n_rows > 0 else 0
    
    # Check price variance
    price_std = df['price'].std()
    price_mean = df['price'].mean()
    price_min = df['price'].min()
    price_max = df['price'].max()
    
    # Check volume
    volume_total = df['volume'].sum()
    volume_mean = df['volume'].mean()
    
    # Identify issues
    issues = []
    if not is_monotonic:
        issues.append(f"Non-monotonic timestamps ({non_monotonic_count} violations)")
    
    if duplicate_ratio > 0.3:
        issues.append(f"High duplicate ratio: {duplicate_ratio:.1%}")
    
    if price_std < 0.10:
        issues.append(f"Degenerate price variance: ${price_std:.2f}")
    
    if price_std == 0:
        issues.append("Zero price variance")
    
    if n_rows < 10:
        issues.append(f"Insufficient data: {n_rows} rows")
    
    # Check for reasonable price range
    if price_min < 1000 or price_max > 200000:  # BTC sanity check
        issues.append(f"Unreasonable price range: ${price_min:.2f} - ${price_max:.2f}")
    
    status = "success" if not issues else "failed"
    
    return {
        "status": status,
        "reason": "Data quality issues" if issues else "All checks passed",
        "n_rows": n_rows,
        "is_monotonic": is_monotonic,
        "non_monotonic_count": int(non_monotonic_count),
        "price_std": float(price_std),
        "price_mean": float(price_mean),
        "price_min": float(price_min),
        "price_max": float(price_max),
        "duplicate_ratio": float(duplicate_ratio),
        "volume_total": float(volume_total),
        "volume_mean": float(volume_mean),
        "issues": issues
    }

def main():
    """Main Phase CLN function."""
    parser = argparse.ArgumentParser(description='ACD Phase CLN - Canonical Clean Build')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE CLN - CANONICAL CLEAN BUILD")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # Define venues and slices to process
    venues = ["binance", "coinbase", "kraken"]
    slices = ["slice_00", "slice_01"]
    
    all_cleaned_data = {}
    all_validation_results = {}
    
    print(f"\n🔧 Processing venues and slices...")
    
    for venue in venues:
        print(f"\n🏢 {venue.upper()}")
        all_cleaned_data[venue] = {}
        all_validation_results[venue] = {}
        
        for slice_name in slices:
            print(f"   Processing {slice_name}...")
            
            # Load data
            df = load_venue_data(s3_client, args.bucket, args.date, venue, slice_name)
            
            if df is None or df.empty:
                print(f"     ❌ No data found")
                all_validation_results[venue][slice_name] = {
                    "status": "failed",
                    "reason": "No data found"
                }
                continue
            
            # Normalize schema
            normalized_df = normalize_schema(df, venue)
            
            if normalized_df.empty:
                print(f"     ❌ Schema normalization failed")
                all_validation_results[venue][slice_name] = {
                    "status": "failed",
                    "reason": "Schema normalization failed"
                }
                continue
            
            # Validate data quality
            validation_result = validate_data_quality(normalized_df, venue)
            all_validation_results[venue][slice_name] = validation_result
            
            if validation_result['status'] == 'success':
                print(f"     ✅ {validation_result['n_rows']} rows, ${validation_result['price_mean']:.2f}±${validation_result['price_std']:.2f}")
                
                # Save cleaned data
                cleaned_key = f"analysis/{args.date}/ACD/_cln/{venue}_{slice_name}_clean.parquet"
                
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                    normalized_df.to_parquet(tmp_file.name, index=False)
                    with open(tmp_file.name, 'rb') as f:
                        cleaned_data = f.read()
                    Path(tmp_file.name).unlink()
                
                s3_client.put_object(
                    Bucket=args.bucket,
                    Key=cleaned_key,
                    Body=cleaned_data,
                    ContentType='application/octet-stream'
                )
                
                print(f"     💾 Saved: s3://{args.bucket}/{cleaned_key}")
                all_cleaned_data[venue][slice_name] = {
                    "s3_key": cleaned_key,
                    "n_rows": validation_result['n_rows'],
                    "validation": validation_result
                }
            else:
                print(f"     ❌ Validation failed: {validation_result['reason']}")
                if validation_result['issues']:
                    for issue in validation_result['issues']:
                        print(f"       ⚠️  {issue}")
    
    # Generate summary
    print(f"\n📊 CANONICAL CLEAN BUILD SUMMARY")
    print("="*60)
    
    total_processed = 0
    total_successful = 0
    total_failed = 0
    
    for venue in venues:
        print(f"\n{venue.upper()}:")
        for slice_name in slices:
            if slice_name in all_validation_results[venue]:
                result = all_validation_results[venue][slice_name]
                total_processed += 1
                
                if result['status'] == 'success':
                    total_successful += 1
                    print(f"  {slice_name}: ✅ {result['n_rows']} rows, ${result['price_mean']:.2f}±${result['price_std']:.2f}")
                else:
                    total_failed += 1
                    print(f"  {slice_name}: ❌ {result['reason']}")
    
    print(f"\nOverall: {total_successful}/{total_processed} successful, {total_failed} failed")
    
    # Check if we have enough data to proceed
    if total_successful < 3:  # Need at least one slice per venue
        print(f"\n❌ INSUFFICIENT DATA: Only {total_successful} successful slices")
        print(f"   Need at least 3 slices (one per venue) to proceed")
        sys.exit(1)
    
    # Save validation results
    validation_summary = {
        "date": args.date,
        "total_processed": total_processed,
        "total_successful": total_successful,
        "total_failed": total_failed,
        "venues": all_validation_results,
        "cleaned_data": all_cleaned_data,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    validation_key = f"analysis/{args.date}/ACD/_cln/validation_summary.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=validation_key,
        Body=json.dumps(validation_summary, indent=2),
        ContentType='application/json'
    )
    
    print(f"\n💾 Saved validation summary: s3://{args.bucket}/{validation_key}")
    
    # Final decision
    if total_successful >= 3:
        print(f"\n✅ CANONICAL CLEAN BUILD COMPLETED")
        print(f"   {total_successful} slices successfully cleaned and validated")
        print(f"   Ready for Phase GRID (Canonical Time Binning)")
    else:
        print(f"\n❌ CANONICAL CLEAN BUILD FAILED")
        print(f"   Insufficient data quality for ACD analysis")
        sys.exit(1)
    
    print(f"\n📁 Generated artifacts:")
    print(f"  Validation summary: s3://{args.bucket}/{validation_key}")
    for venue in venues:
        for slice_name in slices:
            if slice_name in all_cleaned_data[venue]:
                print(f"  {venue} {slice_name}: s3://{args.bucket}/{all_cleaned_data[venue][slice_name]['s3_key']}")

if __name__ == "__main__":
    main()
