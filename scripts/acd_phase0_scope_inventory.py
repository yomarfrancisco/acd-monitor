#!/usr/bin/env python3
"""
ACD Phase 0 - Scope & Provenance Inventory

Discovers available capture dates and inventories all venues with basic stats.
No math, no inference - just data discovery and basic metrics.
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
            logging.FileHandler("acd_phase0_scope_inventory.log"),
        ],
    )


def discover_capture_dates(s3_client, bucket: str) -> List[str]:
    """Discover all available capture dates."""
    logger = logging.getLogger(__name__)

    logger.info("Discovering capture dates...")

    # Check raw_probes
    raw_probes_dates = []
    prefix = "raw_probes/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            prefix = common_prefix["Prefix"]
            if prefix.startswith("raw_probes/") and prefix.endswith("/"):
                date_str = prefix.replace("raw_probes/", "").strip("/")
                if date_str and date_str.isdigit() and len(date_str) == 8:
                    raw_probes_dates.append(date_str)

    # Check backfill
    backfill_dates = []
    prefix = "backfill/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            prefix = common_prefix["Prefix"]
            if prefix.startswith("backfill/") and prefix.endswith("/"):
                # Extract date from backfill/{venue}/{date}/...
                parts = prefix.split("/")
                if len(parts) >= 3 and parts[2].isdigit() and len(parts[2]) == 8:
                    backfill_dates.append(parts[2])

    all_dates = sorted(list(set(raw_probes_dates + backfill_dates)))

    logger.info(f"Found {len(all_dates)} capture dates: {all_dates}")
    return all_dates


def discover_venue_slices(s3_client, bucket: str, date: str, venue: str) -> List[Dict[str, Any]]:
    """Discover slices for a specific venue and date."""
    logger = logging.getLogger(__name__)

    slices = []

    # Check raw_probes
    prefix = f"raw_probes/{date}/venue={venue}/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            slice_str = common_prefix["Prefix"].split("=")[-1].strip("/")
            if slice_str and "slice=" in common_prefix["Prefix"]:
                slices.append(
                    {
                        "slice_name": slice_str,
                        "source": "raw_probes",
                        "path": f"raw_probes/{date}/venue={venue}/slice={slice_str}/",
                    }
                )

    # Check backfill
    prefix = f"backfill/{venue}/{date}/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            window_str = common_prefix["Prefix"].split("/")[-1].strip("/")
            if window_str and "slice_" in window_str:
                slices.append(
                    {
                        "slice_name": window_str,
                        "source": "backfill",
                        "path": f"backfill/{venue}/{date}/{window_str}/",
                    }
                )

    logger.info(f"Found {len(slices)} slices for {venue} on {date}")
    return slices


def analyze_slice_basic_stats(
    s3_client, bucket: str, date: str, venue: str, slice_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze basic stats for a slice."""
    logger = logging.getLogger(__name__)

    slice_name = slice_info["slice_name"]
    source = slice_info["source"]
    path = slice_info["path"]

    try:
        # Load parquet data
        if source == "raw_probes":
            parquet_key = f"{path}sample.parquet"
        else:  # backfill
            parquet_key = f"{path}part-0000.parquet"

        response = s3_client.get_object(Bucket=bucket, Key=parquet_key)
        parquet_data = response["Body"].read()

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        if df.empty:
            return {
                "slice_name": slice_name,
                "source": source,
                "n_rows": 0,
                "start_ts_utc": None,
                "end_ts_utc": None,
                "duration_seconds": 0,
                "duplicate_ratio": 0.0,
                "price_std": None,
                "price_mean": None,
                "price_min": None,
                "price_max": None,
                "volume_total": None,
                "usable": False,
                "error": None,
            }

        # Convert timestamps
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

        # Basic stats
        n_rows = len(df)
        start_ts_utc = df["timestamp_dt"].min()
        end_ts_utc = df["timestamp_dt"].max()
        duration_seconds = (end_ts_utc - start_ts_utc).total_seconds()

        # Duplicate analysis
        if "trade_id" in df.columns:
            duplicates = df.duplicated(subset=["trade_id"]).sum()
        else:
            duplicates = df.duplicated(subset=["timestamp", "price", "volume"]).sum()
        duplicate_ratio = duplicates / n_rows if n_rows > 0 else 0

        # Price analysis
        prices = df["price"]
        price_std = prices.std()
        price_mean = prices.mean()
        price_min = prices.min()
        price_max = prices.max()

        # Volume analysis
        volumes = df["volume"]
        volume_total = volumes.sum()

        # Usability criteria
        usable = (
            n_rows > 10  # At least 10 trades
            and duration_seconds > 0  # Non-zero duration
            and price_std > 0  # Non-zero price variance
            and not pd.isna(price_mean)  # Valid price mean
        )

        stats = {
            "slice_name": slice_name,
            "source": source,
            "n_rows": n_rows,
            "start_ts_utc": start_ts_utc.isoformat(),
            "end_ts_utc": end_ts_utc.isoformat(),
            "duration_seconds": duration_seconds,
            "duplicate_ratio": float(duplicate_ratio),
            "price_std": float(price_std),
            "price_mean": float(price_mean),
            "price_min": float(price_min),
            "price_max": float(price_max),
            "volume_total": float(volume_total),
            "usable": usable,
            "error": None,
        }

        logger.info(
            f"{venue} {slice_name}: {n_rows} rows, {duration_seconds:.1f}s, ${price_mean:.2f}±${price_std:.2f}, usable: {usable}"
        )

        return stats

    except Exception as e:
        logger.error(f"Error analyzing {venue} {slice_name}: {e}")
        return {
            "slice_name": slice_name,
            "source": source,
            "n_rows": 0,
            "start_ts_utc": None,
            "end_ts_utc": None,
            "duration_seconds": 0,
            "duplicate_ratio": 0.0,
            "price_std": None,
            "price_mean": None,
            "price_min": None,
            "price_max": None,
            "volume_total": None,
            "usable": False,
            "error": str(e),
        }


def main():
    """Main Phase 0 function."""
    parser = argparse.ArgumentParser(description="ACD Phase 0 - Scope & Provenance Inventory")
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
    print("🔍 ACD PHASE 0 - SCOPE & PROVENANCE INVENTORY")
    print("=" * 80)

    # Discover capture dates
    print(f"\n📅 Discovering capture dates...")
    try:
        capture_dates = discover_capture_dates(s3_client, args.bucket)

        if not capture_dates:
            print("❌ No capture dates found")
            sys.exit(1)

        print(f"✅ Found {len(capture_dates)} capture dates: {capture_dates}")

    except Exception as e:
        print(f"❌ Error discovering capture dates: {e}")
        sys.exit(1)

    # Determine target date
    if args.date:
        target_date = args.date
        if target_date not in capture_dates:
            print(f"❌ Date {target_date} not found in capture inventory")
            sys.exit(1)
    else:
        target_date = capture_dates[-1]  # Latest date

    print(f"🎯 Processing date: {target_date}")

    # Discover venue slices
    print(f"\n🔍 Discovering venue slices...")
    venues = ["binance", "coinbase", "kraken"]
    venue_slices = {}

    for venue in venues:
        try:
            slices = discover_venue_slices(s3_client, args.bucket, target_date, venue)
            venue_slices[venue] = slices
            print(f"✅ {venue}: {len(slices)} slices")
        except Exception as e:
            print(f"❌ Error discovering slices for {venue}: {e}")
            venue_slices[venue] = []

    # Check if we have data for all venues
    venues_with_data = [venue for venue in venues if venue_slices[venue]]
    if len(venues_with_data) < len(venues):
        missing_venues = [venue for venue in venues if not venue_slices[venue]]
        print(f"❌ STOP: No data for venues: {missing_venues}")
        sys.exit(1)

    # Analyze slices
    print(f"\n📊 Analyzing slice statistics...")
    all_slice_stats = {}

    for venue in venues:
        all_slice_stats[venue] = []

        for slice_info in venue_slices[venue]:
            try:
                stats = analyze_slice_basic_stats(
                    s3_client, args.bucket, target_date, venue, slice_info
                )
                all_slice_stats[venue].append(stats)
            except Exception as e:
                logger.error(f"Error analyzing {venue} {slice_info['slice_name']}: {e}")
                continue

    # Generate inventory report
    print(f"\n📋 Generating inventory report...")

    inventory_data = {
        "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
        "target_date": target_date,
        "available_dates": capture_dates,
        "venues_analyzed": venues,
        "venue_slices": all_slice_stats,
        "summary": {
            "total_venues": len(venues),
            "venues_with_data": len(venues_with_data),
            "total_slices": sum(len(slices) for slices in all_slice_stats.values()),
            "usable_slices": sum(
                len([s for s in slices if s["usable"]]) for slices in all_slice_stats.values()
            ),
        },
    }

    # Save inventory
    inventory_key = f"analysis/{target_date}/ACD/_inv/capture_timeline.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=inventory_key,
        Body=json.dumps(inventory_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved inventory: s3://{args.bucket}/{inventory_key}")

    # Generate markdown report
    markdown_content = f"""# ACD Phase 0 - Scope & Provenance Inventory

**Date**: {target_date}  
**Discovery Time**: {datetime.now(timezone.utc).isoformat()}  
**Total Venues**: {inventory_data['summary']['total_venues']}  
**Venues with Data**: {inventory_data['summary']['venues_with_data']}  
**Total Slices**: {inventory_data['summary']['total_slices']}  
**Usable Slices**: {inventory_data['summary']['usable_slices']}  

## Venue Analysis

"""

    for venue in venues:
        slices = all_slice_stats[venue]
        usable_slices = [s for s in slices if s["usable"]]

        markdown_content += f"### {venue.upper()}\n\n"
        markdown_content += f"**Total Slices**: {len(slices)}\n"
        markdown_content += f"**Usable Slices**: {len(usable_slices)}\n\n"

        if slices:
            markdown_content += "| Slice | Source | Rows | Duration | Price Mean | Price Std | Duplicate % | Usable |\n"
            markdown_content += "|-------|--------|------|----------|------------|-----------|-------------|--------|\n"

            for slice_stats in slices:
                status = "✅" if slice_stats["usable"] else "❌"
                markdown_content += f"| {slice_stats['slice_name']} | {slice_stats['source']} | {slice_stats['n_rows']} | {slice_stats['duration_seconds']:.1f}s | ${slice_stats['price_mean']:.2f} | ${slice_stats['price_std']:.2f} | {slice_stats['duplicate_ratio']:.1%} | {status} |\n"
        else:
            markdown_content += "No slices found.\n"

        markdown_content += "\n"

    # Save markdown report
    markdown_key = f"analysis/{target_date}/ACD/_inv/capture_timeline.md"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=markdown_key,
        Body=markdown_content.encode("utf-8"),
        ContentType="text/markdown",
    )

    print(f"💾 Saved markdown report: s3://{args.bucket}/{markdown_key}")

    # Final summary
    print(f"\n📊 PHASE 0 SUMMARY")
    print("=" * 60)
    print(f"Date: {target_date}")
    print(f"Venues with data: {len(venues_with_data)}/{len(venues)}")
    print(f"Total slices: {inventory_data['summary']['total_slices']}")
    print(f"Usable slices: {inventory_data['summary']['usable_slices']}")

    # Per-venue summary
    for venue in venues:
        slices = all_slice_stats[venue]
        usable_slices = [s for s in slices if s["usable"]]
        print(f"  {venue}: {len(usable_slices)}/{len(slices)} usable")

    print(f"\n📁 Generated artifacts:")
    print(f"  Inventory JSON: s3://{args.bucket}/{inventory_key}")
    print(f"  Markdown report: s3://{args.bucket}/{markdown_key}")


if __name__ == "__main__":
    main()
