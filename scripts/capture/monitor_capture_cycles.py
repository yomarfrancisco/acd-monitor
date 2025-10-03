#!/usr/bin/env python3
"""
Monitor capture cycles to track ETH-USD vs BTC-USD performance
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta

import boto3

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
SYMBOLS = ["BTC-USD", "ETH-USD"]

s3 = boto3.client("s3")


def get_latest_windows():
    """Get the latest windows for each symbol."""
    latest_windows = {}

    for symbol in SYMBOLS:
        try:
            # List all OVERLAP.json files for this symbol
            response = s3.list_objects_v2(
                Bucket=BUCKET, Prefix=f"{PREFIX}/{symbol}/", Delimiter="/"
            )

            # Find the most recent window
            latest_window = None
            latest_time = None

            for obj in response.get("Contents", []):
                if obj["Key"].endswith("OVERLAP.json"):
                    # Extract timestamp from key
                    key_parts = obj["Key"].split("/")
                    if len(key_parts) >= 4:
                        date_part = key_parts[-3]  # e.g., "20250929"
                        time_part = key_parts[-2]  # e.g., "1300-1330"
                        window_time = datetime.strptime(
                            f"{date_part}_{time_part}", "%Y%m%d_%H%M-%H%M"
                        )

                        if latest_time is None or window_time > latest_time:
                            latest_time = window_time
                            latest_window = obj["Key"].replace("/OVERLAP.json", "")

            latest_windows[symbol] = latest_window

        except Exception as e:
            print(f"Error getting latest window for {symbol}: {e}")
            latest_windows[symbol] = None

    return latest_windows


def check_window_quality(base_key):
    """Check quality metrics for a window."""
    if not base_key:
        return None

    try:
        # Check if coverage.json exists
        coverage_key = f"{base_key}/meta/coverage.json"
        try:
            coverage_response = s3.get_object(Bucket=BUCKET, Key=coverage_key)
            coverage_data = json.loads(coverage_response["Body"].read())
        except:
            coverage_data = None

        # Check venues present
        overlap_key = f"{base_key}/OVERLAP.json"
        overlap_response = s3.get_object(Bucket=BUCKET, Key=overlap_key)
        overlap_data = json.loads(overlap_response["Body"].read())
        venues = overlap_data.get("venues", [])

        # Check for parquet files
        venue_presence = {}
        for venue in venues:
            try:
                response = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"{base_key}/ticks/{venue}/")
                parquet_files = [
                    obj["Key"]
                    for obj in response.get("Contents", [])
                    if obj["Key"].endswith(".parquet")
                ]
                venue_presence[venue] = len(parquet_files) > 0
            except:
                venue_presence[venue] = False

        return {
            "venues_present": len([v for v in venue_presence.values() if v]),
            "total_venues": len(venues),
            "venue_presence": venue_presence,
            "coverage_data": coverage_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"Error checking window quality for {base_key}: {e}")
        return None


def run_data_quality_check():
    """Run the data quality validation script."""
    try:
        result = subprocess.run(
            [
                "python",
                "scripts/capture/validate_data_quality.py",
                "--symbols",
                "BTC-USD,ETH-USD",
                "--days-back",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def main():
    """Monitor capture cycles."""
    print("🔍 Monitoring ACD Capture Cycles")
    print("=" * 50)

    # Check current status
    print(f"\n📊 Current Status ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC):")

    latest_windows = get_latest_windows()

    for symbol in SYMBOLS:
        window = latest_windows[symbol]
        if window:
            print(f"  {symbol}: {window}")
            quality = check_window_quality(window)
            if quality:
                print(f"    Venues: {quality['venues_present']}/{quality['total_venues']}")
                if quality["coverage_data"]:
                    overall_coverage = quality["coverage_data"].get("coverage_percentage", 0)
                    print(f"    Coverage: {overall_coverage:.1f}%")
        else:
            print(f"  {symbol}: No recent windows found")

    # Run data quality check
    print(f"\n🧪 Running Data Quality Check...")
    dq_result = run_data_quality_check()

    if "error" in dq_result:
        print(f"  ❌ Error: {dq_result['error']}")
    else:
        print(f"  Return code: {dq_result['returncode']}")
        if dq_result["stdout"]:
            print(f"  Output: {dq_result['stdout'][:200]}...")
        if dq_result["stderr"]:
            print(f"  Errors: {dq_result['stderr'][:200]}...")

    # Check GitHub Actions status
    print(f"\n🚀 GitHub Actions Status:")
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--workflow=capture_continuous.yml", "--limit", "3"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines[:3]:  # Show last 3 runs
                print(f"  {line}")
        else:
            print(f"  Error getting GitHub Actions status: {result.stderr}")
    except Exception as e:
        print(f"  Error: {e}")

    print(f"\n✅ Monitoring complete")


if __name__ == "__main__":
    main()
