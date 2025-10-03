#!/usr/bin/env python3
"""
4-Hour Rolling Segment Analysis Script

Produces production-grade 4-hour resolution quality reports for ACD analysis.
Partitions captured trades into 4-hour blocks and computes comprehensive statistics.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import boto3
import numpy as np
import pandas as pd


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("segment_4h_analysis.log"),
        ],
    )


def load_venue_data(s3_client, bucket: str, venue: str, slice_name: str, date: str) -> pd.DataFrame:
    """
    Load raw parquet data for a specific venue slice.
    """
    logger = logging.getLogger(__name__)

    try:
        # Read sample parquet data
        sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"
        response = s3_client.get_object(Bucket=bucket, Key=sample_key)
        parquet_data = response["Body"].read()

        # Write to temporary file and read
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        # Convert timestamps to datetime
        df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")

        return df

    except Exception as e:
        logger.error(f"Error loading {venue} {slice_name}: {e}")
        return pd.DataFrame()


def partition_into_4h_segments(df: pd.DataFrame, venue: str) -> Dict[str, pd.DataFrame]:
    """
    Partition data into 4-hour segments (00:00-04:00, 04:00-08:00, etc.).
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {}

    # Ensure data is sorted by timestamp
    df_sorted = df.sort_values("dt").reset_index(drop=True)

    # Create 4-hour segments
    segments = {}

    # Define 4-hour windows (UTC)
    for hour_start in range(0, 24, 4):
        hour_end = hour_start + 4

        # Create time range for this segment
        start_time = (
            df_sorted["dt"].min().replace(hour=hour_start, minute=0, second=0, microsecond=0)
        )
        end_time = start_time + timedelta(hours=4)

        # Filter data for this segment
        segment_mask = (df_sorted["dt"] >= start_time) & (df_sorted["dt"] < end_time)
        segment_df = df_sorted[segment_mask].copy()

        if not segment_df.empty:
            segment_name = f"{hour_start:02d}:00-{hour_end:02d}:00"
            segments[segment_name] = segment_df
            logger.info(f"{venue} {segment_name}: {len(segment_df)} trades")

    return segments


def compute_segment_stats(
    segment_df: pd.DataFrame, segment_name: str, venue: str
) -> Dict[str, Any]:
    """
    Compute comprehensive statistics for a 4-hour segment.
    """
    logger = logging.getLogger(__name__)

    if segment_df.empty:
        return {"segment": segment_name, "venue": venue, "trades": 0, "error": "Empty segment"}

    prices = segment_df["price"].values
    volumes = (
        segment_df["volume"].values if "volume" in segment_df.columns else np.zeros(len(segment_df))
    )

    # Basic statistics
    stats = {
        "segment": segment_name,
        "venue": venue,
        "trades": len(segment_df),
        "mean_price": float(np.mean(prices)),
        "median_price": float(np.median(prices)),
        "min_price": float(np.min(prices)),
        "max_price": float(np.max(prices)),
        "std_price": float(np.std(prices)),
        "variance_price": float(np.var(prices)),
        "first_price": float(prices[0]),
        "last_price": float(prices[-1]),
        "price_drift": float(prices[-1] - prices[0]),
        "total_volume": float(np.sum(volumes)),
        "avg_volume_per_trade": float(np.mean(volumes)),
        "time_span_hours": (segment_df["dt"].max() - segment_df["dt"].min()).total_seconds() / 3600,
        "start_time": segment_df["dt"].min().isoformat(),
        "end_time": segment_df["dt"].max().isoformat(),
    }

    return stats


def check_duplicates_and_anomalies(
    segment_df: pd.DataFrame, segment_name: str, venue: str
) -> Dict[str, Any]:
    """
    Check for duplicates and apply anomaly detection rules.
    """
    logger = logging.getLogger(__name__)

    if segment_df.empty:
        return {
            "segment": segment_name,
            "venue": venue,
            "exact_duplicates": 0,
            "timestamp_duplicates": 0,
            "price_duplicates": 0,
            "duplicate_ratio": 0.0,
            "outliers_3sigma": 0,
            "outlier_ratio": 0.0,
            "sanity_violations": 0,
            "sanity_violation_ratio": 0.0,
        }

    # Duplicate analysis
    exact_duplicates = segment_df.duplicated().sum()
    timestamp_duplicates = segment_df["timestamp"].duplicated().sum()
    price_duplicates = segment_df["price"].duplicated().sum()

    duplicate_ratio = exact_duplicates / len(segment_df)

    # 3σ outlier detection
    prices = segment_df["price"].values
    price_mean = np.mean(prices)
    price_std = np.std(prices)

    outliers_3sigma = 0
    if price_std > 0:
        outliers_3sigma = np.sum(np.abs(prices - price_mean) > (3 * price_std))

    outlier_ratio = outliers_3sigma / len(segment_df)

    # Sanity bounds check (BTC < $50,000 or > $500,000)
    sanity_violations = np.sum((prices < 50000) | (prices > 500000))
    sanity_violation_ratio = sanity_violations / len(segment_df)

    return {
        "segment": segment_name,
        "venue": venue,
        "exact_duplicates": int(exact_duplicates),
        "timestamp_duplicates": int(timestamp_duplicates),
        "price_duplicates": int(price_duplicates),
        "duplicate_ratio": float(duplicate_ratio),
        "outliers_3sigma": int(outliers_3sigma),
        "outlier_ratio": float(outlier_ratio),
        "sanity_violations": int(sanity_violations),
        "sanity_violation_ratio": float(sanity_violation_ratio),
    }


def compute_cross_venue_spread(
    venue_stats: Dict[str, Dict[str, Any]], segment_name: str
) -> Dict[str, Any]:
    """
    Compute cross-venue spread analysis for a 4-hour segment.
    """
    logger = logging.getLogger(__name__)

    # Get mean prices for each venue in this segment
    venue_means = {}
    for venue, stats in venue_stats.items():
        if segment_name in stats and "mean_price" in stats[segment_name]:
            venue_means[venue] = stats[segment_name]["mean_price"]

    if len(venue_means) < 2:
        return {
            "segment": segment_name,
            "spread_absolute": 0.0,
            "spread_percentage": 0.0,
            "arbitrage_anomaly": False,
            "venue_means": venue_means,
        }

    # Compute spread
    prices = list(venue_means.values())
    min_price = min(prices)
    max_price = max(prices)
    spread_absolute = max_price - min_price
    spread_percentage = (spread_absolute / min_price) * 100

    # Flag arbitrage anomaly if spread > 1%
    arbitrage_anomaly = spread_percentage > 1.0

    return {
        "segment": segment_name,
        "spread_absolute": float(spread_absolute),
        "spread_percentage": float(spread_percentage),
        "arbitrage_anomaly": arbitrage_anomaly,
        "venue_means": venue_means,
    }


def validate_schema(segment_df: pd.DataFrame, segment_name: str, venue: str) -> Dict[str, Any]:
    """
    Validate schema to confirm trade prints only, no bid/ask/orderbook fields.
    """
    logger = logging.getLogger(__name__)

    if segment_df.empty:
        return {
            "segment": segment_name,
            "venue": venue,
            "fields_present": [],
            "has_bid_ask": False,
            "has_orderbook": False,
            "data_type": "empty",
        }

    fields = list(segment_df.columns)

    # Check for bid/ask/orderbook fields
    bid_ask_fields = [
        f for f in fields if any(keyword in f.lower() for keyword in ["bid", "ask", "spread"])
    ]
    orderbook_fields = [
        f
        for f in fields
        if any(keyword in f.lower() for keyword in ["orderbook", "order_book", "book"])
    ]

    has_bid_ask = len(bid_ask_fields) > 0
    has_orderbook = len(orderbook_fields) > 0

    # Determine data type
    if has_orderbook:
        data_type = "orderbook"
    elif has_bid_ask:
        data_type = "bid_ask"
    else:
        data_type = "trade_prints_only"

    return {
        "segment": segment_name,
        "venue": venue,
        "fields_present": fields,
        "has_bid_ask": has_bid_ask,
        "has_orderbook": has_orderbook,
        "data_type": data_type,
        "bid_ask_fields": bid_ask_fields,
        "orderbook_fields": orderbook_fields,
    }


def generate_markdown_report(
    venue_stats: Dict[str, Dict[str, Any]],
    duplicate_stats: Dict[str, Dict[str, Any]],
    cross_venue_spreads: Dict[str, Any],
    schema_validation: Dict[str, Dict[str, Any]],
) -> str:
    """
    Generate comprehensive Markdown report.
    """
    report = []

    # Header
    report.append("# 4-Hour Rolling Segment Analysis Report")
    report.append(f"**Generated**: {datetime.now(timezone.utc).isoformat()}")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    report.append(
        "This report provides 4-hour rolling segment analysis for captured cryptocurrency exchange data."
    )
    report.append(
        "Each venue's data is partitioned into 4-hour blocks (00:00-04:00, 04:00-08:00, etc.) for detailed analysis."
    )
    report.append("")

    # Per-venue analysis
    for venue in ["coinbase", "kraken", "binance"]:
        if venue not in venue_stats:
            continue

        report.append(f"## {venue.upper()} Analysis")
        report.append("")

        # Create table header
        report.append(
            "| Segment | Trades | Mean Price | Std Dev | Min | Max | Drift | Volume | Duplicates | Outliers |"
        )
        report.append(
            "|---------|--------|------------|---------|-----|-----|-------|--------|------------|----------|"
        )

        # Add data rows
        for segment_name in sorted(venue_stats[venue].keys()):
            stats = venue_stats[venue][segment_name]
            dup_stats = duplicate_stats[venue][segment_name]

            report.append(
                f"| {segment_name} | {stats['trades']} | ${stats['mean_price']:,.2f} | ${stats['std_price']:,.2f} | ${stats['min_price']:,.2f} | ${stats['max_price']:,.2f} | ${stats['price_drift']:+,.2f} | {stats['total_volume']:.2f} | {dup_stats['duplicate_ratio']:.1%} | {dup_stats['outlier_ratio']:.1%} |"
            )

        report.append("")

    # Cross-venue comparison
    report.append("## Cross-Venue Spread Analysis")
    report.append("")
    report.append("| Segment | Spread ($) | Spread (%) | Arbitrage Anomaly |")
    report.append("|---------|------------|------------|-------------------|")

    for segment_name in sorted(cross_venue_spreads.keys()):
        spread = cross_venue_spreads[segment_name]
        anomaly_flag = "⚠️ YES" if spread["arbitrage_anomaly"] else "✅ NO"
        report.append(
            f"| {segment_name} | ${spread['spread_absolute']:,.2f} | {spread['spread_percentage']:.2f}% | {anomaly_flag} |"
        )

    report.append("")

    # Schema validation
    report.append("## Schema Validation")
    report.append("")
    report.append("| Venue | Data Type | Bid/Ask Fields | Orderbook Fields |")
    report.append("|-------|-----------|----------------|------------------|")

    for venue in ["coinbase", "kraken", "binance"]:
        if venue not in schema_validation:
            continue

        # Get first segment for schema validation
        first_segment = next(iter(schema_validation[venue].values()))
        bid_ask_count = len(first_segment["bid_ask_fields"])
        orderbook_count = len(first_segment["orderbook_fields"])

        report.append(
            f"| {venue.upper()} | {first_segment['data_type']} | {bid_ask_count} | {orderbook_count} |"
        )

    report.append("")

    # Quality flags
    report.append("## Quality Flags")
    report.append("")

    # Check for high duplicate ratios
    high_duplicate_venues = []
    for venue in ["coinbase", "kraken", "binance"]:
        if venue not in duplicate_stats:
            continue

        max_duplicate_ratio = max(
            dup_stats["duplicate_ratio"] for dup_stats in duplicate_stats[venue].values()
        )

        if max_duplicate_ratio > 0.5:  # > 50% duplicates
            high_duplicate_venues.append(f"{venue} ({max_duplicate_ratio:.1%})")

    if high_duplicate_venues:
        report.append("⚠️ **HIGH DUPLICATE RATIOS DETECTED**:")
        for venue_info in high_duplicate_venues:
            report.append(f"- {venue_info}")
        report.append("")
    else:
        report.append("✅ **All venues have acceptable duplicate ratios (< 50%)**")
        report.append("")

    return "\n".join(report)


def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(description="4-hour rolling segment analysis")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--date", default="20251002", help="Date to analyze (YYYYMMDD)")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 4-HOUR ROLLING SEGMENT ANALYSIS")
    print("=" * 80)

    venues = ["coinbase", "kraken", "binance"]
    slices = ["slice_00", "slice_01"]

    # Step 1: Load and partition data
    logger.info("Step 1: Loading and partitioning data into 4-hour segments...")

    all_venue_data = {}
    for venue in venues:
        venue_data = []

        # Load all slices for this venue
        for slice_name in slices:
            df = load_venue_data(s3_client, args.bucket, venue, slice_name, args.date)
            if not df.empty:
                venue_data.append(df)

        if venue_data:
            # Combine all slices for this venue
            combined_df = pd.concat(venue_data, ignore_index=True)
            combined_df = combined_df.sort_values("dt")

            # Partition into 4-hour segments
            segments = partition_into_4h_segments(combined_df, venue)
            all_venue_data[venue] = segments

    # Step 2: Compute segment statistics
    logger.info("Step 2: Computing segment statistics...")

    venue_stats = {}
    duplicate_stats = {}
    schema_validation = {}

    for venue, segments in all_venue_data.items():
        venue_stats[venue] = {}
        duplicate_stats[venue] = {}
        schema_validation[venue] = {}

        for segment_name, segment_df in segments.items():
            # Compute statistics
            stats = compute_segment_stats(segment_df, segment_name, venue)
            venue_stats[venue][segment_name] = stats

            # Check duplicates and anomalies
            dup_stats = check_duplicates_and_anomalies(segment_df, segment_name, venue)
            duplicate_stats[venue][segment_name] = dup_stats

            # Validate schema
            schema_stats = validate_schema(segment_df, segment_name, venue)
            schema_validation[venue][segment_name] = schema_stats

            # Check for high duplicate ratios (guardrail)
            if dup_stats["duplicate_ratio"] > 0.5:
                logger.error(
                    f"⚠️ HIGH DUPLICATE RATIO: {venue} {segment_name} has {dup_stats['duplicate_ratio']:.1%} duplicates"
                )
                print(f"⚠️ STOPPING: {venue} {segment_name} has >50% duplicates")
                sys.exit(1)

    # Step 3: Cross-venue spread analysis
    logger.info("Step 3: Computing cross-venue spread analysis...")

    cross_venue_spreads = {}
    all_segments = set()

    # Collect all segment names
    for venue_segments in all_venue_data.values():
        all_segments.update(venue_segments.keys())

    # Compute spreads for each segment
    for segment_name in sorted(all_segments):
        spread_stats = compute_cross_venue_spread(venue_stats, segment_name)
        cross_venue_spreads[segment_name] = spread_stats

    # Step 4: Generate reports
    logger.info("Step 4: Generating reports...")

    # Generate Markdown report
    markdown_report = generate_markdown_report(
        venue_stats, duplicate_stats, cross_venue_spreads, schema_validation
    )

    # Print summary
    print(f"\n📊 SEGMENT ANALYSIS SUMMARY")
    print("-" * 60)

    for venue in venues:
        if venue not in all_venue_data:
            continue

        print(f"\n🏢 {venue.upper()}")
        for segment_name, segment_df in all_venue_data[venue].items():
            stats = venue_stats[venue][segment_name]
            dup_stats = duplicate_stats[venue][segment_name]
            print(
                f"  {segment_name}: {stats['trades']} trades, ${stats['mean_price']:,.2f} mean, {dup_stats['duplicate_ratio']:.1%} duplicates"
            )

    # Cross-venue spreads
    print(f"\n📈 CROSS-VENUE SPREADS")
    print("-" * 60)

    for segment_name in sorted(cross_venue_spreads.keys()):
        spread = cross_venue_spreads[segment_name]
        anomaly_flag = "⚠️" if spread["arbitrage_anomaly"] else "✅"
        print(
            f"  {segment_name}: ${spread['spread_absolute']:,.2f} ({spread['spread_percentage']:.2f}%) {anomaly_flag}"
        )

    # Step 5: Store reports to S3
    logger.info("Step 5: Storing reports to S3...")

    # Create S3 prefix
    s3_prefix = f"analysis/{args.date}/segments_4h_quality_report"

    # Store JSON report
    json_report = {
        "analysis_date": args.date,
        "venue_stats": venue_stats,
        "duplicate_stats": duplicate_stats,
        "cross_venue_spreads": cross_venue_spreads,
        "schema_validation": schema_validation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    json_key = f"{s3_prefix}/segments_4h_analysis.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=json_key,
        Body=json.dumps(json_report, indent=2, default=str),
        ContentType="application/json",
    )

    # Store Markdown report
    markdown_key = f"{s3_prefix}/segments_4h_quality_report.md"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=markdown_key,
        Body=markdown_report.encode("utf-8"),
        ContentType="text/markdown",
    )

    logger.info(f"📁 Reports stored to S3:")
    logger.info(f"  JSON: s3://{args.bucket}/{json_key}")
    logger.info(f"  Markdown: s3://{args.bucket}/{markdown_key}")

    print(f"\n📁 Reports stored to S3:")
    print(f"  JSON: s3://{args.bucket}/{json_key}")
    print(f"  Markdown: s3://{args.bucket}/{markdown_key}")

    # Save local copy
    local_json_file = f"segments_4h_analysis_{args.date}.json"
    local_md_file = f"segments_4h_quality_report_{args.date}.md"

    with open(local_json_file, "w") as f:
        json.dump(json_report, f, indent=2, default=str)

    with open(local_md_file, "w") as f:
        f.write(markdown_report)

    logger.info(f"📁 Local copies saved:")
    logger.info(f"  JSON: {local_json_file}")
    logger.info(f"  Markdown: {local_md_file}")


if __name__ == "__main__":
    main()
