#!/usr/bin/env python3
"""
Daily Summary Analysis Script

Generates comprehensive daily summary statistics across all available slices
for Coinbase, Kraken, and Binance.
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
            logging.FileHandler("daily_summary_analysis.log"),
        ],
    )


def load_venue_data(
    s3_client, bucket: str, venue: str, slice_name: str, date: str
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Load data for a specific venue slice.

    Returns:
        Tuple of (DataFrame, manifest_dict)
    """
    logger = logging.getLogger(__name__)

    try:
        # Read manifest
        manifest_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/probe_manifest.json"
        response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
        manifest = json.loads(response["Body"].read())

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

        return df, manifest

    except Exception as e:
        logger.error(f"Error loading {venue} {slice_name}: {e}")
        return pd.DataFrame(), {}


def compute_daily_summary(s3_client, bucket: str, date: str) -> Dict[str, Any]:
    """
    Compute comprehensive daily summary statistics.
    """
    logger = logging.getLogger(__name__)

    venues = ["coinbase", "kraken", "binance"]
    all_data = {}
    daily_stats = {}

    # Load all data
    for venue in venues:
        venue_data = []
        venue_manifests = []

        # Load all slices for this venue
        slice_num = 0
        while True:
            slice_name = f"slice_{slice_num:02d}"
            try:
                df, manifest = load_venue_data(s3_client, bucket, venue, slice_name, date)
                if df.empty:
                    break
                venue_data.append(df)
                venue_manifests.append(manifest)
                slice_num += 1
            except:
                break

        if venue_data:
            # Combine all slices for this venue
            combined_df = pd.concat(venue_data, ignore_index=True)
            combined_df = combined_df.sort_values("dt")

            all_data[venue] = {
                "data": combined_df,
                "manifests": venue_manifests,
                "slices": slice_num,
            }

    # Compute daily statistics for each venue
    for venue, venue_info in all_data.items():
        df = venue_info["data"]
        manifests = venue_info["manifests"]

        # Basic statistics
        prices = df["price"].values
        volumes = df["volume"].values if "volume" in df.columns else np.zeros(len(df))

        # Outlier detection (3σ rule)
        price_mean = np.mean(prices)
        price_std = np.std(prices)
        outliers = np.abs(prices - price_mean) > (3 * price_std)
        n_outliers = np.sum(outliers)

        # Time analysis
        time_span = (df["dt"].max() - df["dt"].min()).total_seconds() / 3600  # hours

        daily_stats[venue] = {
            "venue": venue,
            "total_slices": venue_info["slices"],
            "total_rows": len(df),
            "time_span_hours": time_span,
            "start_time": df["dt"].min().isoformat(),
            "end_time": df["dt"].max().isoformat(),
            "price_stats": {
                "min": float(np.min(prices)),
                "max": float(np.max(prices)),
                "mean": float(price_mean),
                "std": float(price_std),
                "range": float(np.max(prices) - np.min(prices)),
                "first_price": float(prices[0]),
                "last_price": float(prices[-1]),
                "price_change": float(prices[-1] - prices[0]),
            },
            "volume_stats": {
                "total_volume": float(np.sum(volumes)),
                "mean_volume": float(np.mean(volumes)),
                "max_volume": float(np.max(volumes)),
                "min_volume": float(np.min(volumes)),
            },
            "outlier_stats": {
                "count": int(n_outliers),
                "percentage": float(n_outliers / len(prices) * 100),
                "outlier_indices": np.where(outliers)[0].tolist(),
            },
            "schema_fields": list(df.columns),
            "sample_rows": df.head(10).to_dict("records"),
        }

    return daily_stats, all_data


def check_bid_ask_data(s3_client, bucket: str, date: str) -> Dict[str, Any]:
    """
    Check if bid/ask/orderbook data is captured anywhere.
    """
    logger = logging.getLogger(__name__)

    # Check for any orderbook-related files
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket, Prefix=f"raw_probes/{date}/", MaxKeys=1000
        )

        files = [obj["Key"] for obj in response.get("Contents", [])]

        # Look for orderbook-related keywords
        orderbook_files = []
        bid_ask_files = []

        for file in files:
            if any(keyword in file.lower() for keyword in ["orderbook", "order_book", "book"]):
                orderbook_files.append(file)
            if any(keyword in file.lower() for keyword in ["bid", "ask", "spread"]):
                bid_ask_files.append(file)

        # Check manifest files for orderbook fields
        orderbook_fields = []
        for file in files:
            if file.endswith("probe_manifest.json"):
                try:
                    response = s3_client.get_object(Bucket=bucket, Key=file)
                    manifest = json.loads(response["Body"].read())
                    fields = manifest.get("fields_present", [])
                    if any(
                        field in fields
                        for field in ["bid", "ask", "bid_price", "ask_price", "spread"]
                    ):
                        orderbook_fields.append({"file": file, "fields": fields})
                except:
                    continue

        return {
            "orderbook_files": orderbook_files,
            "bid_ask_files": bid_ask_files,
            "orderbook_fields": orderbook_fields,
            "has_orderbook_data": len(orderbook_files) > 0 or len(orderbook_fields) > 0,
            "data_type": (
                "trade_prints_only" if not orderbook_files and not orderbook_fields else "mixed"
            ),
        }

    except Exception as e:
        logger.error(f"Error checking bid/ask data: {e}")
        return {"error": str(e)}


def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(description="Daily summary analysis")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--date", default="20251002", help="Date to analyze (YYYYMMDD)")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("📊 DAILY SUMMARY ANALYSIS")
    print("=" * 80)

    # Compute daily summary
    logger.info("Computing daily summary statistics...")
    daily_stats, all_data = compute_daily_summary(s3_client, args.bucket, args.date)

    # Print daily summary
    print(f"\n📈 DAILY SUMMARY STATISTICS ({args.date})")
    print("-" * 60)

    for venue, stats in daily_stats.items():
        print(f"\n🏢 {venue.upper()}")
        print(f"   Slices: {stats['total_slices']}")
        print(f"   Total Rows: {stats['total_rows']:,}")
        print(f"   Time Span: {stats['time_span_hours']:.1f} hours")
        print(f"   Period: {stats['start_time']} to {stats['end_time']}")

        ps = stats["price_stats"]
        print(
            f"   Price: ${ps['first_price']:,.2f} → ${ps['last_price']:,.2f} (${ps['price_change']:+,.2f})"
        )
        print(f"   Range: ${ps['min']:,.2f} - ${ps['max']:,.2f} (${ps['range']:,.2f})")
        print(f"   Stats: μ=${ps['mean']:,.2f}, σ=${ps['std']:,.2f}")

        vs = stats["volume_stats"]
        print(f"   Volume: {vs['total_volume']:,.2f} total, {vs['mean_volume']:,.4f} avg")

        os = stats["outlier_stats"]
        if os["count"] > 0:
            print(f"   ⚠️  Outliers: {os['count']} ({os['percentage']:.1f}%)")
        else:
            print(f"   ✅ No outliers")

    # Show raw rows for schema verification
    print(f"\n🔍 RAW DATA SAMPLES (10 rows from latest slice)")
    print("-" * 60)

    for venue, stats in daily_stats.items():
        print(f"\n{venue.upper()} - Sample Data:")
        sample_rows = stats["sample_rows"]
        for i, row in enumerate(sample_rows[:10]):
            # Format the row for display
            formatted_row = {}
            for key, value in row.items():
                if key == "timestamp":
                    formatted_row[key] = value
                elif key == "dt":
                    formatted_row[key] = str(value)
                elif isinstance(value, float):
                    formatted_row[key] = f"{value:.4f}"
                else:
                    formatted_row[key] = value
            print(f"  Row {i+1}: {formatted_row}")

    # Check for bid/ask data
    print(f"\n🔍 BID/ASK/ORDERBOOK DATA CHECK")
    print("-" * 60)

    bid_ask_info = check_bid_ask_data(s3_client, args.bucket, args.date)

    if "error" in bid_ask_info:
        print(f"❌ Error checking bid/ask data: {bid_ask_info['error']}")
    else:
        print(f"Orderbook files found: {len(bid_ask_info['orderbook_files'])}")
        print(f"Bid/ask files found: {len(bid_ask_info['bid_ask_files'])}")
        print(f"Manifests with orderbook fields: {len(bid_ask_info['orderbook_fields'])}")
        print(f"Has orderbook data: {bid_ask_info['has_orderbook_data']}")
        print(f"Data type: {bid_ask_info['data_type']}")

        if bid_ask_info["orderbook_fields"]:
            print("\nOrderbook fields found in manifests:")
            for item in bid_ask_info["orderbook_fields"]:
                print(f"  {item['file']}: {item['fields']}")

    # Save detailed results
    output_file = f"daily_summary_{args.date}.json"
    with open(output_file, "w") as f:
        json.dump(
            {"daily_stats": daily_stats, "bid_ask_info": bid_ask_info, "analysis_date": args.date},
            f,
            indent=2,
            default=str,
        )

    logger.info(f"📁 Detailed results saved to: {output_file}")
    print(f"\n📁 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
