#!/usr/bin/env python3
"""
ACD Phase CW - Canonical Overlap Window

Chooses the maximal 60-minute window with ≥90% overlap across all passing venues.
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
            logging.FileHandler("acd_phase_cw_canonical_window.log"),
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

def load_backfill_data(s3_client, bucket: str, date: str, venue: str) -> Optional[pd.DataFrame]:
    """Load backfilled data for a venue."""
    logger = logging.getLogger(__name__)
    
    # Try to find backfill data
    prefix = f"backfill/{venue}/{date}/"
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if 'Contents' not in response:
            return None
        
        parquet_files = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.parquet'):
                parquet_files.append(key)
        
        if not parquet_files:
            return None
        
        # Use latest file (most recent)
        s3_key = sorted(parquet_files)[-1]
        
    except Exception as e:
        logger.error(f"Error listing windows for {venue}: {e}")
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
        
        logger.info(f"Loaded {venue} backfill data: {len(df)} rows")
        return df
        
    except Exception as e:
        logger.error(f"Error loading {venue} backfill data: {e}")
        return None

def find_canonical_window(venues_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Find the canonical overlap window."""
    logger = logging.getLogger(__name__)
    
    if not venues_data:
        return {
            "status": "failed",
            "reason": "No venues data available",
            "canonical_window": None
        }
    
    # Find overlapping time window
    all_start_times = []
    all_end_times = []
    
    for venue, df in venues_data.items():
        if df.empty:
            continue
        
        start_time = df['timestamp'].min()
        end_time = df['timestamp'].max()
        all_start_times.append(start_time)
        all_end_times.append(end_time)
        
        logger.info(f"{venue}: {start_time} to {end_time}")
    
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
    for venue, df in venues_data.items():
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
    
    # Determine if we meet the requirements
    min_coverage = 90.0  # 90% overlap requirement
    min_duration = 60 * 60  # 60 minutes in seconds
    
    # Check if we have sufficient coverage
    sufficient_coverage = all(
        coverage_analysis[venue]["coverage_percentage"] >= min_coverage
        for venue in coverage_analysis
    )
    
    # Check if we have sufficient duration
    sufficient_duration = canonical_duration >= min_duration
    
    # If not sufficient, try relaxed requirements
    if not sufficient_duration:
        if canonical_duration >= 45 * 60:  # 45 minutes
            relaxed_duration = 45
        elif canonical_duration >= 30 * 60:  # 30 minutes
            relaxed_duration = 30
        else:
            relaxed_duration = 0
    else:
        relaxed_duration = 60
    
    canonical_window = {
        "status": "success" if sufficient_coverage and sufficient_duration else "partial",
        "canonical_start": canonical_start.isoformat(),
        "canonical_end": canonical_end.isoformat(),
        "canonical_duration_seconds": canonical_duration,
        "canonical_duration_minutes": canonical_duration / 60,
        "included_venues": list(venues_data.keys()),
        "coverage_analysis": coverage_analysis,
        "requirements": {
            "min_coverage_percentage": min_coverage,
            "min_duration_minutes": min_duration / 60,
            "sufficient_coverage": sufficient_coverage,
            "sufficient_duration": sufficient_duration,
            "relaxed_duration_minutes": relaxed_duration
        },
        "recommendations": []
    }
    
    # Add recommendations
    if not sufficient_coverage:
        canonical_window["recommendations"].append("Some venues have <90% coverage - consider backfill")
    
    if not sufficient_duration:
        canonical_window["recommendations"].append(f"Duration {canonical_duration/60:.1f}min < 60min - consider backfill")
    
    if len(venues_data) < 2:
        canonical_window["recommendations"].append("Only 1 venue available - consider backfill for additional venues")
    
    logger.info(f"Canonical window: {canonical_start} to {canonical_end} ({canonical_duration/60:.1f}min)")
    logger.info(f"Included venues: {list(venues_data.keys())}")
    logger.info(f"Coverage: {coverage_analysis}")
    
    return canonical_window

def main():
    """Main Phase CW function."""
    parser = argparse.ArgumentParser(description='ACD Phase CW - Canonical Overlap Window')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE CW - CANONICAL OVERLAP WINDOW")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # Load backfill data
    print(f"\n🔍 Loading backfill data...")
    
    venues = ['kraken']  # Only Kraken passed BF1
    venues_data = {}
    
    for venue in venues:
        print(f"\n📊 Loading {venue.upper()}...")
        
        df = load_backfill_data(s3_client, args.bucket, args.date, venue)
        if df is None:
            print(f"   ❌ No backfill data found for {venue}")
            continue
        
        venues_data[venue] = df
        print(f"   ✅ Loaded {len(df)} rows")
    
    if not venues_data:
        print(f"❌ No backfill data found for any venue")
        sys.exit(1)
    
    print(f"✅ Loaded {len(venues_data)} venues with backfill data")
    
    # Find canonical window
    print(f"\n🔍 Finding canonical window...")
    
    canonical_window = find_canonical_window(venues_data)
    
    if canonical_window["status"] == "failed":
        print(f"❌ Failed to find canonical window: {canonical_window['reason']}")
        sys.exit(1)
    
    print(f"✅ Canonical window found")
    print(f"   Duration: {canonical_window['canonical_duration_minutes']:.1f} minutes")
    print(f"   Included: {canonical_window['included_venues']}")
    print(f"   Status: {canonical_window['status']}")
    
    # Check requirements
    requirements = canonical_window["requirements"]
    if not requirements["sufficient_duration"]:
        print(f"⚠️  WARNING: Duration {canonical_window['canonical_duration_minutes']:.1f}min < 60min")
    if not requirements["sufficient_coverage"]:
        print(f"⚠️  WARNING: Some venues have <90% coverage")
    
    # Save canonical window
    print(f"\n💾 Saving canonical window...")
    
    canonical_window_key = f"analysis/{args.date}/ACD/_align/canonical_window.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=canonical_window_key,
        Body=json.dumps(canonical_window, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved canonical window: s3://{args.bucket}/{canonical_window_key}")
    
    # Final summary
    print(f"\n📊 PHASE CW SUMMARY")
    print("="*60)
    print(f"Canonical duration: {canonical_window['canonical_duration_minutes']:.1f} minutes")
    print(f"Included venues: {len(canonical_window['included_venues'])}")
    print(f"Status: {canonical_window['status']}")
    
    if canonical_window["recommendations"]:
        print(f"\n📋 RECOMMENDATIONS:")
        for recommendation in canonical_window["recommendations"]:
            print(f"   • {recommendation}")
    
    if canonical_window["status"] == "success":
        print(f"\n✅ PHASE CW COMPLETE - Proceeding to Phase CLN")
    else:
        print(f"\n⚠️  PHASE CW PARTIAL - Consider backfill for better coverage")

if __name__ == "__main__":
    main()