#!/usr/bin/env python3
"""
ACD Phase Restricted - Time Range Analysis

Analyzes time ranges for tick-level venues to understand overlap issues.
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
            logging.FileHandler("acd_phase_restricted_time_analysis.log"),
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


def load_venue_data(s3_client, bucket: str, date: str, venue: str) -> Optional[pd.DataFrame]:
    """Load data for a specific venue."""
    logger = logging.getLogger(__name__)

    # Try raw_probes first
    prefix = f"raw_probes/{date}/venue={venue}/"
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")
        if "CommonPrefixes" not in response:
            return None

        slices = []
        for common_prefix in response["CommonPrefixes"]:
            slice_name = common_prefix["Prefix"].split("=")[-1].strip("/")
            if slice_name:
                slices.append(slice_name)

        if not slices:
            return None

        # Use first slice
        slice_name = sorted(slices)[0]
        s3_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"

    except Exception as e:
        logger.error(f"Error listing slices for {venue}: {e}")
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

        logger.info(f"Loaded {venue} from {s3_key}: {len(df)} rows")
        return df

    except Exception as e:
        logger.error(f"Error loading {venue} from {s3_key}: {e}")
        return None


def analyze_time_ranges(venues_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Analyze time ranges for all venues."""
    logger = logging.getLogger(__name__)

    time_analysis = {"venues": {}, "overlap_analysis": {}, "recommendations": []}

    # Analyze each venue
    for venue, df in venues_data.items():
        if df.empty:
            continue

        start_time = df["timestamp"].min()
        end_time = df["timestamp"].max()
        duration = (end_time - start_time).total_seconds()

        time_analysis["venues"][venue] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "n_rows": len(df),
            "timezone": str(start_time.tz),
        }

        logger.info(f"{venue}: {start_time} to {end_time} ({duration:.1f}s, {len(df)} rows)")

    # Find overlaps
    venues = list(venues_data.keys())
    if len(venues) >= 2:
        for i, venue1 in enumerate(venues):
            for j, venue2 in enumerate(venues):
                if i >= j:
                    continue

                df1 = venues_data[venue1]
                df2 = venues_data[venue2]

                if df1.empty or df2.empty:
                    continue

                start1 = df1["timestamp"].min()
                end1 = df1["timestamp"].max()
                start2 = df2["timestamp"].min()
                end2 = df2["timestamp"].max()

                # Find overlap
                overlap_start = max(start1, start2)
                overlap_end = min(end1, end2)

                if overlap_start < overlap_end:
                    overlap_duration = (overlap_end - overlap_start).total_seconds()
                    overlap_percentage = (
                        overlap_duration
                        / min((end1 - start1).total_seconds(), (end2 - start2).total_seconds())
                    ) * 100

                    time_analysis["overlap_analysis"][f"{venue1}_vs_{venue2}"] = {
                        "overlap_start": overlap_start.isoformat(),
                        "overlap_end": overlap_end.isoformat(),
                        "overlap_duration_seconds": overlap_duration,
                        "overlap_percentage": overlap_percentage,
                    }

                    logger.info(
                        f"{venue1} vs {venue2}: {overlap_duration:.1f}s overlap ({overlap_percentage:.1f}%)"
                    )
                else:
                    time_analysis["overlap_analysis"][f"{venue1}_vs_{venue2}"] = {
                        "overlap_start": None,
                        "overlap_end": None,
                        "overlap_duration_seconds": 0,
                        "overlap_percentage": 0,
                    }

                    logger.info(f"{venue1} vs {venue2}: No overlap")

    # Generate recommendations
    if not time_analysis["overlap_analysis"]:
        time_analysis["recommendations"].append(
            "No overlapping time windows found - backfill required"
        )
    else:
        max_overlap = max(
            (
                overlap["overlap_duration_seconds"]
                for overlap in time_analysis["overlap_analysis"].values()
            ),
            default=0,
        )

        if max_overlap < 60:  # Less than 1 minute
            time_analysis["recommendations"].append(
                "Very short overlaps - consider backfill for longer windows"
            )
        elif max_overlap < 300:  # Less than 5 minutes
            time_analysis["recommendations"].append(
                "Short overlaps - may be sufficient for initial analysis"
            )
        else:
            time_analysis["recommendations"].append("Adequate overlaps found for analysis")

    return time_analysis


def main():
    """Main time analysis function."""
    parser = argparse.ArgumentParser(description="ACD Phase Restricted - Time Range Analysis")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE RESTRICTED - TIME RANGE ANALYSIS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")
    print(f"🎯 Analyzing tick-level venues: Binance, Kraken, Coinbase")

    # Load tick-level venues
    print(f"\n🔍 Loading tick-level venues...")

    tick_venues = ["binance", "kraken", "coinbase"]
    venues_data = {}

    for venue in tick_venues:
        print(f"\n📊 Loading {venue.upper()}...")

        df = load_venue_data(s3_client, args.bucket, args.date, venue)
        if df is None:
            print(f"   ❌ No data found for {venue}")
            continue

        # Validate tick timing
        time_deltas = df["timestamp"].diff().dropna()
        time_deltas_ns = time_deltas.dt.total_seconds() * 1e9
        cv = float(time_deltas_ns.std() / time_deltas_ns.mean()) if time_deltas_ns.mean() > 0 else 0

        if cv > 1.0:
            venues_data[venue] = df
            print(f"   ✅ Tick-level data confirmed (CV={cv:.3f})")
        else:
            print(f"   ❌ Synthetic data detected (CV={cv:.3f}) - excluding")

    if not venues_data:
        print(f"❌ No tick-level venues found")
        sys.exit(1)

    print(f"✅ Loaded {len(venues_data)} tick-level venues")

    # Analyze time ranges
    print(f"\n🔍 Analyzing time ranges...")

    time_analysis = analyze_time_ranges(venues_data)

    # Print detailed analysis
    print(f"\n📊 TIME RANGE ANALYSIS")
    print("=" * 60)

    for venue, data in time_analysis["venues"].items():
        print(f"\n{venue.upper()}:")
        print(f"  Start: {data['start_time']}")
        print(f"  End: {data['end_time']}")
        print(f"  Duration: {data['duration_seconds']:.1f} seconds")
        print(f"  Rows: {data['n_rows']}")
        print(f"  Timezone: {data['timezone']}")

    print(f"\n📊 OVERLAP ANALYSIS")
    print("=" * 60)

    for pair, overlap in time_analysis["overlap_analysis"].items():
        if overlap["overlap_duration_seconds"] > 0:
            print(f"\n{pair.upper()}:")
            print(f"  Overlap: {overlap['overlap_start']} to {overlap['overlap_end']}")
            print(f"  Duration: {overlap['overlap_duration_seconds']:.1f} seconds")
            print(f"  Percentage: {overlap['overlap_percentage']:.1f}%")
        else:
            print(f"\n{pair.upper()}: No overlap")

    print(f"\n📋 RECOMMENDATIONS")
    print("=" * 60)

    for recommendation in time_analysis["recommendations"]:
        print(f"• {recommendation}")

    # Save results
    print(f"\n💾 Saving time analysis results...")

    results = {
        "date": args.date,
        "time_analysis": time_analysis,
        "summary": {
            "venues_analyzed": len(venues_data),
            "venues_with_data": list(venues_data.keys()),
            "max_overlap_seconds": max(
                (
                    overlap["overlap_duration_seconds"]
                    for overlap in time_analysis["overlap_analysis"].values()
                ),
                default=0,
            ),
            "recommendations": time_analysis["recommendations"],
        },
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results_key = f"analysis/{args.date}/ACD/_restricted/time_analysis_results.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(results, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")

    # Final summary
    print(f"\n📊 TIME ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Venues analyzed: {len(venues_data)}")
    print(f"Max overlap: {results['summary']['max_overlap_seconds']:.1f} seconds")
    print(f"Recommendations: {len(time_analysis['recommendations'])}")


if __name__ == "__main__":
    main()
