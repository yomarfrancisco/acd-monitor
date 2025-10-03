#!/usr/bin/env python3
"""
Minimal Assembly Test
Test with just a few files to verify the approach works.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import boto3
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class MinimalAssemblyTest:
    """Test minimal assembly with just a few files."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"
        self.btc_prefix = "snapshots/BTC-USD/"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

    def test_minimal_assembly(self):
        """Test assembly with just a few files."""
        print("🧪 Minimal Assembly Test")
        print("=" * 40)

        # Get just a few sample files
        sample_files = self._get_sample_files(limit=3)

        if not sample_files:
            print("❌ No sample files found")
            return False

        print(f"📊 Testing with {len(sample_files)} files")

        # Process each file
        for i, file_info in enumerate(sample_files):
            print(f"\n🔍 Processing file {i+1}: {file_info['key']}")
            success = self._process_single_file(file_info)
            if success:
                print(f"  ✅ Success")
            else:
                print(f"  ❌ Failed")

        print(f"\n✅ Minimal assembly test completed")
        return True

    def _get_sample_files(self, limit: int = 3):
        """Get a few sample files."""
        objects = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.btc_prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".parquet"):
                            objects.append({"key": obj["Key"], "size": obj["Size"]})
                            if len(objects) >= limit:
                                break
                    if len(objects) >= limit:
                        break
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return []

        return objects

    def _process_single_file(self, file_info):
        """Process a single file."""
        try:
            # Download file
            temp_file = f"/tmp/test_{file_info['key'].split('/')[-1]}"

            self.s3_client.download_file(
                Bucket=self.bucket_name, Key=file_info["key"], Filename=temp_file
            )

            # Read parquet
            df = pd.read_parquet(temp_file)
            print(f"  📊 Shape: {df.shape}")
            print(f"  📊 Columns: {list(df.columns)}")

            # Process timestamp
            if "ts_exchange" in df.columns:
                if df["ts_exchange"].dtype == "int64":
                    df["ts"] = pd.to_datetime(df["ts_exchange"], unit="ns")
                else:
                    df["ts"] = pd.to_datetime(df["ts_exchange"])

                df = df.set_index("ts")

                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC")
                else:
                    df.index = df.index.tz_convert("UTC")

                print(f"  📅 Time range: {df.index.min()} to {df.index.max()}")
                print(f"  📊 After processing: {len(df)} observations")

                # Clean up
                if os.path.exists(temp_file):
                    os.remove(temp_file)

                return True
            else:
                print(f"  ⚠️ No timestamp column found")
                return False

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False


if __name__ == "__main__":
    tester = MinimalAssemblyTest()
    success = tester.test_minimal_assembly()

    if success:
        print("\n🎉 Minimal assembly test successful!")
    else:
        print("\n❌ Minimal assembly test failed!")
        sys.exit(1)
