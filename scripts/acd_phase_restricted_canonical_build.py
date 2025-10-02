#!/usr/bin/env python3
"""
ACD Phase Restricted - Canonical Build for Tick-Level Venues Only

Builds canonical windows only from venues classified as LIKELY_TICKS:
- Binance, Kraken, Coinbase (included)
- BYBIT (excluded - synthetic data)
- OKX (pending - no data found)
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

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
            logging.FileHandler("acd_phase_restricted_canonical_build.log"),
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

def get_s3_object_text(s3_client, bucket: str, key: str) -> Optional[str]:
    """Helper to get text content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None

def validate_tick_timing(df: pd.DataFrame, venue: str) -> Tuple[bool, Dict[str, Any]]:
    """Validate that data has irregular tick timing (CV > 1)."""
    logger = logging.getLogger(__name__)
    
    if df.empty or 'timestamp' not in df.columns:
        return False, {"error": "No timestamp data"}
    
    # Convert to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values('timestamp')
    
    # Compute deltas in nanoseconds
    time_deltas = df['timestamp'].diff().dropna()
    time_deltas_ns = time_deltas.dt.total_seconds() * 1e9
    
    if len(time_deltas_ns) == 0:
        return False, {"error": "No time deltas"}
    
    # Coefficient of variation
    cv = float(time_deltas_ns.std() / time_deltas_ns.mean()) if time_deltas_ns.mean() > 0 else 0
    
    # Check if CV > 1 (irregular tick timing)
    is_tick_level = cv > 1.0
    
    timing_stats = {
        "cv": cv,
        "is_tick_level": is_tick_level,
        "n_rows": len(df),
        "span_seconds": (df['timestamp'].max() - df['timestamp'].min()).total_seconds(),
        "delta_min": float(time_deltas_ns.min()),
        "delta_median": float(time_deltas_ns.median()),
        "delta_max": float(time_deltas_ns.max())
    }
    
    if not is_tick_level:
        logger.warning(f"{venue}: CV={cv:.3f} - synthetic data detected, excluding from analysis")
    else:
        logger.info(f"{venue}: CV={cv:.3f} - tick-level data confirmed")
    
    return is_tick_level, timing_stats

def load_venue_data(s3_client, bucket: str, date: str, venue: str, data_source: str = "raw_probes") -> Optional[pd.DataFrame]:
    """Load data for a specific venue from the specified source."""
    logger = logging.getLogger(__name__)
    
    if data_source == "raw_probes":
        # Try to find the first available slice
        prefix = f"raw_probes/{date}/venue={venue}/"
        try:
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
            if 'CommonPrefixes' not in response:
                return None
            
            slices = []
            for common_prefix in response['CommonPrefixes']:
                slice_name = common_prefix['Prefix'].split('=')[-1].strip('/')
                if slice_name:
                    slices.append(slice_name)
            
            if not slices:
                return None
            
            # Use first slice
            slice_name = sorted(slices)[0]
            s3_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"
            
        except Exception as e:
            logger.error(f"Error listing slices for {venue}: {e}")
            return None
    
    elif data_source == "backfill":
        # Try canonical window first, then fallback to any available
        canonical_key = f"backfill/{venue}/{date}/canonical_1200_1300/part-0000.parquet"
        parquet_content = get_s3_object_content(s3_client, bucket, canonical_key)
        if parquet_content:
            s3_key = canonical_key
        else:
            # Try to find any available window
            prefix = f"backfill/{venue}/{date}/"
            try:
                response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
                if 'CommonPrefixes' not in response:
                    return None
                
                windows = []
                for common_prefix in response['CommonPrefixes']:
                    window_name = common_prefix['Prefix'].split('/')[-1].strip('/')
                    if window_name:
                        windows.append(window_name)
                
                if not windows:
                    return None
                
                # Use first window
                window_name = sorted(windows)[0]
                s3_key = f"backfill/{venue}/{date}/{window_name}/part-0000.parquet"
                
            except Exception as e:
                logger.error(f"Error listing windows for {venue}: {e}")
                return None
    
    else:
        return None
    
    # Load parquet data
    parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
    if not parquet_content:
        return None
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
            tmp_file.write(parquet_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()
        
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        logger.info(f"Loaded {venue} from {s3_key}: {len(df)} rows")
        return df
        
    except Exception as e:
        logger.error(f"Error loading {venue} from {s3_key}: {e}")
        return None

def build_canonical_window(tick_venues_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Build canonical window from tick-level venues only."""
    logger = logging.getLogger(__name__)
    
    if not tick_venues_data:
        return {
            "status": "failed",
            "reason": "No tick-level venues available",
            "canonical_window": None
        }
    
    # Find overlapping time window
    all_start_times = []
    all_end_times = []
    
    for venue, df in tick_venues_data.items():
        if df.empty:
            continue
        
        start_time = df['timestamp'].min()
        end_time = df['timestamp'].max()
        all_start_times.append(start_time)
        all_end_times.append(end_time)
    
    if not all_start_times:
        return {
            "status": "failed",
            "reason": "No valid time ranges found",
            "canonical_window": None
        }
    
    # Find intersection
    canonical_start = max(all_start_times)
    canonical_end = min(all_end_times)
    
    if canonical_start >= canonical_end:
        return {
            "status": "failed",
            "reason": "No overlapping time window found",
            "canonical_window": None
        }
    
    canonical_duration = (canonical_end - canonical_start).total_seconds()
    
    # Calculate coverage for each venue
    coverage_analysis = {}
    for venue, df in tick_venues_data.items():
        if df.empty:
            continue
        
        venue_start = df['timestamp'].min()
        venue_end = df['timestamp'].max()
        
        # Calculate overlap
        overlap_start = max(canonical_start, venue_start)
        overlap_end = min(canonical_end, venue_end)
        
        if overlap_start < overlap_end:
            overlap_duration = (overlap_end - overlap_start).total_seconds()
            coverage_percentage = (overlap_duration / canonical_duration) * 100
        else:
            coverage_percentage = 0
        
        coverage_analysis[venue] = {
            "venue_start": venue_start.isoformat(),
            "venue_end": venue_end.isoformat(),
            "overlap_start": overlap_start.isoformat(),
            "overlap_end": overlap_end.isoformat(),
            "coverage_percentage": coverage_percentage,
            "n_rows": len(df)
        }
    
    canonical_window = {
        "status": "success",
        "canonical_start": canonical_start.isoformat(),
        "canonical_end": canonical_end.isoformat(),
        "canonical_duration_seconds": canonical_duration,
        "included_venues": list(tick_venues_data.keys()),
        "excluded_venues": ["bybit", "okx"],
        "exclusion_reasons": {
            "bybit": "Synthetic data detected (CV = 0.0)",
            "okx": "No data found"
        },
        "coverage_analysis": coverage_analysis
    }
    
    logger.info(f"Canonical window: {canonical_start} to {canonical_end} ({canonical_duration:.1f}s)")
    logger.info(f"Included venues: {list(tick_venues_data.keys())}")
    logger.info(f"Excluded venues: bybit (synthetic), okx (missing)")
    
    return canonical_window

def main():
    """Main restricted canonical build function."""
    parser = argparse.ArgumentParser(description='ACD Phase Restricted - Canonical Build for Tick-Level Venues')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE RESTRICTED - CANONICAL BUILD FOR TICK-LEVEL VENUES")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    print(f"🎯 Target venues: Binance, Kraken, Coinbase (LIKELY_TICKS)")
    print(f"❌ Excluded venues: BYBIT (synthetic), OKX (missing)")
    
    # Load and validate tick-level venues
    print(f"\n🔍 Loading and validating tick-level venues...")
    
    tick_venues = ['binance', 'kraken', 'coinbase']
    tick_venues_data = {}
    validation_results = {}
    
    for venue in tick_venues:
        print(f"\n📊 Processing {venue.upper()}...")
        
        # Try raw_probes first, then backfill
        df = None
        data_source = None
        
        # Try raw_probes first
        df = load_venue_data(s3_client, args.bucket, args.date, venue, "raw_probes")
        if df is not None:
            data_source = "raw_probes"
        else:
            # Try backfill
            df = load_venue_data(s3_client, args.bucket, args.date, venue, "backfill")
            if df is not None:
                data_source = "backfill"
        
        if df is None:
            print(f"   ❌ No data found for {venue}")
            validation_results[venue] = {
                "status": "failed",
                "reason": "No data found",
                "data_source": None
            }
            continue
        
        # Validate tick timing
        is_tick_level, timing_stats = validate_tick_timing(df, venue)
        
        if is_tick_level:
            tick_venues_data[venue] = df
            validation_results[venue] = {
                "status": "success",
                "data_source": data_source,
                "timing_stats": timing_stats
            }
            print(f"   ✅ Tick-level data confirmed (CV={timing_stats['cv']:.3f})")
        else:
            validation_results[venue] = {
                "status": "excluded",
                "reason": "Synthetic data detected",
                "data_source": data_source,
                "timing_stats": timing_stats
            }
            print(f"   ❌ Synthetic data detected (CV={timing_stats['cv']:.3f}) - excluding")
    
    # Build canonical window
    print(f"\n🔍 Building canonical window...")
    
    canonical_window = build_canonical_window(tick_venues_data)
    
    if canonical_window["status"] != "success":
        print(f"❌ Failed to build canonical window: {canonical_window['reason']}")
        sys.exit(1)
    
    print(f"✅ Canonical window built successfully")
    print(f"   Duration: {canonical_window['canonical_duration_seconds']:.1f} seconds")
    print(f"   Included: {canonical_window['included_venues']}")
    print(f"   Excluded: {canonical_window['excluded_venues']}")
    
    # Save results
    print(f"\n💾 Saving restricted canonical build results...")
    
    results = {
        "date": args.date,
        "canonical_window": canonical_window,
        "validation_results": validation_results,
        "summary": {
            "included_venues": canonical_window["included_venues"],
            "excluded_venues": canonical_window["excluded_venues"],
            "exclusion_reasons": canonical_window["exclusion_reasons"],
            "canonical_duration_seconds": canonical_window["canonical_duration_seconds"]
        },
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    results_key = f"analysis/{args.date}/ACD/_restricted/canonical_build_results.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")
    
    # Final summary
    print(f"\n📊 RESTRICTED CANONICAL BUILD SUMMARY")
    print("="*60)
    print(f"Included venues: {len(canonical_window['included_venues'])}")
    print(f"Excluded venues: {len(canonical_window['excluded_venues'])}")
    print(f"Canonical duration: {canonical_window['canonical_duration_seconds']:.1f} seconds")
    
    print(f"\n✅ READY FOR RESTRICTED ACD ANALYSIS")
    print(f"   Proceeding with tick-level venues only")
    print(f"   BYBIT excluded due to synthetic data")
    print(f"   OKX flagged as pending ingestion")

if __name__ == "__main__":
    main()
