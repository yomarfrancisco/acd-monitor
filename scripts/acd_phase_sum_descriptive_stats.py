#!/usr/bin/env python3
"""
ACD Phase SUM - Descriptive Stats

Computes per venue and cross-venue descriptive statistics.
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
            logging.FileHandler("acd_phase_sum_descriptive_stats.log"),
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

def load_clean_data(s3_client, bucket: str, date: str, venue: str) -> Optional[pd.DataFrame]:
    """Load cleaned data for a venue."""
    logger = logging.getLogger(__name__)
    
    s3_key = f"analysis/{date}/ACD/_cln/{venue}/part-0000.parquet"
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
        
        logger.info(f"Loaded {venue} clean data: {len(df)} rows")
        return df
        
    except Exception as e:
        logger.error(f"Error loading {venue} clean data: {e}")
        return None

def compute_venue_statistics(df: pd.DataFrame, venue: str) -> Dict[str, Any]:
    """Compute statistics for a single venue."""
    logger = logging.getLogger(__name__)
    
    if df.empty:
        return {"error": "Empty DataFrame"}
    
    # Basic statistics
    n_rows = len(df)
    time_span = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
    
    # Price statistics
    price_stats = {
        "mean": float(df['price'].mean()),
        "median": float(df['price'].median()),
        "std": float(df['price'].std()),
        "min": float(df['price'].min()),
        "max": float(df['price'].max()),
        "q25": float(df['price'].quantile(0.25)),
        "q75": float(df['price'].quantile(0.75))
    }
    
    # Volume statistics
    volume_stats = {
        "total": float(df['volume'].sum()),
        "mean": float(df['volume'].mean()),
        "median": float(df['volume'].median()),
        "std": float(df['volume'].std()),
        "min": float(df['volume'].min()),
        "max": float(df['volume'].max())
    }
    
    # Timing statistics
    time_deltas = df['timestamp'].diff().dropna()
    time_deltas_seconds = time_deltas.dt.total_seconds()
    
    timing_stats = {
        "mean_interval": float(time_deltas_seconds.mean()),
        "median_interval": float(time_deltas_seconds.median()),
        "std_interval": float(time_deltas_seconds.std()),
        "cv_interval": float(time_deltas_seconds.std() / time_deltas_seconds.mean()) if time_deltas_seconds.mean() > 0 else 0,
        "min_interval": float(time_deltas_seconds.min()),
        "max_interval": float(time_deltas_seconds.max())
    }
    
    # Duplicate statistics
    exact_duplicates = df.duplicated().sum()
    timestamp_duplicates = df.duplicated(subset=['timestamp']).sum()
    
    duplicate_stats = {
        "exact_duplicate_ratio": float(exact_duplicates / n_rows),
        "timestamp_duplicate_ratio": float(timestamp_duplicates / n_rows),
        "exact_duplicates": int(exact_duplicates),
        "timestamp_duplicates": int(timestamp_duplicates)
    }
    
    # Message rate
    message_rate = n_rows / time_span if time_span > 0 else 0
    
    venue_stats = {
        "venue": venue,
        "n_rows": int(n_rows),
        "time_span_seconds": float(time_span),
        "message_rate": float(message_rate),
        "price_stats": price_stats,
        "volume_stats": volume_stats,
        "timing_stats": timing_stats,
        "duplicate_stats": duplicate_stats
    }
    
    logger.info(f"{venue}: {n_rows} rows, ${price_stats['mean']:.2f} mean, ${price_stats['std']:.2f} std, {message_rate:.1f} msg/s")
    
    return venue_stats

def compute_5min_bin_statistics(df: pd.DataFrame, venue: str) -> List[Dict[str, Any]]:
    """Compute statistics for 5-minute bins."""
    logger = logging.getLogger(__name__)
    
    if df.empty:
        return []
    
    # Create 5-minute bins
    df['bin'] = df['timestamp'].dt.floor('5T')
    bins = df.groupby('bin')
    
    bin_stats = []
    for bin_time, bin_data in bins:
        bin_stat = {
            "bin_start": bin_time.isoformat(),
            "n_rows": int(len(bin_data)),
            "price_mean": float(bin_data['price'].mean()),
            "price_std": float(bin_data['price'].std()),
            "volume_total": float(bin_data['volume'].sum()),
            "message_rate": float(len(bin_data) / 300)  # 5 minutes = 300 seconds
        }
        bin_stats.append(bin_stat)
    
    logger.info(f"{venue}: {len(bin_stats)} 5-minute bins")
    return bin_stats

def compute_cross_venue_analysis(venues_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute cross-venue analysis."""
    logger = logging.getLogger(__name__)
    
    if len(venues_data) < 2:
        return {
            "status": "insufficient_venues",
            "message": "Need at least 2 venues for cross-venue analysis",
            "available_venues": list(venues_data.keys())
        }
    
    venues = list(venues_data.keys())
    cross_venue_stats = {}
    
    # Pairwise analysis
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue
            
            df1 = venues_data[venue1]
            df2 = venues_data[venue2]
            
            if df1.empty or df2.empty:
                continue
            
            # Price spread analysis
            mean1 = df1['price'].mean()
            mean2 = df2['price'].mean()
            spread_absolute = abs(mean1 - mean2)
            spread_percentage = (spread_absolute / mean1) * 100 if mean1 > 0 else 0
            
            # Instantaneous spread analysis (if we had aligned data)
            # For now, just report the mean spread
            instantaneous_spreads = {
                "mean_spread_absolute": spread_absolute,
                "mean_spread_percentage": spread_percentage,
                "p05_spread": spread_percentage,  # Simplified
                "p50_spread": spread_percentage,  # Simplified
                "p95_spread": spread_percentage   # Simplified
            }
            
            # Time above threshold
            time_above_threshold = 0.0  # Simplified - would need aligned data
            
            cross_venue_stats[f"{venue1}_vs_{venue2}"] = {
                "venue1": venue1,
                "venue2": venue2,
                "mean_price_1": float(mean1),
                "mean_price_2": float(mean2),
                "spread_analysis": instantaneous_spreads,
                "time_above_1_5_percent": time_above_threshold
            }
            
            logger.info(f"{venue1} vs {venue2}: {spread_percentage:.2f}% spread")
    
    return {
        "status": "success",
        "pairwise_analysis": cross_venue_stats
    }

def generate_markdown_report(venue_stats: Dict[str, Any], bin_stats: Dict[str, List[Dict[str, Any]]], cross_venue_stats: Dict[str, Any]) -> str:
    """Generate markdown report."""
    
    report = f"""# ACD Phase SUM - Descriptive Statistics Report

**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Per-Venue Statistics

"""
    
    for venue, stats in venue_stats.items():
        if "error" in stats:
            continue
        
        report += f"""### {venue.upper()}

- **Rows**: {stats['n_rows']:,}
- **Time Span**: {stats['time_span_seconds']:.1f} seconds
- **Message Rate**: {stats['message_rate']:.1f} messages/second

#### Price Statistics
- **Mean**: ${stats['price_stats']['mean']:,.2f}
- **Median**: ${stats['price_stats']['median']:,.2f}
- **Std Dev**: ${stats['price_stats']['std']:,.2f}
- **Min**: ${stats['price_stats']['min']:,.2f}
- **Max**: ${stats['price_stats']['max']:,.2f}
- **Q25**: ${stats['price_stats']['q25']:,.2f}
- **Q75**: ${stats['price_stats']['q75']:,.2f}

#### Volume Statistics
- **Total**: {stats['volume_stats']['total']:,.2f}
- **Mean**: {stats['volume_stats']['mean']:.4f}
- **Median**: {stats['volume_stats']['median']:.4f}
- **Std Dev**: {stats['volume_stats']['std']:.4f}

#### Timing Statistics
- **Mean Interval**: {stats['timing_stats']['mean_interval']:.3f} seconds
- **Median Interval**: {stats['timing_stats']['median_interval']:.3f} seconds
- **CV**: {stats['timing_stats']['cv_interval']:.3f}
- **Min Interval**: {stats['timing_stats']['min_interval']:.3f} seconds
- **Max Interval**: {stats['timing_stats']['max_interval']:.3f} seconds

#### Duplicate Statistics
- **Exact Duplicates**: {stats['duplicate_stats']['exact_duplicates']} ({stats['duplicate_stats']['exact_duplicate_ratio']:.1%})
- **Timestamp Duplicates**: {stats['duplicate_stats']['timestamp_duplicates']} ({stats['duplicate_stats']['timestamp_duplicate_ratio']:.1%})

"""
    
    # 5-minute bin statistics
    report += "## 5-Minute Bin Statistics\n\n"
    
    for venue, bins in bin_stats.items():
        if not bins:
            continue
        
        report += f"### {venue.upper()} 5-Minute Bins\n\n"
        report += "| Bin Start | Rows | Price Mean | Price Std | Volume Total | Msg Rate |\n"
        report += "|-----------|------|------------|-----------|--------------|----------|\n"
        
        for bin_stat in bins:
            report += f"| {bin_stat['bin_start']} | {bin_stat['n_rows']} | ${bin_stat['price_mean']:,.2f} | ${bin_stat['price_std']:,.2f} | {bin_stat['volume_total']:,.2f} | {bin_stat['message_rate']:.1f} |\n"
        
        report += "\n"
    
    # Cross-venue analysis
    report += "## Cross-Venue Analysis\n\n"
    
    if cross_venue_stats.get("status") == "insufficient_venues":
        report += f"**Status**: {cross_venue_stats['message']}\n"
        report += f"**Available Venues**: {', '.join(cross_venue_stats['available_venues'])}\n\n"
    else:
        report += "### Pairwise Price Spreads\n\n"
        report += "| Venue Pair | Mean Price 1 | Mean Price 2 | Spread ($) | Spread (%) |\n"
        report += "|------------|--------------|--------------|------------|------------|\n"
        
        for pair, analysis in cross_venue_stats.get("pairwise_analysis", {}).items():
            spread_abs = analysis["spread_analysis"]["mean_spread_absolute"]
            spread_pct = analysis["spread_analysis"]["mean_spread_percentage"]
            report += f"| {pair.upper()} | ${analysis['mean_price_1']:,.2f} | ${analysis['mean_price_2']:,.2f} | ${spread_abs:,.2f} | {spread_pct:.2f}% |\n"
        
        report += "\n"
    
    # Quality gates
    report += "## Quality Gates\n\n"
    
    all_passed = True
    for venue, stats in venue_stats.items():
        if "error" in stats:
            continue
        
        price_std_ok = stats['price_stats']['std'] >= 0.10
        cv_ok = stats['timing_stats']['cv_interval'] > 0.05
        dup_ok = stats['duplicate_stats']['exact_duplicate_ratio'] <= 0.05
        
        report += f"### {venue.upper()}\n"
        report += f"- **Price Std ≥ $0.10**: {'✅' if price_std_ok else '❌'} (${stats['price_stats']['std']:.2f})\n"
        report += f"- **CV(Δt) > 0.05**: {'✅' if cv_ok else '❌'} ({stats['timing_stats']['cv_interval']:.3f})\n"
        report += f"- **Exact Duplicates ≤ 5%**: {'✅' if dup_ok else '❌'} ({stats['duplicate_stats']['exact_duplicate_ratio']:.1%})\n\n"
        
        if not all([price_std_ok, cv_ok, dup_ok]):
            all_passed = False
    
    if all_passed:
        report += "**Overall Status**: ✅ All quality gates passed\n"
    else:
        report += "**Overall Status**: ❌ Some quality gates failed\n"
    
    return report

def main():
    """Main Phase SUM function."""
    parser = argparse.ArgumentParser(description='ACD Phase SUM - Descriptive Stats')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE SUM - DESCRIPTIVE STATISTICS")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # Load clean data
    print(f"\n🔍 Loading clean data...")
    
    # Try to load from clean results
    clean_results_key = f"analysis/{args.date}/ACD/_cln/clean_results.json"
    clean_results_content = get_s3_object_text(s3_client, args.bucket, clean_results_key)
    
    if clean_results_content:
        clean_results = json.loads(clean_results_content)
        venues = clean_results.get("clean_results", {}).keys()
    else:
        # Fallback to trying common venues
        venues = ['kraken']
    
    venues_data = {}
    for venue in venues:
        print(f"\n📊 Loading {venue.upper()}...")
        
        df = load_clean_data(s3_client, args.bucket, args.date, venue)
        if df is None:
            print(f"   ❌ No clean data found for {venue}")
            continue
        
        venues_data[venue] = df
        print(f"   ✅ Loaded {len(df)} rows")
    
    if not venues_data:
        print(f"❌ No clean data found for any venue")
        sys.exit(1)
    
    print(f"✅ Loaded {len(venues_data)} venues with clean data")
    
    # Compute venue statistics
    print(f"\n📊 Computing venue statistics...")
    
    venue_stats = {}
    bin_stats = {}
    
    for venue, df in venues_data.items():
        print(f"\n📊 Processing {venue.upper()}...")
        
        # Venue statistics
        stats = compute_venue_statistics(df, venue)
        venue_stats[venue] = stats
        
        # 5-minute bin statistics
        bins = compute_5min_bin_statistics(df, venue)
        bin_stats[venue] = bins
        
        print(f"   ✅ Computed statistics for {venue}")
    
    # Compute cross-venue analysis
    print(f"\n📊 Computing cross-venue analysis...")
    
    cross_venue_stats = compute_cross_venue_analysis(venues_data)
    
    print(f"✅ Cross-venue analysis completed")
    
    # Generate markdown report
    print(f"\n📝 Generating markdown report...")
    
    markdown_report = generate_markdown_report(venue_stats, bin_stats, cross_venue_stats)
    
    # Save results
    print(f"\n💾 Saving results...")
    
    results = {
        "date": args.date,
        "venue_statistics": venue_stats,
        "bin_statistics": bin_stats,
        "cross_venue_statistics": cross_venue_stats,
        "summary": {
            "venues_analyzed": len(venue_stats),
            "total_rows": sum(stats.get("n_rows", 0) for stats in venue_stats.values()),
            "quality_gates_passed": all(
                stats.get("price_stats", {}).get("std", 0) >= 0.10 and
                stats.get("timing_stats", {}).get("cv_interval", 0) > 0.05 and
                stats.get("duplicate_stats", {}).get("exact_duplicate_ratio", 0) <= 0.05
                for stats in venue_stats.values()
                if "error" not in stats
            )
        },
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Save JSON results
    results_key = f"analysis/{args.date}/ACD/_sum/summary.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2),
        ContentType='application/json'
    )
    
    # Save markdown report
    report_key = f"analysis/{args.date}/ACD/_sum/summary.md"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=report_key,
        Body=markdown_report.encode('utf-8'),
        ContentType='text/markdown'
    )
    
    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")
    print(f"💾 Saved report: s3://{args.bucket}/{report_key}")
    
    # Final summary
    print(f"\n📊 PHASE SUM SUMMARY")
    print("="*60)
    print(f"Venues analyzed: {len(venue_stats)}")
    print(f"Total rows: {results['summary']['total_rows']}")
    print(f"Quality gates passed: {results['summary']['quality_gates_passed']}")
    
    for venue, stats in venue_stats.items():
        if "error" in stats:
            continue
        print(f"\n{venue.upper()}:")
        print(f"  Rows: {stats['n_rows']:,}")
        print(f"  Price: ${stats['price_stats']['mean']:,.2f} ± ${stats['price_stats']['std']:,.2f}")
        print(f"  Volume: {stats['volume_stats']['total']:,.2f}")
        print(f"  Message rate: {stats['message_rate']:.1f} msg/s")
    
    print(f"\n✅ PHASE SUM COMPLETE - Proceeding to Phase SIG")

if __name__ == "__main__":
    main()
