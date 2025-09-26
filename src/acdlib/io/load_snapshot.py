#!/usr/bin/env python3
"""
Unified Snapshot Loader

This module provides functions to load overlap windows and tick data from snapshots,
ensuring all analyses use the exact same window and venues from OVERLAP.json.
"""

import json
import logging
import sys
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_overlap(overlap_path: str) -> Dict:
    """
    Parse OVERLAP.json and return window metadata.

    Args:
        overlap_path: Path to OVERLAP.json file

    Returns:
        Dictionary with start_utc, end_utc, venues, policy, data_root
    """
    logger.info(f"Loading overlap from: {overlap_path}")

    try:
        with open(overlap_path, "r") as f:
            overlap_data = json.load(f)

        # Echo the exact OVERLAP JSON
        overlap_json = json.dumps(overlap_data)
        print(f"[OVERLAP] {overlap_json}")

        # Extract and validate required fields
        start_utc = overlap_data.get("startUTC") or overlap_data.get("start")
        end_utc = overlap_data.get("endUTC") or overlap_data.get("end")
        venues = overlap_data.get("venues", [])
        policy = overlap_data.get("policy", "")

        if not start_utc or not end_utc:
            raise ValueError("Missing startUTC/endUTC in overlap data")

        if not venues:
            raise ValueError("No venues specified in overlap data")

        # Determine data root (look for parquet files in snapshot)
        snapshot_dir = Path(overlap_path).parent
        data_root = snapshot_dir / "ticks"

        result = {
            "start_utc": start_utc,
            "end_utc": end_utc,
            "venues": venues,
            "policy": policy,
            "data_root": str(data_root),
            "overlap_data": overlap_data,
        }

        logger.info(f"Loaded overlap: {start_utc} to {end_utc}, venues: {venues}, policy: {policy}")
        return result

    except Exception as e:
        logger.error(f"Error loading overlap from {overlap_path}: {e}")
        raise


def load_ticks_snapshot(overlap: Dict, asof: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Load tick parquet files for each venue within the overlap window.

    Args:
        overlap: Overlap data from load_overlap()
        asof: Optional as-of timestamp (not used in this implementation)

    Returns:
        Dictionary mapping venue names to tick DataFrames
    """
    logger.info("Loading tick data from snapshot")

    venues_ticks = {}
    data_root = Path(overlap["data_root"])

    for venue in overlap["venues"]:
        venue_dir = data_root / venue
        if not venue_dir.exists():
            logger.warning(f"Venue directory not found: {venue_dir}")
            continue

        # Look for parquet files in the venue directory
        parquet_files = list(venue_dir.glob("**/*.parquet"))
        if not parquet_files:
            logger.warning(f"No parquet files found for venue: {venue}")
            continue

        # Safety check: refuse mock/demo files
        for parquet_file in parquet_files:
            file_name = parquet_file.name.lower()
            file_path = str(parquet_file).lower()

            if "mock" in file_name or "mock" in file_path:
                logger.error(f"[ABORT:snapshot:mock_detected] {parquet_file} - contains 'mock'")
                print(f"[ABORT:snapshot:mock_detected] {parquet_file} - contains 'mock'")
                sys.exit(1)
            elif "_demo" in file_name or "_demo" in file_path:
                logger.error(f"[ABORT:snapshot:mock_detected] {parquet_file} - contains '_demo'")
                print(f"[ABORT:snapshot:mock_detected] {parquet_file} - contains '_demo'")
                sys.exit(1)

        # Load and concatenate parquet files
        venue_ticks = []
        for parquet_file in parquet_files:
            try:
                df = pd.read_parquet(parquet_file)
                if not df.empty:
                    venue_ticks.append(df)
            except Exception as e:
                logger.warning(f"Error reading {parquet_file}: {e}")
                continue

        if venue_ticks:
            # Concatenate all tick data for this venue
            venue_df = pd.concat(venue_ticks, ignore_index=True)

            # Filter by time window if timestamps are available
            if "ts_exchange" in venue_df.columns:
                start_ts = pd.to_datetime(overlap["start_utc"])
                end_ts = pd.to_datetime(overlap["end_utc"])

                # Filter to overlap window
                mask = (venue_df["ts_exchange"] >= start_ts) & (venue_df["ts_exchange"] <= end_ts)
                venue_df = venue_df[mask]

            if not venue_df.empty:
                venues_ticks[venue] = venue_df
                logger.info(f"Loaded {len(venue_df)} ticks for {venue}")
            else:
                logger.warning(f"No ticks in overlap window for {venue}")
        else:
            logger.warning(f"No valid parquet files for {venue}")

    logger.info(f"Loaded tick data for {len(venues_ticks)} venues")
    return venues_ticks


def to_mid(df: pd.DataFrame) -> pd.Series:
    """
    Calculate mid prices from best bid/ask, with fallback to last trade price.

    Args:
        df: DataFrame with best_bid, best_ask, last_trade_px columns

    Returns:
        Series of mid prices
    """
    logger.debug("Calculating mid prices")

    # Try to use best bid/ask if both are available
    if "best_bid" in df.columns and "best_ask" in df.columns:
        # Check for non-null bid/ask pairs
        valid_bid_ask = df["best_bid"].notna() & df["best_ask"].notna()

        if valid_bid_ask.any():
            mid = (df["best_bid"] + df["best_ask"]) / 2
            mid = mid.where(valid_bid_ask)

            # Fill remaining gaps with last trade price
            if "last_trade_px" in df.columns and mid.isna().any():
                logger.warning("[WARN:mid:fallback] Using last_trade_px for missing bid/ask pairs")
                mid = mid.fillna(df["last_trade_px"])

            return mid

    # Fallback to last trade price
    if "last_trade_px" in df.columns:
        logger.warning("[WARN:mid:fallback] Using last_trade_px as mid price")
        return df["last_trade_px"]

    # If no price data available, return NaN
    logger.error("No price data available for mid calculation")
    return pd.Series(index=df.index, dtype=float)


def resample_mids(venues_ticks: Dict[str, pd.DataFrame], rule: str) -> pd.DataFrame:
    """
    Resample mid prices to specified frequency and inner-join venues.

    Args:
        venues_ticks: Dictionary of venue tick DataFrames
        rule: Resampling rule (e.g., '1S', '1T')

    Returns:
        DataFrame with resampled mid prices for each venue
    """
    logger.info(f"Resampling mid prices to {rule}")

    resampled_venues = {}

    for venue, df in venues_ticks.items():
        if df.empty:
            logger.warning(f"Empty DataFrame for {venue}, skipping")
            continue

        # Calculate mid prices
        mid_prices = to_mid(df)

        if mid_prices.empty or mid_prices.isna().all():
            logger.warning(f"No valid mid prices for {venue}, skipping")
            continue

        # Set timestamp as index
        if "ts_exchange" in df.columns:
            df_indexed = df.set_index("ts_exchange")
            mid_series = pd.Series(mid_prices.values, index=df_indexed.index)
        else:
            logger.warning(f"No timestamp column for {venue}, using default index")
            mid_series = mid_prices

        # Resample to specified frequency
        try:
            resampled = mid_series.resample(rule).last()
            resampled_venues[venue] = resampled
            logger.info(f"Resampled {venue}: {len(resampled)} points")
        except Exception as e:
            logger.error(f"Error resampling {venue}: {e}")
            continue

    if not resampled_venues:
        logger.error("No venues successfully resampled")
        return pd.DataFrame()

    # Inner join all venues
    try:
        result_df = pd.DataFrame(resampled_venues)

        # Check for NaNs after inner join
        nan_count = result_df.isna().sum().sum()
        if nan_count > 0:
            logger.error(f"[ABORT:resample:coverage] {nan_count} NaNs found after inner join")
            raise ValueError(f"Resample coverage failed: {nan_count} NaNs")

        logger.info(
            f"Successfully resampled {len(result_df)} points for {len(resampled_venues)} venues"
        )
        return result_df

    except Exception as e:
        logger.error(f"Error in inner join: {e}")
        raise


def load_snapshot_data(overlap_path: str, resample_rule: str = "1S") -> tuple:
    """
    Complete snapshot loading pipeline.

    Args:
        overlap_path: Path to OVERLAP.json
        resample_rule: Resampling frequency

    Returns:
        Tuple of (overlap_data, resampled_mids_df)
    """
    logger.info(f"Loading snapshot data from {overlap_path}")

    # Load overlap metadata
    overlap = load_overlap(overlap_path)

    # Load tick data
    venues_ticks = load_ticks_snapshot(overlap)

    if not venues_ticks:
        logger.error("No tick data loaded from snapshot")
        return overlap, pd.DataFrame()

    # Resample mid prices
    resampled_mids = resample_mids(venues_ticks, resample_rule)

    return overlap, resampled_mids
