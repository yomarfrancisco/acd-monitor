#!/usr/bin/env python3
"""
Raw Data Analysis Script

Detailed analysis of raw parquet data to verify timestamps, compute statistics,
check for duplicates, and compare variance across venues.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
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
            logging.FileHandler("raw_data_analysis.log"),
        ],
    )


def load_raw_data(s3_client, bucket: str, venue: str, slice_name: str, date: str) -> pd.DataFrame:
    """
    Load raw parquet data for detailed analysis.
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


def analyze_timestamps(df: pd.DataFrame, venue: str, slice_name: str) -> Dict[str, Any]:
    """
    Analyze timestamp patterns and verify proper incrementing.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {"error": "Empty dataframe"}

    # Sort by timestamp
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)

    # Calculate time differences
    time_diffs = df_sorted["dt"].diff().dropna()
    time_diffs_ms = time_diffs.dt.total_seconds() * 1000

    # Check for duplicate timestamps
    duplicate_timestamps = df_sorted["timestamp"].duplicated().sum()

    # Check for backwards time jumps
    negative_diffs = (time_diffs_ms < 0).sum()

    # Check for very large gaps (potential data issues)
    large_gaps = (time_diffs_ms > 10000).sum()  # > 10 seconds

    return {
        "venue": venue,
        "slice": slice_name,
        "total_rows": len(df),
        "unique_timestamps": df["timestamp"].nunique(),
        "duplicate_timestamps": int(duplicate_timestamps),
        "negative_time_diffs": int(negative_diffs),
        "large_gaps": int(large_gaps),
        "time_span_seconds": (df_sorted["dt"].max() - df_sorted["dt"].min()).total_seconds(),
        "mean_interval_ms": float(time_diffs_ms.mean()),
        "std_interval_ms": float(time_diffs_ms.std()),
        "min_interval_ms": float(time_diffs_ms.min()),
        "max_interval_ms": float(time_diffs_ms.max()),
        "first_timestamp": df_sorted["timestamp"].iloc[0],
        "last_timestamp": df_sorted["timestamp"].iloc[-1],
        "first_dt": str(df_sorted["dt"].iloc[0]),
        "last_dt": str(df_sorted["dt"].iloc[-1]),
    }


def compute_raw_price_stats(df: pd.DataFrame, venue: str, slice_name: str) -> Dict[str, Any]:
    """
    Compute detailed price statistics from raw data.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {"error": "Empty dataframe"}

    prices = df["price"].values

    # Basic statistics
    stats = {
        "venue": venue,
        "slice": slice_name,
        "count": len(prices),
        "mean": float(np.mean(prices)),
        "std": float(np.std(prices)),
        "min": float(np.min(prices)),
        "max": float(np.max(prices)),
        "range": float(np.max(prices) - np.min(prices)),
        "first_price": float(prices[0]),
        "last_price": float(prices[-1]),
        "price_change": float(prices[-1] - prices[0]),
    }

    # Price increments
    price_diffs = np.diff(prices)
    stats.update(
        {
            "mean_price_change": float(np.mean(price_diffs)),
            "std_price_change": float(np.std(price_diffs)),
            "min_price_change": float(np.min(price_diffs)),
            "max_price_change": float(np.max(price_diffs)),
            "zero_price_changes": int(np.sum(price_diffs == 0)),
            "positive_changes": int(np.sum(price_diffs > 0)),
            "negative_changes": int(np.sum(price_diffs < 0)),
        }
    )

    # Outlier detection (3σ rule)
    price_mean = np.mean(prices)
    price_std = np.std(prices)
    outliers = np.abs(prices - price_mean) > (3 * price_std)
    stats.update(
        {
            "outliers_count": int(np.sum(outliers)),
            "outliers_percentage": float(np.sum(outliers) / len(prices) * 100),
            "outlier_prices": prices[outliers].tolist(),
        }
    )

    return stats


def check_duplicates(df: pd.DataFrame, venue: str, slice_name: str) -> Dict[str, Any]:
    """
    Check for duplicate trades and redundant updates.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {"error": "Empty dataframe"}

    # Check for exact duplicates (all fields same)
    exact_duplicates = df.duplicated().sum()

    # Check for timestamp duplicates
    timestamp_duplicates = df["timestamp"].duplicated().sum()

    # Check for price duplicates
    price_duplicates = df["price"].duplicated().sum()

    # Check for volume duplicates
    volume_duplicates = df["volume"].duplicated().sum()

    # Check for consecutive identical prices
    consecutive_identical = (df["price"].diff() == 0).sum()

    # Check for zero volume trades
    zero_volume = (df["volume"] == 0).sum()

    return {
        "venue": venue,
        "slice": slice_name,
        "total_rows": len(df),
        "exact_duplicates": int(exact_duplicates),
        "timestamp_duplicates": int(timestamp_duplicates),
        "price_duplicates": int(price_duplicates),
        "volume_duplicates": int(volume_duplicates),
        "consecutive_identical_prices": int(consecutive_identical),
        "zero_volume_trades": int(zero_volume),
        "unique_trades_estimate": len(df) - exact_duplicates,
        "duplicate_rate": float(exact_duplicates / len(df) * 100),
    }


def dump_raw_rows(df: pd.DataFrame, venue: str, slice_name: str, n_rows: int = 20) -> List[Dict]:
    """
    Dump raw rows for manual inspection.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return []

    # Sort by timestamp for proper sequence
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)

    # Take first n_rows
    sample_df = df_sorted.head(n_rows)

    # Convert to list of dictionaries
    raw_rows = []
    for idx, row in sample_df.iterrows():
        raw_rows.append(
            {
                "row_index": idx,
                "timestamp": (
                    int(row["timestamp"])
                    if isinstance(row["timestamp"], (int, float))
                    else int(row["timestamp"].timestamp() * 1000)
                ),
                "dt": str(row["dt"]),
                "price": float(row["price"]),
                "volume": float(row["volume"]),
                "venue": row["venue"],
            }
        )

    return raw_rows


def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(description="Raw data analysis")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--date", default="20251002", help="Date to analyze (YYYYMMDD)")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--n-rows", default=20, type=int, help="Number of raw rows to dump")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 RAW DATA ANALYSIS")
    print("=" * 80)

    venues = ["coinbase", "kraken", "binance"]
    slices = ["slice_00", "slice_01"]

    all_results = {}

    for venue in venues:
        venue_results = {}

        for slice_name in slices:
            logger.info(f"Analyzing {venue} {slice_name}...")

            # Load raw data
            df = load_raw_data(s3_client, args.bucket, venue, slice_name, args.date)

            if df.empty:
                logger.warning(f"No data for {venue} {slice_name}")
                continue

            # Analyze timestamps
            timestamp_analysis = analyze_timestamps(df, venue, slice_name)

            # Compute raw price statistics
            price_stats = compute_raw_price_stats(df, venue, slice_name)

            # Check for duplicates
            duplicate_analysis = check_duplicates(df, venue, slice_name)

            # Dump raw rows
            raw_rows = dump_raw_rows(df, venue, slice_name, args.n_rows)

            venue_results[slice_name] = {
                "timestamp_analysis": timestamp_analysis,
                "price_stats": price_stats,
                "duplicate_analysis": duplicate_analysis,
                "raw_rows": raw_rows,
            }

        all_results[venue] = venue_results

    # Print comprehensive results
    print(f"\n📊 TIMESTAMP ANALYSIS")
    print("-" * 60)

    for venue, venue_data in all_results.items():
        print(f"\n🏢 {venue.upper()}")
        for slice_name, slice_data in venue_data.items():
            ta = slice_data["timestamp_analysis"]
            print(f"  {slice_name}:")
            print(f"    Rows: {ta['total_rows']}, Unique timestamps: {ta['unique_timestamps']}")
            print(
                f"    Duplicates: {ta['duplicate_timestamps']}, Negative diffs: {ta['negative_time_diffs']}"
            )
            print(
                f"    Time span: {ta['time_span_seconds']:.2f}s, Mean interval: {ta['mean_interval_ms']:.1f}ms"
            )
            print(f"    First: {ta['first_dt']}")
            print(f"    Last: {ta['last_dt']}")

    print(f"\n📈 PRICE STATISTICS (RAW DATA)")
    print("-" * 60)

    for venue, venue_data in all_results.items():
        print(f"\n🏢 {venue.upper()}")
        for slice_name, slice_data in venue_data.items():
            ps = slice_data["price_stats"]
            print(f"  {slice_name}:")
            print(f"    Count: {ps['count']}, Mean: ${ps['mean']:,.2f}, Std: ${ps['std']:,.2f}")
            print(f"    Range: ${ps['min']:,.2f} - ${ps['max']:,.2f} (${ps['range']:,.2f})")
            print(
                f"    Change: ${ps['first_price']:,.2f} → ${ps['last_price']:,.2f} (${ps['price_change']:+,.2f})"
            )
            print(f"    Outliers: {ps['outliers_count']} ({ps['outliers_percentage']:.1f}%)")

    print(f"\n🔍 DUPLICATE ANALYSIS")
    print("-" * 60)

    for venue, venue_data in all_results.items():
        print(f"\n🏢 {venue.upper()}")
        for slice_name, slice_data in venue_data.items():
            da = slice_data["duplicate_analysis"]
            print(f"  {slice_name}:")
            print(f"    Total rows: {da['total_rows']}, Exact duplicates: {da['exact_duplicates']}")
            print(
                f"    Timestamp dupes: {da['timestamp_duplicates']}, Price dupes: {da['price_duplicates']}"
            )
            print(f"    Consecutive identical: {da['consecutive_identical_prices']}")
            print(f"    Zero volume: {da['zero_volume_trades']}")
            print(f"    Unique trades estimate: {da['unique_trades_estimate']}")

    print(f"\n📋 RAW ROWS DUMP (First {args.n_rows} rows)")
    print("-" * 60)

    for venue, venue_data in all_results.items():
        print(f"\n🏢 {venue.upper()}")
        for slice_name, slice_data in venue_data.items():
            print(f"\n  {slice_name} - Raw Rows:")
            raw_rows = slice_data["raw_rows"]
            for i, row in enumerate(raw_rows[:10]):  # Show first 10
                print(
                    f"    Row {i+1}: ts={row['timestamp']}, dt={row['dt']}, price=${row['price']:,.2f}, vol={row['volume']:.4f}"
                )

    # Cross-venue variance comparison
    print(f"\n📊 CROSS-VENUE VARIANCE COMPARISON")
    print("-" * 60)

    venue_variances = {}
    for venue, venue_data in all_results.items():
        venue_std = []
        for slice_name, slice_data in venue_data.items():
            ps = slice_data["price_stats"]
            venue_std.append(ps["std"])
        venue_variances[venue] = np.mean(venue_std)

    print("Average standard deviation by venue:")
    for venue, variance in sorted(venue_variances.items(), key=lambda x: x[1]):
        print(f"  {venue.upper()}: ${variance:,.2f}")

    # Save detailed results
    output_file = f"raw_data_analysis_{args.date}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    logger.info(f"📁 Detailed results saved to: {output_file}")
    print(f"\n📁 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
