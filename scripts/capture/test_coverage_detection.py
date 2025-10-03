#!/usr/bin/env python3
"""
Test script to debug coverage detection
"""

import boto3
import logging

logging.basicConfig(level=logging.INFO)


def test_coverage_detection():
    s3_client = boto3.client("s3")
    bucket = "acd-monitor-snapshots"
    prefix = "snapshots"
    symbol = "BTC-USD"

    try:
        # List all windows for the symbol
        response = s3_client.list_objects_v2(
            Bucket=bucket, Prefix=f"{prefix}/{symbol}/", Delimiter="/"
        )

        print(f"Found {len(response.get('CommonPrefixes', []))} date prefixes")

        for obj in response.get("CommonPrefixes", []):
            date_path = obj["Prefix"].split("/")[-2]
            print(f"Date path: {date_path}")

            if date_path:
                # List time ranges for this date
                date_response = s3_client.list_objects_v2(
                    Bucket=bucket,
                    Prefix=f"{prefix}/{symbol}/{date_path}/",
                    Delimiter="/",
                )

                print(f"  Found {len(date_response.get('CommonPrefixes', []))} time ranges")

                for time_obj in date_response.get("CommonPrefixes", []):
                    time_range = time_obj["Prefix"].split("/")[-2]
                    print(f"    Time range: {time_range}")

                    if time_range and "-" in time_range:
                        # Check if OVERLAP.json exists
                        overlap_key = f"{prefix}/{symbol}/{date_path}/{time_range}/OVERLAP.json"
                        coverage_key = (
                            f"{prefix}/{symbol}/{date_path}/{time_range}/meta/coverage.json"
                        )

                        print(f"      Checking: {overlap_key}")

                        try:
                            # Check if OVERLAP.json exists
                            s3_client.head_object(Bucket=bucket, Key=overlap_key)
                            print(f"      ✅ OVERLAP.json exists")

                            # Check if coverage.json exists
                            try:
                                s3_client.head_object(Bucket=bucket, Key=coverage_key)
                                print(f"      ✅ Coverage.json exists")
                            except s3_client.exceptions.NoSuchKey:
                                print(f"      ❌ Coverage.json missing")

                        except s3_client.exceptions.NoSuchKey:
                            print(f"      ❌ OVERLAP.json missing")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_coverage_detection()
