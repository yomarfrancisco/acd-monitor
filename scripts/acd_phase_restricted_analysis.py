#!/usr/bin/env python3
"""
ACD Phase Restricted - Analysis for Validated Tick-Level Venues

Proceeds with Binance + Kraken only, building canonical window and generating
exploratory summary stats with clear limitations due to short overlap.
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
from scipy import stats

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_restricted_analysis.log"),
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

def load_venue_data(s3_client, bucket: str, date: str, venue: str) -> Optional[pd.DataFrame]:
    """Load data for a specific venue."""
    logger = logging.getLogger(__name__)
    
    # Try raw_probes first
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

def build_canonical_window(venues_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Build canonical window from validated tick-level venues."""
    logger = logging.getLogger(__name__)
    
    if not venues_data:
        return {
            "status": "failed",
            "reason": "No validated venues available",
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
    
    canonical_window = {
        "status": "success",
        "canonical_start": canonical_start.isoformat(),
        "canonical_end": canonical_end.isoformat(),
        "canonical_duration_seconds": canonical_duration,
        "included_venues": list(venues_data.keys()),
        "excluded_venues": ["coinbase", "bybit", "okx"],
        "exclusion_reasons": {
            "coinbase": "Synthetic data detected (CV = 0.000)",
            "bybit": "Synthetic data detected (CV = 0.000)",
            "okx": "No data found"
        },
        "coverage_analysis": coverage_analysis,
        "limitations": {
            "short_overlap": canonical_duration < 3600,  # Less than 1 hour
            "limited_venues": len(venues_data) < 3,
            "exploratory_only": True
        }
    }
    
    logger.info(f"Canonical window: {canonical_start} to {canonical_end} ({canonical_duration:.1f}s)")
    logger.info(f"Included venues: {list(venues_data.keys())}")
    logger.info(f"Excluded venues: coinbase (synthetic), bybit (synthetic), okx (missing)")
    
    return canonical_window

def compute_summary_statistics(venues_data: Dict[str, pd.DataFrame], canonical_window: Dict[str, Any]) -> Dict[str, Any]:
    """Compute summary statistics for canonical window."""
    logger = logging.getLogger(__name__)
    
    summary_stats = {
        "canonical_window": canonical_window,
        "venue_statistics": {},
        "cross_venue_analysis": {},
        "limitations": canonical_window.get("limitations", {})
    }
    
    # Filter data to canonical window
    canonical_start = pd.to_datetime(canonical_window["canonical_start"])
    canonical_end = pd.to_datetime(canonical_window["canonical_end"])
    
    for venue, df in venues_data.items():
        if df.empty:
            continue
        
        # Filter to canonical window
        window_data = df[
            (df['timestamp'] >= canonical_start) & 
            (df['timestamp'] <= canonical_end)
        ].copy()
        
        if window_data.empty:
            continue
        
        # Compute venue statistics
        price_stats = {
            "n_rows": len(window_data),
            "price_mean": float(window_data['price'].mean()),
            "price_std": float(window_data['price'].std()),
            "price_min": float(window_data['price'].min()),
            "price_max": float(window_data['price'].max()),
            "price_median": float(window_data['price'].median())
        }
        
        volume_stats = {
            "volume_total": float(window_data['volume'].sum()),
            "volume_mean": float(window_data['volume'].mean()),
            "volume_median": float(window_data['volume'].median())
        }
        
        timing_stats = {
            "start_time": window_data['timestamp'].min().isoformat(),
            "end_time": window_data['timestamp'].max().isoformat(),
            "duration_seconds": (window_data['timestamp'].max() - window_data['timestamp'].min()).total_seconds()
        }
        
        summary_stats["venue_statistics"][venue] = {
            "price_stats": price_stats,
            "volume_stats": volume_stats,
            "timing_stats": timing_stats
        }
        
        logger.info(f"{venue}: {price_stats['n_rows']} rows, ${price_stats['price_mean']:.2f} mean, ${price_stats['price_std']:.2f} std")
    
    # Cross-venue analysis
    venues = list(venues_data.keys())
    if len(venues) >= 2:
        for i, venue1 in enumerate(venues):
            for j, venue2 in enumerate(venues):
                if i >= j:
                    continue
                
                df1 = venues_data[venue1]
                df2 = venues_data[venue2]
                
                if df1.empty or df2.empty:
                    continue
                
                # Filter to canonical window
                window1 = df1[
                    (df1['timestamp'] >= canonical_start) & 
                    (df1['timestamp'] <= canonical_end)
                ]
                window2 = df2[
                    (df2['timestamp'] >= canonical_start) & 
                    (df2['timestamp'] <= canonical_end)
                ]
                
                if window1.empty or window2.empty:
                    continue
                
                # Price correlation
                price1 = window1['price'].values
                price2 = window2['price'].values
                
                if len(price1) > 1 and len(price2) > 1:
                    correlation = np.corrcoef(price1, price2)[0, 1] if len(price1) == len(price2) else np.nan
                else:
                    correlation = np.nan
                
                # Price spread
                mean1 = window1['price'].mean()
                mean2 = window2['price'].mean()
                spread_percentage = abs(mean1 - mean2) / mean1 * 100 if mean1 > 0 else 0
                
                summary_stats["cross_venue_analysis"][f"{venue1}_vs_{venue2}"] = {
                    "correlation": float(correlation) if not np.isnan(correlation) else None,
                    "spread_percentage": spread_percentage,
                    "mean_price_1": float(mean1),
                    "mean_price_2": float(mean2)
                }
                
                logger.info(f"{venue1} vs {venue2}: correlation={correlation:.3f}, spread={spread_percentage:.2f}%")
    
    return summary_stats

def compute_leader_follower_analysis(venues_data: Dict[str, pd.DataFrame], canonical_window: Dict[str, Any]) -> Dict[str, Any]:
    """Compute simple leader-follower analysis."""
    logger = logging.getLogger(__name__)
    
    leader_follower = {
        "canonical_window": canonical_window,
        "venue_pairs": {},
        "limitations": canonical_window.get("limitations", {})
    }
    
    # Filter data to canonical window
    canonical_start = pd.to_datetime(canonical_window["canonical_start"])
    canonical_end = pd.to_datetime(canonical_window["canonical_end"])
    
    venues = list(venues_data.keys())
    if len(venues) < 2:
        logger.warning("Insufficient venues for leader-follower analysis")
        return leader_follower
    
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue
            
            df1 = venues_data[venue1]
            df2 = venues_data[venue2]
            
            if df1.empty or df2.empty:
                continue
            
            # Filter to canonical window
            window1 = df1[
                (df1['timestamp'] >= canonical_start) & 
                (df1['timestamp'] <= canonical_end)
            ].copy()
            window2 = df2[
                (df2['timestamp'] >= canonical_start) & 
                (df2['timestamp'] <= canonical_end)
            ].copy()
            
            if window1.empty or window2.empty:
                continue
            
            # Sort by timestamp
            window1 = window1.sort_values('timestamp')
            window2 = window2.sort_values('timestamp')
            
            # Compute price changes
            price1_changes = window1['price'].diff().dropna()
            price2_changes = window2['price'].diff().dropna()
            
            if len(price1_changes) > 1 and len(price2_changes) > 1:
                # Cross-correlation with small lags
                max_lag = min(5, len(price1_changes) // 4)  # Limit lag to avoid overfitting
                correlations = []
                
                for lag in range(-max_lag, max_lag + 1):
                    if lag == 0:
                        corr = np.corrcoef(price1_changes, price2_changes)[0, 1] if len(price1_changes) == len(price2_changes) else np.nan
                    elif lag > 0:
                        # venue1 leads venue2
                        if len(price1_changes) > lag and len(price2_changes) > lag:
                            corr = np.corrcoef(price1_changes[:-lag], price2_changes[lag:])[0, 1] if len(price1_changes[:-lag]) == len(price2_changes[lag:]) else np.nan
                        else:
                            corr = np.nan
                    else:
                        # venue2 leads venue1
                        lag_abs = abs(lag)
                        if len(price1_changes) > lag_abs and len(price2_changes) > lag_abs:
                            corr = np.corrcoef(price1_changes[lag_abs:], price2_changes[:-lag_abs])[0, 1] if len(price1_changes[lag_abs:]) == len(price2_changes[:-lag_abs]) else np.nan
                        else:
                            corr = np.nan
                    
                    correlations.append({
                        "lag": lag,
                        "correlation": float(corr) if not np.isnan(corr) else None
                    })
                
                # Find best correlation
                valid_correlations = [c for c in correlations if c["correlation"] is not None]
                if valid_correlations:
                    best_corr = max(valid_correlations, key=lambda x: abs(x["correlation"]))
                    leader = venue1 if best_corr["lag"] > 0 else venue2 if best_corr["lag"] < 0 else "simultaneous"
                else:
                    best_corr = {"lag": 0, "correlation": 0}
                    leader = "indeterminate"
                
                leader_follower["venue_pairs"][f"{venue1}_vs_{venue2}"] = {
                    "best_correlation": best_corr["correlation"],
                    "best_lag": best_corr["lag"],
                    "leader": leader,
                    "all_correlations": correlations
                }
                
                logger.info(f"{venue1} vs {venue2}: best lag={best_corr['lag']}, corr={best_corr['correlation']:.3f}, leader={leader}")
            else:
                logger.warning(f"Insufficient data for leader-follower analysis: {venue1} vs {venue2}")
    
    return leader_follower

def main():
    """Main restricted analysis function."""
    parser = argparse.ArgumentParser(description='ACD Phase Restricted - Analysis for Validated Tick-Level Venues')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE RESTRICTED - ANALYSIS FOR VALIDATED TICK-LEVEL VENUES")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    print(f"🎯 Target venues: Binance, Kraken (validated tick-level)")
    print(f"❌ Excluded venues: Coinbase (synthetic), BYBIT (synthetic), OKX (missing)")
    print(f"⚠️  EXPLORATORY ANALYSIS - Limited by short overlap")
    
    # Load and validate tick-level venues
    print(f"\n🔍 Loading and validating tick-level venues...")
    
    tick_venues = ['binance', 'kraken']
    venues_data = {}
    validation_results = {}
    
    for venue in tick_venues:
        print(f"\n📊 Processing {venue.upper()}...")
        
        df = load_venue_data(s3_client, args.bucket, args.date, venue)
        if df is None:
            print(f"   ❌ No data found for {venue}")
            validation_results[venue] = {
                "status": "failed",
                "reason": "No data found"
            }
            continue
        
        # Validate tick timing
        is_tick_level, timing_stats = validate_tick_timing(df, venue)
        
        if is_tick_level:
            venues_data[venue] = df
            validation_results[venue] = {
                "status": "success",
                "timing_stats": timing_stats
            }
            print(f"   ✅ Tick-level data confirmed (CV={timing_stats['cv']:.3f})")
        else:
            validation_results[venue] = {
                "status": "excluded",
                "reason": "Synthetic data detected",
                "timing_stats": timing_stats
            }
            print(f"   ❌ Synthetic data detected (CV={timing_stats['cv']:.3f}) - excluding")
    
    if not venues_data:
        print(f"❌ No validated tick-level venues found")
        sys.exit(1)
    
    print(f"✅ Loaded {len(venues_data)} validated tick-level venues")
    
    # Build canonical window
    print(f"\n🔍 Building canonical window...")
    
    canonical_window = build_canonical_window(venues_data)
    
    if canonical_window["status"] != "success":
        print(f"❌ Failed to build canonical window: {canonical_window['reason']}")
        sys.exit(1)
    
    print(f"✅ Canonical window built successfully")
    print(f"   Duration: {canonical_window['canonical_duration_seconds']:.1f} seconds")
    print(f"   Included: {canonical_window['included_venues']}")
    print(f"   Excluded: {canonical_window['excluded_venues']}")
    
    # Check limitations
    limitations = canonical_window.get("limitations", {})
    if limitations.get("short_overlap", False):
        print(f"⚠️  WARNING: Short overlap detected - results are exploratory only")
    if limitations.get("limited_venues", False):
        print(f"⚠️  WARNING: Limited venues - results may not be statistically reliable")
    
    # Compute summary statistics
    print(f"\n📊 Computing summary statistics...")
    
    summary_stats = compute_summary_statistics(venues_data, canonical_window)
    
    print(f"✅ Summary statistics computed")
    
    # Compute leader-follower analysis
    print(f"\n📊 Computing leader-follower analysis...")
    
    leader_follower = compute_leader_follower_analysis(venues_data, canonical_window)
    
    print(f"✅ Leader-follower analysis computed")
    
    # Save results
    print(f"\n💾 Saving restricted analysis results...")
    
    results = {
        "date": args.date,
        "canonical_window": canonical_window,
        "validation_results": validation_results,
        "summary_statistics": summary_stats,
        "leader_follower_analysis": leader_follower,
        "limitations": limitations,
        "summary": {
            "included_venues": canonical_window["included_venues"],
            "excluded_venues": canonical_window["excluded_venues"],
            "exclusion_reasons": canonical_window["exclusion_reasons"],
            "canonical_duration_seconds": canonical_window["canonical_duration_seconds"],
            "exploratory_only": limitations.get("exploratory_only", False),
            "statistically_reliable": not limitations.get("short_overlap", False) and not limitations.get("limited_venues", False)
        },
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    results_key = f"analysis/{args.date}/ACD/_restricted/restricted_analysis_results.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")
    
    # Final summary
    print(f"\n📊 RESTRICTED ACD ANALYSIS SUMMARY")
    print("="*60)
    print(f"Included venues: {len(canonical_window['included_venues'])}")
    print(f"Excluded venues: {len(canonical_window['excluded_venues'])}")
    print(f"Canonical duration: {canonical_window['canonical_duration_seconds']:.1f} seconds")
    print(f"Exploratory only: {limitations.get('exploratory_only', False)}")
    print(f"Statistically reliable: {not limitations.get('short_overlap', False) and not limitations.get('limited_venues', False)}")
    
    if limitations.get("short_overlap", False):
        print(f"\n⚠️  LIMITATIONS:")
        print(f"   • Short overlap detected - results are exploratory only")
        print(f"   • Consider backfill for longer windows")
        print(f"   • Results may not be statistically reliable")
    
    print(f"\n✅ RESTRICTED ACD ANALYSIS COMPLETE")
    print(f"   Proceeding with validated tick-level venues only")
    print(f"   Results saved for further analysis")

if __name__ == "__main__":
    main()
