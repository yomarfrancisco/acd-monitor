#!/usr/bin/env python3
"""
Coverage Monitoring and Quality Gating

This script monitors venue coverage across windows and ensures quality gates
are met before running detectors.
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

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def check_window_coverage(
    symbol: str, date: str, time_range: str, bucket: str, prefix: str
) -> Dict:
    """Check coverage for a specific window."""
    try:
        s3_client = boto3.client("s3")

        # Construct S3 paths
        overlap_key = f"{prefix}/{symbol}/{date}/{time_range}/OVERLAP.json"
        coverage_key = f"{prefix}/{symbol}/{date}/{time_range}/meta/coverage.json"

        # Load OVERLAP.json
        try:
            overlap_response = s3_client.get_object(Bucket=bucket, Key=overlap_key)
            overlap_data = json.loads(overlap_response["Body"].read())
        except s3_client.exceptions.NoSuchKey:
            return {"status": "missing", "reason": "OVERLAP.json not found"}

        # Load coverage.json if available
        coverage_data = {}
        try:
            coverage_response = s3_client.get_object(Bucket=bucket, Key=coverage_key)
            coverage_data = json.loads(coverage_response["Body"].read())
        except s3_client.exceptions.NoSuchKey:
            # Use coverage from OVERLAP.json
            coverage_data = {
                venue: {"coverage_percentage": overlap_data["coverage"][venue] * 100}
                for venue in overlap_data["venues"]
            }

        # Calculate coverage statistics
        venues = overlap_data["venues"]
        coverage_percentages = [
            coverage_data.get(venue, {}).get("coverage_percentage", 0)
            for venue in venues
        ]

        high_coverage_venues = [
            venue
            for venue, data in coverage_data.items()
            if data.get("coverage_percentage", 0) >= 95.0
        ]

        return {
            "status": "available",
            "window": f"{symbol}/{date}/{time_range}",
            "venues": venues,
            "coverage_data": coverage_data,
            "high_coverage_venues": high_coverage_venues,
            "venues_count": len(venues),
            "high_coverage_count": len(high_coverage_venues),
            "meets_threshold": len(high_coverage_venues) >= 3,
            "min_coverage": min(coverage_percentages) if coverage_percentages else 0,
            "max_coverage": max(coverage_percentages) if coverage_percentages else 0,
            "avg_coverage": (
                sum(coverage_percentages) / len(coverage_percentages)
                if coverage_percentages
                else 0
            ),
        }

    except Exception as e:
        logger.error(f"Error checking coverage for {symbol}/{date}/{time_range}: {e}")
        return {"status": "error", "reason": str(e)}


def generate_coverage_report(
    symbols: List[str], days_back: int, bucket: str, prefix: str
) -> Dict:
    """Generate coverage report for recent windows."""
    try:
        s3_client = boto3.client("s3")

        # Get list of all windows
        windows = []
        for symbol in symbols:
            try:
                response = s3_client.list_objects_v2(
                    Bucket=bucket, Prefix=f"{prefix}/{symbol}/", Delimiter="/"
                )

                for obj in response.get("CommonPrefixes", []):
                    date_path = obj["Prefix"].split("/")[-2]
                    if date_path:
                        # List time ranges for this date
                        date_response = s3_client.list_objects_v2(
                            Bucket=bucket,
                            Prefix=f"{prefix}/{symbol}/{date_path}/",
                            Delimiter="/",
                        )

                        for time_obj in date_response.get("CommonPrefixes", []):
                            time_range = time_obj["Prefix"].split("/")[-2]
                            if time_range and "-" in time_range:
                                windows.append((symbol, date_path, time_range))

            except Exception as e:
                logger.error(f"Error listing windows for {symbol}: {e}")
                continue

        # Check coverage for each window
        coverage_results = []
        for symbol, date, time_range in windows:
            result = check_window_coverage(symbol, date, time_range, bucket, prefix)
            coverage_results.append(result)

        # Generate summary statistics
        total_windows = len(coverage_results)
        available_windows = len(
            [r for r in coverage_results if r.get("status") == "available"]
        )
        meets_threshold_windows = len(
            [r for r in coverage_results if r.get("meets_threshold", False)]
        )

        # Venue performance summary
        venue_stats = {}
        for result in coverage_results:
            if result.get("status") == "available":
                for venue, data in result.get("coverage_data", {}).items():
                    if venue not in venue_stats:
                        venue_stats[venue] = {
                            "windows": 0,
                            "total_coverage": 0,
                            "high_coverage": 0,
                        }

                    venue_stats[venue]["windows"] += 1
                    venue_stats[venue]["total_coverage"] += data.get(
                        "coverage_percentage", 0
                    )
                    if data.get("coverage_percentage", 0) >= 95.0:
                        venue_stats[venue]["high_coverage"] += 1

        # Calculate venue averages
        for venue, stats in venue_stats.items():
            if stats["windows"] > 0:
                stats["avg_coverage"] = stats["total_coverage"] / stats["windows"]
                stats["high_coverage_rate"] = stats["high_coverage"] / stats["windows"]

        return {
            "summary": {
                "total_windows": total_windows,
                "available_windows": available_windows,
                "meets_threshold_windows": meets_threshold_windows,
                "threshold_rate": (
                    meets_threshold_windows / available_windows
                    if available_windows > 0
                    else 0
                ),
            },
            "venue_performance": venue_stats,
            "window_details": coverage_results,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        logger.error(f"Error generating coverage report: {e}")
        return {"error": str(e)}


def create_coverage_table(coverage_results: List[Dict]) -> str:
    """Create a markdown table of coverage results."""
    table_lines = [
        "## Coverage Summary Table",
        "",
        "| Window | Binance | Coinbase | Kraken | OKX | Bybit | Venues_OK? |",
        "|--------|---------|----------|--------|-----|-------|------------|",
    ]

    for result in coverage_results:
        if result.get("status") != "available":
            continue

        window = result.get("window", "Unknown")
        coverage_data = result.get("coverage_data", {})
        meets_threshold = result.get("meets_threshold", False)

        # Get coverage percentages for each venue
        binance_cov = coverage_data.get("binance", {}).get("coverage_percentage", 0)
        coinbase_cov = coverage_data.get("coinbase", {}).get("coverage_percentage", 0)
        kraken_cov = coverage_data.get("kraken", {}).get("coverage_percentage", 0)
        okx_cov = coverage_data.get("okx", {}).get("coverage_percentage", 0)
        bybit_cov = coverage_data.get("bybit", {}).get("coverage_percentage", 0)

        status = "YES" if meets_threshold else "NO"
        venue_count = result.get("high_coverage_count", 0)

        table_lines.append(
            f"| {window} | {binance_cov:.0f}% | {coinbase_cov:.0f}% | {kraken_cov:.0f}% | {okx_cov:.0f}% | {bybit_cov:.0f}% | {status} ({venue_count}) |"
        )

    return "\n".join(table_lines)


def write_coverage_report(report: Dict, output_path: str):
    """Write coverage report to file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON report
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        # Write markdown table
        table_file = output_file.with_suffix(".md")
        table_content = create_coverage_table(report.get("window_details", []))

        with open(table_file, "w") as f:
            f.write(table_content)

        logger.info(f"Coverage report written to {output_file} and {table_file}")

    except Exception as e:
        logger.error(f"Error writing coverage report: {e}")


def main():
    """Main function for coverage monitoring."""
    parser = argparse.ArgumentParser(description="Monitor venue coverage")
    parser.add_argument(
        "--symbols", default="BTC-USD,ETH-USD", help="Comma-separated list of symbols"
    )
    parser.add_argument(
        "--days-back", type=int, default=1, help="Number of days to look back"
    )
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")
    parser.add_argument(
        "--output", default="reports/coverage_report.json", help="Output file path"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Parse symbols
        symbols = [s.strip() for s in args.symbols.split(",")]

        # Generate coverage report
        report = generate_coverage_report(
            symbols, args.days_back, args.bucket, args.prefix
        )

        if "error" in report:
            logger.error(f"Coverage report generation failed: {report['error']}")
            sys.exit(1)

        # Write report
        write_coverage_report(report, args.output)

        # Print summary
        summary = report.get("summary", {})
        print(f"Coverage Report Summary:")
        print(f"  Total windows: {summary.get('total_windows', 0)}")
        print(f"  Available windows: {summary.get('available_windows', 0)}")
        print(f"  Meets threshold: {summary.get('meets_threshold_windows', 0)}")
        print(f"  Threshold rate: {summary.get('threshold_rate', 0):.1%}")

        # Print venue performance
        venue_performance = report.get("venue_performance", {})
        if venue_performance:
            print(f"\nVenue Performance:")
            for venue, stats in venue_performance.items():
                print(
                    f"  {venue}: {stats.get('avg_coverage', 0):.1f}% avg, {stats.get('high_coverage_rate', 0):.1%} high coverage"
                )

        sys.exit(0)

    except Exception as e:
        logger.error(f"Coverage monitoring failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
