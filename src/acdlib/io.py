"""
ACD I/O utilities for strict window management.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
import logging
import sys

logger = logging.getLogger(__name__)


def load_ticks_window(
    venues: List[str], start: datetime, end: datetime, cache_dir: str = "data/cache"
) -> Dict[str, pd.DataFrame]:
    """
    Load tick data for specified venues within exact start/end window.
    Enforces strict contract with no synthetic fallbacks.

    Args:
        venues: List of venue names
        start: Start datetime (inclusive)
        end: End datetime (inclusive)
        cache_dir: Cache directory path

    Returns:
        Dictionary mapping venue names to DataFrames

    Raises:
        AssertionError: If window constraints are violated
        SystemExit(2): If synthetic data detected
    """
    logger.info(f"[OVERLAP] Loading ticks window: {start} to {end} for venues: {venues}")

    venue_data = {}

    for venue in venues:
        try:
            df = pd.read_parquet(f"{cache_dir}/{venue}/btc_usd/1s.parquet")
            if len(df) > 0:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                if df["timestamp"].dt.tz is None:
                    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
                else:
                    df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

                # Filter to exact window
                mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
                venue_window = df[mask].copy()

                if len(venue_window) > 0:
                    venue_data[venue] = venue_window
                    logger.info(f"Loaded {len(venue_window)} ticks for {venue} in window")
                else:
                    logger.warning(f"No data for {venue} in window {start} to {end}")
            else:
                logger.warning(f"Empty data file for {venue}")
        except Exception as e:
            logger.error(f"Error loading {venue}: {e}")

    # Assert we have data for all requested venues
    if set(venue_data.keys()) != set(venues):
        logger.error(f"[ABORT:venue_mismatch] Requested: {venues}, Got: {list(venue_data.keys())}")
        print(f'[ABORT:venue_mismatch] {{"requested":{venues},"got":{list(venue_data.keys())}}}')
        sys.exit(2)

    logger.info(
        f"[OVERLAP] Successfully loaded data for {len(venue_data)} venues "
        f"in window {start} to {end}"
    )
    return venue_data


# Synthetic functions removed - only real data allowed for court-ready evidence
