#!/usr/bin/env python3
"""
Comprehensive Binance Repair & Quarantine Audit

Systematically analyzes all Binance slices for data quality issues,
performs de-duplication, and cross-venue validation.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
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
            logging.FileHandler("comprehensive_binance_audit.log"),
        ],
    )


def discover_capture_scope(s3_client, bucket: str) -> Dict[str, Any]:
    """Discover all available capture dates and slices."""
    logger = logging.getLogger(__name__)

    logger.info("Discovering capture scope...")

    # List all objects in raw_probes
    prefix = "raw_probes/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    dates = []
    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            prefix = common_prefix["Prefix"]
            if prefix.startswith("raw_probes/") and prefix.endswith("/"):
                date_str = prefix.replace("raw_probes/", "").strip("/")
                if date_str and date_str.isdigit() and len(date_str) == 8:
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
    """Load slice data from S3."""
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


def deduplicate_binance_slice(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """De-duplicate Binance data using deterministic keys."""
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
        # Use timestamp_rounded_us, price, volume (microsecond rounding)
        if df["timestamp"].dtype == "object" or "datetime" in str(df["timestamp"].dtype):
            # If timestamp is already datetime, convert to nanoseconds
            timestamp_ns = df["timestamp"].astype("int64")
        else:
            # If timestamp is numeric, assume it's already in the right units
            timestamp_ns = df["timestamp"]

        # Round to nearest microsecond (divide by 1000, round, multiply by 1000)
        df["timestamp_rounded_us"] = (timestamp_ns // 1000) * 1000
        df["dedup_key"] = (
            df["timestamp_rounded_us"].astype(str)
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
    if "timestamp_rounded_us" in unique_df.columns:
        unique_df = unique_df.drop("timestamp_rounded_us", axis=1)

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
    """Compute comprehensive statistics for a slice."""
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
            "price_variance": None,
            "volume_total": None,
            "volume_avg_per_trade": None,
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
    price_variance = prices.var()

    # Volume statistics
    volumes = df["volume"]
    volume_total = volumes.sum()
    volume_avg_per_trade = volumes.mean()

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
        "price_variance": float(price_variance),
        "volume_total": float(volume_total),
        "volume_avg_per_trade": float(volume_avg_per_trade),
    }

    logger.info(f"Computed stats: {len(df)} rows, ${price_mean:.2f} mean, ${price_std:.2f} std")

    return stats


def cross_venue_validation(
    binance_stats: Dict[str, Any], coinbase_stats: Dict[str, Any], kraken_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Perform cross-venue validation checks."""
    logger = logging.getLogger(__name__)

    validation_results = {
        "per_venue_stats": {
            "binance": binance_stats,
            "coinbase": coinbase_stats,
            "kraken": kraken_stats,
        },
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
    """Main comprehensive audit function."""
    parser = argparse.ArgumentParser(description="Comprehensive Binance Repair & Quarantine Audit")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔧 COMPREHENSIVE BINANCE REPAIR & QUARANTINE AUDIT")
    print("=" * 80)

    # Step 1: Discover capture scope
    logger.info("Step 1: Discovering capture scope...")
    capture_inventory = discover_capture_scope(s3_client, args.bucket)

    if capture_inventory["total_dates"] == 0:
        print("❌ No capture data found. Checked prefixes: raw_probes/")
        sys.exit(1)

    print(f"📅 Found {capture_inventory['total_dates']} capture dates")

    # Process each date
    all_results = {}
    quarantine_log = []
    repull_stubs = []

    for date in capture_inventory["dates"]:
        print(f"\n📊 Processing date: {date}")

        # Check if Binance has slices
        if "binance" not in capture_inventory["dates"][date]["venue_slices"]:
            print(f"⚠️  No Binance data found for {date}")
            continue

        binance_slices = capture_inventory["dates"][date]["venue_slices"]["binance"]
        print(f"🔍 Found {len(binance_slices)} Binance slices: {', '.join(binance_slices)}")

        date_results = {}

        for slice_name in binance_slices:
            print(f"\n🔧 Processing Binance {slice_name}...")

            try:
                # Load Binance data
                binance_df = load_slice_data(s3_client, args.bucket, date, "binance", slice_name)

                # De-duplicate
                binance_dedup_df, dedup_audit = deduplicate_binance_slice(binance_df)

                # Check for immediate quarantine conditions
                if dedup_audit["duplicate_ratio"] > 0.6:
                    print(
                        f"❌ QUARANTINE: Duplicate ratio {dedup_audit['duplicate_ratio']:.1%} exceeds 60%"
                    )
                    quarantine_log.append(
                        {
                            "date": date,
                            "slice": slice_name,
                            "reason": f"Duplicate ratio {dedup_audit['duplicate_ratio']:.1%} > 60%",
                            "duplicate_ratio": dedup_audit["duplicate_ratio"],
                        }
                    )
                    continue

                # Compute stats
                binance_stats = compute_slice_stats(binance_dedup_df)

                # Check for degenerate variance
                if binance_stats["price_std"] < 0.10:
                    print(f"❌ QUARANTINE: Price variance {binance_stats['price_std']:.4f} < $0.10")
                    quarantine_log.append(
                        {
                            "date": date,
                            "slice": slice_name,
                            "reason": f"Price variance {binance_stats['price_std']:.4f} < $0.10",
                            "price_std": binance_stats["price_std"],
                        }
                    )
                    continue

                # Cross-venue validation
                print(f"🔍 Cross-venue validation for {slice_name}...")

                # Load peer data
                coinbase_df = load_slice_data(s3_client, args.bucket, date, "coinbase", slice_name)
                kraken_df = load_slice_data(s3_client, args.bucket, date, "kraken", slice_name)

                coinbase_stats = compute_slice_stats(coinbase_df)
                kraken_stats = compute_slice_stats(kraken_df)

                # Perform validation
                validation_results = cross_venue_validation(
                    binance_stats, coinbase_stats, kraken_stats
                )

                if validation_results["final_verdict"] == "quarantine":
                    print(f"❌ QUARANTINE: {', '.join(validation_results['reasons'])}")
                    quarantine_log.append(
                        {
                            "date": date,
                            "slice": slice_name,
                            "reason": ", ".join(validation_results["reasons"]),
                            "validation_results": validation_results,
                        }
                    )
                else:
                    print(f"✅ ACCEPT: {slice_name} passed all validation checks")

                # Store results
                date_results[slice_name] = {
                    "dedup_audit": dedup_audit,
                    "binance_stats": binance_stats,
                    "coinbase_stats": coinbase_stats,
                    "kraken_stats": kraken_stats,
                    "validation_results": validation_results,
                    "status": validation_results["final_verdict"],
                }

                # Save repaired data if not quarantined
                if validation_results["final_verdict"] == "accept":
                    repaired_key = (
                        f"analysis/{date}/repaired/binance/slice={slice_name}/part-0000.parquet"
                    )
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
                    print(f"💾 Saved repaired data to {repaired_key}")

            except Exception as e:
                logger.error(f"Error processing {date} {slice_name}: {e}")
                print(f"❌ Error processing {slice_name}: {e}")
                continue

        all_results[date] = date_results

    # Generate re-pull stubs for quarantined slices
    for quarantine_entry in quarantine_log:
        date = quarantine_entry["date"]
        slice_name = quarantine_entry["slice"]

        # Determine time window from slice name
        if slice_name == "slice_00":
            start_time = f"{date}T00:00:00+00:00"
            end_time = f"{date}T00:15:00+00:00"
        elif slice_name == "slice_01":
            start_time = f"{date}T12:00:00+00:00"
            end_time = f"{date}T12:15:00+00:00"
        else:
            # Default to 15-minute window
            start_time = f"{date}T00:00:00+00:00"
            end_time = f"{date}T00:15:00+00:00"

        repull_stub = {
            "date": date,
            "slice": slice_name,
            "time_window": {"start": start_time, "end": end_time},
            "api_endpoint": "/api/v3/trades",
            "symbol": "BTCUSDT",
            "target_path": f"backfill/binance/{date}/slice_{slice_name.split('_')[1]}/part-0000.parquet",
            "quarantine_reason": quarantine_entry["reason"],
        }

        repull_stubs.append(repull_stub)

    # Save comprehensive results
    logger.info("Saving comprehensive results...")

    # Save capture inventory
    inventory_key = f"analysis/{date}/_diag/capture_inventory.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=inventory_key,
        Body=json.dumps(capture_inventory, indent=2),
        ContentType="application/json",
    )

    # Save repair audit
    repair_audit_key = f"analysis/{date}/_diag/binance_repair_audit.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=repair_audit_key,
        Body=json.dumps(all_results, indent=2),
        ContentType="application/json",
    )

    # Save quarantine log
    quarantine_key = f"analysis/{date}/_diag/quarantine_log.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=quarantine_key,
        Body=json.dumps(quarantine_log, indent=2),
        ContentType="application/json",
    )

    # Save re-pull stubs
    repull_key = f"analysis/{date}/_diag/repull_stubs.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=repull_key,
        Body=json.dumps(repull_stubs, indent=2),
        ContentType="application/json",
    )

    # Final summary
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Dates processed: {len(all_results)}")
    print(f"Total slices analyzed: {sum(len(slices) for slices in all_results.values())}")
    print(f"Quarantined slices: {len(quarantine_log)}")
    print(f"Re-pull stubs generated: {len(repull_stubs)}")

    if quarantine_log:
        print(f"\n🚫 QUARANTINED SLICES:")
        for entry in quarantine_log:
            print(f"  {entry['date']} {entry['slice']}: {entry['reason']}")

    if repull_stubs:
        print(f"\n🔄 RE-PULL STUBS:")
        for stub in repull_stubs:
            print(f"  {stub['date']} {stub['slice']}: {stub['target_path']}")

    print(f"\n📁 Results saved to S3:")
    print(f"  Inventory: s3://{args.bucket}/{inventory_key}")
    print(f"  Repair audit: s3://{args.bucket}/{repair_audit_key}")
    print(f"  Quarantine log: s3://{args.bucket}/{quarantine_key}")
    print(f"  Re-pull stubs: s3://{args.bucket}/{repull_key}")


if __name__ == "__main__":
    main()
