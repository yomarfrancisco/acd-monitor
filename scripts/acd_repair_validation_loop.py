#!/usr/bin/env python3
"""
ACD Repair & Validation Loop

Comprehensive analysis of captured data with deterministic de-duplication,
cross-venue validation, and quarantine classification.
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
            logging.FileHandler("acd_repair_validation_loop.log"),
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
        "earliest_date": dates[0] if dates else None,
        "latest_date": dates[-1] if dates else None,
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


def check_api_provenance(
    s3_client, bucket: str, date: str, venue: str, slice_name: str
) -> Dict[str, Any]:
    """Check API provenance from capture logs and manifests."""
    logger = logging.getLogger(__name__)

    provenance_info = {
        "api_traces_present": False,
        "synthetic_flags": False,
        "fallback_flags": False,
        "provenance": "INDETERMINATE",
    }

    # Check capture log
    log_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/capture.log.txt"
    try:
        response = s3_client.get_object(Bucket=bucket, Key=log_key)
        log_content = response["Body"].read().decode("utf-8")

        # More flexible API trace detection
        if any(
            phrase in log_content.lower()
            for phrase in [
                "api call successful",
                "websocket data received",
                "reality probe",
                "messages:",
                "provenance: real",
                "venue:",
            ]
        ):
            provenance_info["api_traces_present"] = True

        if "synthetic" in log_content.lower():
            provenance_info["synthetic_flags"] = True

        if "fallback" in log_content.lower():
            provenance_info["fallback_flags"] = True

    except Exception as e:
        logger.warning(f"Could not read capture log for {venue} {slice_name}: {e}")

    # Check manifest
    manifest_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/probe_manifest.json"
    try:
        response = s3_client.get_object(Bucket=bucket, Key=manifest_key)
        manifest_content = response["Body"].read().decode("utf-8")
        manifest = json.loads(manifest_content)

        if manifest.get("provenance") == "REAL":
            provenance_info["provenance"] = "REAL"
        elif manifest.get("provenance") == "SYNTHETIC":
            provenance_info["provenance"] = "SYNTHETIC"
            provenance_info["synthetic_flags"] = True

    except Exception as e:
        logger.warning(f"Could not read manifest for {venue} {slice_name}: {e}")

    # Determine final provenance
    if provenance_info["api_traces_present"] and not provenance_info["synthetic_flags"]:
        provenance_info["provenance"] = "REAL"
    elif provenance_info["synthetic_flags"] or provenance_info["fallback_flags"]:
        provenance_info["provenance"] = "SYNTHETIC"

    return provenance_info


def analyze_slice_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze slice statistics including duplicates and price/volume stats."""
    logger = logging.getLogger(__name__)

    if df.empty:
        return {
            "rows": 0,
            "duration_seconds": 0,
            "message_rate": 0,
            "exact_duplicates": 0,
            "exact_duplicate_ratio": 0.0,
            "keyed_duplicates": 0,
            "keyed_duplicate_ratio": 0.0,
            "price_last": None,
            "price_mean": None,
            "price_std": None,
            "price_min": None,
            "price_max": None,
            "price_iqr": None,
            "price_degenerate": False,
            "volume_total": None,
            "volume_median_trade_size": None,
            "min_timestamp": None,
            "max_timestamp": None,
        }

    # Basic stats
    rows = len(df)

    # Time analysis
    timestamps = pd.to_datetime(df["timestamp"], unit="ms")
    min_timestamp = timestamps.min()
    max_timestamp = timestamps.max()
    duration_seconds = (max_timestamp - min_timestamp).total_seconds()
    message_rate = rows / duration_seconds if duration_seconds > 0 else 0

    # Duplicate analysis
    exact_duplicates = df.duplicated().sum()
    exact_duplicate_ratio = exact_duplicates / rows if rows > 0 else 0

    # Keyed duplicates (trade_id or timestamp+price+volume)
    if "trade_id" in df.columns:
        keyed_duplicates = df.duplicated(subset=["trade_id"]).sum()
    else:
        # Use timestamp_rounded_us, price, volume
        if df["timestamp"].dtype == "object" or "datetime" in str(df["timestamp"].dtype):
            timestamp_ns = df["timestamp"].astype("int64")
        else:
            timestamp_ns = df["timestamp"]

        df_temp = df.copy()
        df_temp["timestamp_rounded_us"] = (timestamp_ns // 1000) * 1000
        keyed_duplicates = df_temp.duplicated(
            subset=["timestamp_rounded_us", "price", "volume"]
        ).sum()

    keyed_duplicate_ratio = keyed_duplicates / rows if rows > 0 else 0

    # Price analysis
    prices = df["price"]
    price_last = prices.iloc[-1] if not prices.empty else None
    price_mean = prices.mean()
    price_std = prices.std()
    price_min = prices.min()
    price_max = prices.max()
    price_iqr = prices.quantile(0.75) - prices.quantile(0.25)
    price_degenerate = price_std < 0.10

    # Volume analysis
    volumes = df["volume"]
    volume_total = volumes.sum()
    volume_median_trade_size = volumes.median()

    stats = {
        "rows": rows,
        "duration_seconds": duration_seconds,
        "message_rate": message_rate,
        "exact_duplicates": int(exact_duplicates),
        "exact_duplicate_ratio": float(exact_duplicate_ratio),
        "keyed_duplicates": int(keyed_duplicates),
        "keyed_duplicate_ratio": float(keyed_duplicate_ratio),
        "price_last": float(price_last) if price_last is not None else None,
        "price_mean": float(price_mean),
        "price_std": float(price_std),
        "price_min": float(price_min),
        "price_max": float(price_max),
        "price_iqr": float(price_iqr),
        "price_degenerate": bool(price_degenerate),
        "volume_total": float(volume_total),
        "volume_median_trade_size": float(volume_median_trade_size),
        "min_timestamp": min_timestamp.isoformat(),
        "max_timestamp": max_timestamp.isoformat(),
    }

    logger.info(
        f"Analyzed slice: {rows} rows, {duration_seconds:.1f}s, ${price_mean:.2f}±${price_std:.2f}"
    )

    return stats


def deduplicate_slice(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Perform deterministic de-duplication."""
    logger = logging.getLogger(__name__)

    total_rows = len(df)
    logger.info(f"Starting de-duplication with {total_rows} rows")

    # Create de-duplication key
    if "trade_id" in df.columns:
        # Use trade_id if present
        df["dedup_key"] = df["trade_id"].astype(str)
        key_type = "trade_id"
    else:
        # Use timestamp_rounded_us, price, volume
        if df["timestamp"].dtype == "object" or "datetime" in str(df["timestamp"].dtype):
            timestamp_ns = df["timestamp"].astype("int64")
        else:
            timestamp_ns = df["timestamp"]

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

    # Remove temporary columns
    if "dedup_key" in unique_df.columns:
        unique_df = unique_df.drop("dedup_key", axis=1)
    if "timestamp_rounded_us" in unique_df.columns:
        unique_df = unique_df.drop("timestamp_rounded_us", axis=1)

    unique_rows = len(unique_df)
    exact_duplicate_rows = total_rows - unique_rows
    duplicate_ratio = exact_duplicate_rows / total_rows if total_rows > 0 else 0

    dedup_audit = {
        "pre_dedup_rows": total_rows,
        "post_dedup_rows": unique_rows,
        "duplicates_removed": exact_duplicate_rows,
        "duplicate_ratio": duplicate_ratio,
        "key_type": key_type,
    }

    logger.info(
        f"De-duplication complete: {unique_rows} unique rows, {exact_duplicate_rows} duplicates ({duplicate_ratio:.1%})"
    )

    return unique_df, dedup_audit


def cross_venue_validation(
    binance_stats: Dict[str, Any], coinbase_stats: Dict[str, Any], kraken_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Perform cross-venue validation checks."""
    logger = logging.getLogger(__name__)

    validation_results = {
        "spread_checks": {},
        "variance_checks": {},
        "final_verdict": "ACCEPT",
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
        validation_results["final_verdict"] = "QUARANTINE"
        validation_results["reasons"].append(f"Price spread exceeds 1.0% threshold")

    if not variance_check_pass:
        validation_results["final_verdict"] = "QUARANTINE"
        validation_results["reasons"].append(
            f"Price variance is degenerate (std < ${min_std_threshold})"
        )

    if validation_results["final_verdict"] == "ACCEPT":
        validation_results["reasons"].append("All validation checks passed")

    logger.info(f"Cross-venue validation: {validation_results['final_verdict']}")
    logger.info(f"Spread checks: {spread_checks_pass}, Variance check: {variance_check_pass}")

    return validation_results


def classify_slice(
    provenance_info: Dict[str, Any],
    pre_stats: Dict[str, Any],
    post_stats: Dict[str, Any],
    validation_results: Dict[str, Any],
) -> str:
    """Classify slice as ACCEPT/QUARANTINE/INDETERMINATE."""

    # Check for INDETERMINATE conditions
    if provenance_info["provenance"] == "INDETERMINATE":
        return "INDETERMINATE"

    if not provenance_info["api_traces_present"]:
        return "INDETERMINATE"

    # Check for QUARANTINE conditions
    if post_stats["keyed_duplicate_ratio"] > 0.30:
        return "QUARANTINE"

    if post_stats["price_degenerate"]:
        return "QUARANTINE"

    if validation_results["final_verdict"] == "QUARANTINE":
        return "QUARANTINE"

    # If we get here, ACCEPT
    return "ACCEPT"


def generate_repull_stub(date: str, slice_name: str, quarantine_reason: str) -> Dict[str, Any]:
    """Generate re-pull stub for quarantined slice."""

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

    return {
        "date": date,
        "slice": slice_name,
        "time_window": {"start": start_time, "end": end_time},
        "api_endpoint": "/api/v3/trades",
        "symbol": "BTCUSDT",
        "target_path": f"backfill/binance/{date}/slice_{slice_name.split('_')[1]}/part-0000.parquet",
        "quarantine_reason": quarantine_reason,
        "generated_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    """Main repair and validation loop."""
    parser = argparse.ArgumentParser(description="ACD Repair & Validation Loop")
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
    print("🔧 ACD REPAIR & VALIDATION LOOP")
    print("=" * 80)

    # Step 1: Discover capture scope
    logger.info("Step 1: Discovering capture scope...")
    capture_inventory = discover_capture_scope(s3_client, args.bucket)

    if capture_inventory["total_dates"] == 0:
        print("❌ No capture data found. Checked prefixes: raw_probes/")
        sys.exit(1)

    print(f"📅 Earliest date: {capture_inventory['earliest_date']}")
    print(f"📅 Latest date: {capture_inventory['latest_date']}")
    print(f"📊 Total dates: {capture_inventory['total_dates']}")

    # Determine target date
    if args.date:
        target_date = args.date
        if target_date not in capture_inventory["dates"]:
            print(f"❌ Date {target_date} not found in capture inventory")
            sys.exit(1)
    else:
        target_date = capture_inventory["latest_date"]

    print(f"🎯 Processing date: {target_date}")

    # Check if required venues exist
    required_venues = ["binance", "coinbase", "kraken"]
    for venue in required_venues:
        if venue not in capture_inventory["dates"][target_date]["venue_slices"]:
            print(f"❌ Venue {venue} not found for date {target_date}")
            sys.exit(1)

    # Process each slice
    slice_results = {}
    quarantine_log = []
    repull_stubs = []

    # Get all slices (assuming all venues have same slices)
    binance_slices = capture_inventory["dates"][target_date]["venue_slices"]["binance"]

    for slice_name in binance_slices:
        print(f"\n🔧 Processing slice: {slice_name}")

        try:
            # Load data for all venues
            binance_df = load_slice_data(s3_client, args.bucket, target_date, "binance", slice_name)
            coinbase_df = load_slice_data(
                s3_client, args.bucket, target_date, "coinbase", slice_name
            )
            kraken_df = load_slice_data(s3_client, args.bucket, target_date, "kraken", slice_name)

            # Check API provenance for Binance
            provenance_info = check_api_provenance(
                s3_client, args.bucket, target_date, "binance", slice_name
            )

            if provenance_info["provenance"] == "INDETERMINATE":
                print(f"❌ INDETERMINATE: No API traces found for Binance {slice_name}")
                slice_results[slice_name] = {
                    "status": "INDETERMINATE",
                    "reason": "No API traces found",
                    "provenance_info": provenance_info,
                }
                continue

            # Analyze pre-dedup stats
            binance_pre_stats = analyze_slice_stats(binance_df)
            coinbase_stats = analyze_slice_stats(coinbase_df)
            kraken_stats = analyze_slice_stats(kraken_df)

            # De-duplicate Binance data
            binance_dedup_df, dedup_audit = deduplicate_slice(binance_df)

            # Check for immediate quarantine
            if dedup_audit["duplicate_ratio"] > 0.60:
                print(
                    f"❌ QUARANTINE: Duplicate ratio {dedup_audit['duplicate_ratio']:.1%} exceeds 60%"
                )
                quarantine_log.append(
                    {
                        "date": target_date,
                        "slice": slice_name,
                        "reason": f"Duplicate ratio {dedup_audit['duplicate_ratio']:.1%} > 60%",
                        "duplicate_ratio": dedup_audit["duplicate_ratio"],
                    }
                )
                continue

            # Analyze post-dedup stats
            binance_post_stats = analyze_slice_stats(binance_dedup_df)

            # Cross-venue validation
            validation_results = cross_venue_validation(
                binance_post_stats, coinbase_stats, kraken_stats
            )

            # Classify slice
            classification = classify_slice(
                provenance_info, binance_pre_stats, binance_post_stats, validation_results
            )

            print(f"📊 Classification: {classification}")

            # Store results
            slice_results[slice_name] = {
                "status": classification,
                "provenance_info": provenance_info,
                "pre_stats": binance_pre_stats,
                "post_stats": binance_post_stats,
                "dedup_audit": dedup_audit,
                "coinbase_stats": coinbase_stats,
                "kraken_stats": kraken_stats,
                "validation_results": validation_results,
            }

            # Handle based on classification
            if classification == "QUARANTINE":
                quarantine_log.append(
                    {
                        "date": target_date,
                        "slice": slice_name,
                        "reason": ", ".join(validation_results["reasons"]),
                        "duplicate_ratio": dedup_audit["duplicate_ratio"],
                        "price_std": binance_post_stats["price_std"],
                    }
                )

                # Generate re-pull stub
                repull_stub = generate_repull_stub(
                    target_date, slice_name, ", ".join(validation_results["reasons"])
                )
                repull_stubs.append(repull_stub)

            elif classification == "ACCEPT":
                # Save repaired data
                repaired_key = (
                    f"analysis/{target_date}/repaired/binance/slice={slice_name}/part-0000.parquet"
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
            logger.error(f"Error processing {slice_name}: {e}")
            print(f"❌ Error processing {slice_name}: {e}")
            continue

    # Save artifacts
    logger.info("Saving artifacts...")

    # Save capture inventory
    inventory_key = f"analysis/{target_date}/_diag/capture_inventory.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=inventory_key,
        Body=json.dumps(capture_inventory, indent=2),
        ContentType="application/json",
    )

    # Save slice results
    for slice_name, results in slice_results.items():
        slice_key = f"analysis/{target_date}/_diag/binance_{slice_name}_stats.json"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=slice_key,
            Body=json.dumps(results, indent=2),
            ContentType="application/json",
        )

    # Save quarantine log
    if quarantine_log:
        quarantine_key = f"analysis/{target_date}/_diag/quarantine_log.json"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=quarantine_key,
            Body=json.dumps(quarantine_log, indent=2),
            ContentType="application/json",
        )

    # Save re-pull stubs
    if repull_stubs:
        repull_key = f"analysis/{target_date}/_diag/repull_stubs.json"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=repull_key,
            Body=json.dumps(repull_stubs, indent=2),
            ContentType="application/json",
        )

    # Generate daily roll-up
    accept_count = sum(1 for r in slice_results.values() if r["status"] == "ACCEPT")
    indeterminate_count = sum(1 for r in slice_results.values() if r["status"] == "INDETERMINATE")
    quarantine_count = sum(1 for r in slice_results.values() if r["status"] == "QUARANTINE")

    daily_summary = {
        "date": target_date,
        "inventory": capture_inventory,
        "slice_results": slice_results,
        "summary": {
            "total_slices": len(slice_results),
            "accept_count": accept_count,
            "indeterminate_count": indeterminate_count,
            "quarantine_count": quarantine_count,
        },
        "quarantine_log": quarantine_log,
        "repull_stubs": repull_stubs,
    }

    summary_key = f"analysis/{target_date}/_diag/summary.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=summary_key,
        Body=json.dumps(daily_summary, indent=2),
        ContentType="application/json",
    )

    # Final summary
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Date processed: {target_date}")
    print(f"Total slices: {len(slice_results)}")
    print(f"✅ ACCEPT: {accept_count}")
    print(f"⚠️  INDETERMINATE: {indeterminate_count}")
    print(f"❌ QUARANTINE: {quarantine_count}")

    if quarantine_log:
        print(f"\n🚫 QUARANTINED SLICES:")
        for entry in quarantine_log:
            print(f"  {entry['slice']}: {entry['reason']}")

    if repull_stubs:
        print(f"\n🔄 RE-PULL STUBS:")
        for stub in repull_stubs:
            print(f"  {stub['slice']}: {stub['target_path']}")

    print(f"\n📁 Results saved to S3:")
    print(f"  Inventory: s3://{args.bucket}/{inventory_key}")
    print(f"  Summary: s3://{args.bucket}/{summary_key}")
    if quarantine_log:
        print(f"  Quarantine log: s3://{args.bucket}/{quarantine_key}")
    if repull_stubs:
        print(f"  Re-pull stubs: s3://{args.bucket}/{repull_key}")


if __name__ == "__main__":
    main()
