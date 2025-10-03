#!/usr/bin/env python3
"""
Daily Health and Cost Report

This script generates daily health reports including coverage summaries,
detector results, and cost estimates.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import pandas as pd

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def get_s3_storage_usage(bucket: str, prefix: str) -> Dict:
    """Get S3 storage usage statistics."""
    try:
        s3_client = boto3.client("s3")

        # List all objects
        paginator = s3_client.get_paginator("list_objects_v2")
        total_size = 0
        object_count = 0
        by_storage_class = {}

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                size = obj["Size"]
                storage_class = obj.get("StorageClass", "STANDARD")

                total_size += size
                object_count += 1

                if storage_class not in by_storage_class:
                    by_storage_class[storage_class] = {"size": 0, "count": 0}

                by_storage_class[storage_class]["size"] += size
                by_storage_class[storage_class]["count"] += 1

        # Convert to GB
        total_gb = total_size / (1024**3)

        return {
            "total_size_gb": round(total_gb, 2),
            "object_count": object_count,
            "by_storage_class": {
                sc: {
                    "size_gb": round(data["size"] / (1024**3), 2),
                    "count": data["count"],
                }
                for sc, data in by_storage_class.items()
            },
        }

    except Exception as e:
        logger.error(f"Failed to get S3 storage usage: {e}")
        return {"error": str(e)}


def estimate_daily_costs(storage_usage: Dict) -> Dict:
    """Estimate daily storage costs."""
    try:
        # AWS S3 pricing (as of 2024)
        pricing = {
            "STANDARD": 0.023,  # per GB per month
            "STANDARD_IA": 0.0125,  # per GB per month
            "GLACIER": 0.004,  # per GB per month
            "DEEP_ARCHIVE": 0.00099,  # per GB per month
        }

        daily_costs = {}
        total_daily_cost = 0

        for storage_class, data in storage_usage.get("by_storage_class", {}).items():
            size_gb = data["size_gb"]
            monthly_cost = size_gb * pricing.get(storage_class, 0.023)
            daily_cost = monthly_cost / 30

            daily_costs[storage_class] = round(daily_cost, 2)
            total_daily_cost += daily_cost

        return {
            "daily_costs_by_class": daily_costs,
            "total_daily_cost": round(total_daily_cost, 2),
            "total_monthly_cost": round(total_daily_cost * 30, 2),
        }

    except Exception as e:
        logger.error(f"Failed to estimate costs: {e}")
        return {"error": str(e)}


def get_coverage_summary(symbols: List[str], days_back: int, bucket: str, prefix: str) -> Dict:
    """Get coverage summary for recent windows."""
    try:
        s3_client = boto3.client("s3")

        # Get coverage data for recent windows
        coverage_data = []

        for symbol in symbols:
            try:
                # List recent windows
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
                                # Check if coverage.json exists
                                coverage_key = (
                                    f"{prefix}/{symbol}/{date_path}/{time_range}/meta/coverage.json"
                                )
                                try:
                                    coverage_response = s3_client.get_object(
                                        Bucket=bucket, Key=coverage_key
                                    )
                                    coverage_json = json.loads(coverage_response["Body"].read())

                                    # Calculate venues_ok
                                    high_coverage_venues = [
                                        venue
                                        for venue, data in coverage_json.items()
                                        if data.get("coverage_percentage", 0) >= 95.0
                                    ]
                                    venues_ok = len(high_coverage_venues) >= 3

                                    coverage_data.append(
                                        {
                                            "window": f"{symbol}/{date_path}/{time_range}",
                                            "venues_ok": venues_ok,
                                            "high_coverage_venues": len(high_coverage_venues),
                                            "coverage_data": coverage_json,
                                        }
                                    )

                                except s3_client.exceptions.NoSuchKey:
                                    continue

            except Exception as e:
                logger.error(f"Error getting coverage for {symbol}: {e}")
                continue

        # Calculate summary statistics
        total_windows = len(coverage_data)
        venues_ok_windows = len([w for w in coverage_data if w["venues_ok"]])
        venues_ok_rate = venues_ok_windows / total_windows if total_windows > 0 else 0

        return {
            "total_windows": total_windows,
            "venues_ok_windows": venues_ok_windows,
            "venues_ok_rate": round(venues_ok_rate, 3),
            "coverage_data": coverage_data,
        }

    except Exception as e:
        logger.error(f"Failed to get coverage summary: {e}")
        return {"error": str(e)}


def get_detector_results(symbols: List[str], days_back: int) -> Dict:
    """Get detector results from recent analysis."""
    try:
        # Look for detector results in experiments/phase5
        detector_results = {
            "spread_v2": {"passes": 0, "fails": 0, "total": 0},
            "leadlag_v2": {"passes": 0, "fails": 0, "total": 0},
            "infoshare_v2": {"passes": 0, "fails": 0, "total": 0},
        }

        # This would need to be implemented based on actual detector output files
        # For now, return placeholder data
        return {
            "detector_results": detector_results,
            "note": "Detector results parsing not yet implemented",
        }

    except Exception as e:
        logger.error(f"Failed to get detector results: {e}")
        return {"error": str(e)}


def generate_daily_report(symbols: List[str], days_back: int, bucket: str, prefix: str) -> Dict:
    """Generate comprehensive daily health report."""
    try:
        logger.info("Generating daily health report...")

        # Get storage usage
        storage_usage = get_s3_storage_usage(bucket, prefix)
        if "error" in storage_usage:
            logger.error(f"Storage usage error: {storage_usage['error']}")
            storage_usage = {"total_size_gb": 0, "object_count": 0}

        # Estimate costs
        cost_estimate = estimate_daily_costs(storage_usage)
        if "error" in cost_estimate:
            logger.error(f"Cost estimation error: {cost_estimate['error']}")
            cost_estimate = {"total_daily_cost": 0, "total_monthly_cost": 0}

        # Get coverage summary
        coverage_summary = get_coverage_summary(symbols, days_back, bucket, prefix)
        if "error" in coverage_summary:
            logger.error(f"Coverage summary error: {coverage_summary['error']}")
            coverage_summary = {
                "total_windows": 0,
                "venues_ok_windows": 0,
                "venues_ok_rate": 0,
            }

        # Get detector results
        detector_results = get_detector_results(symbols, days_back)
        if "error" in detector_results:
            logger.error(f"Detector results error: {detector_results['error']}")
            detector_results = {"detector_results": {}}

        # Generate report
        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "symbols": symbols,
            "days_back": days_back,
            "storage_usage": storage_usage,
            "cost_estimate": cost_estimate,
            "coverage_summary": coverage_summary,
            "detector_results": detector_results,
        }

        return report

    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return {"error": str(e)}


def write_daily_report(report: Dict, output_path: str):
    """Write daily report to file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON report
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        # Write markdown summary
        md_file = output_file.with_suffix(".md")
        md_content = f"""# Daily Health Report - {report.get('generated_at', 'Unknown')}

## Storage Usage
- **Total Size**: {report.get('storage_usage', {}).get('total_size_gb', 0)} GB
- **Object Count**: {report.get('storage_usage', {}).get('object_count', 0)}
- **Daily Cost**: ${report.get('cost_estimate', {}).get('total_daily_cost', 0)}
- **Monthly Cost**: ${report.get('cost_estimate', {}).get('total_monthly_cost', 0)}

## Coverage Summary
- **Total Windows**: {report.get('coverage_summary', {}).get('total_windows', 0)}
- **Venues OK**: {report.get('coverage_summary', {}).get('venues_ok_windows', 0)}
- **Success Rate**: {report.get('coverage_summary', {}).get('venues_ok_rate', 0):.1%}

## Detector Results
{report.get('detector_results', {}).get('note', 'No detector results available')}

## Budget Alert
{'⚠️ **BUDGET ALERT**: Daily cost exceeds $20 threshold!' if report.get('cost_estimate', {}).get('total_daily_cost', 0) > 20 else '✅ Daily cost within budget'}
"""

        with open(md_file, "w") as f:
            f.write(md_content)

        logger.info(f"Daily report written to {output_file} and {md_file}")

    except Exception as e:
        logger.error(f"Error writing daily report: {e}")


def main():
    """Main function for daily health report."""
    parser = argparse.ArgumentParser(description="Generate daily health report")
    parser.add_argument(
        "--symbols", default="BTC-USD,ETH-USD", help="Comma-separated list of symbols"
    )
    parser.add_argument("--days-back", type=int, default=1, help="Number of days to look back")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")
    parser.add_argument("--output", default="reports/daily_status.json", help="Output file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Parse symbols
        symbols = [s.strip() for s in args.symbols.split(",")]

        # Generate report
        report = generate_daily_report(symbols, args.days_back, args.bucket, args.prefix)

        if "error" in report:
            logger.error(f"Daily report generation failed: {report['error']}")
            sys.exit(1)

        # Write report
        write_daily_report(report, args.output)

        # Print summary
        print(f"Daily Health Report Summary:")
        print(f"  Storage: {report.get('storage_usage', {}).get('total_size_gb', 0)} GB")
        print(f"  Daily Cost: ${report.get('cost_estimate', {}).get('total_daily_cost', 0)}")
        print(f"  Windows: {report.get('coverage_summary', {}).get('total_windows', 0)}")
        print(f"  Venues OK: {report.get('coverage_summary', {}).get('venues_ok_windows', 0)}")
        print(f"  Success Rate: {report.get('coverage_summary', {}).get('venues_ok_rate', 0):.1%}")

        # Budget alert
        daily_cost = report.get("cost_estimate", {}).get("total_daily_cost", 0)
        if daily_cost > 20:
            print(f"⚠️ BUDGET ALERT: Daily cost ${daily_cost} exceeds $20 threshold!")
        else:
            print(f"✅ Daily cost ${daily_cost} within budget")

        sys.exit(0)

    except Exception as e:
        logger.error(f"Daily health report failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
