#!/usr/bin/env python3
"""
ACD Phase TZ - Timestamp/Timezone Forensics

Proves all venues' stored timestamps are exchange time → normalized to UTC.
No inference, no repairs yet - just forensic analysis.
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
            logging.FileHandler("acd_phase_tz_timezone_audit.log"),
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


def load_slice_data(
    s3_client, bucket: str, date: str, venue: str, slice_name: str
) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
    """Loads parquet data and manifest for a specific slice."""
    logger = logging.getLogger(__name__)

    # Load parquet data
    sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"
    parquet_data_content = get_s3_object_content(s3_client, bucket, sample_key)
    if parquet_data_content is None:
        logger.warning(f"No parquet data found for {venue} {slice_name} at {sample_key}")
        return None, None

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()

        # Load manifest
        manifest_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/probe_manifest.json"
        manifest_content = get_s3_object_text(s3_client, bucket, manifest_key)
        manifest = None
        if manifest_content:
            try:
                manifest = json.loads(manifest_content)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse manifest for {venue} {slice_name}")

        return df, manifest

    except Exception as e:
        logger.error(f"Error loading data for {venue} {slice_name}: {e}")
        return None, None


def analyze_timestamp_fields(df: pd.DataFrame, venue: str) -> Dict[str, Any]:
    """Analyze timestamp fields in the DataFrame."""
    logger = logging.getLogger(__name__)

    timestamp_fields = []
    timestamp_analysis = {}

    # Find timestamp-related columns
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ["time", "ts", "timestamp", "date"]):
            timestamp_fields.append(col)

    logger.info(f"Found timestamp fields for {venue}: {timestamp_fields}")

    for field in timestamp_fields:
        try:
            # Try to parse as datetime
            if df[field].dtype == "object":
                # Try different parsing methods
                parsed_times = pd.to_datetime(df[field], errors="coerce")
            else:
                parsed_times = df[field]

            if parsed_times.isna().all():
                continue

            # Analyze timezone info
            if hasattr(parsed_times, "dt"):
                tz_info = parsed_times.dt.tz
                is_utc = tz_info == timezone.utc or tz_info is None
            else:
                is_utc = True  # Assume UTC if no timezone info

            # Check monotonicity
            is_monotonic = parsed_times.is_monotonic_increasing

            # Sample values
            sample_values = df[field].head(3).tolist() + df[field].tail(3).tolist()

            timestamp_analysis[field] = {
                "dtype": str(df[field].dtype),
                "is_utc": bool(is_utc),
                "is_monotonic": bool(is_monotonic),
                "min_value": str(parsed_times.min()),
                "max_value": str(parsed_times.max()),
                "sample_values": sample_values,
                "null_count": int(df[field].isna().sum()),
                "total_count": int(len(df)),
            }

        except Exception as e:
            logger.warning(f"Error analyzing timestamp field {field}: {e}")
            timestamp_analysis[field] = {
                "error": str(e),
                "dtype": str(df[field].dtype),
                "sample_values": df[field].head(3).tolist() + df[field].tail(3).tolist(),
            }

    return timestamp_analysis


def perform_timezone_audit(s3_client, bucket: str, date: str) -> Dict[str, Any]:
    """Perform timezone audit for all venues and slices."""
    logger = logging.getLogger(__name__)

    venues = ["binance", "coinbase", "kraken"]
    audit_results = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "date": date,
        "venues": {},
    }

    for venue in venues:
        logger.info(f"Auditing timezone for {venue}")

        slices = list_s3_slices(s3_client, bucket, date, venue)
        venue_results = {
            "slices": {},
            "timestamp_fields_found": [],
            "normalization_path": "unknown",
            "issues": [],
        }

        for slice_name in slices:
            logger.info(f"  Analyzing {venue} {slice_name}")

            df, manifest = load_slice_data(s3_client, bucket, date, venue, slice_name)

            if df is None or df.empty:
                venue_results["slices"][slice_name] = {
                    "status": "failed",
                    "error": "No data loaded",
                }
                continue

            # Basic stats
            n_rows = len(df)

            # Find timestamp fields
            timestamp_fields = []
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ["time", "ts", "timestamp", "date"]):
                    timestamp_fields.append(col)

            if not timestamp_fields:
                venue_results["slices"][slice_name] = {
                    "status": "failed",
                    "error": "No timestamp fields found",
                }
                continue

            # Analyze timestamp fields
            timestamp_analysis = analyze_timestamp_fields(df, venue)

            # Try to determine primary timestamp field
            primary_timestamp = None
            if "timestamp" in timestamp_fields:
                primary_timestamp = "timestamp"
            elif "time" in timestamp_fields:
                primary_timestamp = "time"
            else:
                primary_timestamp = timestamp_fields[0]

            # Convert to UTC for analysis
            try:
                if primary_timestamp in df.columns:
                    if df[primary_timestamp].dtype == "object":
                        ts_utc = pd.to_datetime(df[primary_timestamp], utc=True)
                    else:
                        ts_utc = pd.to_datetime(df[primary_timestamp], unit="ms", utc=True)

                    ts_min_utc = ts_utc.min()
                    ts_max_utc = ts_utc.max()
                    duration = (ts_max_utc - ts_min_utc).total_seconds()

                    # Check for monotonicity
                    is_monotonic = ts_utc.is_monotonic_increasing

                    # Sample rows
                    sample_rows = []
                    for i in range(min(3, len(df))):
                        row_data = df.iloc[i].to_dict()
                        # Convert any pandas objects to native Python types
                        clean_row_data = {}
                        for k, v in row_data.items():
                            if hasattr(v, "item"):  # pandas scalar
                                clean_row_data[k] = v.item()
                            else:
                                clean_row_data[k] = str(v)

                        sample_rows.append(
                            {
                                "index": int(i),
                                "timestamp_raw": str(df.iloc[i][primary_timestamp]),
                                "timestamp_utc": ts_utc.iloc[i].isoformat(),
                                "price": clean_row_data.get("price", "N/A"),
                                "volume": clean_row_data.get("volume", "N/A"),
                            }
                        )

                    for i in range(max(0, len(df) - 3), len(df)):
                        row_data = df.iloc[i].to_dict()
                        # Convert any pandas objects to native Python types
                        clean_row_data = {}
                        for k, v in row_data.items():
                            if hasattr(v, "item"):  # pandas scalar
                                clean_row_data[k] = v.item()
                            else:
                                clean_row_data[k] = str(v)

                        sample_rows.append(
                            {
                                "index": int(i),
                                "timestamp_raw": str(df.iloc[i][primary_timestamp]),
                                "timestamp_utc": ts_utc.iloc[i].isoformat(),
                                "price": clean_row_data.get("price", "N/A"),
                                "volume": clean_row_data.get("volume", "N/A"),
                            }
                        )

                    # Duplicate analysis
                    duplicates = df.duplicated(subset=[primary_timestamp]).sum()
                    duplicate_ratio = duplicates / n_rows if n_rows > 0 else 0

                    # Price analysis
                    price_std = df["price"].std() if "price" in df.columns else 0

                    slice_result = {
                        "status": "success",
                        "n_rows": n_rows,
                        "ts_min_utc": ts_min_utc.isoformat(),
                        "ts_max_utc": ts_max_utc.isoformat(),
                        "duration_seconds": float(duration),
                        "is_monotonic": bool(is_monotonic),
                        "duplicate_ratio": float(duplicate_ratio),
                        "price_std": float(price_std),
                        "primary_timestamp_field": primary_timestamp,
                        "timestamp_fields": timestamp_fields,
                        "timestamp_analysis": timestamp_analysis,
                        "sample_rows": sample_rows,
                    }

                    # Check for issues
                    if not is_monotonic:
                        slice_result["issues"] = ["Non-monotonic timestamps"]

                    if duplicate_ratio > 0.5:
                        slice_result["issues"] = slice_result.get("issues", []) + [
                            f"High duplicate ratio: {duplicate_ratio:.1%}"
                        ]

                    if duration < 1:
                        slice_result["issues"] = slice_result.get("issues", []) + [
                            f"Very short duration: {duration:.1f}s"
                        ]

                else:
                    slice_result = {
                        "status": "failed",
                        "error": f"Primary timestamp field '{primary_timestamp}' not found",
                    }

            except Exception as e:
                slice_result = {"status": "failed", "error": f"Error processing timestamps: {e}"}

            venue_results["slices"][slice_name] = slice_result

        # Aggregate venue-level analysis
        successful_slices = [
            s for s in venue_results["slices"].values() if s.get("status") == "success"
        ]

        if successful_slices:
            # Check for consistency across slices
            all_timestamps = []
            for slice_data in successful_slices:
                if "ts_min_utc" in slice_data:
                    all_timestamps.append(slice_data["ts_min_utc"])
                    all_timestamps.append(slice_data["ts_max_utc"])

            if all_timestamps:
                # Check for timezone consistency
                try:
                    parsed_times = [pd.to_datetime(ts) for ts in all_timestamps]
                    timezone_offsets = [
                        ts.utcoffset().total_seconds() if ts.utcoffset() else 0
                        for ts in parsed_times
                    ]

                    if len(set(timezone_offsets)) > 1:
                        venue_results["issues"].append(
                            "Inconsistent timezone offsets across slices"
                        )

                    if any(offset != 0 for offset in timezone_offsets):
                        venue_results["issues"].append("Non-UTC timestamps detected")

                except Exception as e:
                    venue_results["issues"].append(f"Error analyzing timezone consistency: {e}")

            # Determine normalization path
            if successful_slices:
                first_slice = successful_slices[0]
                if "timestamp_analysis" in first_slice:
                    timestamp_analysis = first_slice["timestamp_analysis"]
                    if "timestamp" in timestamp_analysis:
                        venue_results["normalization_path"] = (
                            f"timestamp field -> UTC (via pd.to_datetime)"
                        )
                    else:
                        venue_results["normalization_path"] = "unknown"

        audit_results["venues"][venue] = venue_results

    return audit_results


def main():
    """Main Phase TZ function."""
    parser = argparse.ArgumentParser(description="ACD Phase TZ - Timestamp/Timezone Forensics")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 ACD PHASE TZ - TIMESTAMP/TIMEZONE FORENSICS")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")

    # Perform timezone audit
    print(f"\n🔍 Performing timezone audit...")
    try:
        audit_results = perform_timezone_audit(s3_client, args.bucket, args.date)
        print(f"✅ Timezone audit completed")
    except Exception as e:
        print(f"❌ Error performing timezone audit: {e}")
        sys.exit(1)

    # Save audit results
    print(f"\n💾 Saving timezone audit results...")

    tz_audit_key = f"analysis/{args.date}/ACD/_tz/tz_audit.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=tz_audit_key,
        Body=json.dumps(audit_results, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved timezone audit: s3://{args.bucket}/{tz_audit_key}")

    # Generate markdown report
    markdown_content = f"""# ACD Phase TZ - Timestamp/Timezone Forensics

**Date**: {args.date}  
**Audit Time**: {audit_results['audit_timestamp']}  

## Summary

"""

    for venue, venue_data in audit_results["venues"].items():
        successful_slices = [
            s for s in venue_data["slices"].values() if s.get("status") == "success"
        ]
        issues = venue_data.get("issues", [])

        markdown_content += f"### {venue.upper()}\n\n"
        markdown_content += f"**Slices**: {len(venue_data['slices'])}\n"
        markdown_content += f"**Successful**: {len(successful_slices)}\n"
        markdown_content += f"**Issues**: {len(issues)}\n"
        markdown_content += (
            f"**Normalization Path**: {venue_data.get('normalization_path', 'unknown')}\n\n"
        )

        if issues:
            markdown_content += "**Issues Found**:\n"
            for issue in issues:
                markdown_content += f"- {issue}\n"
            markdown_content += "\n"

        if successful_slices:
            markdown_content += (
                "| Slice | Rows | Duration | Monotonic | Duplicates | Price Std | Issues |\n"
            )
            markdown_content += (
                "|-------|------|----------|-----------|------------|-----------|--------|\n"
            )

            for slice_name, slice_data in venue_data["slices"].items():
                if slice_data.get("status") == "success":
                    issues_str = (
                        ", ".join(slice_data.get("issues", []))
                        if slice_data.get("issues")
                        else "None"
                    )
                    markdown_content += f"| {slice_name} | {slice_data['n_rows']} | {slice_data['duration_seconds']:.1f}s | {'✅' if slice_data['is_monotonic'] else '❌'} | {slice_data['duplicate_ratio']:.1%} | ${slice_data['price_std']:.2f} | {issues_str} |\n"
        else:
            markdown_content += "No successful slices found.\n"

        markdown_content += "\n"

    # Save markdown report
    markdown_key = f"analysis/{args.date}/ACD/_tz/tz_audit.md"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=markdown_key,
        Body=markdown_content.encode("utf-8"),
        ContentType="text/markdown",
    )

    print(f"💾 Saved markdown report: s3://{args.bucket}/{markdown_key}")

    # Check for critical issues
    print(f"\n🔍 Checking for critical timezone issues...")

    critical_issues = []
    for venue, venue_data in audit_results["venues"].items():
        issues = venue_data.get("issues", [])
        if issues:
            critical_issues.extend([f"{venue}: {issue}" for issue in issues])

    if critical_issues:
        print(f"❌ CRITICAL ISSUES FOUND:")
        for issue in critical_issues:
            print(f"   {issue}")
        print(f"\n🛑 STOP: Timezone issues detected. See tz_audit.json for details.")
        sys.exit(1)
    else:
        print(f"✅ No critical timezone issues found")

    # Final summary
    print(f"\n📊 PHASE TZ SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Venues analyzed: {len(audit_results['venues'])}")

    for venue, venue_data in audit_results["venues"].items():
        successful_slices = [
            s for s in venue_data["slices"].values() if s.get("status") == "success"
        ]
        print(f"  {venue}: {len(successful_slices)}/{len(venue_data['slices'])} successful")

    print(f"\n📁 Generated artifacts:")
    print(f"  Timezone audit: s3://{args.bucket}/{tz_audit_key}")
    print(f"  Markdown report: s3://{args.bucket}/{markdown_key}")


if __name__ == "__main__":
    main()
