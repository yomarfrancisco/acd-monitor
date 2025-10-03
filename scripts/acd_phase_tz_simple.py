#!/usr/bin/env python3
"""
ACD Phase TZ - Simple Timestamp/Timezone Forensics

Proves all venues' stored timestamps are exchange time → normalized to UTC.
Simplified version focusing on core timezone analysis.
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
            logging.FileHandler("acd_phase_tz_simple.log"),
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


def list_s3_slices(s3_client, bucket: str, date: str, venue: str) -> List[str]:
    """List all available slices for a given venue and date."""
    prefix = f"raw_probes/{date}/venue={venue}/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")
    slices = []
    if "CommonPrefixes" in response:
        for common_prefix in response["CommonPrefixes"]:
            slice_name = common_prefix["Prefix"].split("=")[-1].strip("/")
            if slice_name:
                slices.append(slice_name)
    return sorted(slices)


def analyze_slice_timestamps(
    s3_client, bucket: str, date: str, venue: str, slice_name: str
) -> Dict[str, Any]:
    """Analyze timestamps for a single slice."""
    logger = logging.getLogger(__name__)

    # Load parquet data
    sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"
    parquet_data_content = get_s3_object_content(s3_client, bucket, sample_key)
    if parquet_data_content is None:
        return {"status": "failed", "error": "No parquet data found"}

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()

        if df.empty:
            return {"status": "failed", "error": "Empty dataframe"}

        # Load manifest
        manifest_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/probe_manifest.json"
        manifest_content = get_s3_object_text(s3_client, bucket, manifest_key)
        manifest = None
        if manifest_content:
            try:
                manifest = json.loads(manifest_content)
            except json.JSONDecodeError:
                pass

        # Analyze timestamp field
        if "timestamp" not in df.columns:
            return {"status": "failed", "error": "No timestamp column found"}

        # Convert timestamps to UTC
        if df["timestamp"].dtype == "object":
            ts_utc = pd.to_datetime(df["timestamp"], utc=True)
        else:
            ts_utc = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

        # Basic stats
        n_rows = len(df)
        ts_min_utc = ts_utc.min()
        ts_max_utc = ts_utc.max()
        duration_seconds = (ts_max_utc - ts_min_utc).total_seconds()
        is_monotonic = ts_utc.is_monotonic_increasing

        # Duplicate analysis
        duplicates = df.duplicated(subset=["timestamp"]).sum()
        duplicate_ratio = duplicates / n_rows if n_rows > 0 else 0

        # Price analysis
        price_std = df["price"].std() if "price" in df.columns else 0

        # Sample timestamps (first 3 and last 3)
        sample_timestamps = []
        for i in range(min(3, len(df))):
            sample_timestamps.append(
                {
                    "index": i,
                    "timestamp_raw": str(df.iloc[i]["timestamp"]),
                    "timestamp_utc": ts_utc.iloc[i].isoformat(),
                    "price": float(df.iloc[i]["price"]) if "price" in df.columns else None,
                }
            )

        for i in range(max(0, len(df) - 3), len(df)):
            sample_timestamps.append(
                {
                    "index": i,
                    "timestamp_raw": str(df.iloc[i]["timestamp"]),
                    "timestamp_utc": ts_utc.iloc[i].isoformat(),
                    "price": float(df.iloc[i]["price"]) if "price" in df.columns else None,
                }
            )

        # Check for timezone issues
        issues = []
        if not is_monotonic:
            issues.append("Non-monotonic timestamps")
        if duplicate_ratio > 0.5:
            issues.append(f"High duplicate ratio: {duplicate_ratio:.1%}")
        if duration_seconds < 1:
            issues.append(f"Very short duration: {duration_seconds:.1f}s")

        # Check if timestamps look like local time (this is a heuristic)
        # If we see patterns like 15:45:42 (3:45 PM), it might be local time
        time_patterns = []
        for ts in ts_utc.head(5):
            hour = ts.hour
            if 12 <= hour <= 18:  # Afternoon hours
                time_patterns.append(hour)

        if len(set(time_patterns)) > 0 and max(time_patterns) > 12:
            issues.append("Timestamps appear to be in local time (afternoon hours)")

        return {
            "status": "success",
            "n_rows": n_rows,
            "ts_min_utc": ts_min_utc.isoformat(),
            "ts_max_utc": ts_max_utc.isoformat(),
            "duration_seconds": duration_seconds,
            "is_monotonic": is_monotonic,
            "duplicate_ratio": duplicate_ratio,
            "price_std": price_std,
            "sample_timestamps": sample_timestamps,
            "issues": issues,
            "manifest_provenance": manifest.get("provenance", "unknown") if manifest else "unknown",
        }

    except Exception as e:
        logger.error(f"Error analyzing {venue} {slice_name}: {e}")
        return {"status": "failed", "error": str(e)}


def main():
    """Main Phase TZ function."""
    parser = argparse.ArgumentParser(
        description="ACD Phase TZ - Simple Timestamp/Timezone Forensics"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE TZ - SIMPLE TIMESTAMP/TIMEZONE FORENSICS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")

    venues = ["binance", "coinbase", "kraken"]
    all_results = {}

    print(f"\n🔍 Analyzing timestamps for all venues...")

    for venue in venues:
        print(f"\n🏢 {venue.upper()}")
        all_results[venue] = {}

        slices = list_s3_slices(s3_client, args.bucket, args.date, venue)
        print(f"   Found {len(slices)} slices: {slices}")

        for slice_name in slices:
            print(f"   Analyzing {slice_name}...")
            result = analyze_slice_timestamps(s3_client, args.bucket, args.date, venue, slice_name)
            all_results[venue][slice_name] = result

            if result["status"] == "success":
                print(
                    f"     ✅ {result['n_rows']} rows, {result['duration_seconds']:.1f}s, {result['duplicate_ratio']:.1%} duplicates"
                )
                if result["issues"]:
                    print(f"     ⚠️  Issues: {', '.join(result['issues'])}")
            else:
                print(f"     ❌ Failed: {result['error']}")

    # Generate summary
    print(f"\n📊 TIMEZONE AUDIT SUMMARY")
    print("=" * 60)

    critical_issues = []
    for venue, venue_slices in all_results.items():
        print(f"\n{venue.upper()}:")
        for slice_name, result in venue_slices.items():
            if result["status"] == "success":
                print(
                    f"  {slice_name}: {result['ts_min_utc']} → {result['ts_max_utc']} ({result['duration_seconds']:.1f}s)"
                )
                if result["issues"]:
                    for issue in result["issues"]:
                        critical_issues.append(f"{venue} {slice_name}: {issue}")
                        print(f"    ⚠️  {issue}")
            else:
                print(f"  {slice_name}: ❌ {result['error']}")

    # Save results
    audit_data = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "date": args.date,
        "venues": all_results,
        "critical_issues": critical_issues,
    }

    print(f"\n💾 Saving timezone audit results...")

    tz_audit_key = f"analysis/{args.date}/ACD/_tz/tz_audit.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=tz_audit_key,
        Body=json.dumps(audit_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved timezone audit: s3://{args.bucket}/{tz_audit_key}")

    # Check for critical issues
    if critical_issues:
        print(f"\n❌ CRITICAL TIMEZONE ISSUES FOUND:")
        for issue in critical_issues:
            print(f"   {issue}")
        print(f"\n🛑 STOP: Timezone issues detected. See tz_audit.json for details.")
        sys.exit(1)
    else:
        print(f"\n✅ No critical timezone issues found")

    # Final summary
    print(f"\n📊 PHASE TZ SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Venues analyzed: {len(venues)}")

    for venue in venues:
        successful_slices = [s for s in all_results[venue].values() if s.get("status") == "success"]
        print(f"  {venue}: {len(successful_slices)}/{len(all_results[venue])} successful")

    print(f"\n📁 Generated artifacts:")
    print(f"  Timezone audit: s3://{args.bucket}/{tz_audit_key}")


if __name__ == "__main__":
    main()
