#!/usr/bin/env python3
"""
Deep S3 Audit - Check for BTC-USD data more thoroughly
"""

import boto3
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import json
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class DeepS3Auditor:
    """Deep audit of S3 for BTC-USD data."""

    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = "acd-monitor-snapshots"

    def deep_audit(self):
        """Perform deep audit of S3 structure."""
        print("🔍 Deep S3 Audit - Checking for BTC-USD Data")
        print("=" * 60)

        # List all objects in the bucket
        print("📥 Listing all objects in bucket...")
        all_objects = self._list_all_objects()

        # Filter for BTC-USD related objects
        btc_objects = [
            obj for obj in all_objects if "BTC-USD" in obj["Key"] or "btc" in obj["Key"].lower()
        ]

        print(f"📊 Found {len(btc_objects)} BTC-USD related objects")

        if btc_objects:
            print("\n🔍 BTC-USD Objects Found:")
            for obj in btc_objects[:20]:  # Show first 20
                print(f"  📄 {obj['Key']} ({obj['Size']} bytes)")

            if len(btc_objects) > 20:
                print(f"  ... and {len(btc_objects) - 20} more")

        # Check for recent data
        print("\n🔍 Checking for recent data...")
        recent_objects = [
            obj for obj in btc_objects if "2025-09" in obj["Key"] or "2025-10" in obj["Key"]
        ]
        print(f"📅 Recent objects (2025-09/10): {len(recent_objects)}")

        # Check for venue-specific data
        venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        venue_data = {}
        for venue in venues:
            venue_objects = [obj for obj in btc_objects if venue in obj["Key"].lower()]
            venue_data[venue] = len(venue_objects)
            print(f"  {venue}: {len(venue_objects)} objects")

        # Check for parquet files specifically
        parquet_objects = [obj for obj in btc_objects if obj["Key"].endswith(".parquet")]
        print(f"\n📊 Parquet files: {len(parquet_objects)}")

        # Generate report
        report = {
            "audit_date": datetime.now().isoformat(),
            "bucket": self.bucket_name,
            "total_objects": len(all_objects),
            "btc_objects": len(btc_objects),
            "recent_objects": len(recent_objects),
            "parquet_objects": len(parquet_objects),
            "venue_data": venue_data,
            "sample_objects": btc_objects[:10] if btc_objects else [],
        }

        # Save report
        os.makedirs("analysis/wave2/btc_usd_s3_audit", exist_ok=True)
        with open("analysis/wave2/btc_usd_s3_audit/deep_audit_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n✅ Deep audit completed")
        print(f"📁 Report saved to analysis/wave2/btc_usd_s3_audit/deep_audit_report.json")

        return report

    def _list_all_objects(self):
        """List all objects in the bucket."""
        objects = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name):
                if "Contents" in page:
                    objects.extend(page["Contents"])
        except Exception as e:
            print(f"❌ Error listing objects: {e}")
            return []

        return objects


if __name__ == "__main__":
    auditor = DeepS3Auditor()
    auditor.deep_audit()
