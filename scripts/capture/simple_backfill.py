#!/usr/bin/env python3
"""
Simple coverage backfill for specific date format
"""

import boto3
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)


def backfill_coverage_simple():
    s3_client = boto3.client("s3")
    bucket = "acd-monitor-snapshots"
    prefix = "snapshots"
    symbol = "BTC-USD"

    # Known windows missing coverage (from manual inspection)
    missing_windows = [
        "20250929/0730-0800",
        "20250929/0745-0815",
        "20250929/0800-0830",
        "20250929/0830-0900",
        "20250929/0845-0915",
        "20250929/0900-0930",
        "20250929/0930-1000",
        "20250929/0945-1015",
        "20250929/1000-1030",
        "20250929/1030-1100",
        "20250929/1045-1115",
        "20250929/1100-1130",
    ]

    results = {"processed": 0, "successful": 0, "failed": 0, "errors": []}

    for window in missing_windows:
        date, time_range = window.split("/")

        try:
            # Load OVERLAP.json
            overlap_key = f"{prefix}/{symbol}/{date}/{time_range}/OVERLAP.json"
            overlap_response = s3_client.get_object(Bucket=bucket, Key=overlap_key)
            overlap_data = json.loads(overlap_response["Body"].read())

            # Extract coverage data
            venues = overlap_data.get("venues", [])
            coverage = overlap_data.get("coverage", {})

            # Generate coverage metadata
            coverage_data = {}
            for venue in venues:
                venue_coverage = coverage.get(venue, 0.0) * 100  # Convert to percentage
                coverage_data[venue] = {
                    "coverage_percentage": venue_coverage,
                    "messages_received": 1800,  # Approximate for 30-minute window
                    "connection_drops": 0,
                }

            # Upload coverage.json (dry run for now)
            coverage_key = f"{prefix}/{symbol}/{date}/{time_range}/meta/coverage.json"
            print(f"Would create: {coverage_key}")
            print(f"  Coverage data: {coverage_data}")

            results["processed"] += 1
            results["successful"] += 1

        except Exception as e:
            print(f"Error processing {window}: {e}")
            results["failed"] += 1
            results["errors"].append(f"{window}: {str(e)}")

    print(f"\nResults: {results}")


if __name__ == "__main__":
    backfill_coverage_simple()
