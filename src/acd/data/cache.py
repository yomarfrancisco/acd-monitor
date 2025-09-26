"""
Data cache system for market data storage and retrieval.
"""

import os
import pandas as pd

# import pyarrow as pa  # Unused for now
# import pyarrow.parquet as pq  # Unused for now
from datetime import datetime

from typing import Optional, Dict, Any
import logging

# import hashlib  # Unused for now


class DataCache:
    """
    Parquet-based cache system for market data.

    Provides deterministic partitioning by day with cache hit/miss logging.
    """

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)

        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_path(self, venue: str, pair: str, frequency: str) -> str:
        """
        Generate deterministic cache path for data.

        Args:
            venue: Exchange venue
            pair: Trading pair
            frequency: Data frequency ('1min', '1s', etc.)

        Returns:
            Cache file path
        """
        # Normalize pair name for filesystem
        normalized_pair = pair.replace("-", "_").replace("/", "_").lower()

        # Create deterministic path structure
        path = os.path.join(self.cache_dir, venue.lower(), normalized_pair, f"{frequency}.parquet")

        return path

    def get(
        self, venue: str, pair: str, frequency: str, start_utc: datetime, end_utc: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve cached data if available.

        Args:
            venue: Exchange venue
            pair: Trading pair
            frequency: Data frequency
            start_utc: Start datetime
            end_utc: End datetime

        Returns:
            Cached DataFrame or None if not found
        """
        cache_path = self.get_cache_path(venue, pair, frequency)

        if not os.path.exists(cache_path):
            self.logger.info(f"[DATA:cache:miss] {venue}:{pair}:{frequency} - file not found")
            return None

        try:
            # Read parquet file
            df = pd.read_parquet(cache_path)

            if df.empty:
                self.logger.info(f"[DATA:cache:miss] {venue}:{pair}:{frequency} - empty file")
                return None

            # Filter by date range - handle both 'time' and 'timestamp' columns
            if "time" in df.columns:
                time_col = "time"
            elif "timestamp" in df.columns:
                time_col = "timestamp"
            else:
                self.logger.warning(
                    f"[DATA:cache:error] {venue}:{pair}:{frequency} - no time column found"
                )
                return None

            df[time_col] = pd.to_datetime(df[time_col])
            # Ensure timezone-aware comparison
            if df[time_col].dt.tz is None:
                df[time_col] = df[time_col].dt.tz_localize("UTC")
            else:
                df[time_col] = df[time_col].dt.tz_convert("UTC")

            # Convert start/end to UTC timezone-aware
            if start_utc.tzinfo is None:
                start_utc = start_utc.replace(tzinfo=None)
                start_utc = pd.Timestamp(start_utc, tz="UTC")
            if end_utc.tzinfo is None:
                end_utc = end_utc.replace(tzinfo=None)
                end_utc = pd.Timestamp(end_utc, tz="UTC")

            mask = (df[time_col] >= start_utc) & (df[time_col] <= end_utc)
            filtered_df = df[mask].copy()

            if filtered_df.empty:
                self.logger.info(f"[DATA:cache:miss] {venue}:{pair}:{frequency} - no data in range")
                return None

            self.logger.info(
                f"[DATA:cache:hit] {venue}:{pair}:{frequency} - {len(filtered_df)} bars"
            )
            return filtered_df

        except Exception as e:
            self.logger.warning(f"[DATA:cache:error] {venue}:{pair}:{frequency} - {str(e)}")
            return None

    def put(
        self,
        venue: str,
        pair: str,
        frequency: str,
        df: pd.DataFrame,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store data in cache.

        Args:
            venue: Exchange venue
            pair: Trading pair
            frequency: Data frequency
            df: DataFrame to cache
            metadata: Optional metadata to store
        """
        if df.empty:
            self.logger.warning(f"[DATA:cache:skip] {venue}:{pair}:{frequency} - empty DataFrame")
            return

        cache_path = self.get_cache_path(venue, pair, frequency)

        # Ensure directory exists
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        try:
            # Prepare DataFrame for caching
            cache_df = df.copy()

            # Ensure time column is datetime
            if "time" in cache_df.columns:
                cache_df["time"] = pd.to_datetime(cache_df["time"])

            # Add metadata if provided
            if metadata:
                for key, value in metadata.items():
                    cache_df[f"_meta_{key}"] = value

            # Write to parquet
            cache_df.to_parquet(cache_path, index=False, engine="pyarrow")

            self.logger.info(
                f"[DATA:cache:write] {venue}:{pair}:{frequency} - {len(cache_df)} bars"
            )

        except Exception as e:
            self.logger.error(f"[DATA:cache:error] {venue}:{pair}:{frequency} - {str(e)}")
            raise

    def exists(self, venue: str, pair: str, frequency: str) -> bool:
        """
        Check if cached data exists.

        Args:
            venue: Exchange venue
            pair: Trading pair
            frequency: Data frequency

        Returns:
            True if cache exists and is not empty
        """
        cache_path = self.get_cache_path(venue, pair, frequency)

        if not os.path.exists(cache_path):
            return False

        try:
            # Check if file has data
            df = pd.read_parquet(cache_path)
            return not df.empty
        except Exception:
            return False

    def get_cache_info(self, venue: str, pair: str, frequency: str) -> Dict[str, Any]:
        """
        Get cache file information.

        Args:
            venue: Exchange venue
            pair: Trading pair
            frequency: Data frequency

        Returns:
            Dictionary with cache information
        """
        cache_path = self.get_cache_path(venue, pair, frequency)

        info = {
            "path": cache_path,
            "exists": os.path.exists(cache_path),
            "size_bytes": 0,
            "rows": 0,
            "start_time": None,
            "end_time": None,
        }

        if info["exists"]:
            try:
                # Get file size
                info["size_bytes"] = os.path.getsize(cache_path)

                # Get data info
                df = pd.read_parquet(cache_path)
                info["rows"] = len(df)

                if "time" in df.columns and not df.empty:
                    df["time"] = pd.to_datetime(df["time"])
                    info["start_time"] = df["time"].min()
                    info["end_time"] = df["time"].max()

            except Exception as e:
                self.logger.warning(
                    f"[DATA:cache:info:error] {venue}:{pair}:{frequency} - {str(e)}"
                )

        return info

    def clear_cache(
        self,
        venue: Optional[str] = None,
        pair: Optional[str] = None,
        frequency: Optional[str] = None,
    ) -> int:
        """
        Clear cache files matching criteria.

        Args:
            venue: Exchange venue (None for all)
            pair: Trading pair (None for all)
            frequency: Data frequency (None for all)

        Returns:
            Number of files removed
        """
        removed_count = 0

        if venue and pair and frequency:
            # Clear specific cache file
            cache_path = self.get_cache_path(venue, pair, frequency)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                removed_count = 1
                self.logger.info(f"[DATA:cache:clear] {venue}:{pair}:{frequency}")
        else:
            # Clear matching cache files
            for root, dirs, files in os.walk(self.cache_dir):
                for file in files:
                    if file.endswith(".parquet"):
                        file_path = os.path.join(root, file)

                        # Parse path to extract venue/pair/frequency
                        rel_path = os.path.relpath(file_path, self.cache_dir)
                        path_parts = rel_path.split(os.sep)

                        if len(path_parts) >= 3:
                            file_venue = path_parts[0]
                            file_pair = path_parts[1]
                            file_freq = file.replace(".parquet", "")

                            # Check if matches criteria
                            match = True
                            if venue and file_venue != venue.lower():
                                match = False
                            if (
                                pair
                                and file_pair != pair.replace("-", "_").replace("/", "_").lower()
                            ):
                                match = False
                            if frequency and file_freq != frequency:
                                match = False

                            if match:
                                os.remove(file_path)
                                removed_count += 1
                                self.logger.info(
                                    f"[DATA:cache:clear] {file_venue}:{file_pair}:{file_freq}"
                                )

        return removed_count
