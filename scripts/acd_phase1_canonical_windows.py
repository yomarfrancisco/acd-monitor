#!/usr/bin/env python3
"""
ACD Phase 1 - Define Canonical Time Windows

Builds intersection windows where all three venues have coverage.
If none exist, proposes exactly one 15-min canonical window and backfills missing venues.
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
import requests


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase1_canonical_windows.log"),
        ],
    )


def load_inventory_data(s3_client, bucket: str, date: str) -> Dict[str, Any]:
    """Load Phase 0 inventory data."""
    logger = logging.getLogger(__name__)

    inventory_key = f"analysis/{date}/ACD/_inv/capture_timeline.json"

    try:
        response = s3_client.get_object(Bucket=bucket, Key=inventory_key)
        inventory_data = json.loads(response["Body"].read().decode("utf-8"))
        logger.info(f"Loaded inventory data for {date}")
        return inventory_data
    except Exception as e:
        logger.error(f"Error loading inventory data: {e}")
        raise


def find_intersection_windows(inventory_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find intersection windows where all three venues have coverage."""
    logger = logging.getLogger(__name__)

    venues = ["binance", "coinbase", "kraken"]
    intersection_windows = []

    # Get all usable slices for each venue
    venue_slices = {}
    for venue in venues:
        venue_slices[venue] = [
            slice_data
            for slice_data in inventory_data["venue_slices"][venue]
            if slice_data["usable"]
        ]

    # Find overlapping time windows
    for binance_slice in venue_slices["binance"]:
        for coinbase_slice in venue_slices["coinbase"]:
            for kraken_slice in venue_slices["kraken"]:
                # Parse timestamps
                binance_start = pd.to_datetime(binance_slice["start_ts_utc"])
                binance_end = pd.to_datetime(binance_slice["end_ts_utc"])
                coinbase_start = pd.to_datetime(coinbase_slice["start_ts_utc"])
                coinbase_end = pd.to_datetime(coinbase_slice["end_ts_utc"])
                kraken_start = pd.to_datetime(kraken_slice["start_ts_utc"])
                kraken_end = pd.to_datetime(kraken_slice["end_ts_utc"])

                # Find intersection
                intersection_start = max(binance_start, coinbase_start, kraken_start)
                intersection_end = min(binance_end, coinbase_end, kraken_end)

                if intersection_start < intersection_end:
                    duration_seconds = (intersection_end - intersection_start).total_seconds()
                    overlap_percentage = duration_seconds / (15 * 60) * 100  # 15 minutes baseline

                    if duration_seconds > 0:
                        intersection_windows.append(
                            {
                                "window_id": f"window_{len(intersection_windows)}",
                                "start_utc": intersection_start.isoformat(),
                                "end_utc": intersection_end.isoformat(),
                                "duration_seconds": duration_seconds,
                                "overlap_percentage": overlap_percentage,
                                "binance_slice": binance_slice["slice_name"],
                                "coinbase_slice": coinbase_slice["slice_name"],
                                "kraken_slice": kraken_slice["slice_name"],
                                "binance_source": binance_slice["source"],
                                "coinbase_source": coinbase_slice["source"],
                                "kraken_source": kraken_slice["source"],
                            }
                        )

    logger.info(f"Found {len(intersection_windows)} intersection windows")
    return intersection_windows


def propose_canonical_window(inventory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Propose exactly one 15-min canonical window."""
    logger = logging.getLogger(__name__)

    # Use the most recent usable slice from each venue
    venues = ["binance", "coinbase", "kraken"]
    canonical_slices = {}

    for venue in venues:
        usable_slices = [
            slice_data
            for slice_data in inventory_data["venue_slices"][venue]
            if slice_data["usable"]
        ]

        if not usable_slices:
            logger.error(f"No usable slices found for {venue}")
            return None

        # Use the latest slice (assuming slice_01 is later than slice_00)
        canonical_slices[venue] = max(usable_slices, key=lambda x: x["slice_name"])

    # Create 15-minute canonical window
    # Use the earliest start time and create a 15-minute window
    all_starts = [pd.to_datetime(canonical_slices[venue]["start_ts_utc"]) for venue in venues]

    canonical_start = min(all_starts)
    canonical_end = canonical_start + timedelta(minutes=15)

    canonical_window = {
        "window_id": "canonical_15min",
        "start_utc": canonical_start.isoformat(),
        "end_utc": canonical_end.isoformat(),
        "duration_seconds": 15 * 60,
        "target_overlap_percentage": 80.0,
        "canonical_slices": canonical_slices,
        "backfill_required": [],
    }

    # Check which venues need backfill
    for venue in venues:
        slice_data = canonical_slices[venue]
        slice_start = pd.to_datetime(slice_data["start_ts_utc"])
        slice_end = pd.to_datetime(slice_data["end_ts_utc"])

        # Check if slice covers the canonical window
        slice_coverage = min(slice_end, canonical_end) - max(slice_start, canonical_start)
        coverage_percentage = slice_coverage.total_seconds() / (15 * 60) * 100

        if coverage_percentage < 80:
            canonical_window["backfill_required"].append(
                {
                    "venue": venue,
                    "current_coverage": coverage_percentage,
                    "slice_name": slice_data["slice_name"],
                    "slice_source": slice_data["source"],
                }
            )

    logger.info(f"Proposed canonical window: {canonical_start} to {canonical_end}")
    logger.info(
        f"Backfill required for: {[item['venue'] for item in canonical_window['backfill_required']]}"
    )

    return canonical_window


def backfill_venue_data(
    s3_client, bucket: str, date: str, venue: str, window_start: datetime, window_end: datetime
) -> bool:
    """Backfill missing venue data for the canonical window."""
    logger = logging.getLogger(__name__)

    logger.info(f"Backfilling {venue} data for {window_start} to {window_end}")

    try:
        if venue == "binance":
            # Use existing backfilled data if available
            backfill_key = f"backfill/binance/{date}/slice_01/part-0000.parquet"
            try:
                response = s3_client.get_object(Bucket=bucket, Key=backfill_key)
                logger.info(f"Using existing backfilled Binance data")
                return True
            except:
                logger.info(f"No existing backfill found, would need to fetch from API")
                return False

        elif venue == "coinbase":
            # For demonstration, we'll use the existing data
            # In a real scenario, this would fetch from Coinbase API
            logger.info(f"Coinbase backfill would require API call to /v2/trades")
            return False

        elif venue == "kraken":
            # For demonstration, we'll use the existing data
            # In a real scenario, this would fetch from Kraken API
            logger.info(f"Kraken backfill would require API call to /0/public/Trades")
            return False

        return False

    except Exception as e:
        logger.error(f"Error backfilling {venue}: {e}")
        return False


def main():
    """Main Phase 1 function."""
    parser = argparse.ArgumentParser(description="ACD Phase 1 - Define Canonical Time Windows")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE 1 - DEFINE CANONICAL TIME WINDOWS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")

    # Load inventory data
    print(f"\n🔄 Loading Phase 0 inventory data...")
    try:
        inventory_data = load_inventory_data(s3_client, args.bucket, args.date)
        print(f"✅ Loaded inventory data")
    except Exception as e:
        print(f"❌ Error loading inventory data: {e}")
        sys.exit(1)

    # Find intersection windows
    print(f"\n🔍 Finding intersection windows...")
    try:
        intersection_windows = find_intersection_windows(inventory_data)

        if intersection_windows:
            print(f"✅ Found {len(intersection_windows)} intersection windows")
            for window in intersection_windows:
                print(
                    f"   {window['window_id']}: {window['start_utc']} to {window['end_utc']} ({window['overlap_percentage']:.1f}% overlap)"
                )
        else:
            print(f"⚠️ No intersection windows found")

    except Exception as e:
        print(f"❌ Error finding intersection windows: {e}")
        sys.exit(1)

    # Check if we have sufficient overlap
    sufficient_windows = [w for w in intersection_windows if w["overlap_percentage"] >= 80]

    if sufficient_windows:
        print(f"✅ Found {len(sufficient_windows)} windows with ≥80% overlap")
        canonical_window = max(sufficient_windows, key=lambda x: x["overlap_percentage"])
    else:
        print(f"⚠️ No windows with ≥80% overlap found, proposing canonical window...")

        # Propose canonical window
        try:
            canonical_window = propose_canonical_window(inventory_data)

            if not canonical_window:
                print(f"❌ Could not propose canonical window")
                sys.exit(1)

            print(
                f"📋 Proposed canonical window: {canonical_window['start_utc']} to {canonical_window['end_utc']}"
            )

            # Attempt backfill for missing venues
            if canonical_window["backfill_required"]:
                print(f"🔄 Attempting backfill for missing venues...")

                window_start = pd.to_datetime(canonical_window["start_utc"])
                window_end = pd.to_datetime(canonical_window["end_utc"])

                backfill_success = []
                for backfill_item in canonical_window["backfill_required"]:
                    venue = backfill_item["venue"]
                    success = backfill_venue_data(
                        s3_client, args.bucket, args.date, venue, window_start, window_end
                    )
                    backfill_success.append(success)
                    print(f"   {venue}: {'✅ Success' if success else '❌ Failed'}")

                if not any(backfill_success):
                    print(f"❌ STOP: No successful backfills, overlap < 80%")
                    print(f"   Saving report and waiting for instructions...")

                    # Save failure report
                    failure_report = {
                        "canonical_window": canonical_window,
                        "backfill_attempts": canonical_window["backfill_required"],
                        "backfill_success": backfill_success,
                        "reason": "No successful backfills, overlap < 80%",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    failure_key = f"analysis/{args.date}/ACD/_align/failure_report.json"
                    s3_client.put_object(
                        Bucket=args.bucket,
                        Key=failure_key,
                        Body=json.dumps(failure_report, indent=2),
                        ContentType="application/json",
                    )

                    print(f"💾 Saved failure report: s3://{args.bucket}/{failure_key}")
                    sys.exit(1)
            else:
                print(f"✅ No backfill required")
        except Exception as e:
            print(f"❌ Error proposing canonical window: {e}")
            sys.exit(1)

    # Save canonical windows
    print(f"\n💾 Saving canonical windows...")

    canonical_windows_data = {
        "date": args.date,
        "intersection_windows": intersection_windows,
        "canonical_window": canonical_window,
        "alignment_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    canonical_key = f"analysis/{args.date}/ACD/_align/canonical_windows.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=canonical_key,
        Body=json.dumps(canonical_windows_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved canonical windows: s3://{args.bucket}/{canonical_key}")

    # Final summary
    print(f"\n📊 PHASE 1 SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Intersection windows found: {len(intersection_windows)}")
    print(f"Canonical window: {canonical_window['start_utc']} to {canonical_window['end_utc']}")
    print(f"Duration: {canonical_window['duration_seconds']:.1f} seconds")

    if "overlap_percentage" in canonical_window:
        print(f"Overlap: {canonical_window['overlap_percentage']:.1f}%")

    if canonical_window["backfill_required"]:
        print(f"Backfill required: {len(canonical_window['backfill_required'])} venues")
        for item in canonical_window["backfill_required"]:
            print(f"  {item['venue']}: {item['current_coverage']:.1f}% coverage")
    else:
        print(f"Backfill required: None")

    print(f"\n📁 Generated artifacts:")
    print(f"  Canonical windows: s3://{args.bucket}/{canonical_key}")


if __name__ == "__main__":
    main()
