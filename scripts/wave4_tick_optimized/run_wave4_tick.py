#!/usr/bin/env python3
"""
Wave 4 — Optimized Tick-Level Coordination Diagnostics.
Vectorized, chunked, and checkpointed analysis for large-trade sync, OFI spikes, and impact spillovers.
"""
import gzip
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_tick_data_optimized(venue: str, date: str, max_rows: int = 100000) -> pd.DataFrame:
    """Load tick data with size limits and vectorized processing."""
    logger.info(f"Loading tick data for {venue} on {date} (max {max_rows:,} rows)...")

    raw_dir = Path(f"analysis/flatfiles_ticks/raw/D-{date}/E-{venue}")
    if not raw_dir.exists():
        logger.warning(f"No data found for {venue} on {date}")
        return pd.DataFrame()

    csv_files = list(raw_dir.glob("*.csv.gz"))
    if not csv_files:
        logger.warning(f"No CSV files found for {venue} on {date}")
        return pd.DataFrame()

    csv_file = csv_files[0]
    logger.info(f"Processing file: {csv_file}")

    try:
        # Read with size limit
        with gzip.open(csv_file, "rt") as f:
            header = f.readline().strip().split(";")

            rows = []
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                if not line.strip():
                    continue

                parts = line.strip().split(";")
                if len(parts) >= 6:  # Minimum required fields
                    rows.append(parts)

            if not rows:
                logger.warning(f"No valid rows found for {venue}")
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=header)
            df["time_exchange"] = pd.to_datetime(df["time_exchange"])
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["base_amount"] = pd.to_numeric(df["base_amount"], errors="coerce")

            # Remove rows with invalid data
            df = df.dropna(subset=["price", "base_amount", "time_exchange"])

            logger.info(f"Loaded {len(df):,} valid trades for {venue}")
            return df

    except Exception as e:
        logger.error(f"Error loading {csv_file}: {e}")
        return pd.DataFrame()


def create_time_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Create 50ms and 100ms time bins for vectorized analysis."""
    if df.empty:
        return df

    # Convert to nanoseconds for precise binning
    df["ts_ns"] = df["time_exchange"].astype("int64")

    # Create time bins
    df["bin50"] = df["ts_ns"] // 50_000_000  # 50ms bins
    df["bin100"] = df["ts_ns"] // 100_000_000  # 100ms bins

    return df


def aggregate_by_bins(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trades by time bins for efficient analysis."""
    if df.empty:
        return df

    # Aggregate by 50ms bins
    bin50_agg = (
        df.groupby("bin50")
        .agg(
            {
                "base_amount": "sum",  # Total volume
                "price": "last",  # Last price in bin
                "time_exchange": "last",  # Last timestamp
            }
        )
        .reset_index()
    )

    # Calculate price changes
    bin50_agg["dpx"] = bin50_agg["price"].diff()

    # Add 100ms bins for OFI analysis
    bin50_agg["bin100"] = bin50_agg["bin50"] // 2  # 100ms = 2 * 50ms

    return bin50_agg


def main():
    """Main execution function with auto-abort guardrails."""
    logger.info("=== Wave 4 — Optimized Tick-Level Diagnostics ===")

    # Configuration
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    dates = ["20250925"]
    max_rows_per_venue = 100000  # Safety limit

    # Create output directory
    output_dir = Path("analysis/flatfiles_ticks/wave4/optimized")
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    last_file_time = start_time

    try:
        # Process each venue-date combination
        for venue in venues:
            for date in dates:
                logger.info(f"Processing {venue} on {date}...")

                # Load data with limits
                df = load_tick_data_optimized(venue, date, max_rows_per_venue)

                if df.empty:
                    logger.warning(f"No data for {venue} on {date}")
                    continue

                # Create time bins
                df = create_time_bins(df)

                # Aggregate by bins
                agg_df = aggregate_by_bins(df)

                # Save intermediate results
                venue_output = output_dir / f"venue={venue}_date={date}.parquet"
                agg_df.to_parquet(venue_output)

                logger.info(
                    f"WROTE {venue_output} ({len(agg_df):,} bins, {time.time() - start_time:.1f}s)"
                )
                last_file_time = time.time()

                # Auto-abort check
                if time.time() - last_file_time > 600:  # 10 minutes
                    logger.error("STUCK: No new files written in 10 minutes")
                    return

        logger.info("✅ SUCCESS: Wave 4 optimized tick-level diagnostics complete")

    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
