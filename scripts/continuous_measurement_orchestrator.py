#!/usr/bin/env python3
"""
Continuous Measurement Orchestrator
Automatically processes new S3 snapshots and generates continuous metrics
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import boto3
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ContinuousMeasurementOrchestrator:
    def __init__(self, bucket: str = "acd-monitor-snapshots"):
        self.s3 = boto3.client("s3")
        self.bucket = bucket
        self.processed_windows = set()

    def get_available_windows(self) -> List[Dict[str, str]]:
        """Get list of available windows from S3"""
        windows = []

        try:
            # List all snapshots
            response = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix="snapshots/", Delimiter="/"
            )

            for prefix in response.get("CommonPrefixes", []):
                symbol = prefix["Prefix"].split("/")[1]

                # List dates for this symbol
                date_response = self.s3.list_objects_v2(
                    Bucket=self.bucket, Prefix=f"snapshots/{symbol}/", Delimiter="/"
                )

                for date_prefix in date_response.get("CommonPrefixes", []):
                    date = date_prefix["Prefix"].split("/")[2]

                    # List time ranges for this date
                    time_response = self.s3.list_objects_v2(
                        Bucket=self.bucket,
                        Prefix=f"snapshots/{symbol}/{date}/",
                        Delimiter="/",
                    )

                    for time_prefix in time_response.get("CommonPrefixes", []):
                        time_range = time_prefix["Prefix"].split("/")[3]

                        # Check if OVERLAP.json exists AND tick data is available
                        overlap_key = f"snapshots/{symbol}/{date}/{time_range}/OVERLAP.json"
                        tick_key = f"snapshots/{symbol}/{date}/{time_range}/ticks/binance/part-0000.parquet"
                        try:
                            # Check both OVERLAP.json and at least one tick file
                            self.s3.head_object(Bucket=self.bucket, Key=overlap_key)
                            self.s3.head_object(Bucket=self.bucket, Key=tick_key)
                            windows.append(
                                {
                                    "symbol": symbol,
                                    "date": date,
                                    "time_range": time_range,
                                    "overlap_key": overlap_key,
                                }
                            )
                        except:
                            continue

        except Exception as e:
            logger.error(f"Failed to get available windows: {e}")

        return windows

    def is_window_processed(self, symbol: str, date: str, time_range: str) -> bool:
        """Check if window has already been processed"""
        window_id = f"{symbol}_{date}_{time_range}"
        return window_id in self.processed_windows

    def process_window(self, symbol: str, date: str, time_range: str) -> bool:
        """Process a single window"""
        window_id = f"{symbol}_{date}_{time_range}"

        if self.is_window_processed(symbol, date, time_range):
            logger.info(f"Window {window_id} already processed, skipping")
            return True

        logger.info(f"Processing window {window_id}")

        try:
            # Run continuous measurement script
            output_path = f"continuous_metrics/{symbol}/{date}/{time_range}/metrics.json"

            cmd = [
                "python",
                "scripts/continuous_measurement.py",
                "--symbol",
                symbol,
                "--date",
                date,
                "--time-range",
                time_range,
                "--output-path",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                logger.info(f"✅ Successfully processed {window_id}")
                self.processed_windows.add(window_id)
                return True
            else:
                logger.error(f"❌ Failed to process {window_id}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout processing {window_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Error processing {window_id}: {e}")
            return False

    def run_continuous_measurement(self, max_windows: int = None):
        """Run continuous measurement on all available windows"""
        logger.info("Starting continuous measurement orchestrator")

        # Get available windows
        windows = self.get_available_windows()
        logger.info(f"Found {len(windows)} available windows")

        if max_windows:
            windows = windows[:max_windows]
            logger.info(f"Processing first {max_windows} windows")

        processed_count = 0
        failed_count = 0

        for window in windows:
            symbol = window["symbol"]
            date = window["date"]
            time_range = window["time_range"]

            if self.process_window(symbol, date, time_range):
                processed_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Continuous measurement completed: {processed_count} processed, {failed_count} failed"
        )
        return processed_count, failed_count

    def run_monitoring_mode(self, check_interval: int = 300):
        """Run in monitoring mode, checking for new windows periodically"""
        logger.info(f"Starting monitoring mode (checking every {check_interval} seconds)")

        while True:
            try:
                # Get available windows
                windows = self.get_available_windows()

                # Process unprocessed windows
                new_windows = []
                for window in windows:
                    if not self.is_window_processed(
                        window["symbol"], window["date"], window["time_range"]
                    ):
                        new_windows.append(window)

                if new_windows:
                    logger.info(f"Found {len(new_windows)} new windows to process")
                    for window in new_windows:
                        self.process_window(window["symbol"], window["date"], window["time_range"])
                else:
                    logger.info("No new windows found")

                # Wait before next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring mode: {e}")
                time.sleep(60)  # Wait before retrying


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Continuous Measurement Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["batch", "monitor"],
        default="batch",
        help="Run mode: batch (process all) or monitor (continuous)",
    )
    parser.add_argument("--max-windows", type=int, help="Maximum number of windows to process")
    parser.add_argument(
        "--check-interval",
        type=int,
        default=300,
        help="Check interval in seconds for monitoring mode",
    )
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = ContinuousMeasurementOrchestrator(bucket=args.bucket)

    if args.mode == "batch":
        # Process all available windows
        processed, failed = orchestrator.run_continuous_measurement(max_windows=args.max_windows)
        logger.info(f"Batch processing completed: {processed} processed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)

    elif args.mode == "monitor":
        # Run in monitoring mode
        orchestrator.run_monitoring_mode(check_interval=args.check_interval)


if __name__ == "__main__":
    main()
