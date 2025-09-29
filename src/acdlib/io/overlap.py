"""
Real overlap finder for ACD analysis.
Finds genuine simultaneous data across all venues with no synthetic fallbacks.
"""

import pandas as pd
from datetime import datetime
from typing import List, Tuple, Optional
import logging
import sys
import json
from pathlib import Path

logger = logging.getLogger(__name__)


def find_real_overlap(
    venues: List[str],
    pair: str = "btc_usd",
    freq: str = "1s",
    max_gap: float = 1.0,
    cache_dir: str = "data/cache",
) -> Tuple[datetime, datetime, List[str], str]:
    """
    Find real overlapping data across all venues with no synthetic fallbacks.

    Args:
        venues: List of venue names to check
        pair: Trading pair (default: btc_usd)
        freq: Data frequency (default: 1s)
        max_gap: Maximum allowed gap in seconds (default: 1.0)
        cache_dir: Cache directory path

    Returns:
        Tuple of (start, end, venues_used, policy)

    Raises:
        SystemExit(2): If no sufficient overlap found
    """
    logger.info(f"[OVERLAP:search] Finding real overlap for {venues} on {pair} at {freq}")

    venue_data = {}
    coverage_info = {}

    # Load all venue data
    for venue in venues:
        try:
            df = pd.read_parquet(f"{cache_dir}/{venue}/{pair}/{freq}.parquet")
            if len(df) > 0:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                if df["timestamp"].dt.tz is None:
                    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
                else:
                    df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

                df = df.sort_values("timestamp")
                venue_data[venue] = df

                # Check for continuous coverage (no gaps > max_gap)
                time_diffs = df["timestamp"].diff().dt.total_seconds()
                gaps = time_diffs[time_diffs > max_gap]

                coverage_info[venue] = {
                    "start": df["timestamp"].min(),
                    "end": df["timestamp"].max(),
                    "count": len(df),
                    "gaps": len(gaps),
                    "max_gap": gaps.max() if len(gaps) > 0 else 0,
                    "continuous": len(gaps) == 0,
                }

                logger.info(
                    f"{venue}: {coverage_info[venue]['start']} to {coverage_info[venue]['end']} "
                    f"({coverage_info[venue]['count']} ticks, {coverage_info[venue]['gaps']} gaps)"
                )
            else:
                logger.warning(f"{venue}: Empty data file")
        except Exception as e:
            logger.error(f"{venue}: Error loading data - {e}")

    if len(venue_data) < 4:
        logger.error(f"[OVERLAP:INSUFFICIENT] Only {len(venue_data)} venues with data, need >=4")
        venues_list = list(venue_data.keys())
        print(
            f'[OVERLAP:INSUFFICIENT] {{"venues":{venues_list},'
            f'"minutes":0,"reason":"insufficient venues with data"}}'
        )
        sys.exit(2)

    # Find temporal intersection
    all_starts = [info["start"] for info in coverage_info.values()]
    all_ends = [info["end"] for info in coverage_info.values()]

    overlap_start = max(all_starts)
    overlap_end = min(all_ends)

    if overlap_start >= overlap_end:
        logger.error("[OVERLAP:INSUFFICIENT] No temporal overlap between venues")
        venues_list = list(venue_data.keys())
        print(
            f'[OVERLAP:INSUFFICIENT] {{"venues":{venues_list},'
            f'"minutes":0,"reason":"no temporal overlap between venues"}}'
        )
        sys.exit(2)

    overlap_duration = (overlap_end - overlap_start).total_seconds() / 60
    logger.info(
        f"Potential overlap: {overlap_start} to {overlap_end} ({overlap_duration:.1f} minutes)"
    )

    # Check continuous data in this window for each venue
    continuous_venues = []
    excluded_venues = []

    for venue, df in venue_data.items():
        mask = (df["timestamp"] >= overlap_start) & (df["timestamp"] <= overlap_end)
        venue_overlap = df[mask].copy()

        if len(venue_overlap) > 0:
            # Check for gaps > max_gap in overlap window
            venue_overlap = venue_overlap.sort_values("timestamp")
            time_diffs = venue_overlap["timestamp"].diff().dt.total_seconds()
            gaps = time_diffs[time_diffs > max_gap]

            if len(gaps) == 0:
                logger.info(f"{venue}: CONTINUOUS in overlap ({len(venue_overlap)} ticks)")
                continuous_venues.append(venue)
            else:
                max_gap_val = gaps.max() if len(gaps) > 0 else 0
                logger.warning(
                    f"{venue}: {len(gaps)} gaps > {max_gap}s in overlap "
                    f"(largest: {max_gap_val:.1f}s)"
                )
                excluded_venues.append(venue)
        else:
            logger.warning(f"{venue}: NO DATA in overlap window")
            excluded_venues.append(venue)

    logger.info(f"Continuous venues: {len(continuous_venues)}/{len(venue_data)}")
    logger.info(f"Excluded: {excluded_venues}")

    # Apply strict policy: ALL5>=30m else ALL5>=20m else ALL5>=10m
    # else BEST4>=30m else BEST4>=20m else BEST4>=10m
    if len(continuous_venues) >= 5 and overlap_duration >= 30:
        policy = "ALL5>=30m"
        venues_used = continuous_venues
    elif len(continuous_venues) >= 5 and overlap_duration >= 20:
        policy = "ALL5>=20m"
        venues_used = continuous_venues
    elif len(continuous_venues) >= 5 and overlap_duration >= 10:
        policy = "ALL5>=10m"
        venues_used = continuous_venues
    elif len(continuous_venues) >= 4 and overlap_duration >= 30:
        policy = "BEST4>=30m"
        venues_used = continuous_venues
    elif len(continuous_venues) >= 4 and overlap_duration >= 20:
        policy = "BEST4>=20m"
        venues_used = continuous_venues
    elif len(continuous_venues) >= 4 and overlap_duration >= 10:
        policy = "BEST4>=10m"
        venues_used = continuous_venues
    else:
        logger.error(
            f"[OVERLAP:INSUFFICIENT] Insufficient overlap: "
            f"{len(continuous_venues)} venues, {overlap_duration:.1f} minutes"
        )
        print(
            f'[OVERLAP:INSUFFICIENT] {{"venues":{continuous_venues},'
            f'"minutes":{overlap_duration:.1f},'
            f'"reason":"not enough simultaneous data"}}'
        )
        sys.exit(2)

    # Print the exact overlap JSON
    overlap_json = (
        f'[OVERLAP] {{"startUTC":"{overlap_start}","endUTC":"{overlap_end}",'
        f'"minutes":{overlap_duration:.1f},"venues":{venues_used},'
        f'"excluded":{excluded_venues},"policy":"{policy}"}}'
    )
    print(overlap_json)
    logger.info(
        f"Found real overlap: {policy} with {len(venues_used)} venues "
        f"for {overlap_duration:.1f} minutes"
    )

    return overlap_start, overlap_end, venues_used, policy


def find_real_overlap_rolling(
    venues: List[str],
    pair: str = "btc_usd",
    freq: str = "1s",
    max_gap_s: float = 1.0,
    min_minutes: List[int] = [30, 20, 10],
    quorum: int = 4,
    cache_dir: str = "data/ticks",
) -> Optional[Tuple[datetime, datetime, List[str], str]]:
    """
    Find real overlapping data with rolling window monitoring.

    Args:
        venues: List of venue names to check
        pair: Trading pair (default: btc_usd)
        freq: Data frequency (default: 1s)
        max_gap_s: Maximum allowed gap in seconds (default: 1.0)
        min_minutes: List of minimum minutes to try [30, 20, 10]
        quorum: Minimum number of venues required (default: 4)
        cache_dir: Cache directory path (default: data/ticks)

    Returns:
        Tuple of (start, end, venues_used, policy) if overlap found, None otherwise
    """
    logger.info(f"[OVERLAP:rolling] Checking for overlap: {venues} on {pair} at {freq}")

    venue_data = {}
    coverage_info = {}

    # Load all venue data from tick partitions
    for venue in venues:
        try:
            # Look for recent tick data in partitions
            tick_dir = Path(cache_dir) / venue / pair / freq
            if not tick_dir.exists():
                logger.warning(f"No tick data directory for {venue}")
                continue

            # Find most recent data files
            data_files = []
            for date_dir in tick_dir.iterdir():
                if date_dir.is_dir():
                    for hour_dir in date_dir.iterdir():
                        if hour_dir.is_dir():
                            for file_path in hour_dir.glob("*.parquet"):
                                data_files.append(file_path)

            if not data_files:
                logger.warning(f"No tick data files for {venue}")
                continue

            # Load most recent data
            recent_files = sorted(data_files, key=lambda x: x.stat().st_mtime)[
                -10:
            ]  # Last 10 files
            dfs = []
            for file_path in recent_files:
                try:
                    df = pd.read_parquet(file_path)
                    dfs.append(df)
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
                    continue

            if not dfs:
                continue

            df = pd.concat(dfs, ignore_index=True)
            df = df.sort_values("ts_local")

            # Convert timestamps
            df["timestamp"] = pd.to_datetime(df["ts_local"], unit="ms")
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
            else:
                df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

            venue_data[venue] = df

            # Check for continuous coverage
            time_diffs = df["timestamp"].diff().dt.total_seconds()
            gaps = time_diffs[time_diffs > max_gap_s]

            coverage_info[venue] = {
                "start": df["timestamp"].min(),
                "end": df["timestamp"].max(),
                "count": len(df),
                "gaps": len(gaps),
                "max_gap": gaps.max() if len(gaps) > 0 else 0,
                "continuous": len(gaps) == 0,
            }

            logger.info(
                f"{venue}: {coverage_info[venue]['start']} to {coverage_info[venue]['end']} "
                f"({coverage_info[venue]['count']} ticks, {coverage_info[venue]['gaps']} gaps)"
            )

        except Exception as e:
            logger.error(f"{venue}: Error loading tick data - {e}")

    if len(venue_data) < quorum:
        logger.warning(
            f"[OVERLAP:PENDING] Only {len(venue_data)} venues with data, need >= {quorum}"
        )
        pending_info = {
            "minutes_max": 0,
            "venues_ready": list(venue_data.keys()),
            "venues_missing": [v for v in venues if v not in venue_data.keys()],
        }
        print(f"[OVERLAP:PENDING] {json.dumps(pending_info)}")
        return None

    # Find temporal intersection
    all_starts = [info["start"] for info in coverage_info.values()]
    all_ends = [info["end"] for info in coverage_info.values()]

    overlap_start = max(all_starts)
    overlap_end = min(all_ends)

    if overlap_start >= overlap_end:
        logger.warning("[OVERLAP:PENDING] No temporal overlap between venues")
        pending_info = {
            "minutes_max": 0,
            "venues_ready": list(venue_data.keys()),
            "venues_missing": [v for v in venues if v not in venue_data.keys()],
        }
        print(f"[OVERLAP:PENDING] {json.dumps(pending_info)}")
        return None

    overlap_duration = (overlap_end - overlap_start).total_seconds() / 60
    logger.info(
        f"Potential overlap: {overlap_start} to {overlap_end} ({overlap_duration:.1f} minutes)"
    )

    # Check continuous data in this window for each venue
    continuous_venues = []
    excluded_venues = []

    for venue, df in venue_data.items():
        mask = (df["timestamp"] >= overlap_start) & (df["timestamp"] <= overlap_end)
        venue_overlap = df[mask].copy()

        if len(venue_overlap) > 0:
            # Check for gaps > max_gap_s in overlap window
            venue_overlap = venue_overlap.sort_values("timestamp")
            time_diffs = venue_overlap["timestamp"].diff().dt.total_seconds()
            gaps = time_diffs[time_diffs > max_gap_s]

            if len(gaps) == 0:
                logger.info(f"{venue}: CONTINUOUS in overlap ({len(venue_overlap)} ticks)")
                continuous_venues.append(venue)
            else:
                logger.warning(f"{venue}: {len(gaps)} gaps > {max_gap_s}s in overlap")
                excluded_venues.append(venue)
        else:
            logger.warning(f"{venue}: NO DATA in overlap window")
            excluded_venues.append(venue)

    logger.info(f"Continuous venues: {len(continuous_venues)}/{len(venue_data)}")

    # Apply strict policy: BEST4>=30m, BEST4>=20m, BEST4>=10m, ALL5>=10m
    for min_min in min_minutes:
        if len(continuous_venues) >= quorum and overlap_duration >= min_min:
            if len(continuous_venues) >= 5 and min_min == 10:
                policy = "ALL5_10m"
            else:
                policy = f"BEST4_{min_min}m"

            # Print the exact overlap JSON
            overlap_json = (
                f'[OVERLAP] {{"startUTC":"{overlap_start}","endUTC":"{overlap_end}",'
                f'"minutes":{overlap_duration:.1f},"venues":{continuous_venues},'
                f'"excluded":{excluded_venues},"policy":"{policy}"}}'
            )
            print(overlap_json)
            logger.info(
                f"Found real overlap: {policy} with {len(continuous_venues)} venues "
                f"for {overlap_duration:.1f} minutes"
            )

            return overlap_start, overlap_end, continuous_venues, policy

    # No sufficient overlap found
    pending_info = {
        "minutes_max": overlap_duration,
        "venues_ready": continuous_venues,
        "venues_missing": excluded_venues,
    }
    print(f"[OVERLAP:PENDING] {json.dumps(pending_info)}")
    return None


def abort_on_synthetic(policy: str) -> None:
    """
    Hard abort if synthetic policy is detected.

    Args:
        policy: The overlap policy string

    Raises:
        SystemExit(2): If policy starts with "SYNTHETIC"
    """
    if policy.startswith("SYNTHETIC"):
        logger.error(f"[ABORT:synthetic] Synthetic policy detected: {policy}")
        print(
            f'[ABORT:synthetic] {{"policy":"{policy}",'
            f'"reason":"synthetic data not allowed in court-ready evidence"}}'
        )
        sys.exit(2)
