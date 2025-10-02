#!/usr/bin/env python3
"""
Reader Validation for Canonical Data

This script validates canonical data for Wave-1 analysis by checking:
- Row counts match expected values
- Price ranges are within sanity bounds
- Uniqueness constraints are satisfied
- Venue coverage is as expected

Usage:
    python analytics/reader_checks/reader_validate.py --date 20251001
"""

import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pandas as pd

# Configuration
S3_BUCKET = "acd-monitor-snapshots"
CANONICAL_PREFIX = "canonical"
ARTIFACTS_DIR = "artifacts/_checks_reader"


def load_expected_counts(date_ymd: str) -> dict:
    """Load expected counts from JSON file."""
    expected_file = Path(__file__).parent / "EXPECTED_COUNTS_20251001.json"
    with open(expected_file, 'r') as f:
        return json.load(f)


def validate_rowcounts(s3_client, date_ymd: str) -> tuple[bool, dict]:
    """Validate row counts match expected values."""
    print("🔍 Validating row counts...")

    # Load expected counts
    expected = load_expected_counts(date_ymd)

    # Read BTC data
    btc_data = []
    btc_counts = {}
    btc_venues = ['coinbase', 'kraken', 'okx']

    for venue in btc_venues:
        try:
            key = f"{CANONICAL_PREFIX}/{date_ymd}/btc_ticks/venue={venue}/part-0000.parquet"
            file_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            df = pd.read_parquet(io.BytesIO(file_obj['Body'].read()))
            btc_data.append(df)
            btc_counts[venue] = len(df)
            print(f"  BTC {venue}: {len(df):,} records")
        except Exception as e:
            print(f"  Error reading BTC {venue}: {e}")
            btc_counts[venue] = 0

    btc_total = sum(btc_counts.values())

    # Read ETH data
    eth_data = []
    eth_counts = {}
    eth_venues = ['coinbase', 'kraken']

    for venue in eth_venues:
        try:
            key = f"{CANONICAL_PREFIX}/{date_ymd}/eth_ticks/venue={venue}/part-0000.parquet"
            file_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            df = pd.read_parquet(io.BytesIO(file_obj['Body'].read()))
            eth_data.append(df)
            eth_counts[venue] = len(df)
            print(f"  ETH {venue}: {len(df):,} records")
        except Exception as e:
            print(f"  Error reading ETH {venue}: {e}")
            eth_counts[venue] = 0

    eth_total = sum(eth_counts.values())

    # Validate against expected counts
    btc_match = all(
        btc_counts.get(
            venue,
            0) == expected['btc'][venue] for venue in expected['btc'] if venue != 'total')
    eth_match = all(
        eth_counts.get(
            venue,
            0) == expected['eth'][venue] for venue in expected['eth'] if venue != 'total')
    btc_total_match = btc_total == expected['btc']['total']
    eth_total_match = eth_total == expected['eth']['total']

    validation_passed = btc_match and eth_match and btc_total_match and eth_total_match

    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'stage': 'E',
        'validation': 'rowcount_reader',
        'btc_counts': btc_counts,
        'eth_counts': eth_counts,
        'btc_total': btc_total,
        'eth_total': eth_total,
        'expected_btc': expected['btc'],
        'expected_eth': expected['eth'],
        'btc_match': btc_match,
        'eth_match': eth_match,
        'btc_total_match': btc_total_match,
        'eth_total_match': eth_total_match,
        'validation_passed': validation_passed
    }

    print(f"  ✅ Rowcount validation: {validation_passed}")
    return validation_passed, result, btc_data, eth_data


def validate_ranges(btc_data: list, eth_data: list) -> tuple[bool, dict]:
    """Validate price ranges are within sanity bounds."""
    print("🔍 Validating price ranges...")

    btc_combined = pd.concat(btc_data, ignore_index=True) if btc_data else pd.DataFrame()
    eth_combined = pd.concat(eth_data, ignore_index=True) if eth_data else pd.DataFrame()

    # BTC range validation
    btc_min = float(btc_combined['last_px'].min()) if len(btc_combined) > 0 else 0.0
    btc_max = float(btc_combined['last_px'].max()) if len(btc_combined) > 0 else 0.0
    btc_min_ok = btc_min >= 80000
    btc_max_ok = btc_max <= 118500  # ±0.5% slack vs Stage D

    # ETH range validation
    eth_min = float(eth_combined['last_px'].min()) if len(eth_combined) > 0 else 0.0
    eth_max = float(eth_combined['last_px'].max()) if len(eth_combined) > 0 else 0.0
    eth_min_ok = eth_min >= 2000
    eth_max_ok = eth_max <= 4500

    print(f"  BTC range: ${btc_min:,.2f} - ${btc_max:,.2f} "
          f"(min OK: {btc_min_ok}, max OK: {btc_max_ok})")
    print(f"  ETH range: ${eth_min:,.2f} - ${eth_max:,.2f} "
          f"(min OK: {eth_min_ok}, max OK: {eth_max_ok})")

    validation_passed = btc_min_ok and btc_max_ok and eth_min_ok and eth_max_ok

    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'stage': 'E',
        'validation': 'range_reader',
        'btc_min': btc_min,
        'btc_max': btc_max,
        'btc_min_ok': btc_min_ok,
        'btc_max_ok': btc_max_ok,
        'eth_min': eth_min,
        'eth_max': eth_max,
        'eth_min_ok': eth_min_ok,
        'eth_max_ok': eth_max_ok,
        'validation_passed': validation_passed
    }

    print(f"  ✅ Range validation: {validation_passed}")
    return validation_passed, result


def validate_uniqueness(btc_data: list, eth_data: list) -> tuple[bool, dict]:
    """Validate uniqueness constraints."""
    print("🔍 Validating uniqueness constraints...")

    btc_combined = pd.concat(btc_data, ignore_index=True) if btc_data else pd.DataFrame()
    eth_combined = pd.concat(eth_data, ignore_index=True) if eth_data else pd.DataFrame()

    # BTC uniqueness check
    btc_unique_keys = 0
    btc_total_records = 0
    if len(btc_combined) > 0:
        btc_combined['uniqueness_key'] = btc_combined['symbol'] + '|' + \
            btc_combined['venue'] + '|' + btc_combined['ts_exchange_ms'].astype(str)
        btc_unique_keys = btc_combined['uniqueness_key'].nunique()
        btc_total_records = len(btc_combined)

    # ETH uniqueness check
    eth_unique_keys = 0
    eth_total_records = 0
    if len(eth_combined) > 0:
        eth_combined['uniqueness_key'] = eth_combined['symbol'] + '|' + \
            eth_combined['venue'] + '|' + eth_combined['ts_exchange_ms'].astype(str)
        eth_unique_keys = eth_combined['uniqueness_key'].nunique()
        eth_total_records = len(eth_combined)

    btc_unique = btc_unique_keys == btc_total_records
    eth_unique = eth_unique_keys == eth_total_records

    print(f"  BTC: {btc_unique_keys:,} unique keys out of {btc_total_records:,} records")
    print(f"  ETH: {eth_unique_keys:,} unique keys out of {eth_total_records:,} records")

    validation_passed = btc_unique and eth_unique

    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'stage': 'E',
        'validation': 'uniqueness_reader',
        'btc_unique_keys': btc_unique_keys,
        'btc_total_records': btc_total_records,
        'eth_unique_keys': eth_unique_keys,
        'eth_total_records': eth_total_records,
        'btc_unique': btc_unique,
        'eth_unique': eth_unique,
        'validation_passed': validation_passed
    }

    print(f"  ✅ Uniqueness validation: {validation_passed}")
    return validation_passed, result


def validate_venues(btc_data: list, eth_data: list) -> tuple[bool, dict]:
    """Validate venue coverage."""
    print("🔍 Validating venue coverage...")

    btc_combined = pd.concat(btc_data, ignore_index=True) if btc_data else pd.DataFrame()
    eth_combined = pd.concat(eth_data, ignore_index=True) if eth_data else pd.DataFrame()

    # BTC venues
    btc_venues = set(btc_combined['venue'].unique()) if len(btc_combined) > 0 else set()
    expected_btc_venues = {'coinbase', 'kraken', 'okx'}
    btc_venues_ok = btc_venues == expected_btc_venues

    # ETH venues
    eth_venues = set(eth_combined['venue'].unique()) if len(eth_combined) > 0 else set()
    expected_eth_venues = {'coinbase', 'kraken'}
    eth_venues_ok = eth_venues == expected_eth_venues

    # Check no bybit present
    no_bybit_btc = 'bybit' not in btc_venues
    no_bybit_eth = 'bybit' not in eth_venues

    print(f"  BTC venues: {sorted(btc_venues)} (expected: {sorted(expected_btc_venues)})")
    print(f"  ETH venues: {sorted(eth_venues)} (expected: {sorted(expected_eth_venues)})")
    print(f"  No bybit in BTC: {no_bybit_btc}")
    print(f"  No bybit in ETH: {no_bybit_eth}")

    validation_passed = btc_venues_ok and eth_venues_ok and no_bybit_btc and no_bybit_eth

    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'stage': 'E',
        'validation': 'venues_reader',
        'btc_venues': sorted(btc_venues),
        'eth_venues': sorted(eth_venues),
        'expected_btc_venues': sorted(expected_btc_venues),
        'expected_eth_venues': sorted(expected_eth_venues),
        'btc_venues_ok': btc_venues_ok,
        'eth_venues_ok': eth_venues_ok,
        'no_bybit_btc': no_bybit_btc,
        'no_bybit_eth': no_bybit_eth,
        'validation_passed': validation_passed
    }

    print(f"  ✅ Venues validation: {validation_passed}")
    return validation_passed, result


def save_results(s3_client, date_ymd: str, results: dict):
    """Save validation results to both S3 and local artifacts."""
    print("💾 Saving validation results...")

    # Create artifacts directory
    artifacts_path = Path(ARTIFACTS_DIR)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    # Save each validation result
    for validation_name, result in results.items():
        if validation_name == 'summary':
            continue

        # Save to S3
        s3_key = f"{CANONICAL_PREFIX}/{date_ymd}/_checks_reader/{validation_name}.json"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(result, indent=2)
        )

        # Save to local artifacts
        local_file = artifacts_path / f"{validation_name}.json"
        with open(local_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"  Saved {validation_name}.json")

    # Save summary
    summary = results['summary']
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=f"{CANONICAL_PREFIX}/{date_ymd}/_checks_reader/final_summary.json",
        Body=json.dumps(summary, indent=2)
    )

    local_summary = artifacts_path / "final_summary.json"
    with open(local_summary, 'w') as f:
        json.dump(summary, f, indent=2)

    print("  Saved final_summary.json")


def main():
    parser = argparse.ArgumentParser(description='Validate canonical data for Wave-1 analysis')
    parser.add_argument('--date', required=True, help='Date in YYYYMMDD format (e.g., 20251001)')
    args = parser.parse_args()

    print(f"🔍 Validating canonical data for {args.date}")

    # Initialize S3 client
    s3_client = boto3.client('s3')

    # Run validations
    rowcount_passed, rowcount_result, btc_data, eth_data = validate_rowcounts(s3_client, args.date)
    range_passed, range_result = validate_ranges(btc_data, eth_data)
    uniqueness_passed, uniqueness_result = validate_uniqueness(btc_data, eth_data)
    venues_passed, venues_result = validate_venues(btc_data, eth_data)

    # Create summary
    all_passed = rowcount_passed and range_passed and uniqueness_passed and venues_passed
    summary = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'stage': 'E',
        'status': 'COMPLETED' if all_passed else 'FAILED',
        'date': args.date,
        'validations_passed': all_passed,
        'rowcount_passed': rowcount_passed,
        'range_passed': range_passed,
        'uniqueness_passed': uniqueness_passed,
        'venues_passed': venues_passed,
        'ready_for_wave1': all_passed
    }

    # Save results
    results = {
        'rowcount_reader': rowcount_result,
        'range_reader': range_result,
        'uniqueness_reader': uniqueness_result,
        'venues_reader': venues_result,
        'summary': summary
    }

    save_results(s3_client, args.date, results)

    # Final status
    if all_passed:
        print("✅ All validations passed - ready for Wave-1 analysis")
        return 0
    else:
        print("❌ Some validations failed - not ready for Wave-1 analysis")
        return 1


if __name__ == "__main__":
    exit(main())
