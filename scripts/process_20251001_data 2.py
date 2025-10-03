#!/usr/bin/env python3
"""
Process 2025-10-01 data into derived tables for Wave-1 analysis.

This script:
1. Reads all 2025-10-01 parquet files from S3
2. Processes them into the standard format
3. Writes to derived tables for clean views
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path

import boto3
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_s3_file(s3_client, bucket, key):
    """Process a single S3 parquet file and return processed DataFrame."""
    try:
        file_obj = s3_client.get_object(Bucket=bucket, Key=key)
        df = pd.read_parquet(io.BytesIO(file_obj["Body"].read()))

        if len(df) == 0:
            return None

        # Extract metadata from S3 path
        path_parts = key.split("/")
        symbol = path_parts[1]  # BTC-USD or ETH-USD
        date = path_parts[2]  # 20251001
        window = path_parts[3]  # 0045-0115
        venue = path_parts[5]  # coinbase, kraken, etc.

        # Add processed columns
        df["ts_verified"] = pd.to_datetime(df["ts_exchange"], unit="us")
        df["vdate_ymd"] = date
        df["vwindow"] = window
        df["venue"] = venue
        df["symbol"] = symbol

        # Calculate mid price and spread
        df["mid_px"] = (df["best_bid"] + df["best_ask"]) / 2.0
        df["spread_bps"] = (df["best_ask"] - df["best_bid"]) / df["mid_px"] * 10000.0

        # Sanity check based on symbol
        if symbol == "BTC-USD":
            df["sanity_price_ok"] = (df["last_px"] >= 80000).astype(int)
        elif symbol == "ETH-USD":
            df["sanity_price_ok"] = (df["last_px"] >= 2000).astype(int)
        else:
            df["sanity_price_ok"] = 1

        # Add S3 path
        df["_path"] = key

        return df

    except Exception as e:
        logger.error(f"Error processing {key}: {e}")
        return None


def list_s3_files(s3_client, bucket, prefix):
    """List all parquet files in S3 with given prefix."""
    files = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                if obj["Key"].endswith(".parquet"):
                    files.append(obj["Key"])

    return files


def process_20251001_data():
    """Main function to process all 2025-10-01 data."""
    s3 = boto3.client("s3")
    bucket = "acd-monitor-snapshots"

    logger.info("Starting 2025-10-01 data processing...")

    # Process BTC-USD data
    logger.info("Processing BTC-USD data...")
    btc_files = list_s3_files(s3, bucket, "snapshots/BTC-USD/20251001/")
    btc_dataframes = []

    for file in btc_files:
        logger.info(f"Processing {file}")
        df = process_s3_file(s3, bucket, file)
        if df is not None:
            btc_dataframes.append(df)

    if btc_dataframes:
        btc_combined = pd.concat(btc_dataframes, ignore_index=True)
        logger.info(f"BTC-USD: {len(btc_combined)} records from {len(btc_dataframes)} files")

        # Save to S3 as parquet
        output_key = "processed/btc_ticks_20251001.parquet"
        btc_combined.to_parquet(f"s3://{bucket}/{output_key}", index=False)
        logger.info(f"BTC-USD data saved to s3://{bucket}/{output_key}")

    # Process ETH-USD data
    logger.info("Processing ETH-USD data...")
    eth_files = list_s3_files(s3, bucket, "snapshots/ETH-USD/20251001/")
    eth_dataframes = []

    for file in eth_files:
        logger.info(f"Processing {file}")
        df = process_s3_file(s3, bucket, file)
        if df is not None:
            eth_dataframes.append(df)

    if eth_dataframes:
        eth_combined = pd.concat(eth_dataframes, ignore_index=True)
        logger.info(f"ETH-USD: {len(eth_combined)} records from {len(eth_dataframes)} files")

        # Save to S3 as parquet
        output_key = "processed/eth_ticks_20251001.parquet"
        eth_combined.to_parquet(f"s3://{bucket}/{output_key}", index=False)
        logger.info(f"ETH-USD data saved to s3://{bucket}/{output_key}")

    logger.info("2025-10-01 data processing completed!")

    # Print summary
    if btc_dataframes:
        btc_summary = (
            btc_combined.groupby("venue")
            .agg({"last_px": ["count", "mean", "min", "max"], "sanity_price_ok": "sum"})
            .round(2)
        )
        print("\nBTC-USD Summary by Venue:")
        print(btc_summary)

    if eth_dataframes:
        eth_summary = (
            eth_combined.groupby("venue")
            .agg({"last_px": ["count", "mean", "min", "max"], "sanity_price_ok": "sum"})
            .round(2)
        )
        print("\nETH-USD Summary by Venue:")
        print(eth_summary)


if __name__ == "__main__":
    process_20251001_data()
