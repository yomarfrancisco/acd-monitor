#!/usr/bin/env python3
"""
Stage Reality Data Script

Copies real data from raw_probes to analysis staging directory.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import boto3
import pandas as pd


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("stage_reality_data.log"),
        ],
    )


def stage_reality_data(venue: str, slice_name: str, date: str, bucket: str) -> Dict[str, Any]:
    """
    Stage real data from raw_probes to analysis staging directory.

    Args:
        venue: Venue name (e.g., 'coinbase')
        slice_name: Slice name (e.g., 'slice_00')
        date: Date string (YYYYMMDD)
        bucket: S3 bucket name

    Returns:
        Staging results and manifest
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Staging {venue} {slice_name} data from raw_probes")

    s3_client = boto3.client("s3")

    try:
        # Read the probe manifest
        probe_manifest_key = (
            f"raw_probes/{date}/venue={venue}/slice={slice_name}/probe_manifest.json"
        )
        response = s3_client.get_object(Bucket=bucket, Key=probe_manifest_key)
        probe_manifest = json.loads(response["Body"].read())

        # Read the sample parquet data
        sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"
        response = s3_client.get_object(Bucket=bucket, Key=sample_key)
        parquet_data = response["Body"].read()

        # Write to temporary file and read from there
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        logger.info(f"Loaded {len(df)} rows from {venue} {slice_name}")

        # Create staging manifest
        staging_manifest = {
            "provenance": "REAL",
            "source": "raw_probes",
            "rows": len(df),
            "fields_present": list(df.columns),
            "venue": venue,
            "slice": slice_name,
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "original_manifest": probe_manifest,
        }

        # Stage the data
        staging_prefix = f"analysis/{date}/staging/btc_ticks/venue={venue}/slice={slice_name}"
        staging_key = f"{staging_prefix}/part-0000.parquet"

        # Convert DataFrame to parquet bytes
        parquet_buffer = df.to_parquet()

        # Upload to staging
        s3_client.put_object(
            Bucket=bucket,
            Key=staging_key,
            Body=parquet_buffer,
            ContentType="application/octet-stream",
        )

        # Upload staging manifest
        manifest_key = f"{staging_prefix}/manifest.json"
        s3_client.put_object(
            Bucket=bucket,
            Key=manifest_key,
            Body=json.dumps(staging_manifest, indent=2),
            ContentType="application/json",
        )

        logger.info(f"✅ Staged {venue} {slice_name} to {staging_key}")

        return {
            "success": True,
            "staging_key": staging_key,
            "manifest_key": manifest_key,
            "rows": len(df),
            "fields": list(df.columns),
        }

    except Exception as e:
        logger.error(f"❌ Failed to stage {venue} {slice_name}: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Stage Reality Data")
    parser.add_argument("--venue", default="coinbase", help="Venue name")
    parser.add_argument("--slice", default="slice_00", help="Slice name")
    parser.add_argument("--date", default=None, help="Date (YYYYMMDD), defaults to today")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Set date
    if args.date:
        date = args.date
    else:
        date = datetime.now().strftime("%Y%m%d")

    logger.info(f"Staging {args.venue} {args.slice} data from {date}")

    # Stage the data
    result = stage_reality_data(
        venue=args.venue, slice_name=args.slice, date=date, bucket=args.bucket
    )

    if result["success"]:
        print(f"\n✅ SUCCESS: Staged {args.venue} {args.slice}")
        print(f"📁 S3 Key: {result['staging_key']}")
        print(f"📄 Manifest: {result['manifest_key']}")
        print(f"📊 Rows: {result['rows']}")
        print(f"🏷️  Fields: {', '.join(result['fields'])}")
    else:
        print(f"\n❌ FAILED: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
