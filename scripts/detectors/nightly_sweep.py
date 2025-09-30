#!/usr/bin/env python3
"""
Nightly Detector Sweep

This script runs detectors on all windows from the last 24 hours that meet quality gates:
- venues_ok=YES (≥3 venues, ≥95% coverage each)
- Only BTC-USD and ETH-USD
- Writes results to S3 under detectors/<symbol>/<date>/<window>/
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import pandas as pd

# Add src to path for acdlib imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def get_eligible_windows(bucket: str, prefix: str, hours_back: int = 24) -> List[Dict]:
    """Get windows from last 24h that meet quality gates."""
    s3_client = boto3.client("s3")
    eligible_windows = []

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)

    # List all windows in the time range
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket, Prefix=f"{prefix}/", Delimiter="/"
        )

        for prefix_obj in response.get("CommonPrefixes", []):
            symbol_prefix = prefix_obj["Prefix"]
            symbol = symbol_prefix.split("/")[-2]  # Extract symbol from path

            if symbol not in ["BTC-USD", "ETH-USD"]:
                continue

            # List windows for this symbol
            symbol_response = s3_client.list_objects_v2(
                Bucket=bucket, Prefix=symbol_prefix
            )

            for window_obj in symbol_response.get("CommonPrefixes", []):
                window_path = window_obj["Prefix"]
                window_name = window_path.split("/")[-2]  # Extract window name

                # Check if this window meets quality gates
                if check_window_quality(s3_client, bucket, window_path):
                    eligible_windows.append(
                        {
                            "symbol": symbol,
                            "window": window_name,
                            "s3_path": window_path,
                            "overlap_path": f"{window_path}OVERLAP.json",
                        }
                    )

    except Exception as e:
        logger.error(f"Error listing windows: {e}")
        return []

    return eligible_windows


def check_window_quality(s3_client, bucket: str, window_path: str) -> bool:
    """Check if a window meets quality gates (venues_ok=YES)."""
    try:
        # Load coverage data
        coverage_key = f"{window_path}meta/coverage.json"
        try:
            coverage_response = s3_client.get_object(Bucket=bucket, Key=coverage_key)
            coverage_data = json.loads(coverage_response["Body"].read())
        except s3_client.exceptions.NoSuchKey:
            # No coverage data available
            return False

        # Check venues and coverage
        venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        high_coverage_venues = 0

        for venue in venues:
            if venue in coverage_data:
                coverage_pct = coverage_data[venue].get("coverage_percentage", 0)
                if coverage_pct >= 95.0:
                    high_coverage_venues += 1

        # Must have ≥3 venues with ≥95% coverage
        return high_coverage_venues >= 3

    except Exception as e:
        logger.warning(f"Error checking quality for {window_path}: {e}")
        return False


def run_spread_v2_detector(
    symbol: str, window: str, overlap_path: str, bucket: str, output_prefix: str
) -> Dict:
    """Run Spread v2 detector on a window."""
    try:
        # Import here to avoid circular imports
        from scripts.detect.spread_v2_detect import run_spread_v2_analysis

        # Run the detector
        result = run_spread_v2_analysis(
            snapshot_path=f"s3://{bucket}/{overlap_path}",
            roll_window=60,
            z_threshold=-1.5,
            min_duration=10,
            merge_gap=2,
            mc_k=5,
            mc_per_episode=100,
            mc_gap=10,
            bb_size=10,
            bb_n=1000,
            fdr=0.05,
            seed=42,
        )

        return {
            "status": "success",
            "episodes_found": len(result.get("episodes", [])),
            "result": result,
        }

    except Exception as e:
        logger.error(f"Spread v2 failed for {symbol}/{window}: {e}")
        return {"status": "error", "error": str(e)}


def run_leadlag_v2_detector(
    symbol: str, window: str, overlap_path: str, bucket: str, output_prefix: str
) -> Dict:
    """Run Lead-Lag v2 detector on a window."""
    try:
        # Import here to avoid circular imports
        from scripts.detect.leadlag_v2 import run_leadlag_v2_analysis

        # Run the detector
        result = run_leadlag_v2_analysis(
            snapshot_path=f"s3://{bucket}/{overlap_path}",
            horizons=[1, 5, 10, 30],
            rho_min=0.12,
            alpha=0.10,
            bootstrap=300,
            block_size=10,
            placebo_shifts=[-60, 60],
            seed=42,
        )

        return {
            "status": "success",
            "edges_found": len(result.get("edges", [])),
            "result": result,
        }

    except Exception as e:
        logger.error(f"Lead-Lag v2 failed for {symbol}/{window}: {e}")
        return {"status": "error", "error": str(e)}


def run_infoshare_v2_detector(
    symbol: str, window: str, overlap_path: str, bucket: str, output_prefix: str
) -> Dict:
    """Run InfoShare v2 detector on a window."""
    try:
        # Import here to avoid circular imports
        from scripts.detect.infoshare_v2 import run_infoshare_v2_analysis

        # Run the detector
        result = run_infoshare_v2_analysis(
            snapshot_path=f"s3://{bucket}/{overlap_path}",
            cadences=["1s"],
            vecm_lags="auto",
            bootstrap=300,
            seed=42,
        )

        return {
            "status": "success",
            "rank": result.get("cointegration_rank", 0),
            "result": result,
        }

    except Exception as e:
        logger.error(f"InfoShare v2 failed for {symbol}/{window}: {e}")
        return {"status": "error", "error": str(e)}


def save_detector_results(
    s3_client, bucket: str, symbol: str, window: str, detector: str, results: Dict
):
    """Save detector results to S3."""
    try:
        # Construct output path
        date_str = datetime.utcnow().strftime("%Y%m%d")
        output_key = f"detectors/{symbol}/{date_str}/{window}/{detector}_results.json"

        # Save results
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=json.dumps(results, indent=2),
            ContentType="application/json",
        )

        logger.info(f"Saved {detector} results to s3://{bucket}/{output_key}")

    except Exception as e:
        logger.error(f"Failed to save {detector} results: {e}")


def main():
    parser = argparse.ArgumentParser(description="Nightly Detector Sweep")
    parser.add_argument(
        "--bucket", default="acd-monitor-snapshots", help="S3 bucket name"
    )
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix for snapshots")
    parser.add_argument(
        "--hours-back", type=int, default=24, help="Hours to look back for windows"
    )
    parser.add_argument(
        "--detectors",
        nargs="+",
        default=["spread_v2", "leadlag_v2", "infoshare_v2"],
        help="Detectors to run",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger.info("Starting nightly detector sweep")
    logger.info(f"Looking for windows from last {args.hours_back} hours")
    logger.info(f"Running detectors: {', '.join(args.detectors)}")

    # Get eligible windows
    eligible_windows = get_eligible_windows(args.bucket, args.prefix, args.hours_back)
    logger.info(f"Found {len(eligible_windows)} eligible windows")

    if not eligible_windows:
        logger.warning("No eligible windows found")
        return

    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Run detectors on each window
    total_results = {
        "spread_v2": {"windows_run": 0, "episodes_found": [], "errors": 0},
        "leadlag_v2": {"windows_run": 0, "edges_found": [], "errors": 0},
        "infoshare_v2": {"windows_run": 0, "rank_gt_0": 0, "errors": 0},
    }

    for window_info in eligible_windows:
        symbol = window_info["symbol"]
        window = window_info["window"]
        overlap_path = window_info["overlap_path"]

        logger.info(f"Processing {symbol}/{window}")

        # Run each detector
        for detector in args.detectors:
            if detector == "spread_v2":
                results = run_spread_v2_detector(
                    symbol, window, overlap_path, args.bucket, args.prefix
                )
                total_results["spread_v2"]["windows_run"] += 1
                if results["status"] == "success":
                    total_results["spread_v2"]["episodes_found"].append(
                        results["episodes_found"]
                    )
                else:
                    total_results["spread_v2"]["errors"] += 1

            elif detector == "leadlag_v2":
                results = run_leadlag_v2_detector(
                    symbol, window, overlap_path, args.bucket, args.prefix
                )
                total_results["leadlag_v2"]["windows_run"] += 1
                if results["status"] == "success":
                    total_results["leadlag_v2"]["edges_found"].append(
                        results["edges_found"]
                    )
                else:
                    total_results["leadlag_v2"]["errors"] += 1

            elif detector == "infoshare_v2":
                results = run_infoshare_v2_detector(
                    symbol, window, overlap_path, args.bucket, args.prefix
                )
                total_results["infoshare_v2"]["windows_run"] += 1
                if results["status"] == "success":
                    if results["rank"] > 0:
                        total_results["infoshare_v2"]["rank_gt_0"] += 1
                else:
                    total_results["infoshare_v2"]["errors"] += 1

            # Save results
            save_detector_results(
                s3_client, args.bucket, symbol, window, detector, results
            )

    # Print summary
    logger.info("=== Nightly Sweep Summary ===")
    for detector, stats in total_results.items():
        if detector == "spread_v2":
            median_episodes = (
                sorted(stats["episodes_found"])[len(stats["episodes_found"]) // 2]
                if stats["episodes_found"]
                else 0
            )
            logger.info(
                f"Spread v2: {stats['windows_run']} windows, {median_episodes} median episodes, {stats['errors']} errors"
            )
        elif detector == "leadlag_v2":
            median_edges = (
                sorted(stats["edges_found"])[len(stats["edges_found"]) // 2]
                if stats["edges_found"]
                else 0
            )
            logger.info(
                f"Lead-Lag v2: {stats['windows_run']} windows, {median_edges} median edges, {stats['errors']} errors"
            )
        elif detector == "infoshare_v2":
            logger.info(
                f"InfoShare v2: {stats['windows_run']} windows, {stats['rank_gt_0']} with rank>0, {stats['errors']} errors"
            )

    logger.info("Nightly detector sweep completed")


if __name__ == "__main__":
    main()
