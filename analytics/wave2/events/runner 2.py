#!/usr/bin/env python3
"""Wave-2 Event Studies Runner - CLI interface for compute_events.py"""

import argparse
import os
import sys

from compute_events import EventStudiesEngine


def main():
    parser = argparse.ArgumentParser(description="Wave-2 Event Studies Runner")
    parser.add_argument("--date", required=True, help="Analysis date (YYYYMMDD)")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--symbol", default="btc_usd", help="Symbol to analyze")
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        default=True,
        help="Do not overwrite existing outputs",
    )

    args = parser.parse_args()

    # Validate inputs
    if len(args.date) != 8 or not args.date.isdigit():
        print(f"Error: Invalid date format '{args.date}'. Expected YYYYMMDD")
        sys.exit(1)

    if not args.bucket:
        print("Error: Bucket name is required")
        sys.exit(1)

    # Run the engine
    engine = EventStudiesEngine(
        bucket=args.bucket, date=args.date, symbol=args.symbol, no_overwrite=args.no_overwrite
    )

    success = engine.run()
    if not success:
        print("Event studies computation failed")
        sys.exit(1)

    print("Event studies computation completed successfully")


if __name__ == "__main__":
    main()
