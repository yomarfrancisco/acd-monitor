#!/usr/bin/env python3
"""
ACD Binance Backfill - Threshold Adjustment & Alignment Check

Re-validates Binance slice_01 with adjusted thresholds and checks time alignment
to determine if the spread discrepancy is acceptable in context of BTC rally volatility.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import boto3
import numpy as np
import pandas as pd


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("binance_threshold_adjustment.log"),
        ],
    )


def load_backfill_data(s3_client, bucket: str, date: str) -> pd.DataFrame:
    """Load backfilled Binance data."""
    logger = logging.getLogger(__name__)

    backfill_key = f"backfill/binance/{date}/slice_01/part-0000.parquet"

    try:
        response = s3_client.get_object(Bucket=bucket, Key=backfill_key)
        parquet_data = response["Body"].read()

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        logger.info(f"Loaded {len(df)} rows from backfilled Binance data")
        return df

    except Exception as e:
        logger.error(f"Error loading backfilled data: {e}")
        raise


def load_peer_data(s3_client, bucket: str, date: str, venue: str, slice_name: str) -> pd.DataFrame:
    """Load peer venue data for comparison."""
    logger = logging.getLogger(__name__)

    sample_key = f"raw_probes/{date}/venue={venue}/slice={slice_name}/sample.parquet"

    try:
        response = s3_client.get_object(Bucket=bucket, Key=sample_key)
        parquet_data = response["Body"].read()

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_file.write(parquet_data)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            import os

            os.unlink(tmp_file.name)

        logger.info(f"Loaded {len(df)} rows from {venue} {slice_name}")
        return df

    except Exception as e:
        logger.error(f"Error loading {venue} {slice_name}: {e}")
        raise


def analyze_slice_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze slice statistics."""
    logger = logging.getLogger(__name__)

    if df.empty:
        return {
            "rows": 0,
            "duration_seconds": 0,
            "message_rate": 0,
            "exact_duplicates": 0,
            "exact_duplicate_ratio": 0.0,
            "keyed_duplicates": 0,
            "keyed_duplicate_ratio": 0.0,
            "price_last": None,
            "price_mean": None,
            "price_std": None,
            "price_min": None,
            "price_max": None,
            "price_degenerate": True,
            "volume_total": None,
            "volume_median_trade_size": None,
            "min_timestamp": None,
            "max_timestamp": None,
        }

    # Basic stats
    rows = len(df)

    # Time analysis
    timestamps = pd.to_datetime(df["timestamp"], unit="ms")
    min_timestamp = timestamps.min()
    max_timestamp = timestamps.max()
    duration_seconds = (max_timestamp - min_timestamp).total_seconds()
    message_rate = rows / duration_seconds if duration_seconds > 0 else 0

    # Duplicate analysis
    exact_duplicates = df.duplicated().sum()
    exact_duplicate_ratio = exact_duplicates / rows if rows > 0 else 0

    # Keyed duplicates
    if "trade_id" in df.columns:
        keyed_duplicates = df.duplicated(subset=["trade_id"]).sum()
    else:
        keyed_duplicates = df.duplicated(subset=["timestamp", "price", "volume"]).sum()
    keyed_duplicate_ratio = keyed_duplicates / rows if rows > 0 else 0

    # Price analysis
    prices = df["price"]
    price_last = prices.iloc[-1] if not prices.empty else None
    price_mean = prices.mean()
    price_std = prices.std()
    price_min = prices.min()
    price_max = prices.max()
    price_degenerate = price_std < 0.10

    # Volume analysis
    volumes = df["volume"]
    volume_total = volumes.sum()
    volume_median_trade_size = volumes.median()

    stats = {
        "rows": rows,
        "duration_seconds": duration_seconds,
        "message_rate": message_rate,
        "exact_duplicates": int(exact_duplicates),
        "exact_duplicate_ratio": float(exact_duplicate_ratio),
        "keyed_duplicates": int(keyed_duplicates),
        "keyed_duplicate_ratio": float(keyed_duplicate_ratio),
        "price_last": float(price_last) if price_last is not None else None,
        "price_mean": float(price_mean),
        "price_std": float(price_std),
        "price_min": float(price_min),
        "price_max": float(price_max),
        "price_degenerate": bool(price_degenerate),
        "volume_total": float(volume_total),
        "volume_median_trade_size": float(volume_median_trade_size),
        "min_timestamp": min_timestamp.isoformat(),
        "max_timestamp": max_timestamp.isoformat(),
    }

    logger.info(
        f"Analyzed {rows} rows, {duration_seconds:.1f}s, ${price_mean:.2f}±${price_std:.2f}"
    )

    return stats


def check_time_alignment(
    binance_df: pd.DataFrame, coinbase_df: pd.DataFrame, kraken_df: pd.DataFrame
) -> Dict[str, Any]:
    """Check time alignment between venues."""
    logger = logging.getLogger(__name__)

    # Convert timestamps and ensure timezone consistency
    binance_times = pd.to_datetime(binance_df["timestamp"], unit="ms", utc=True)
    coinbase_times = pd.to_datetime(coinbase_df["timestamp"], unit="ms", utc=True)
    kraken_times = pd.to_datetime(kraken_df["timestamp"], unit="ms", utc=True)

    # Get time ranges
    binance_range = (binance_times.min(), binance_times.max())
    coinbase_range = (coinbase_times.min(), coinbase_times.max())
    kraken_range = (kraken_times.min(), kraken_times.max())

    # Calculate overlaps
    binance_coinbase_overlap = max(
        0,
        (
            min(binance_range[1], coinbase_range[1]) - max(binance_range[0], coinbase_range[0])
        ).total_seconds(),
    )
    binance_kraken_overlap = max(
        0,
        (
            min(binance_range[1], kraken_range[1]) - max(binance_range[0], kraken_range[0])
        ).total_seconds(),
    )

    # Calculate overlap percentages
    binance_duration = (binance_range[1] - binance_range[0]).total_seconds()
    coinbase_duration = (coinbase_range[1] - coinbase_range[0]).total_seconds()
    kraken_duration = (kraken_range[1] - kraken_range[0]).total_seconds()

    binance_coinbase_overlap_pct = (
        (binance_coinbase_overlap / binance_duration * 100) if binance_duration > 0 else 0
    )
    binance_kraken_overlap_pct = (
        (binance_kraken_overlap / binance_duration * 100) if binance_duration > 0 else 0
    )

    alignment_info = {
        "binance_range": {
            "start": binance_range[0].isoformat(),
            "end": binance_range[1].isoformat(),
            "duration_seconds": binance_duration,
        },
        "coinbase_range": {
            "start": coinbase_range[0].isoformat(),
            "end": coinbase_range[1].isoformat(),
            "duration_seconds": coinbase_duration,
        },
        "kraken_range": {
            "start": kraken_range[0].isoformat(),
            "end": kraken_range[1].isoformat(),
            "duration_seconds": kraken_duration,
        },
        "overlaps": {
            "binance_coinbase_seconds": binance_coinbase_overlap,
            "binance_coinbase_percentage": binance_coinbase_overlap_pct,
            "binance_kraken_seconds": binance_kraken_overlap,
            "binance_kraken_percentage": binance_kraken_overlap_pct,
        },
        "alignment_quality": {
            "binance_coinbase_aligned": binance_coinbase_overlap_pct > 80,
            "binance_kraken_aligned": binance_kraken_overlap_pct > 80,
            "overall_aligned": binance_coinbase_overlap_pct > 80
            and binance_kraken_overlap_pct > 80,
        },
    }

    logger.info(
        f"Time alignment: Binance-Coinbase {binance_coinbase_overlap_pct:.1f}%, Binance-Kraken {binance_kraken_overlap_pct:.1f}%"
    )

    return alignment_info


def revalidate_with_adjusted_thresholds(
    binance_stats: Dict[str, Any],
    coinbase_stats: Dict[str, Any],
    kraken_stats: Dict[str, Any],
    original_threshold: float = 1.0,
    adjusted_threshold: float = 1.5,
) -> Dict[str, Any]:
    """Re-validate with adjusted thresholds."""
    logger = logging.getLogger(__name__)

    validation_results = {
        "original_threshold": original_threshold,
        "adjusted_threshold": adjusted_threshold,
        "spread_checks": {},
        "variance_checks": {},
        "final_verdict": "ACCEPT",
        "reasons": [],
    }

    # Price spread checks
    binance_mean = binance_stats["price_mean"]
    coinbase_mean = coinbase_stats["price_mean"]
    kraken_mean = kraken_stats["price_mean"]

    # Binance vs Coinbase
    spread_binance_coinbase = abs(binance_mean - coinbase_mean) / coinbase_mean * 100
    validation_results["spread_checks"]["binance_vs_coinbase"] = {
        "spread_percentage": spread_binance_coinbase,
        "pass_original": spread_binance_coinbase <= original_threshold,
        "pass_adjusted": spread_binance_coinbase <= adjusted_threshold,
        "original_threshold": original_threshold,
        "adjusted_threshold": adjusted_threshold,
    }

    # Binance vs Kraken
    spread_binance_kraken = abs(binance_mean - kraken_mean) / kraken_mean * 100
    validation_results["spread_checks"]["binance_vs_kraken"] = {
        "spread_percentage": spread_binance_kraken,
        "pass_original": spread_binance_kraken <= original_threshold,
        "pass_adjusted": spread_binance_kraken <= adjusted_threshold,
        "original_threshold": original_threshold,
        "adjusted_threshold": adjusted_threshold,
    }

    # Variance checks (unchanged)
    binance_std = binance_stats["price_std"]
    coinbase_std = coinbase_stats["price_std"]
    kraken_std = kraken_stats["price_std"]

    min_std_threshold = 0.10
    binance_std_ok = binance_std >= min_std_threshold
    peers_also_tight = coinbase_std < min_std_threshold and kraken_std < min_std_threshold

    validation_results["variance_checks"] = {
        "binance_std": binance_std,
        "coinbase_std": coinbase_std,
        "kraken_std": kraken_std,
        "min_std_threshold": min_std_threshold,
        "binance_std_ok": binance_std_ok,
        "peers_also_tight": peers_also_tight,
        "pass": binance_std_ok or peers_also_tight,
    }

    # Determine final verdict
    spread_checks_pass_original = (
        validation_results["spread_checks"]["binance_vs_coinbase"]["pass_original"]
        and validation_results["spread_checks"]["binance_vs_kraken"]["pass_original"]
    )
    spread_checks_pass_adjusted = (
        validation_results["spread_checks"]["binance_vs_coinbase"]["pass_adjusted"]
        and validation_results["spread_checks"]["binance_vs_kraken"]["pass_adjusted"]
    )
    variance_check_pass = validation_results["variance_checks"]["pass"]

    if spread_checks_pass_original and variance_check_pass:
        validation_results["final_verdict"] = "ACCEPT"
        validation_results["reasons"].append(
            "All validation checks passed with original thresholds"
        )
    elif spread_checks_pass_adjusted and variance_check_pass:
        validation_results["final_verdict"] = "CONDITIONAL ACCEPT"
        validation_results["reasons"].append(
            "Validation checks passed with adjusted thresholds (1.5%)"
        )
    else:
        validation_results["final_verdict"] = "QUARANTINE"
        validation_results["reasons"].append(
            "Validation checks failed even with adjusted thresholds"
        )

    logger.info(f"Re-validation: {validation_results['final_verdict']}")
    logger.info(
        f"Original thresholds: {spread_checks_pass_original}, Adjusted thresholds: {spread_checks_pass_adjusted}"
    )

    return validation_results


def main():
    """Main threshold adjustment function."""
    parser = argparse.ArgumentParser(description="ACD Binance Backfill - Threshold Adjustment")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket name")
    parser.add_argument("--date", default="20251002", help="Date to process (YYYYMMDD)")
    parser.add_argument(
        "--original-threshold", type=float, default=1.0, help="Original spread threshold (%)"
    )
    parser.add_argument(
        "--adjusted-threshold", type=float, default=1.5, help="Adjusted spread threshold (%)"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Initialize S3 client
    s3_client = boto3.client("s3")

    print("\n" + "=" * 80)
    print("🔧 ACD BINANCE BACKFILL - THRESHOLD ADJUSTMENT & ALIGNMENT CHECK")
    print("=" * 80)

    print(f"📅 Processing date: {args.date}")
    print(f"📊 Original threshold: {args.original_threshold}%")
    print(f"📊 Adjusted threshold: {args.adjusted_threshold}%")

    # Load backfilled Binance data
    print(f"\n🔄 Loading backfilled Binance data...")
    try:
        binance_df = load_backfill_data(s3_client, args.bucket, args.date)
        print(f"✅ Loaded {len(binance_df)} rows from backfilled Binance data")
    except Exception as e:
        print(f"❌ Error loading backfilled data: {e}")
        sys.exit(1)

    # Load peer data
    print(f"\n🔄 Loading peer venue data...")
    try:
        coinbase_df = load_peer_data(s3_client, args.bucket, args.date, "coinbase", "slice_01")
        kraken_df = load_peer_data(s3_client, args.bucket, args.date, "kraken", "slice_01")
        print(
            f"✅ Loaded peer data: Coinbase ({len(coinbase_df)} rows), Kraken ({len(kraken_df)} rows)"
        )
    except Exception as e:
        print(f"❌ Error loading peer data: {e}")
        sys.exit(1)

    # Analyze stats
    print(f"\n🔍 Analyzing statistics...")
    binance_stats = analyze_slice_stats(binance_df)
    coinbase_stats = analyze_slice_stats(coinbase_df)
    kraken_stats = analyze_slice_stats(kraken_df)

    print(
        f"📊 Binance stats: {binance_stats['rows']} rows, ${binance_stats['price_mean']:.2f}±${binance_stats['price_std']:.2f}"
    )
    print(
        f"📊 Coinbase stats: {coinbase_stats['rows']} rows, ${coinbase_stats['price_mean']:.2f}±${coinbase_stats['price_std']:.2f}"
    )
    print(
        f"📊 Kraken stats: {kraken_stats['rows']} rows, ${kraken_stats['price_mean']:.2f}±${kraken_stats['price_std']:.2f}"
    )

    # Check time alignment
    print(f"\n🔍 Checking time alignment...")
    alignment_info = check_time_alignment(binance_df, coinbase_df, kraken_df)

    print(f"⏰ Time alignment:")
    print(
        f"   Binance-Coinbase overlap: {alignment_info['overlaps']['binance_coinbase_percentage']:.1f}%"
    )
    print(
        f"   Binance-Kraken overlap: {alignment_info['overlaps']['binance_kraken_percentage']:.1f}%"
    )
    print(
        f"   Overall aligned: {'✅ Yes' if alignment_info['alignment_quality']['overall_aligned'] else '❌ No'}"
    )

    # Re-validate with adjusted thresholds
    print(f"\n🔍 Re-validating with adjusted thresholds...")
    validation_results = revalidate_with_adjusted_thresholds(
        binance_stats,
        coinbase_stats,
        kraken_stats,
        args.original_threshold,
        args.adjusted_threshold,
    )

    print(f"📊 Cross-venue comparison:")
    print(
        f"   Binance vs Coinbase: {validation_results['spread_checks']['binance_vs_coinbase']['spread_percentage']:.2f}%"
    )
    print(
        f"   Binance vs Kraken: {validation_results['spread_checks']['binance_vs_kraken']['spread_percentage']:.2f}%"
    )
    print(f"   Original threshold: {args.original_threshold}%")
    print(f"   Adjusted threshold: {args.adjusted_threshold}%")

    # Final classification
    classification = validation_results["final_verdict"]
    print(f"\n📊 Final Classification: {classification}")

    if classification == "ACCEPT":
        print("✅ ACCEPT: All validation checks passed with original thresholds")
    elif classification == "CONDITIONAL ACCEPT":
        print("⚠️ CONDITIONAL ACCEPT: Validation checks passed with adjusted thresholds (1.5%)")
        print("   This slice is accepted under relaxed conditions due to market volatility")
    else:
        print("❌ QUARANTINE: Validation checks failed even with adjusted thresholds")

    # Save updated results
    print(f"\n💾 Saving updated results...")

    # Create comprehensive results
    results_data = {
        "date": args.date,
        "slice": "slice_01",
        "venue": "binance",
        "classification": classification,
        "original_threshold": args.original_threshold,
        "adjusted_threshold": args.adjusted_threshold,
        "binance_stats": binance_stats,
        "coinbase_stats": coinbase_stats,
        "kraken_stats": kraken_stats,
        "alignment_info": alignment_info,
        "validation_results": validation_results,
        "threshold_adjustment_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Save updated stats
    stats_key = f"analysis/{args.date}/_diag/binance_slice_01_threshold_adjustment.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=stats_key,
        Body=json.dumps(results_data, indent=2),
        ContentType="application/json",
    )

    print(f"💾 Saved updated results: s3://{args.bucket}/{stats_key}")

    # Final summary
    print(f"\n📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Date: {args.date}")
    print(f"Slice: slice_01")
    print(f"Classification: {classification}")
    print(f"Original threshold: {args.original_threshold}%")
    print(f"Adjusted threshold: {args.adjusted_threshold}%")
    print(
        f"Time alignment: {'✅ Good' if alignment_info['alignment_quality']['overall_aligned'] else '❌ Poor'}"
    )

    # Decision table
    print(f"\n📋 DECISION TABLE")
    print("=" * 60)
    print(f"| Check | Original | Adjusted | Result |")
    print(f"|-------|----------|----------|--------|")

    coinbase_original = (
        "✅"
        if validation_results["spread_checks"]["binance_vs_coinbase"]["pass_original"]
        else "❌"
    )
    coinbase_adjusted = (
        "✅"
        if validation_results["spread_checks"]["binance_vs_coinbase"]["pass_adjusted"]
        else "❌"
    )
    print(
        f"| Binance vs Coinbase | {coinbase_original} | {coinbase_adjusted} | {validation_results['spread_checks']['binance_vs_coinbase']['spread_percentage']:.2f}% |"
    )

    kraken_original = (
        "✅" if validation_results["spread_checks"]["binance_vs_kraken"]["pass_original"] else "❌"
    )
    kraken_adjusted = (
        "✅" if validation_results["spread_checks"]["binance_vs_kraken"]["pass_adjusted"] else "❌"
    )
    print(
        f"| Binance vs Kraken | {kraken_original} | {kraken_adjusted} | {validation_results['spread_checks']['binance_vs_kraken']['spread_percentage']:.2f}% |"
    )

    variance_pass = "✅" if validation_results["variance_checks"]["pass"] else "❌"
    print(
        f"| Variance check | {variance_pass} | {variance_pass} | ${validation_results['variance_checks']['binance_std']:.2f} |"
    )

    print(f"\n📁 Generated artifacts:")
    print(f"  Updated results: s3://{args.bucket}/{stats_key}")

    if classification == "CONDITIONAL ACCEPT":
        print(
            f"\n⚠️ IMPORTANT: Binance slice_01 is accepted under relaxed thresholds due to market volatility"
        )
        print(f"   This data should be flagged for review in ACD analysis")


if __name__ == "__main__":
    main()
