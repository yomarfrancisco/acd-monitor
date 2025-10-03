#!/usr/bin/env python3
"""
ACD Phase CLN - Clean & Normalize

Loads backfilled ticks within canonical window and standardizes schema.
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
            logging.FileHandler("acd_phase_cln_clean_normalize.log"),
        ],
    )


def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None


def get_s3_object_text(s3_client, bucket: str, key: str) -> Optional[str]:
    """Helper to get text content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None


def load_canonical_window(s3_client, bucket: str, date: str) -> Optional[Dict[str, Any]]:
    """Load canonical window definition."""
    canonical_key = f"analysis/{date}/ACD/_align/canonical_window.json"
    canonical_content = get_s3_object_text(s3_client, bucket, canonical_key)

    if not canonical_content:
        return None

    try:
        return json.loads(canonical_content)
    except json.JSONDecodeError:
        return None


def load_venue_backfill_data(
    s3_client, bucket: str, date: str, venue: str
) -> Optional[pd.DataFrame]:
    """Load backfilled data for a venue."""
    logger = logging.getLogger(__name__)

    # Find backfill data
    prefix = f"backfill/{venue}/{date}/"
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if "Contents" not in response:
            return None

        parquet_files = []
        for obj in response["Contents"]:
            key = obj["Key"]
            if key.endswith(".parquet"):
                parquet_files.append(key)

        if not parquet_files:
            return None

        # Use latest file
        s3_key = sorted(parquet_files)[-1]

    except Exception as e:
        logger.error(f"Error listing files for {venue}: {e}")
        return None

    # Load parquet data
    parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
    if not parquet_content:
        return None

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()

        # Ensure timestamp is datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        logger.info(f"Loaded {venue} backfill data: {len(df)} rows")
        return df

    except Exception as e:
        logger.error(f"Error loading {venue} backfill data: {e}")
        return None


def clean_and_normalize_data(
    df: pd.DataFrame, venue: str, canonical_window: Dict[str, Any]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Clean and normalize data for a venue."""
    logger = logging.getLogger(__name__)

    if df.empty:
        return df, {"error": "Empty DataFrame"}

    # Filter to canonical window
    canonical_start = pd.to_datetime(canonical_window["canonical_start"])
    canonical_end = pd.to_datetime(canonical_window["canonical_end"])

    # Filter data to canonical window
    window_data = df[
        (df["timestamp"] >= canonical_start) & (df["timestamp"] <= canonical_end)
    ].copy()

    if window_data.empty:
        return window_data, {"error": "No data in canonical window"}

    # Standardize schema
    cleaned_data = pd.DataFrame()

    # Required fields
    cleaned_data["timestamp"] = window_data["timestamp"]
    cleaned_data["price"] = pd.to_numeric(window_data["price"], errors="coerce")
    cleaned_data["volume"] = pd.to_numeric(window_data["volume"], errors="coerce")
    cleaned_data["venue"] = venue

    # Optional fields
    if "trade_id" in window_data.columns:
        cleaned_data["trade_id"] = window_data["trade_id"]
    else:
        cleaned_data["trade_id"] = None

    if "symbol" in window_data.columns:
        cleaned_data["symbol"] = window_data["symbol"]
    else:
        cleaned_data["symbol"] = "BTCUSD"  # Default symbol

    # Remove rows with invalid data
    initial_rows = len(cleaned_data)
    cleaned_data = cleaned_data.dropna(subset=["timestamp", "price", "volume"])
    final_rows = len(cleaned_data)

    # Validate monotonicity by timestamp
    cleaned_data = cleaned_data.sort_values("timestamp")
    is_monotonic = cleaned_data["timestamp"].is_monotonic_increasing

    # Compute statistics
    stats = {
        "initial_rows": initial_rows,
        "final_rows": final_rows,
        "dropped_rows": initial_rows - final_rows,
        "is_monotonic": is_monotonic,
        "time_span_seconds": (
            cleaned_data["timestamp"].max() - cleaned_data["timestamp"].min()
        ).total_seconds(),
        "price_stats": {
            "mean": float(cleaned_data["price"].mean()),
            "std": float(cleaned_data["price"].std()),
            "min": float(cleaned_data["price"].min()),
            "max": float(cleaned_data["price"].max()),
        },
        "volume_stats": {
            "total": float(cleaned_data["volume"].sum()),
            "mean": float(cleaned_data["volume"].mean()),
            "median": float(cleaned_data["volume"].median()),
        },
    }

    logger.info(
        f"{venue}: {final_rows} rows, ${stats['price_stats']['mean']:.2f} mean, ${stats['price_stats']['std']:.2f} std"
    )

    return cleaned_data, stats


def save_clean_data(s3_client, bucket: str, date: str, venue: str, df: pd.DataFrame) -> str:
    """Save cleaned data to S3."""
    logger = logging.getLogger(__name__)

    s3_key = f"analysis/{date}/ACD/_cln/{venue}/part-0000.parquet"

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
        df.to_parquet(tmp_file.name, index=False)
        s3_client.upload_file(tmp_file.name, bucket, s3_key)
        Path(tmp_file.name).unlink()

    logger.info(f"Saved {venue} clean data: s3://{bucket}/{s3_key}")
    return s3_key


def main():
    """Main Phase CLN function."""
    parser = argparse.ArgumentParser(description="ACD Phase CLN - Clean & Normalize")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE CLN - CLEAN & NORMALIZE")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")

    # Load canonical window
    print(f"\n🔍 Loading canonical window...")

    canonical_window = load_canonical_window(s3_client, args.bucket, args.date)
    if not canonical_window:
        print(f"❌ No canonical window found")
        sys.exit(1)

    print(f"✅ Canonical window loaded")
    print(f"   Duration: {canonical_window['canonical_duration_minutes']:.1f} minutes")
    print(f"   Included: {canonical_window['included_venues']}")

    # Load and clean data for each venue
    print(f"\n🔍 Loading and cleaning venue data...")

    venues = canonical_window["included_venues"]
    clean_results = {}

    for venue in venues:
        print(f"\n📊 Processing {venue.upper()}...")

        # Load backfill data
        df = load_venue_backfill_data(s3_client, args.bucket, args.date, venue)
        if df is None:
            print(f"   ❌ No backfill data found for {venue}")
            continue

        # Clean and normalize
        cleaned_df, stats = clean_and_normalize_data(df, venue, canonical_window)

        if cleaned_df.empty:
            print(f"   ❌ No data in canonical window for {venue}")
            continue

        # Save clean data
        s3_key = save_clean_data(s3_client, args.bucket, args.date, venue, cleaned_df)

        clean_results[venue] = {"s3_key": s3_key, "stats": stats, "status": "success"}

        print(f"   ✅ Cleaned {stats['final_rows']} rows")
        print(
            f"   📊 Price: ${stats['price_stats']['mean']:.2f} ± ${stats['price_stats']['std']:.2f}"
        )
        print(f"   📊 Volume: {stats['volume_stats']['total']:.2f} total")

    if not clean_results:
        print(f"❌ No venues successfully cleaned")
        sys.exit(1)

    print(f"✅ Cleaned {len(clean_results)} venues")

    # Save clean results
    print(f"\n💾 Saving clean results...")

    results = {
        "date": args.date,
        "canonical_window": canonical_window,
        "clean_results": clean_results,
        "summary": {
            "cleaned_venues": list(clean_results.keys()),
            "total_rows": sum(result["stats"]["final_rows"] for result in clean_results.values()),
            "canonical_duration_minutes": canonical_window["canonical_duration_minutes"],
        },
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results_key = f"analysis/{args.date}/ACD/_cln/clean_results.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved clean results: s3://{args.bucket}/{results_key}")

    # Final summary
    print(f"\n📊 PHASE CLN SUMMARY")
    print("=" * 60)
    print(f"Cleaned venues: {len(clean_results)}")
    print(f"Total rows: {results['summary']['total_rows']}")
    print(f"Canonical duration: {canonical_window['canonical_duration_minutes']:.1f} minutes")

    for venue, result in clean_results.items():
        stats = result["stats"]
        print(f"\n{venue.upper()}:")
        print(f"  Rows: {stats['final_rows']}")
        print(f"  Price: ${stats['price_stats']['mean']:.2f} ± ${stats['price_stats']['std']:.2f}")
        print(f"  Volume: {stats['volume_stats']['total']:.2f}")
        print(f"  Monotonic: {'✅' if stats['is_monotonic'] else '❌'}")

    print(f"\n✅ PHASE CLN COMPLETE - Proceeding to Phase SUM")


if __name__ == "__main__":
    main()
