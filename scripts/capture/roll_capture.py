#!/usr/bin/env python3
"""
Rolling Capture Daemon

This script runs continuously, capturing 30-minute windows every 15 minutes
with 50% overlap for continuous data collection.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def get_next_window_start(current_time: datetime) -> datetime:
    """Get the next 15-minute window start time."""
    # Round down to the nearest 15-minute mark
    minute = (current_time.minute // 15) * 15
    return current_time.replace(minute=minute, second=0, microsecond=0)


def check_existing_window(
    symbol: str, start_time: datetime, bucket: str, prefix: str
) -> bool:
    """Check if a window already exists in S3."""
    try:
        s3_client = boto3.client("s3")

        date_str = start_time.strftime("%Y%m%d")
        time_str = f"{start_time.strftime('%H%M')}-{(start_time + timedelta(minutes=30)).strftime('%H%M')}"
        s3_key = f"{prefix}/{symbol}/{date_str}/{time_str}/OVERLAP.json"

        s3_client.head_object(Bucket=bucket, Key=s3_key)
        return True

    except s3_client.exceptions.NoSuchKey:
        return False
    except Exception as e:
        logger.warning(f"Error checking existing window: {e}")
        return False


def capture_window_safe(
    symbol: str, start_time: datetime, venues: List[str], bucket: str, prefix: str
) -> bool:
    """Safely capture a window with error handling."""
    try:
        # Check if window already exists
        if check_existing_window(symbol, start_time, bucket, prefix):
            logger.info(f"Window {symbol} {start_time} already exists, skipping")
            return True

        # Import and run capture_window
        sys.path.append(str(Path(__file__).parent))
        from capture_window import capture_window

        end_time = start_time + timedelta(minutes=30)

        success = capture_window(symbol, start_time, end_time, venues, bucket, prefix)

        if success:
            logger.info(f"Successfully captured {symbol} window {start_time}")
        else:
            logger.error(f"Failed to capture {symbol} window {start_time}")

        return success

    except Exception as e:
        logger.error(f"Error capturing window {symbol} {start_time}: {e}")
        return False


def run_capture_cycle(
    symbols: List[str], venues: List[str], bucket: str, prefix: str
) -> Dict:
    """Run one capture cycle for all symbols."""
    results = {}
    current_time = datetime.utcnow()
    window_start = get_next_window_start(current_time)

    logger.info(f"Running capture cycle for {len(symbols)} symbols at {window_start}")

    for symbol in symbols:
        logger.info(f"Capturing {symbol}")

        success = capture_window_safe(symbol, window_start, venues, bucket, prefix)
        results[symbol] = {
            "success": success,
            "window_start": window_start.isoformat() + "Z",
            "window_end": (window_start + timedelta(minutes=30)).isoformat() + "Z",
        }

        if success:
            logger.info(f"✅ {symbol} capture successful")
        else:
            logger.error(f"❌ {symbol} capture failed")

    return results


def run_daemon(
    symbols: List[str],
    venues: List[str],
    bucket: str,
    prefix: str,
    max_cycles: Optional[int] = None,
) -> None:
    """Run the capture daemon continuously."""
    logger.info(f"Starting capture daemon for symbols: {symbols}")
    logger.info(f"Venues: {venues}")
    logger.info(f"S3: s3://{bucket}/{prefix}")

    cycle_count = 0

    try:
        while True:
            cycle_start = time.time()

            # Run capture cycle
            results = run_capture_cycle(symbols, venues, bucket, prefix)

            # Log results
            successful = sum(1 for r in results.values() if r["success"])
            total = len(results)
            logger.info(
                f"Cycle {cycle_count + 1}: {successful}/{total} symbols successful"
            )

            # Check if we should stop
            cycle_count += 1
            if max_cycles and cycle_count >= max_cycles:
                logger.info(f"Reached max cycles ({max_cycles}), stopping")
                break

            # Wait for next cycle (15 minutes)
            cycle_duration = time.time() - cycle_start
            sleep_time = max(0, 900 - cycle_duration)  # 15 minutes = 900 seconds

            logger.info(
                f"Cycle completed in {cycle_duration:.1f}s, sleeping for {sleep_time:.1f}s"
            )
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        raise


def main():
    """Main function for rolling capture daemon."""
    parser = argparse.ArgumentParser(description="Rolling capture daemon")
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of symbols (e.g., BTC-USD,ETH-USD)",
    )
    parser.add_argument(
        "--venues",
        default="binance,coinbase,kraken,okx,bybit",
        help="Comma-separated list of venues",
    )
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")
    parser.add_argument(
        "--max-cycles", type=int, help="Maximum number of cycles to run"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Parse symbols and venues
        symbols = [s.strip() for s in args.symbols.split(",")]
        venues = [v.strip() for v in args.venues.split(",")]

        # Run daemon
        run_daemon(symbols, venues, args.bucket, args.prefix, args.max_cycles)

    except Exception as e:
        logger.error(f"Daemon failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
