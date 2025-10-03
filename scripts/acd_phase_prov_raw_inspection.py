#!/usr/bin/env python3
"""
ACD Phase PROV/RAW - Direct S3 Row Inspection

Read-only inspection of raw parquet files to determine if data is trade ticks or resampled/candles.
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
            logging.FileHandler("acd_phase_prov_raw_inspection.log"),
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


def discover_earliest_date(s3_client, bucket: str) -> Optional[str]:
    """Discover the earliest available date under raw_probes/."""
    logger = logging.getLogger(__name__)

    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix="raw_probes/", Delimiter="/")
        if "CommonPrefixes" not in response:
            return None

        dates = []
        for prefix in response["CommonPrefixes"]:
            date_str = prefix["Prefix"].split("/")[1]
            if date_str and len(date_str) == 8:  # YYYYMMDD format
                dates.append(date_str)

        if not dates:
            return None

        earliest_date = min(dates)
        logger.info(f"Earliest date found: {earliest_date}")
        return earliest_date

    except Exception as e:
        logger.error(f"Error discovering earliest date: {e}")
        return None


def list_venue_slices(s3_client, bucket: str, date: str, venue: str) -> List[str]:
    """List available slices for a venue on a specific date."""
    logger = logging.getLogger(__name__)

    try:
        prefix = f"raw_probes/{date}/venue={venue}/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

        slices = []
        if "CommonPrefixes" in response:
            for common_prefix in response["CommonPrefixes"]:
                slice_name = common_prefix["Prefix"].split("=")[-1].strip("/")
                if slice_name:
                    slices.append(slice_name)

        return sorted(slices)

    except Exception as e:
        logger.error(f"Error listing slices for {venue}: {e}")
        return []


def find_parquet_file(
    s3_client, bucket: str, date: str, venue: str, slice_name: str
) -> Optional[str]:
    """Find the first parquet file for a venue/slice."""
    logger = logging.getLogger(__name__)

    try:
        prefix = f"raw_probes/{date}/venue={venue}/slice={slice_name}/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        parquet_files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                if key.endswith(".parquet"):
                    parquet_files.append(key)

        if parquet_files:
            # Return first file by sorted name (deterministic)
            return sorted(parquet_files)[0]

        return None

    except Exception as e:
        logger.error(f"Error finding parquet file for {venue}/{slice_name}: {e}")
        return None


def read_parquet_sample(
    s3_client, bucket: str, s3_key: str, n_rows: int = 100
) -> Optional[pd.DataFrame]:
    """Read first n_rows from a parquet file."""
    logger = logging.getLogger(__name__)

    try:
        parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
        if not parquet_content:
            return None

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()

        # Return first n_rows
        return df.head(n_rows)

    except Exception as e:
        logger.error(f"Error reading parquet file {s3_key}: {e}")
        return None


def analyze_timing_diagnostics(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze timing characteristics of the data."""
    if df.empty or "timestamp" not in df.columns:
        return {"error": "No timestamp data"}

    # Convert to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")

    # Compute deltas in nanoseconds
    time_deltas = df["timestamp"].diff().dropna()
    time_deltas_ns = time_deltas.dt.total_seconds() * 1e9

    # Basic stats
    n_rows = len(df)
    span_seconds = (df["timestamp"].max() - df["timestamp"].min()).total_seconds()

    if len(time_deltas_ns) == 0:
        return {
            "n_rows": n_rows,
            "span_seconds": span_seconds,
            "delta_min": 0,
            "delta_median": 0,
            "delta_max": 0,
            "cv": 0,
            "regular_intervals": True,
        }

    delta_min = float(time_deltas_ns.min())
    delta_median = float(time_deltas_ns.median())
    delta_max = float(time_deltas_ns.max())

    # Coefficient of variation
    cv = float(time_deltas_ns.std() / time_deltas_ns.mean()) if time_deltas_ns.mean() > 0 else 0

    # Regular intervals check (all deltas identical within 1ms tolerance)
    tolerance_ns = 1e6  # 1ms in nanoseconds
    if len(time_deltas_ns) > 1:
        mode_delta = (
            time_deltas_ns.mode().iloc[0]
            if len(time_deltas_ns.mode()) > 0
            else time_deltas_ns.iloc[0]
        )
        within_tolerance = (
            (time_deltas_ns >= mode_delta - tolerance_ns)
            & (time_deltas_ns <= mode_delta + tolerance_ns)
        ).all()
        regular_intervals = within_tolerance
    else:
        regular_intervals = True

    return {
        "n_rows": n_rows,
        "span_seconds": span_seconds,
        "delta_min": delta_min,
        "delta_median": delta_median,
        "delta_max": delta_max,
        "cv": cv,
        "regular_intervals": bool(regular_intervals),
    }


def analyze_id_diagnostics(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze trade ID characteristics."""
    id_fields = ["trade_id", "id", "tradeId", "tradeId"]
    trade_id_present = False
    uniqueness_ratio = 0.0

    for field in id_fields:
        if field in df.columns:
            trade_id_present = True
            unique_count = df[field].nunique()
            total_count = len(df)
            uniqueness_ratio = unique_count / total_count if total_count > 0 else 0
            break

    return {"trade_id_present": trade_id_present, "uniqueness_ratio": uniqueness_ratio}


def detect_candle_fields(df: pd.DataFrame) -> List[str]:
    """Detect if any candle/bar fields are present."""
    candle_fields = ["open", "high", "low", "close", "o", "h", "l", "c", "interval", "window"]
    present_fields = []

    for field in candle_fields:
        if field in df.columns:
            present_fields.append(field)

    return present_fields


def classify_data_type(
    timing_diag: Dict[str, Any], id_diag: Dict[str, Any], candle_fields: List[str]
) -> Tuple[str, str]:
    """Classify data type based on evidence."""

    if "error" in timing_diag:
        return "INDETERMINATE", "Error in timing analysis"

    # Check for candle fields
    if candle_fields:
        return "CANDLES", f"Candle fields present: {candle_fields}"

    # Check for regular intervals
    if timing_diag.get("regular_intervals", False):
        return "LIKELY_CANDLES", "Regular intervals detected (suggests resampling)"

    # Check for trade ID presence and uniqueness
    if id_diag.get("trade_id_present", False) and id_diag.get("uniqueness_ratio", 0) > 0.8:
        return "TRADE_TICKS", "Trade ID present with high uniqueness ratio"

    # Check for irregular timing
    if timing_diag.get("cv", 0) > 0.1:
        return "LIKELY_TICKS", "Irregular timing intervals (CV > 0.1)"

    # Default
    return "INDETERMINATE", "Insufficient evidence for classification"


def inspect_venue_data(s3_client, bucket: str, date: str, venue: str) -> Dict[str, Any]:
    """Inspect data for a specific venue."""
    logger = logging.getLogger(__name__)

    result = {
        "venue": venue,
        "date": date,
        "status": "failed",
        "s3_key": None,
        "sample_data": None,
        "timing_diagnostics": None,
        "id_diagnostics": None,
        "candle_fields": [],
        "classification": "INDETERMINATE",
        "evidence": "No data found",
    }

    # List available slices
    slices = list_venue_slices(s3_client, bucket, date, venue)
    if not slices:
        result["evidence"] = "No slices found"
        return result

    # Use first slice
    slice_name = slices[0]

    # Find parquet file
    s3_key = find_parquet_file(s3_client, bucket, date, venue, slice_name)
    if not s3_key:
        result["evidence"] = "No parquet file found"
        return result

    result["s3_key"] = s3_key

    # Read sample data
    df = read_parquet_sample(s3_client, bucket, s3_key, 100)
    if df is None:
        result["evidence"] = "Could not read parquet file"
        return result

    # Extract requested columns only
    requested_columns = ["timestamp", "price", "volume", "trade_id", "id", "side", "venue"]
    available_columns = [col for col in requested_columns if col in df.columns]

    if available_columns:
        sample_df = df[available_columns].head(100)
        # Convert timestamps to strings for JSON serialization
        if "timestamp" in sample_df.columns:
            sample_df = sample_df.copy()
            sample_df["timestamp"] = sample_df["timestamp"].astype(str)
        result["sample_data"] = sample_df.to_dict("records")
    else:
        sample_df = df.head(100)
        # Convert timestamps to strings for JSON serialization
        if "timestamp" in sample_df.columns:
            sample_df = sample_df.copy()
            sample_df["timestamp"] = sample_df["timestamp"].astype(str)
        result["sample_data"] = sample_df.to_dict("records")

    # Analyze timing
    timing_diag = analyze_timing_diagnostics(df)
    result["timing_diagnostics"] = timing_diag

    # Analyze IDs
    id_diag = analyze_id_diagnostics(df)
    result["id_diagnostics"] = id_diag

    # Detect candle fields
    candle_fields = detect_candle_fields(df)
    result["candle_fields"] = candle_fields

    # Classify
    classification, evidence = classify_data_type(timing_diag, id_diag, candle_fields)
    result["classification"] = classification
    result["evidence"] = evidence
    result["status"] = "success"

    return result


def main():
    """Main inspection function."""
    parser = argparse.ArgumentParser(description="ACD Phase PROV/RAW - Direct S3 Row Inspection")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE PROV/RAW - DIRECT S3 ROW INSPECTION")
    print("=" * 80)

    # Discover earliest date
    print(f"\n🔍 Discovering earliest available date...")
    earliest_date = discover_earliest_date(s3_client, args.bucket)

    if not earliest_date:
        print(f"❌ No data found under raw_probes/")
        sys.exit(1)

    print(f"✅ Earliest date: {earliest_date}")

    # Convert to readable format
    date_readable = f"{earliest_date[:4]}-{earliest_date[4:6]}-{earliest_date[6:8]}"

    # Inspect each venue
    venues = ["binance", "kraken", "okx", "coinbase", "bybit"]
    results = {}

    for venue in venues:
        print(f"\n🔍 Inspecting {venue.upper()}...")

        try:
            result = inspect_venue_data(s3_client, args.bucket, earliest_date, venue)
            results[venue] = result

            if result["status"] == "success":
                print(f"   ✅ {result['classification']}: {result['evidence']}")
            else:
                print(f"   ❌ {result['evidence']}")

        except Exception as e:
            print(f"   ❌ Error inspecting {venue}: {e}")
            results[venue] = {"venue": venue, "status": "error", "evidence": f"Error: {e}"}

    # Print detailed results
    print(f"\n" + "=" * 80)
    print("📊 DETAILED INSPECTION RESULTS")
    print("=" * 80)

    for venue, result in results.items():
        if result["status"] != "success":
            continue

        print(f"\nVenue={venue.upper()} | Date={date_readable} | File={result['s3_key']}")
        print("-" * 80)

        # Sample data
        if result["sample_data"]:
            print(f"Head(100):")
            df_sample = pd.DataFrame(result["sample_data"])
            print(df_sample.to_string(index=False, max_rows=10))
            if len(df_sample) > 10:
                print(f"... and {len(df_sample) - 10} more rows")

        # Timing diagnostics
        timing = result["timing_diagnostics"]
        if timing and "error" not in timing:
            print(f"\nTiming diagnostics:")
            print(f"  n_rows: {timing['n_rows']}")
            print(f"  span_seconds: {timing['span_seconds']:.1f}")
            print(f"  delta_min: {timing['delta_min']:.0f} ns")
            print(f"  delta_median: {timing['delta_median']:.0f} ns")
            print(f"  delta_max: {timing['delta_max']:.0f} ns")
            print(f"  CV: {timing['cv']:.6f}")
            print(f"  regular_intervals: {timing['regular_intervals']}")

        # ID diagnostics
        id_diag = result["id_diagnostics"]
        if id_diag:
            print(f"\nID diagnostics:")
            print(f"  trade_id_present: {id_diag['trade_id_present']}")
            print(f"  uniqueness_ratio: {id_diag['uniqueness_ratio']:.3f}")

        # Schema flags
        candle_fields = result["candle_fields"]
        print(f"\nSchema flags:")
        print(f"  candle_fields_present: {candle_fields if candle_fields else 'None'}")

        # Verdict
        print(f"\nVerdict: {result['classification']}")
        print(f"Evidence: {result['evidence']}")

    # Summary
    print(f"\n" + "=" * 80)
    print("📋 CROSS-VENUE SUMMARY")
    print("=" * 80)

    classifications = {}
    for venue, result in results.items():
        if result["status"] == "success":
            classifications[venue] = result["classification"]

    summary_parts = []
    for venue, classification in classifications.items():
        if classification == "TRADE_TICKS":
            summary_parts.append(f"{venue.upper()} irregular")
        elif classification == "LIKELY_TICKS":
            summary_parts.append(f"{venue.upper()} likely irregular")
        elif classification in ["CANDLES", "LIKELY_CANDLES"]:
            summary_parts.append(f"{venue.upper()} regular/resampled")
        else:
            summary_parts.append(f"{venue.upper()} indeterminate")

    if summary_parts:
        summary = "; ".join(summary_parts) + "."
        print(f"Summary: {summary}")
    else:
        print("Summary: No successful inspections completed.")

    # Save results
    print(f"\n💾 Saving inspection results...")

    inspection_results = {
        "date": earliest_date,
        "date_readable": date_readable,
        "venues": results,
        "summary": summary if summary_parts else "No successful inspections",
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    results_key = f"analysis/{earliest_date}/ACD/_prov/raw_inspection_results.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=results_key,
        Body=json.dumps(inspection_results, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved results: s3://{args.bucket}/{results_key}")


if __name__ == "__main__":
    main()
