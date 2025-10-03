#!/usr/bin/env python3
"""
CoinAPI Flat Files - Task 1: Discover Symbols

Lists exchanges and symbols via Flat Files API to identify BTC/USDT or BTC/USD per target venue.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
import requests


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("coinapi_discover_symbols.log"),
        ],
    )


def get_coinapi_key() -> str:
    """Get CoinAPI key from environment variable."""
    api_key = os.getenv("COINAPI_KEY")
    if not api_key:
        raise ValueError("COINAPI_KEY environment variable not set")
    return api_key


def discover_exchanges(api_key: str) -> List[Dict[str, Any]]:
    """Discover available exchanges from CoinAPI."""
    logger = logging.getLogger(__name__)

    url = "https://rest.coinapi.io/v1/exchanges"
    headers = {"X-CoinAPI-Key": api_key}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        exchanges = response.json()

        logger.info(f"Found {len(exchanges)} exchanges")
        return exchanges

    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering exchanges: {e}")
        raise


def discover_symbols(api_key: str) -> List[Dict[str, Any]]:
    """Discover available symbols from CoinAPI."""
    logger = logging.getLogger(__name__)

    url = "https://rest.coinapi.io/v1/symbols"
    headers = {"X-CoinAPI-Key": api_key}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        symbols = response.json()

        logger.info(f"Found {len(symbols)} symbols")
        return symbols

    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering symbols: {e}")
        raise


def filter_btc_symbols(
    symbols: List[Dict[str, Any]], target_venues: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter symbols for BTC pairs on target venues."""
    logger = logging.getLogger(__name__)

    btc_symbols = {}

    for symbol in symbols:
        symbol_id = symbol.get("symbol_id", "")
        exchange_id = symbol.get("exchange_id", "")

        # Check if it's a BTC pair
        if not (symbol_id.startswith("BTC") or "BTC" in symbol_id):
            continue

        # Check if it's on a target venue
        if exchange_id.upper() not in [v.upper() for v in target_venues]:
            continue

        # Prefer USDT, then USD
        if "USDT" in symbol_id:
            pair_type = "USDT"
        elif "USD" in symbol_id:
            pair_type = "USD"
        else:
            continue

        if exchange_id not in btc_symbols:
            btc_symbols[exchange_id] = []

        btc_symbols[exchange_id].append(
            {
                "symbol_id": symbol_id,
                "exchange_id": exchange_id,
                "pair_type": pair_type,
                "asset_id_base": symbol.get("asset_id_base"),
                "asset_id_quote": symbol.get("asset_id_quote"),
                "data_start": symbol.get("data_start"),
                "data_end": symbol.get("data_end"),
                "data_quote_start": symbol.get("data_quote_start"),
                "data_quote_end": symbol.get("data_quote_end"),
                "volume_1hrs_usd": symbol.get("volume_1hrs_usd"),
                "volume_1day_usd": symbol.get("volume_1day_usd"),
                "volume_1mth_usd": symbol.get("volume_1mth_usd"),
            }
        )

    # Sort by preference (USDT first, then by volume)
    for exchange_id in btc_symbols:
        btc_symbols[exchange_id].sort(
            key=lambda x: (x["pair_type"] != "USDT", -x.get("volume_1day_usd", 0))
        )

    logger.info(f"Found BTC symbols for {len(btc_symbols)} exchanges")
    for exchange_id, symbols_list in btc_symbols.items():
        logger.info(f"  {exchange_id}: {len(symbols_list)} symbols")

    return btc_symbols


def save_symbol_inventory(
    s3_client, bucket: str, btc_symbols: Dict[str, List[Dict[str, Any]]], target_venues: List[str]
) -> str:
    """Save symbol inventory to S3."""
    logger = logging.getLogger(__name__)

    inventory = {
        "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
        "target_venues": target_venues,
        "btc_symbols": btc_symbols,
        "summary": {
            "total_exchanges": len(btc_symbols),
            "exchanges_with_btc": list(btc_symbols.keys()),
            "total_symbols": sum(len(symbols) for symbols in btc_symbols.values()),
        },
    }

    s3_key = "analysis/COINAPI/_inv/symbol_inventory.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=json.dumps(inventory, indent=2),
        ContentType="application/json",
    )

    logger.info(f"Saved symbol inventory: s3://{bucket}/{s3_key}")
    return s3_key


def main():
    """Main discovery function."""
    parser = argparse.ArgumentParser(description="CoinAPI Flat Files - Discover Symbols")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔍 COINAPI FLAT FILES - TASK 1: DISCOVER SYMBOLS")
    print("=" * 80)

    # Get API key
    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Target venues
    target_venues = ["BINANCE", "KRAKEN", "COINBASE", "OKX", "BYBIT"]
    print(f"🎯 Target venues: {', '.join(target_venues)}")

    # Discover exchanges
    print(f"\n🔍 Discovering exchanges...")
    try:
        exchanges = discover_exchanges(api_key)
        print(f"✅ Found {len(exchanges)} exchanges")
    except Exception as e:
        print(f"❌ Error discovering exchanges: {e}")
        sys.exit(1)

    # Discover symbols
    print(f"\n🔍 Discovering symbols...")
    try:
        symbols = discover_symbols(api_key)
        print(f"✅ Found {len(symbols)} symbols")
    except Exception as e:
        print(f"❌ Error discovering symbols: {e}")
        sys.exit(1)

    # Filter BTC symbols
    print(f"\n🔍 Filtering BTC symbols for target venues...")
    btc_symbols = filter_btc_symbols(symbols, target_venues)

    if not btc_symbols:
        print(f"❌ No BTC symbols found for target venues")
        sys.exit(1)

    print(f"✅ Found BTC symbols for {len(btc_symbols)} exchanges")

    # Display results
    print(f"\n📊 BTC SYMBOL INVENTORY")
    print("=" * 60)

    for exchange_id, symbols_list in btc_symbols.items():
        print(f"\n{exchange_id.upper()}:")
        for i, symbol in enumerate(symbols_list[:3]):  # Show top 3
            print(f"  {i+1}. {symbol['symbol_id']} ({symbol['pair_type']})")
            if symbol.get("volume_1day_usd"):
                print(f"     Volume: ${symbol['volume_1day_usd']:,.0f}/day")
        if len(symbols_list) > 3:
            print(f"     ... and {len(symbols_list) - 3} more")

    # Save inventory
    print(f"\n💾 Saving symbol inventory...")
    try:
        s3_key = save_symbol_inventory(s3_client, args.bucket, btc_symbols, target_venues)
        print(f"✅ Saved: s3://{args.bucket}/{s3_key}")
    except Exception as e:
        print(f"❌ Error saving inventory: {e}")
        sys.exit(1)

    # Final summary
    print(f"\n📊 SYMBOL DISCOVERY SUMMARY")
    print("=" * 60)
    print(f"Target venues: {len(target_venues)}")
    print(f"Exchanges with BTC: {len(btc_symbols)}")
    print(f"Total BTC symbols: {sum(len(symbols) for symbols in btc_symbols.values())}")

    # Check if we have enough venues
    if len(btc_symbols) < 3:
        print(f"\n⚠️  WARNING: Only {len(btc_symbols)} venues have BTC symbols")
        print(f"   Need ≥3 venues for ACD analysis")
    else:
        print(f"\n✅ SUCCESS: {len(btc_symbols)} venues have BTC symbols")
        print(f"   Proceeding to Task 2: Pick Day")


if __name__ == "__main__":
    main()
