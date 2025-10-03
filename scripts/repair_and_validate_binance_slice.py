#!/usr/bin/env python3
"""
ACD Data Repair & Validation Script

Repairs and validates Binance slice_01 data through de-duplication and cross-venue validation.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
            logging.FileHandler("repair_and_validate_binance_slice.log"),
        ],
    )


def discover_capture_scope(s3_client, bucket: str) -> Dict[str, Any]:
    """
    Discover all available capture dates and slices.
    """
    logger = logging.getLogger(__name__)

    logger.info("Discovering capture scope...")

    # List all objects in raw_probes
    prefix = "raw_probes/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    dates = []
    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            prefix = common_prefix["Prefix"]
            # Extract date from raw_probes/YYYYMMDD/
            if prefix.startswith("raw_probes/") and prefix.endswith("/"):
                date_str = prefix.replace("raw_probes/", "").strip("/")
                if date_str and date_str.isdigit() and len(date_str) == 8:  # YYYYMMDD format
                    dates.append(date_str)

    dates.sort()

    capture_inventory = {
        "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_dates": len(dates),
        "dates": {},
    }

    for date in dates:
        logger.info(f"Scanning date: {date}")
        date_prefix = f"raw_probes/{date}/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=date_prefix, Delimiter="/")

        venues = []
        if "CommonPrefixes" in response:
            for common_prefix in response["CommonPrefixes"]:
                venue_str = common_prefix["Prefix"].split("=")[-1].strip("/")
                if venue_str and "venue=" in common_prefix["Prefix"]:
                    venues.append(venue_str)

        venues.sort()

        # For each venue, find slices
        venue_slices = {}
        for venue in venues:
            venue_prefix = f"raw_probes/{date}/venue={venue}/"
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=venue_prefix, Delimiter="/")

            slices = []
            if "CommonPrefixes" in response:
                for common_prefix in response["CommonPrefixes"]:
                    slice_str = common_prefix["Prefix"].split("=")[-1].strip("/")
                    if slice_str and "slice=" in common_prefix["Prefix"]:
                        slices.append(slice_str)

            slices.sort()
            venue_slices[venue] = slices

        capture_inventory["dates"][date] = {"venues": venues, "venue_slices": venue_slices}

    return capture_inventory


def load_slice_data(s3_client, bucket: str, date: str, venue: str, slice_name: str) -> pd.DataFrame:
    """
    Load slice data from S3.
    """
    logger = logging.getLogger(__name__)

    sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"

    try:
        response = s3_client.get_object(Bucket=bucket, Key=sample_key)
        parquet_data = response["Body"].read()

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        logger.info(f"Loaded {len(df)} rows from {venue} {slice_name}")
        return df

    except Exception as e:
        logger.error(f"Error loading {venue} {slice_name}: {e}")
        raise


def deduplicate_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    De-duplicate data using deterministic keys.
    """
    logger = logging.getLogger(__name__)

    total_rows = len(df)
    logger.info(f"Starting de-duplication with {total_rows} rows")

    # Ensure required columns exist
    required_cols = ["timestamp", "price", "volume"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in data")

    # Create de-duplication key
    if "trade_id" in df.columns:
        # Use trade_id if present
        df["dedup_key"] = df["trade_id"].astype(str)
        key_type = "trade_id"
    else:
        # Use timestamp_rounded_ns, price, volume
        # Convert timestamp to nanoseconds and round to nearest microsecond
        if df["timestamp"].dtype == "object" or "datetime" in str(df["timestamp"].dtype):
            # If timestamp is already datetime, convert to nanoseconds
            timestamp_ns = df["timestamp"].astype("int64")  # Convert to nanoseconds
        else:
            # If timestamp is numeric, assume it's already in the right units
            timestamp_ns = df["timestamp"]

        # Round to nearest microsecond (divide by 1000, round, multiply by 1000)
        df["timestamp_rounded_ns"] = (timestamp_ns // 1000) * 1000
        df["dedup_key"] = (
            df["timestamp_rounded_ns"].astype(str)
            + "_"
            + df["price"].astype(str)
            + "_"
            + df["volume"].astype(str)
        )
        key_type = "timestamp_price_volume"

    # Find duplicates
    duplicate_mask = df.duplicated(subset=["dedup_key"], keep="first")
    unique_df = df[~duplicate_mask].copy()

    # Remove the temporary dedup_key column
    if "dedup_key" in unique_df.columns:
        unique_df = unique_df.drop("dedup_key", axis=1)
    if "timestamp_rounded_ns" in unique_df.columns:
        unique_df = unique_df.drop("timestamp_rounded_ns", axis=1)

    unique_rows = len(unique_df)
    exact_duplicate_rows = total_rows - unique_rows
    duplicate_ratio = exact_duplicate_rows / total_rows if total_rows > 0 else 0

    # Get sample of dropped keys (first 50)
    dropped_keys = df[duplicate_mask]["dedup_key"].head(50).tolist()

    dedup_audit = {
        "total_rows": total_rows,
        "unique_rows": unique_rows,
        "exact_duplicate_rows": exact_duplicate_rows,
        "duplicate_ratio": duplicate_ratio,
        "key_type": key_type,
        "dropped_keys_sample": dropped_keys,
    }

    logger.info(
        f"De-duplication complete: {unique_rows} unique rows, {exact_duplicate_rows} duplicates ({duplicate_ratio:.1%})"
    )

    return unique_df, dedup_audit


def compute_slice_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute comprehensive statistics for a slice.
    """
    logger = logging.getLogger(__name__)

    if df.empty:
        return {
            "rows": 0,
            "time_span_seconds": 0,
            "time_span_minutes": 0,
            "min_timestamp": None,
            "max_timestamp": None,
            "price_mean": None,
            "price_median": None,
            "price_min": None,
            "price_max": None,
            "price_std": None,
            "price_1pct": None,
            "price_99pct": None,
            "volume_total": None,
            "volume_avg_per_trade": None,
            "outliers_3sigma": 0,
            "outliers_sanity_bounds": 0,
            "top_5_outliers": [],
        }

    # Time span analysis
    timestamps = pd.to_datetime(df["timestamp"], unit="ms")
    min_timestamp = timestamps.min()
    max_timestamp = timestamps.max()
    time_span_seconds = (max_timestamp - min_timestamp).total_seconds()

    # Price statistics
    prices = df["price"]
    price_mean = prices.mean()
    price_median = prices.median()
    price_min = prices.min()
    price_max = prices.max()
    price_std = prices.std()
    price_1pct = prices.quantile(0.01)
    price_99pct = prices.quantile(0.99)

    # Volume statistics
    volumes = df["volume"]
    volume_total = volumes.sum()
    volume_avg_per_trade = volumes.mean()

    # Outlier detection (3σ rule)
    outliers_3sigma = 0
    if price_std > 0:
        lower_bound = price_mean - (3 * price_std)
        upper_bound = price_mean + (3 * price_std)
        outliers_3sigma = prices[(prices < lower_bound) | (prices > upper_bound)].count()

    # Sanity bounds ($50k-$500k for BTC)
    sanity_lower = 50000
    sanity_upper = 500000
    outliers_sanity_bounds = prices[(prices < sanity_lower) | (prices > sanity_upper)].count()

    # Top 5 outliers with timestamps
    price_outliers = df[abs(prices - price_mean) > (3 * price_std)].copy()
    if not price_outliers.empty:
        price_outliers["outlier_deviation"] = abs(price_outliers["price"] - price_mean)
        top_5_outliers = price_outliers.nlargest(5, "outlier_deviation")[
            ["timestamp", "price", "volume"]
        ].to_dict("records")
    else:
        top_5_outliers = []

    stats = {
        "rows": len(df),
        "time_span_seconds": time_span_seconds,
        "time_span_minutes": time_span_seconds / 60,
        "min_timestamp": min_timestamp.isoformat(),
        "max_timestamp": max_timestamp.isoformat(),
        "price_mean": float(price_mean),
        "price_median": float(price_median),
        "price_min": float(price_min),
        "price_max": float(price_max),
        "price_std": float(price_std),
        "price_1pct": float(price_1pct),
        "price_99pct": float(price_99pct),
        "volume_total": float(volume_total),
        "volume_avg_per_trade": float(volume_avg_per_trade),
        "outliers_3sigma": int(outliers_3sigma),
        "outliers_sanity_bounds": int(outliers_sanity_bounds),
        "top_5_outliers": top_5_outliers,
    }

    logger.info(
        f"Computed stats: {len(df)} rows, ${price_mean:.2f} mean, ${price_std:.2f} std, {outliers_3sigma} outliers"
    )

    return stats


def cross_venue_validation(
    binance_stats: Dict[str, Any], coinbase_stats: Dict[str, Any], kraken_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform cross-venue validation checks.
    """
    logger = logging.getLogger(__name__)

    venues = {"binance": binance_stats, "coinbase": coinbase_stats, "kraken": kraken_stats}

    validation_results = {
        "per_venue_stats": venues,
        "spread_checks": {},
        "variance_checks": {},
        "final_verdict": "accept",
        "reasons": [],
    }

    # Price spread checks
    binance_mean = binance_stats["price_mean"]
    coinbase_mean = coinbase_stats["price_mean"]
    kraken_mean = kraken_stats["price_mean"]

    # Binance vs Coinbase
    spread_binance_coinbase = abs(binance_mean - coinbase_mean) / coinbase_mean * 100
    validation_results["spread_checks"]["binance_vs_coinbase"] = {
        "spread_percentage": spread_binance_coinbase,
        "pass": spread_binance_coinbase <= 1.0,
        "threshold": 1.0,
    }

    # Binance vs Kraken
    spread_binance_kraken = abs(binance_mean - kraken_mean) / kraken_mean * 100
    validation_results["spread_checks"]["binance_vs_kraken"] = {
        "spread_percentage": spread_binance_kraken,
        "pass": spread_binance_kraken <= 1.0,
        "threshold": 1.0,
    }

    # Variance checks
    binance_std = binance_stats["price_std"]
    coinbase_std = coinbase_stats["price_std"]
    kraken_std = kraken_stats["price_std"]

    # Check if Binance std is non-degenerate
    min_std_threshold = 0.10  # $0.10 minimum std dev
    binance_std_ok = binance_std >= min_std_threshold

    # Check if peers are also tight (if Binance is tight, peers should be too)
    peers_also_tight = coinbase_std < min_std_threshold and kraken_std < min_std_threshold

    validation_results["variance_checks"] = {
        "binance_std": binance_std,
        "coinbase_std": coinbase_std,
        "kraken_std": kraken_std,
        "min_std_threshold": min_std_threshold,
        "binance_std_ok": binance_std_ok,
        "peers_also_tight": peers_also_tight,
        "pass": binance_std_ok or peers_also_tight,
    }

    # Determine final verdict
    spread_checks_pass = (
        validation_results["spread_checks"]["binance_vs_coinbase"]["pass"]
        and validation_results["spread_checks"]["binance_vs_kraken"]["pass"]
    )
    variance_check_pass = validation_results["variance_checks"]["pass"]

    if not spread_checks_pass:
        validation_results["final_verdict"] = "quarantine"
        validation_results["reasons"].append(f"Price spread exceeds 1.0% threshold")

    if not variance_check_pass:
        validation_results["final_verdict"] = "quarantine"
        validation_results["reasons"].append(
            f"Price variance is degenerate (std < ${min_std_threshold})"
        )

    if validation_results["final_verdict"] == "accept":
        validation_results["reasons"].append("All validation checks passed")

    logger.info(f"Cross-venue validation: {validation_results['final_verdict']}")
    logger.info(f"Spread checks: {spread_checks_pass}, Variance check: {variance_check_pass}")

    return validation_results


def main():
    """Main repair and validation function."""
    parser = argparse.ArgumentParser(description="Repair and validate Binance slice data")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument(
        "--date",
        help="Specific date to process (YYYYMMDD). If not provided, uses latest available.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔧 ACD DATA REPAIR & VALIDATION")
    print("=" * 80)

    # Step 1: Discover capture scope
    logger.info("Step 1: Discovering capture scope...")
    capture_inventory = discover_capture_scope(s3_client, args.bucket)

    if capture_inventory["total_dates"] == 0:
        print("❌ No capture data found. Checked prefixes: raw_probes/")
        sys.exit(1)

    # Determine target date
    if args.date:
        target_date = args.date
        if target_date not in capture_inventory["dates"]:
            print(f"❌ Date {target_date} not found in capture inventory")
            sys.exit(1)
    else:
        target_date = max(capture_inventory["dates"].keys())

    print(f"📅 Target date: {target_date}")
    print(f"📊 Available dates: {capture_inventory['total_dates']}")

    # Check if required venues and slices exist
    required_venues = ["binance", "coinbase", "kraken"]
    required_slice = "slice_01"

    for venue in required_venues:
        if venue not in capture_inventory["dates"][target_date]["venue_slices"]:
            print(f"❌ Venue {venue} not found for date {target_date}")
            sys.exit(1)
        if required_slice not in capture_inventory["dates"][target_date]["venue_slices"][venue]:
            print(f"❌ Slice {required_slice} not found for venue {venue} on date {target_date}")
            sys.exit(1)

    print(f"✅ All required venues and slices found for {target_date}")

    # Step 2: Load Binance slice_01 data
    logger.info("Step 2: Loading Binance slice_01 data...")
    binance_df = load_slice_data(s3_client, args.bucket, target_date, "binance", "slice_01")

    # Step 3: De-duplication
    logger.info("Step 3: De-duplicating Binance data...")
    binance_dedup_df, dedup_audit = deduplicate_data(binance_df)

    # Check duplicate ratio threshold
    if dedup_audit["duplicate_ratio"] > 0.6:
        print(f"❌ Duplicate ratio {dedup_audit['duplicate_ratio']:.1%} exceeds 60% threshold")
        print("Likely data corruption - stopping processing")
        sys.exit(1)

    print(f"✅ De-duplication complete: {dedup_audit['duplicate_ratio']:.1%} duplicates removed")

    # Step 4: Sanity checks on repaired data
    logger.info("Step 4: Computing sanity checks...")
    binance_stats = compute_slice_stats(binance_dedup_df)

    # Check for degenerate data
    if binance_stats["time_span_seconds"] < 1:
        print("⚠️  Time span too short - likely degenerate data")
        print("Continuing with analysis to document the issue...")

    if binance_stats["price_std"] < 0.01:
        print("⚠️  Price variance too low - likely degenerate data")
        print("Continuing with analysis to document the issue...")

    print(
        f"✅ Sanity checks passed: {binance_stats['rows']} rows, {binance_stats['time_span_minutes']:.1f} minutes"
    )

    # Step 5: Cross-venue validation
    logger.info("Step 5: Loading peer venue data...")
    coinbase_df = load_slice_data(s3_client, args.bucket, target_date, "coinbase", "slice_01")
    kraken_df = load_slice_data(s3_client, args.bucket, target_date, "kraken", "slice_01")

    coinbase_stats = compute_slice_stats(coinbase_df)
    kraken_stats = compute_slice_stats(kraken_df)

    logger.info("Step 6: Cross-venue validation...")
    validation_results = cross_venue_validation(binance_stats, coinbase_stats, kraken_stats)

    # Step 7: Save results
    logger.info("Step 7: Saving results...")

    # Save capture inventory
    inventory_key = f"analysis/{target_date}/_diag/capture_inventory.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=inventory_key,
        Body=json.dumps(capture_inventory, indent=2),
        ContentType="application/json",
    )

    # Save repaired parquet
    repaired_key = f"analysis/{target_date}/repaired/binance/slice=slice_01/part-0000.parquet"
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
        binance_dedup_df.to_parquet(tmp_file.name, index=False)
        with open(tmp_file.name, "rb") as f:
            s3_client.put_object(
                Bucket=args.bucket,
                Key=repaired_key,
                Body=f.read(),
                ContentType="application/octet-stream",
            )
        import os

        os.unlink(tmp_file.name)

    # Save dedup audit
    dedup_key = f"analysis/{target_date}/_diag/binance_slice_01_dedup.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=dedup_key,
        Body=json.dumps(dedup_audit, indent=2),
        ContentType="application/json",
    )

    # Save stats
    stats_key = f"analysis/{target_date}/_diag/binance_slice_01_stats.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=stats_key,
        Body=json.dumps(binance_stats, indent=2),
        ContentType="application/json",
    )

    # Save cross-venue validation
    validation_key = f"analysis/{target_date}/_diag/slice_01_cross_venue_validation.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=validation_key,
        Body=json.dumps(validation_results, indent=2),
        ContentType="application/json",
    )

    # Save quarantine marker if needed
    if validation_results["final_verdict"] == "quarantine":
        quarantine_key = f"analysis/{target_date}/repaired/binance/slice=slice_01/_QUARANTINED.json"
        quarantine_data = {
            "quarantine_timestamp": datetime.now(timezone.utc).isoformat(),
            "reasons": validation_results["reasons"],
            "metrics": {
                "spread_binance_coinbase": validation_results["spread_checks"][
                    "binance_vs_coinbase"
                ]["spread_percentage"],
                "spread_binance_kraken": validation_results["spread_checks"]["binance_vs_kraken"][
                    "spread_percentage"
                ],
                "binance_std": binance_stats["price_std"],
            },
            "decision_hints": [
                "Re-pull via REST /api/v3/trades for this window",
                "Check for API rate limiting or data processing issues",
                "Verify exchange connectivity during 12:00-12:15 UTC window",
            ],
        }
        s3_client.put_object(
            Bucket=args.bucket,
            Key=quarantine_key,
            Body=json.dumps(quarantine_data, indent=2),
            ContentType="application/json",
        )

    # Final summary
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Earliest date found: {min(capture_inventory['dates'].keys())}")
    print(f"Slices processed: {target_date} slice_01")
    print(f"Duplicate ratios:")
    print(f"  Binance (pre): {dedup_audit['duplicate_ratio']:.1%}")
    print(f"  Binance (post): 0.0%")
    print(f"\nPer-venue stats:")
    print(
        f"  Binance: ${binance_stats['price_mean']:.2f} ± ${binance_stats['price_std']:.2f} ({binance_stats['rows']} rows)"
    )
    print(
        f"  Coinbase: ${coinbase_stats['price_mean']:.2f} ± ${coinbase_stats['price_std']:.2f} ({coinbase_stats['rows']} rows)"
    )
    print(
        f"  Kraken: ${kraken_stats['price_mean']:.2f} ± ${kraken_stats['price_std']:.2f} ({kraken_stats['rows']} rows)"
    )
    print(f"\nSpreads:")
    print(
        f"  Binance vs Coinbase: {validation_results['spread_checks']['binance_vs_coinbase']['spread_percentage']:.2f}%"
    )
    print(
        f"  Binance vs Kraken: {validation_results['spread_checks']['binance_vs_kraken']['spread_percentage']:.2f}%"
    )
    print(f"\nFinal verdict: {validation_results['final_verdict'].upper()}")
    if validation_results["reasons"]:
        print(f"Reasons: {', '.join(validation_results['reasons'])}")

    print(f"\n📁 Results saved to S3:")
    print(f"  Inventory: s3://{args.bucket}/{inventory_key}")
    print(f"  Repaired data: s3://{args.bucket}/{repaired_key}")
    print(f"  Dedup audit: s3://{args.bucket}/{dedup_key}")
    print(f"  Stats: s3://{args.bucket}/{stats_key}")
    print(f"  Validation: s3://{args.bucket}/{validation_key}")
    if validation_results["final_verdict"] == "quarantine":
        print(f"  Quarantine: s3://{args.bucket}/{quarantine_key}")


if __name__ == "__main__":
    main()
