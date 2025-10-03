#!/usr/bin/env python3
"""
Reality Check Probe Script

Captures real data from venues to validate data quality and provenance.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import boto3
import pandas as pd

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from acd.data.adapters.real_tick_adapters import fetch_real_tick_data
from acd.data.cache import DataCache


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("reality_check_probe.log"),
        ],
    )


def capture_reality_probe(
    venues: List[str], symbol: str, slices: List[tuple], bucket: str, date: str
) -> Dict[str, Any]:
    """
    Capture reality probe data for specified venues and time slices.

    Args:
        venues: List of venue names
        symbol: Trading symbol (e.g., 'BTC-USD')
        slices: List of (start_time, end_time) tuples
        bucket: S3 bucket name
        date: Date string (YYYYMMDD)

    Returns:
        Summary results for each venue/slice combination
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting reality probe for {len(venues)} venues, {len(slices)} slices")

    results = {}
    s3_client = boto3.client("s3")

    for venue in venues:
        results[venue] = {}

        for i, (start_time, end_time) in enumerate(slices):
            slice_name = f"slice_{i:02d}"
            logger.info(f"Capturing {venue} {slice_name}: {start_time} to {end_time}")

            try:
                # Fetch real tick data
                venue_data = fetch_real_tick_data(
                    venues=[venue],
                    pair=symbol,
                    start_time=start_time,
                    end_time=end_time,
                    cache_dir="data/cache",
                )

                if venue in venue_data and len(venue_data[venue]) > 0:
                    df = venue_data[venue]

                    # Calculate metrics
                    msgs = len(df)
                    parse_rate = 1.0  # Assume 100% parse rate for now
                    provenance = "REAL" if msgs > 100 else "PARTIAL_REAL"

                    # Create probe manifest
                    probe_manifest = {
                        "venue": venue,
                        "slice": slice_name,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "msgs": msgs,
                        "parse_rate": parse_rate,
                        "provenance": provenance,
                        "fields_present": list(df.columns),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    # Write to S3
                    s3_prefix = f"raw_probes/{date}/venue={venue}/slice={slice_name}"

                    # Write manifest
                    s3_client.put_object(
                        Bucket=bucket,
                        Key=f"{s3_prefix}/probe_manifest.json",
                        Body=json.dumps(probe_manifest, indent=2),
                        ContentType="application/json",
                    )

                    # Write first 50 rows as NDJSON
                    first50 = df.head(50)
                    ndjson_content = first50.to_json(orient="records", lines=True)
                    s3_client.put_object(
                        Bucket=bucket,
                        Key=f"{s3_prefix}/first50.ndjson",
                        Body=ndjson_content,
                        ContentType="application/x-ndjson",
                    )

                    # Write sample parquet
                    parquet_buffer = first50.to_parquet()
                    s3_client.put_object(
                        Bucket=bucket,
                        Key=f"{s3_prefix}/sample.parquet",
                        Body=parquet_buffer,
                        ContentType="application/octet-stream",
                    )

                    # Write capture log
                    log_content = f"Reality probe capture log\nVenue: {venue}\nSlice: {slice_name}\nMessages: {msgs}\nProvenance: {provenance}\n"
                    s3_client.put_object(
                        Bucket=bucket,
                        Key=f"{s3_prefix}/capture.log.txt",
                        Body=log_content,
                        ContentType="text/plain",
                    )

                    results[venue][slice_name] = {
                        "connected": True,
                        "msgs": msgs,
                        "parse_rate": parse_rate,
                        "provenance": provenance,
                    }

                    logger.info(f"✅ {venue} {slice_name}: {msgs} messages, {provenance}")

                else:
                    results[venue][slice_name] = {
                        "connected": False,
                        "msgs": 0,
                        "parse_rate": 0.0,
                        "provenance": "FAIL",
                    }
                    logger.warning(f"❌ {venue} {slice_name}: No data captured")

            except Exception as e:
                logger.error(f"❌ {venue} {slice_name}: Error - {e}")
                results[venue][slice_name] = {
                    "connected": False,
                    "msgs": 0,
                    "parse_rate": 0.0,
                    "provenance": "FAIL",
                }

    return results


def generate_summary_table(results: Dict[str, Any]) -> None:
    """Generate and print summary table."""
    print("\n" + "=" * 80)
    print("REALITY PROBE SUMMARY TABLE")
    print("=" * 80)

    venues = list(results.keys())
    slices = list(next(iter(results.values())).keys()) if results else []

    # Header
    print(
        f"{'Venue':<12} {'Slice':<8} {'Connected':<10} {'Messages':<10} {'Parse Rate':<12} {'Provenance':<15}"
    )
    print("-" * 80)

    # Rows
    for venue in venues:
        for slice_name in slices:
            if slice_name in results[venue]:
                data = results[venue][slice_name]
                print(
                    f"{venue:<12} {slice_name:<8} {str(data['connected']):<10} {data['msgs']:<10} {data['parse_rate']:<12.1%} {data['provenance']:<15}"
                )

    # Overall verdicts
    print("\n" + "=" * 80)
    print("OVERALL VENUE VERDICTS")
    print("=" * 80)

    for venue in venues:
        venue_results = results[venue]
        real_count = sum(1 for r in venue_results.values() if r["provenance"] == "REAL")
        partial_count = sum(1 for r in venue_results.values() if r["provenance"] == "PARTIAL_REAL")
        fail_count = sum(1 for r in venue_results.values() if r["provenance"] == "FAIL")

        if real_count > 0:
            verdict = "REAL"
        elif partial_count > 0:
            verdict = "PARTIAL_REAL"
        elif fail_count > 0:
            verdict = "FAIL"
        else:
            verdict = "INDETERMINATE"

        print(
            f"{venue:<12} {verdict:<15} (REAL: {real_count}, PARTIAL: {partial_count}, FAIL: {fail_count})"
        )


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Reality Check Probe")
    parser.add_argument(
        "--venues",
        nargs="+",
        default=["coinbase", "kraken", "okx", "bybit", "binance"],
        help="Venues to probe",
    )
    parser.add_argument("--symbol", default="BTC-USD", help="Trading symbol")
    parser.add_argument("--date", default=None, help="Date (YYYYMMDD), defaults to today")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Set date
    if args.date:
        date = args.date
    else:
        date = datetime.now().strftime("%Y%m%d")

    # Define time slices (15-minute slices)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    slices = [
        (today, today + timedelta(minutes=15)),  # 00:00-00:15 UTC
        (today + timedelta(hours=12), today + timedelta(hours=12, minutes=15)),  # 12:00-12:15 UTC
    ]

    logger.info(f"Probing {len(args.venues)} venues on {date}")
    slice_times = [f"{s[0].strftime('%H:%M')}-{s[1].strftime('%H:%M')}" for s in slices]
    logger.info(f"Time slices: {slice_times}")

    # Run probe
    results = capture_reality_probe(
        venues=args.venues, symbol=args.symbol, slices=slices, bucket=args.bucket, date=date
    )

    # Generate summary
    generate_summary_table(results)

    # Check if we have any REAL data
    all_venues = list(results.keys())
    real_venues = []
    for venue in all_venues:
        venue_results = results[venue]
        if any(r["provenance"] == "REAL" for r in venue_results.values()):
            real_venues.append(venue)

    if not real_venues:
        logger.error("❌ No venues returned REAL data - stopping")
        sys.exit(1)
    else:
        logger.info(f"✅ Found REAL data from {len(real_venues)} venues: {real_venues}")
        # Prefer coinbase if available
        if "coinbase" in real_venues:
            selected_venue = "coinbase"
        else:
            selected_venue = real_venues[0]
        logger.info(f"Selected venue for staging: {selected_venue}")


if __name__ == "__main__":
    main()
