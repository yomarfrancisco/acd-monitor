#!/usr/bin/env python3
"""
ICP-VMM Backfill Index Generator

Creates _index.json for cross-comparison of runs.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import boto3
from datetime import datetime, timezone


def get_s3_runs(bucket: str, prefix: str) -> List[Dict[str, Any]]:
    """Get list of ICP-VMM runs from S3."""
    s3 = boto3.client("s3")

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

        runs = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/MANIFEST.json"):
                # Extract window ID from path
                path_parts = key.split("/")
                if len(path_parts) >= 2:
                    window_id = path_parts[-2]

                    # Try to get manifest content
                    try:
                        manifest_response = s3.get_object(Bucket=bucket, Key=key)
                        manifest = json.loads(manifest_response["Body"].read())

                        runs.append(
                            {
                                "windowId": window_id,
                                "s3_prefix": f"s3://{bucket}/{'/'.join(path_parts[:-1])}/",
                                "manifestHash": manifest.get("integrity", {}).get(
                                    "manifestHash", ""
                                ),
                                "runStatus": manifest.get("run", {}).get(
                                    "runStatus", "UNKNOWN"
                                ),
                                "timestamp": manifest.get("run", {}).get(
                                    "generatedAt", ""
                                ),
                                "venues": manifest.get("run", {}).get("venues", []),
                                "observations": manifest.get("run", {}).get(
                                    "observations", {}
                                ),
                                "coverage": manifest.get("run", {}).get("coverage", {}),
                            }
                        )
                    except Exception as e:
                        print(f"⚠️ Could not read manifest for {window_id}: {e}")
                        continue

        return sorted(runs, key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        print(f"❌ Error listing S3 objects: {e}")
        return []


def create_index(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create index.json content."""
    return {
        "indexVersion": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalRuns": len(runs),
        "runs": runs,
        "summary": {
            "statusCounts": {
                "PROVISIONAL": len(
                    [r for r in runs if r["runStatus"] == "PROVISIONAL"]
                ),
                "INSUFFICIENT": len(
                    [r for r in runs if r["runStatus"] == "INSUFFICIENT"]
                ),
                "INVARIANT": len([r for r in runs if r["runStatus"] == "INVARIANT"]),
                "VARIANT": len([r for r in runs if r["runStatus"] == "VARIANT"]),
                "ERROR": len([r for r in runs if r["runStatus"] == "ERROR"]),
            },
            "latestRun": runs[0] if runs else None,
            "venueCoverage": {
                venue: len([r for r in runs if venue in r.get("venues", [])])
                for venue in ["binance", "coinbase", "kraken", "okx", "bybit"]
            },
        },
    }


def upload_index(bucket: str, prefix: str, index_content: Dict[str, Any]) -> bool:
    """Upload index.json to S3."""
    s3 = boto3.client("s3")

    try:
        index_key = f"{prefix}/_index.json"
        s3.put_object(
            Bucket=bucket,
            Key=index_key,
            Body=json.dumps(index_content, indent=2),
            ContentType="application/json",
        )
        print(f"✅ Index uploaded to s3://{bucket}/{index_key}")
        return True
    except Exception as e:
        print(f"❌ Error uploading index: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python backfill_index.py <bucket> <prefix>")
        sys.exit(1)

    bucket = sys.argv[1]
    prefix = sys.argv[2]

    print(f"📊 Generating index for s3://{bucket}/{prefix}")

    # Get runs from S3
    runs = get_s3_runs(bucket, prefix)
    print(f"✅ Found {len(runs)} runs")

    if not runs:
        print("⚠️ No runs found")
        sys.exit(0)

    # Create index
    index_content = create_index(runs)

    # Upload index
    if upload_index(bucket, prefix, index_content):
        print("🎉 Index generation completed successfully!")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
