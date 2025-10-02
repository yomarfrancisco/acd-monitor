#!/usr/bin/env python3
"""
ACD Phase GRID - Simple Canonical Time Binning

Creates individual windows for each venue's data since there's no common intersection.
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
            logging.FileHandler("acd_phase_grid_simple_binning.log"),
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

def load_cleaned_data(s3_client, bucket: str, date: str) -> Dict[str, Dict[str, pd.DataFrame]]:
    """Load all cleaned data from Phase CLN."""
    logger = logging.getLogger(__name__)
    
    # Load validation summary to get available data
    validation_key = f"analysis/{date}/ACD/_cln/validation_summary.json"
    validation_content = get_s3_object_content(s3_client, bucket, validation_key)
    
    if not validation_content:
        logger.error("No validation summary found")
        return {}
    
    validation_data = json.loads(validation_content.decode('utf-8'))
    cleaned_data = validation_data.get('cleaned_data', {})
    
    all_data = {}
    
    for venue, venue_slices in cleaned_data.items():
        all_data[venue] = {}
        
        for slice_name, slice_info in venue_slices.items():
            s3_key = slice_info['s3_key']
            
            # Load parquet data
            parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
            if parquet_content:
                try:
                    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                        tmp_file.write(parquet_content)
                        tmp_file.flush()
                        df = pd.read_parquet(tmp_file.name)
                        Path(tmp_file.name).unlink()
                    
                    # Ensure timestamp is datetime
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                    df['dt'] = pd.to_datetime(df['dt'], utc=True)
                    
                    all_data[venue][slice_name] = df
                    logger.info(f"Loaded {venue} {slice_name}: {len(df)} rows")
                    
                except Exception as e:
                    logger.error(f"Error loading {venue} {slice_name}: {e}")
            else:
                logger.warning(f"No data found for {venue} {slice_name}")
    
    return all_data

def create_individual_windows(all_data: Dict[str, Dict[str, pd.DataFrame]]) -> List[Dict[str, Any]]:
    """Create individual windows for each venue's data."""
    logger = logging.getLogger(__name__)
    
    windows = []
    
    for venue, venue_slices in all_data.items():
        for slice_name, df in venue_slices.items():
            if not df.empty:
                # Create a window for this specific slice
                start_time = df['timestamp'].min()
                end_time = df['timestamp'].max()
                duration = (end_time - start_time).total_seconds()
                
                window_id = f"{venue}_{slice_name}"
                
                windows.append({
                    "window_id": window_id,
                    "venue": venue,
                    "slice_name": slice_name,
                    "start_utc": start_time.isoformat(),
                    "end_utc": end_time.isoformat(),
                    "duration_seconds": duration,
                    "start_timestamp": start_time.isoformat(),
                    "end_timestamp": end_time.isoformat(),
                    "n_rows": len(df)
                })
                
                logger.info(f"Created window {window_id}: {start_time} to {end_time} ({duration:.1f}s)")
    
    return windows

def bin_venue_data(df: pd.DataFrame, window: Dict[str, Any], venue: str) -> Dict[str, Any]:
    """Bin venue data for a specific window."""
    logger = logging.getLogger(__name__)
    
    if df.empty:
        return {
            "venue": venue,
            "window_id": window['window_id'],
            "n_rows": 0,
            "coverage_percentage": 0.0,
            "bins": [],
            "usable": False
        }
    
    # Filter data to window
    window_start = pd.to_datetime(window['start_timestamp'])
    window_end = pd.to_datetime(window['end_timestamp'])
    
    window_data = df[
        (df['timestamp'] >= window_start) & 
        (df['timestamp'] < window_end)
    ].copy()
    
    if window_data.empty:
        return {
            "venue": venue,
            "window_id": window['window_id'],
            "n_rows": 0,
            "coverage_percentage": 0.0,
            "bins": [],
            "usable": False
        }
    
    # Bin to 1-second intervals
    window_data['bin_time'] = window_data['timestamp'].dt.floor('1s')
    
    # Aggregate by bin
    binned_data = window_data.groupby('bin_time').agg({
        'price': ['last', 'mean', 'std', 'min', 'max'],
        'volume': ['sum', 'mean', 'count']
    }).round(2)
    
    # Flatten column names
    binned_data.columns = ['_'.join(col).strip() for col in binned_data.columns]
    binned_data = binned_data.reset_index()
    
    # Calculate coverage
    total_seconds = window['duration_seconds']
    actual_seconds = len(binned_data)
    coverage_percentage = (actual_seconds / total_seconds) * 100 if total_seconds > 0 else 100.0
    
    # Convert to list of dictionaries
    bins = []
    for _, row in binned_data.iterrows():
        bins.append({
            "timestamp": row['bin_time'].isoformat(),
            "last_price": float(row['price_last']),
            "mean_price": float(row['price_mean']),
            "price_std": float(row['price_std']) if not pd.isna(row['price_std']) else 0.0,
            "price_min": float(row['price_min']),
            "price_max": float(row['price_max']),
            "volume_sum": float(row['volume_sum']),
            "volume_mean": float(row['volume_mean']),
            "trade_count": int(row['volume_count'])
        })
    
    return {
        "venue": venue,
        "window_id": window['window_id'],
        "n_rows": len(window_data),
        "coverage_percentage": coverage_percentage,
        "bins": bins,
        "usable": True  # All individual windows are usable
    }

def process_individual_windows(all_data: Dict[str, Dict[str, pd.DataFrame]], windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process individual windows for each venue."""
    logger = logging.getLogger(__name__)
    
    processed_windows = []
    
    for window in windows:
        venue = window['venue']
        slice_name = window['slice_name']
        
        # Get the data for this venue/slice
        if venue in all_data and slice_name in all_data[venue]:
            df = all_data[venue][slice_name]
            venue_result = bin_venue_data(df, window, venue)
            
            processed_windows.append({
                "window": window,
                "results": {venue: venue_result},
                "all_venues_usable": True  # Individual windows are always usable
            })
            
            logger.info(f"Processed window {window['window_id']}: {venue_result['n_rows']} rows, {venue_result['coverage_percentage']:.1f}% coverage")
        else:
            logger.warning(f"No data found for {venue} {slice_name}")
    
    return processed_windows

def main():
    """Main Phase GRID function."""
    parser = argparse.ArgumentParser(description='ACD Phase GRID - Simple Canonical Time Binning')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE GRID - SIMPLE CANONICAL TIME BINNING")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # Load cleaned data
    print(f"\n🔄 Loading cleaned data from Phase CLN...")
    try:
        all_data = load_cleaned_data(s3_client, args.bucket, args.date)
        
        if not all_data:
            print(f"❌ No cleaned data found")
            sys.exit(1)
        
        print(f"✅ Loaded cleaned data for {len(all_data)} venues")
        for venue, venue_slices in all_data.items():
            print(f"   {venue}: {len(venue_slices)} slices")
            
    except Exception as e:
        print(f"❌ Error loading cleaned data: {e}")
        sys.exit(1)
    
    # Create individual windows
    print(f"\n🔍 Creating individual windows for each venue...")
    try:
        windows = create_individual_windows(all_data)
        
        if not windows:
            print(f"❌ No windows created")
            sys.exit(1)
        
        print(f"✅ Created {len(windows)} individual windows")
        for window in windows:
            print(f"   {window['window_id']}: {window['start_utc']} to {window['end_utc']} ({window['duration_seconds']:.1f}s)")
            
    except Exception as e:
        print(f"❌ Error creating individual windows: {e}")
        sys.exit(1)
    
    # Process individual windows
    print(f"\n🔍 Processing individual windows...")
    try:
        processed_windows = process_individual_windows(all_data, windows)
        
        if not processed_windows:
            print(f"❌ No windows processed")
            sys.exit(1)
        
        print(f"✅ Processed {len(processed_windows)} windows")
        
    except Exception as e:
        print(f"❌ Error processing windows: {e}")
        sys.exit(1)
    
    # Save grid inventory
    print(f"\n💾 Saving grid inventory...")
    
    grid_inventory = {
        "date": args.date,
        "total_windows": len(windows),
        "processed_windows": len(processed_windows),
        "windows": windows,
        "processed_window_results": processed_windows,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    grid_key = f"analysis/{args.date}/ACD/_grid/grid_inventory.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=grid_key,
        Body=json.dumps(grid_inventory, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved grid inventory: s3://{args.bucket}/{grid_key}")
    
    # Final summary
    print(f"\n📊 SIMPLE CANONICAL TIME BINNING SUMMARY")
    print("="*60)
    print(f"Date: {args.date}")
    print(f"Total windows: {len(windows)}")
    print(f"Processed windows: {len(processed_windows)}")
    
    if processed_windows:
        print(f"\nProcessed windows:")
        for processed_window in processed_windows:
            window = processed_window['window']
            results = processed_window['results']
            
            print(f"  {window['window_id']}: {window['start_utc']} to {window['end_utc']}")
            for venue, result in results.items():
                print(f"    {venue}: {result['n_rows']} rows, {result['coverage_percentage']:.1f}% coverage")
    
    print(f"\n✅ SIMPLE CANONICAL TIME BINNING COMPLETED")
    print(f"   {len(processed_windows)} windows ready for ACD analysis")
    print(f"   Ready for Phase SUM (Summary Statistics)")
    
    print(f"\n📁 Generated artifacts:")
    print(f"  Grid inventory: s3://{args.bucket}/{grid_key}")

if __name__ == "__main__":
    main()
