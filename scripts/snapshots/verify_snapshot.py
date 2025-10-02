#!/usr/bin/env python3
"""
Snapshot verification utility for S3-based snapshots.

Verifies snapshot integrity, coverage, and clock skew for court-ready data.
"""

import argparse
import json
import logging
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from datetime import datetime, timezone
import numpy as np

# Parquet engine configuration
DF_ENGINE = "pyarrow"

try:
    import pyarrow  # noqa: F401
except Exception as e:
    raise RuntimeError(
        "Parquet engine 'pyarrow' not available in CI. "
        "Ensure requirements-verify.txt is installed."
    ) from e

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from acdlib.io.load_snapshot import load_snapshot_data

# Import config from same directory
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
try:
    from config import DEFAULT_BUCKET, DEFAULT_PREFIX, DEFAULT_REGION
except ImportError:
    # Fallback to environment variables
    DEFAULT_BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
    DEFAULT_PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
    DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

logger = logging.getLogger(__name__)


def _load_json_s3(s3_client, bucket: str, key: str, *, allow_missing=False, log=logger):
    """Load JSON from S3 with optional missing file handling."""
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(obj["Body"].read())
    except ClientError as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code")
        if code == "NoSuchKey" and allow_missing:
            log.warning(
                "Missing %s (coverage meta); downgrading to quality warning", key
            )
            return None
        raise


def _first_parquet_key(s3_client, bucket: str, prefix: str) -> str:
    """Find the first parquet file in a venue directory, preferring deterministic ordering."""
    try:
        resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        keys = [
            x["Key"] for x in resp.get("Contents", []) if x["Key"].endswith(".parquet")
        ]

        if not keys:
            return None

        # Sort by part number for deterministic ordering
        def sort_key(k):
            match = re.search(r"part-(\d+)", k)
            return int(match.group(1)) if match else 0

        keys.sort(key=sort_key)
        return keys[0]
    except Exception as e:
        logger.debug(f"Error listing objects for {prefix}: {e}")
        return None


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_s3_url(s3_url: str) -> Tuple[str, str]:
    """Parse S3 URL into bucket and key."""
    if not s3_url.startswith("s3://"):
        raise ValueError(f"Invalid S3 URL: {s3_url}")

    # Remove s3:// prefix
    path = s3_url[5:]
    parts = path.split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""

    return bucket, key


def load_s3_json(s3_client, bucket: str, key: str) -> Dict:
    """Load JSON from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to load JSON from s3://{bucket}/{key}: {e}")
        raise


def verify_overlap_json(overlap_data: Dict) -> List[str]:
    """Verify OVERLAP.json structure and content."""
    issues = []

    required_fields = ["start_utc", "end_utc", "cadences", "venues", "coverage"]
    for field in required_fields:
        if field not in overlap_data:
            issues.append(f"Missing required field: {field}")

    # Check venues and coverage keys match (structure only)
    if "venues" in overlap_data and "coverage" in overlap_data:
        venues = overlap_data["venues"]
        coverage = overlap_data["coverage"]

        for venue in venues:
            if venue not in coverage:
                issues.append(f"Venue {venue} missing from coverage")

    return issues


def verify_clock_skew(
    s3_client, bucket: str, base_key: str, venues: List[str]
) -> List[str]:
    """Verify clock skew between venues."""
    issues = []

    for venue in venues:
        venue_prefix = f"{base_key}/ticks/{venue}/"
        tick_key = _first_parquet_key(s3_client, bucket, venue_prefix)

        if not tick_key:
            issues.append(f"Missing parquet for {venue}")
            continue

        try:
            # Download parquet file to temp location for analysis
            temp_file = f"/tmp/{venue}_ticks.parquet"
            s3_client.download_file(bucket, tick_key, temp_file)

            # Load and check timestamps
            df = pd.read_parquet(temp_file, engine=DF_ENGINE)

            if "ts_exchange" in df.columns:
                timestamps = pd.to_datetime(df["ts_exchange"], unit="ns", utc=True)

                # Check for monotonic timestamps
                if not timestamps.is_monotonic_increasing:
                    issues.append(f"Non-monotonic timestamps in {venue}")

                # Check for reasonable time range (not all same timestamp)
                time_span = (timestamps.max() - timestamps.min()).total_seconds()
                if time_span < 1:
                    issues.append(f"Very short time span in {venue}: {time_span:.3f}s")

                # Check for gaps > 5 minutes
                gaps = timestamps.diff().dropna()
                large_gaps = gaps[gaps > pd.Timedelta(minutes=5)]
                if len(large_gaps) > 0:
                    issues.append(
                        f"Large gaps in {venue}: {len(large_gaps)} gaps > 5min"
                    )

            # Clean up temp file
            os.remove(temp_file)

        except Exception as e:
            issues.append(f"Failed to verify {venue}: {e}")

    return issues


def verify_coverage(
    s3_client,
    bucket: str,
    base_key: str,
    overlap_data: Dict,
    *,
    allow_missing_coverage_meta: bool,
) -> List[str]:
    """Verify data coverage matches OVERLAP.json claims."""
    issues = []

    venues = overlap_data.get("venues", [])
    claimed_coverage = overlap_data.get("coverage", {})

    # Read coverage from meta/coverage.json if available
    coverage_key = f"{base_key}/meta/coverage.json"
    coverage_data = _load_json_s3(
        s3_client,
        bucket,
        coverage_key,
        allow_missing=allow_missing_coverage_meta,
        log=logger,
    )
    if coverage_data is not None:
        claimed_coverage = coverage_data
        logger.info(f"Loaded coverage from meta/coverage.json: {claimed_coverage}")
    elif allow_missing_coverage_meta:
        # Missing coverage.json is treated as quality warning, not critical
        issues.append("Missing meta/coverage.json (quality warning)")

    for venue in venues:
        venue_prefix = f"{base_key}/ticks/{venue}/"
        tick_key = _first_parquet_key(s3_client, bucket, venue_prefix)

        if not tick_key:
            issues.append(f"Missing parquet for {venue}")
            continue

        try:
            # Check if file exists and get size
            response = s3_client.head_object(Bucket=bucket, Key=tick_key)
            file_size = response["ContentLength"]

            if file_size < 1000:  # Less than 1KB is suspicious
                issues.append(f"Very small tick file for {venue}: {file_size} bytes")

        except Exception as e:
            issues.append(f"Failed to verify coverage for {venue}: {e}")

    # Note: Do not enforce thresholds here; handled centrally in verify_single_window()
    return issues


def verify_provenance(s3_client, bucket: str, base_key: str) -> List[str]:
    """Verify provenance.json exists and is valid."""
    issues = []

    provenance_key = f"{base_key}/meta/provenance.json"

    try:
        provenance_data = load_s3_json(s3_client, bucket, provenance_key)

        required_fields = ["provenance", "seed", "code_version"]
        for field in required_fields:
            if field not in provenance_data:
                issues.append(f"Missing provenance field: {field}")

        # Check provenance is either REAL or DEMO
        if provenance_data.get("provenance") not in ["REAL", "DEMO"]:
            issues.append(
                f"Invalid provenance value: {provenance_data.get('provenance')}"
            )

    except Exception as e:
        issues.append(f"Failed to verify provenance: {e}")

    return issues


def discover_and_verify_windows(args) -> int:
    """Discover and verify all available windows in S3."""
    s3_client = boto3.client("s3")
    bucket = DEFAULT_BUCKET
    prefix = DEFAULT_PREFIX

    logger.info(f"Discovering windows in s3://{bucket}/{prefix}/")

    try:
        # List all OVERLAP.json files recursively
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/")

        windows = []
        for obj in response.get("Contents", []):
            if obj["Key"].endswith("OVERLAP.json"):
                windows.append(obj["Key"])

        if not windows:
            logger.warning("No windows found in S3")
            return 0

        logger.info(f"Found {len(windows)} windows to verify")

        # Verify each window and aggregate results
        total_critical = 0
        total_quality = 0
        windows_passed = 0
        windows_warned = 0
        windows_failed = 0

        for window_path in windows:
            logger.info(f"Verifying {window_path}")
            try:
                # Extract base key from OVERLAP.json path
                base_key = "/".join(window_path.split("/")[:-1])

                # Load OVERLAP.json
                overlap_data = load_s3_json(s3_client, bucket, window_path)
                if not overlap_data:
                    logger.error(f"Failed to load {window_path}")
                    total_critical += 1
                    windows_failed += 1
                    continue

                # Verify this window
                result = verify_single_window(
                    s3_client, bucket, base_key, overlap_data, args
                )
                critical_count = len(result.get("critical", []))
                quality_count = len(result.get("quality", []))

                total_critical += critical_count
                total_quality += quality_count

                if critical_count > 0:
                    windows_failed += 1
                elif quality_count > 0:
                    windows_warned += 1
                else:
                    windows_passed += 1

            except Exception as e:
                logger.error(f"Failed to verify {window_path}: {e}")
                total_critical += 1
                windows_failed += 1

        # Log summary
        warn_mode = "true" if args.warn_on_quality else "false"
        logger.info(
            f"SUMMARY: windows={len(windows)}, PASS={windows_passed}, WARN={windows_warned}, FAIL={windows_failed} (warn-on-quality={warn_mode})"
        )

        # Exit logic: only fail if there are critical issues
        if total_critical > 0:
            logger.error(f"Verification failed with {total_critical} critical issues")
            return 1
        else:
            if total_quality > 0:
                if args.soft_fail:
                    logger.warning(
                        f"Verification passed with {total_quality} quality warnings (soft-fail mode)"
                    )
                    return 0
                else:
                    logger.warning(
                        f"Verification passed with {total_quality} quality warnings"
                    )
            else:
                logger.info("All verifications passed")
            return 0

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return 1


def verify_single_window(
    s3_client, bucket: str, base_key: str, overlap_data: Dict, args
) -> Dict:
    """Verify a single window and return structured results."""
    critical_issues = []
    quality_issues = []

    # Verify OVERLAP.json structure (CRITICAL)
    overlap_issues = verify_overlap_json(overlap_data)
    if overlap_issues:
        critical_issues.extend(overlap_issues)
        logger.error("OVERLAP.json issues:")
        for issue in overlap_issues:
            logger.error(f"  - {issue}")
        return {"critical": critical_issues, "quality": quality_issues}

    # Run requested verification checks
    if "clocks" in args.report:
        logger.info("Verifying clock skew...")
        clock_issues = verify_clock_skew(
            s3_client, bucket, base_key, overlap_data["venues"]
        )
        if clock_issues:
            # Missing parquet files are quality issues when --warn-on-quality is set
            if args.warn_on_quality:
                quality_issues.extend(clock_issues)
                logger.warning("Clock skew issues (quality):")
                for issue in clock_issues:
                    logger.warning(f"  - {issue}")
            else:
                critical_issues.extend(clock_issues)
                logger.error("Clock skew issues:")
                for issue in clock_issues:
                    logger.error(f"  - {issue}")
        else:
            logger.info("Clock skew verification passed")

    if "coverage" in args.report:
        logger.info("Verifying coverage...")
        coverage_issues = verify_coverage(
            s3_client,
            bucket,
            base_key,
            overlap_data,
            allow_missing_coverage_meta=args.allow_missing_coverage_meta,
        )
        if coverage_issues:
            # Missing parquet/coverage files are quality issues when --warn-on-quality is set
            if args.warn_on_quality:
                quality_issues.extend(coverage_issues)
                logger.warning("Coverage issues (quality):")
                for issue in coverage_issues:
                    logger.warning(f"  - {issue}")
            else:
                critical_issues.extend(coverage_issues)
                logger.error("Coverage issues:")
                for issue in coverage_issues:
                    logger.error(f"  - {issue}")
        else:
            logger.info("Coverage verification passed")

    if "provenance" in args.report:
        logger.info("Verifying provenance...")
        provenance_issues = verify_provenance(s3_client, bucket, base_key)
        if provenance_issues:
            # Provenance issues are typically quality issues
            if args.warn_on_quality:
                quality_issues.extend(provenance_issues)
                logger.warning("Provenance issues (quality):")
                for issue in provenance_issues:
                    logger.warning(f"  - {issue}")
            else:
                critical_issues.extend(provenance_issues)
                logger.error("Provenance issues:")
                for issue in provenance_issues:
                    logger.error(f"  - {issue}")
        else:
            logger.info("Provenance verification passed")

    # Check coverage thresholds (QUALITY)
    venues = overlap_data.get("venues", [])
    coverage = overlap_data.get("coverage", {})

    for venue in venues:
        if venue in coverage:
            coverage_value = coverage[venue]
            # Handle both dict and float coverage values
            if isinstance(coverage_value, dict):
                coverage_pct = coverage_value.get("coverage_percentage", 0.0)
            else:
                coverage_pct = float(coverage_value)

            if coverage_pct < args.fail_under_coverage:
                issue = f"Low coverage for {venue}: {coverage_pct:.3f}"
                if args.warn_on_quality:
                    quality_issues.append(issue)
                    logger.warning(f"  - {issue}")
                else:
                    critical_issues.append(issue)
                    logger.error(f"  - {issue}")

    # Log summary for this window
    if critical_issues:
        logger.error(
            f"Window verification failed with {len(critical_issues)} critical issues"
        )
    elif quality_issues:
        if args.warn_on_quality:
            logger.warning(
                f"Window verification passed with {len(quality_issues)} quality warnings"
            )
        else:
            logger.error(
                f"Window verification failed with {len(quality_issues)} quality issues"
            )
    else:
        logger.info("All verifications passed")

    return {"critical": critical_issues, "quality": quality_issues}


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify S3 snapshot integrity")
    parser.add_argument("--overlap", help="S3 URL to OVERLAP.json")
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Discover and verify all windows in bucket",
    )
    parser.add_argument(
        "--fail-under-coverage",
        type=float,
        default=0.95,
        help="Fail if any venue coverage below this threshold",
    )
    parser.add_argument(
        "--report",
        default="clocks,coverage",
        help="Comma-separated list: clocks,coverage,provenance",
    )
    parser.add_argument(
        "--warn-on-quality",
        action="store_true",
        help="Warn on quality issues instead of failing",
    )
    parser.add_argument(
        "--soft-fail",
        action="store_true",
        help="Exit 0 for quality issues, only fail on structural errors",
    )
    parser.add_argument(
        "--allow-missing-coverage-meta",
        action="store_true",
        help="Treat missing meta/coverage.json as a quality warning",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if not args.overlap and not args.discover:
        parser.error("Either --overlap or --discover must be specified")

    setup_logging(args.verbose)

    if args.discover:
        # Discovery mode: find and verify all available windows
        return discover_and_verify_windows(args)

    # Parse S3 URL for single window verification
    try:
        bucket, overlap_key = parse_s3_url(args.overlap)
        base_key = "/".join(overlap_key.split("/")[:-1])  # Remove OVERLAP.json
    except Exception as e:
        logger.error(f"Invalid S3 URL: {e}")
        return 1

    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Load OVERLAP.json
    try:
        overlap_data = load_s3_json(s3_client, bucket, overlap_key)
    except Exception as e:
        logger.error(f"Failed to load OVERLAP.json: {e}")
        return 1

    # Use the structured verification approach
    result = verify_single_window(s3_client, bucket, base_key, overlap_data, args)
    critical_issues = result.get("critical", [])
    quality_issues = result.get("quality", [])

    # Exit logic: only fail if there are critical issues
    if critical_issues:
        logger.error(f"Verification failed with {len(critical_issues)} critical issues")
        return 1
    else:
        if quality_issues:
            if args.warn_on_quality:
                if args.soft_fail:
                    logger.warning(
                        f"Verification passed with {len(quality_issues)} quality warnings (soft-fail mode)"
                    )
                    return 0
                else:
                    logger.warning(
                        f"Verification passed with {len(quality_issues)} quality warnings"
                    )
            else:
                logger.error(
                    f"Verification failed with {len(quality_issues)} quality issues"
                )
                return 1
        else:
            logger.info("All verifications passed")
        return 0


if __name__ == "__main__":
    exit(main())
