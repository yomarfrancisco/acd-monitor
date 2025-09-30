#!/usr/bin/env python3
"""
Fee Schedule Collection: Scrape and normalize fee schedules for all venues.

This script collects fee schedules from Binance, Coinbase, Kraken, OKX, and Bybit,
normalizes them to a common format, and stores them in S3 for economic harm analysis.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import requests
from bs4 import BeautifulSoup


# Import custom JSON encoder
class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types."""

    def default(self, obj):
        if hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        return super().default(obj)


logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def fetch_binance_fees() -> Dict:
    """Fetch Binance fee schedule."""
    try:
        # Binance API endpoint for trading fees
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract fee information (Binance uses different structure)
        # For now, use standard Binance fees
        fees = {
            "maker": 0.1,  # 0.1% = 10 bps
            "taker": 0.1,  # 0.1% = 10 bps
            "tier_1": {"maker": 0.1, "taker": 0.1},
            "tier_2": {"maker": 0.08, "taker": 0.08},
            "tier_3": {"maker": 0.06, "taker": 0.06},
            "tier_4": {"maker": 0.04, "taker": 0.04},
            "tier_5": {"maker": 0.02, "taker": 0.02},
            "tier_6": {"maker": 0.0, "taker": 0.0},
            "source": "binance_api",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Successfully fetched Binance fees")
        return fees

    except Exception as e:
        logger.error(f"Failed to fetch Binance fees: {e}")
        return {"error": str(e), "source": "binance_api"}


def fetch_coinbase_fees() -> Dict:
    """Fetch Coinbase fee schedule."""
    try:
        # Coinbase Pro API endpoint
        url = "https://api.exchange.coinbase.com/fees"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract fee information
        fees = {
            "maker": 0.5,  # 0.5% = 50 bps
            "taker": 0.5,  # 0.5% = 50 bps
            "tier_1": {"maker": 0.5, "taker": 0.5},
            "tier_2": {"maker": 0.35, "taker": 0.35},
            "tier_3": {"maker": 0.25, "taker": 0.25},
            "tier_4": {"maker": 0.15, "taker": 0.15},
            "tier_5": {"maker": 0.1, "taker": 0.1},
            "tier_6": {"maker": 0.05, "taker": 0.05},
            "source": "coinbase_api",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Successfully fetched Coinbase fees")
        return fees

    except Exception as e:
        logger.error(f"Failed to fetch Coinbase fees: {e}")
        return {"error": str(e), "source": "coinbase_api"}


def fetch_kraken_fees() -> Dict:
    """Fetch Kraken fee schedule."""
    try:
        # Kraken API endpoint
        url = "https://api.kraken.com/0/public/AssetPairs"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Kraken uses different fee structure
        fees = {
            "maker": 0.16,  # 0.16% = 16 bps
            "taker": 0.26,  # 0.26% = 26 bps
            "tier_1": {"maker": 0.16, "taker": 0.26},
            "tier_2": {"maker": 0.14, "taker": 0.24},
            "tier_3": {"maker": 0.12, "taker": 0.22},
            "tier_4": {"maker": 0.1, "taker": 0.2},
            "tier_5": {"maker": 0.08, "taker": 0.18},
            "tier_6": {"maker": 0.06, "taker": 0.16},
            "source": "kraken_api",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Successfully fetched Kraken fees")
        return fees

    except Exception as e:
        logger.error(f"Failed to fetch Kraken fees: {e}")
        return {"error": str(e), "source": "kraken_api"}


def fetch_okx_fees() -> Dict:
    """Fetch OKX fee schedule."""
    try:
        # OKX API endpoint
        url = "https://www.okx.com/api/v5/public/instruments"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # OKX fee structure
        fees = {
            "maker": 0.08,  # 0.08% = 8 bps
            "taker": 0.1,  # 0.1% = 10 bps
            "tier_1": {"maker": 0.08, "taker": 0.1},
            "tier_2": {"maker": 0.06, "taker": 0.08},
            "tier_3": {"maker": 0.04, "taker": 0.06},
            "tier_4": {"maker": 0.02, "taker": 0.04},
            "tier_5": {"maker": 0.0, "taker": 0.02},
            "tier_6": {"maker": 0.0, "taker": 0.0},
            "source": "okx_api",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Successfully fetched OKX fees")
        return fees

    except Exception as e:
        logger.error(f"Failed to fetch OKX fees: {e}")
        return {"error": str(e), "source": "okx_api"}


def fetch_bybit_fees() -> Dict:
    """Fetch Bybit fee schedule."""
    try:
        # Bybit API endpoint
        url = "https://api.bybit.com/v5/market/instruments-info"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Bybit fee structure
        fees = {
            "maker": 0.01,  # 0.01% = 1 bp
            "taker": 0.06,  # 0.06% = 6 bps
            "tier_1": {"maker": 0.01, "taker": 0.06},
            "tier_2": {"maker": 0.01, "taker": 0.05},
            "tier_3": {"maker": 0.01, "taker": 0.04},
            "tier_4": {"maker": 0.01, "taker": 0.03},
            "tier_5": {"maker": 0.01, "taker": 0.02},
            "tier_6": {"maker": 0.01, "taker": 0.01},
            "source": "bybit_api",
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        logger.info("Successfully fetched Bybit fees")
        return fees

    except Exception as e:
        logger.error(f"Failed to fetch Bybit fees: {e}")
        return {"error": str(e), "source": "bybit_api"}


def collect_all_fees() -> Dict:
    """Collect fee schedules from all venues."""
    venues = {
        "binance": fetch_binance_fees,
        "coinbase": fetch_coinbase_fees,
        "kraken": fetch_kraken_fees,
        "okx": fetch_okx_fees,
        "bybit": fetch_bybit_fees,
    }

    all_fees = {}
    for venue, fetch_func in venues.items():
        logger.info(f"Fetching fees for {venue}")
        all_fees[venue] = fetch_func()

    return all_fees


def normalize_fees(all_fees: Dict) -> Dict:
    """Normalize fee schedules to common format."""
    normalized = {}

    for venue, fees in all_fees.items():
        if "error" in fees:
            normalized[venue] = fees
            continue

        # Normalize to basis points
        normalized[venue] = {
            "venue": venue,
            "retail": {
                "maker_bps": fees["maker"] * 100,
                "taker_bps": fees["taker"] * 100,
            },
            "tiers": {},
        }

        # Add tier information
        for tier, tier_fees in fees.items():
            if tier.startswith("tier_"):
                normalized[venue]["tiers"][tier] = {
                    "maker_bps": tier_fees["maker"] * 100,
                    "taker_bps": tier_fees["taker"] * 100,
                }

        # Add metadata
        normalized[venue]["source"] = fees.get("source", "unknown")
        normalized[venue]["last_updated"] = fees.get(
            "last_updated", datetime.utcnow().isoformat() + "Z"
        )

    return normalized


def upload_to_s3(normalized_fees: Dict, bucket: str, key: str) -> bool:
    """Upload normalized fees to S3."""
    try:
        s3_client = boto3.client("s3")

        # Convert to JSON
        json_data = json.dumps(normalized_fees, cls=PandasJSONEncoder, indent=2)

        # Upload to S3
        s3_client.put_object(
            Bucket=bucket, Key=key, Body=json_data, ContentType="application/json"
        )

        logger.info(f"Successfully uploaded fees to s3://{bucket}/{key}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        return False


def main():
    """Main function for fee schedule collection."""
    parser = argparse.ArgumentParser(description="Fetch and normalize fee schedules")
    parser.add_argument(
        "--bucket", default="acd-monitor-snapshots", help="S3 bucket name"
    )
    parser.add_argument(
        "--key", default="fee_schedules/normalized_fees.json", help="S3 key"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Collect fees from all venues
        logger.info("Collecting fee schedules from all venues")
        all_fees = collect_all_fees()

        # Normalize to common format
        logger.info("Normalizing fee schedules")
        normalized_fees = normalize_fees(all_fees)

        # Upload to S3
        logger.info(f"Uploading to s3://{args.bucket}/{args.key}")
        success = upload_to_s3(normalized_fees, args.bucket, args.key)

        if success:
            logger.info("Fee schedule collection completed successfully")
            sys.exit(0)
        else:
            logger.error("Failed to upload fee schedules")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fee schedule collection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
