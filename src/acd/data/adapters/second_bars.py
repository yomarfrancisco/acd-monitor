"""
Second-level bars adapter for market data access.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# from typing import Dict, Any, Optional  # Unused for now
import logging

from .base import BaseBarsAdapter


class SecondBarsAdapter(BaseBarsAdapter):
    """
    Adapter for second-level OHLCV data.

    Provides standardized access to second bars with synthetic generation
    when native second data is unavailable.
    """

    def __init__(self, cache_enabled: bool = True, synthetic: bool = True):
        self.cache_enabled = cache_enabled
        self.synthetic = synthetic
        self.logger = logging.getLogger(__name__)

    def get(
        self, pair: str, venue: str, start_utc: datetime, end_utc: datetime, tz: str = "UTC"
    ) -> pd.DataFrame:
        """
        Get second-level bars for the specified parameters.

        Args:
            pair: Trading pair (e.g., 'BTC-USD')
            venue: Exchange venue (e.g., 'binance')
            start_utc: Start datetime in UTC
            end_utc: End datetime in UTC
            tz: Timezone for output (default: 'UTC')

        Returns:
            DataFrame with columns: [time, open, high, low, close, volume]
        """
        self.logger.info(f"[DATA:second:request] {venue}:{pair} {start_utc} to {end_utc}")

        if self.synthetic:
            self.logger.info(
                "[DATA:second:synthetic] Using synthetic second bars (isSyntheticSecond=true)"
            )
            df = self._generate_synthetic_seconds(pair, venue, start_utc, end_utc)
        else:
            # In production, this would fetch real second data
            df = self._fetch_native_seconds(pair, venue, start_utc, end_utc)

        # Standardize schema
        df = self._standardize_schema(df)

        # Validate data
        df = self._validate_data(df)

        # Convert timezone if needed
        if tz != "UTC" and "time" in df.columns:
            df["time"] = df["time"].dt.tz_convert(tz)

        self.logger.info(f"[DATA:second:response] {len(df)} bars for {venue}:{pair}")

        return df

    def _generate_synthetic_seconds(
        self, pair: str, venue: str, start_utc: datetime, end_utc: datetime
    ) -> pd.DataFrame:
        """
        Generate synthetic second bars by evenly distributing minute moves.

        Args:
            pair: Trading pair
            venue: Exchange venue
            start_utc: Start datetime
            end_utc: End datetime

        Returns:
            DataFrame with second bars
        """
        # First get minute data
        from .minute_bars import MinuteBarsAdapter

        minute_adapter = MinuteBarsAdapter()
        minute_df = minute_adapter.get(pair, venue, start_utc, end_utc)

        if minute_df.empty:
            return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

        # Generate second bars by distributing minute moves
        second_data = []

        for _, minute_row in minute_df.iterrows():
            minute_start = minute_row["time"]
            minute_end = minute_start + timedelta(minutes=1)

            # Create 60 second timestamps within this minute
            second_timestamps = pd.date_range(
                start=minute_start, end=minute_end - timedelta(seconds=1), freq="1s", tz="UTC"
            )

            # Distribute the minute move across 60 seconds
            total_move = minute_row["close"] - minute_row["open"]
            volume_per_second = minute_row["volume"] / 60

            # Generate second-by-second prices
            for i, second_ts in enumerate(second_timestamps):
                # Linear interpolation of price within the minute
                progress = i / 59.0  # 0 to 1
                price = minute_row["open"] + total_move * progress

                # Add small random variation for realism
                variation = np.random.normal(0, abs(total_move) * 0.01)
                price += variation

                # Generate OHLC for this second
                # Most seconds will have OHLC = same price, but some will have small ranges
                if np.random.random() < 0.1:  # 10% chance of intra-second range
                    range_size = abs(total_move) * 0.1
                    high = price + range_size * np.random.random()
                    low = price - range_size * np.random.random()
                else:
                    high = low = price

                second_data.append(
                    {
                        "time": second_ts,
                        "open": round(price, 2),
                        "high": round(high, 2),
                        "low": round(low, 2),
                        "close": round(price, 2),
                        "volume": round(volume_per_second, 2),
                    }
                )

        df = pd.DataFrame(second_data)

        self.logger.info(f"[DATA:second:synthetic] Generated {len(df)} synthetic second bars")

        return df

    def _fetch_native_seconds(
        self, pair: str, venue: str, start_utc: datetime, end_utc: datetime
    ) -> pd.DataFrame:
        """
        Fetch native second data from source (placeholder for production).

        Args:
            pair: Trading pair
            venue: Exchange venue
            start_utc: Start datetime
            end_utc: End datetime

        Returns:
            DataFrame with second bars
        """
        # Placeholder for real second data fetching
        # In production, this would connect to real-time data feeds

        self.logger.warning(
            f"[DATA:second:native] Native second data not available for {venue}:{pair}"
        )

        # Fall back to synthetic generation
        return self._generate_synthetic_seconds(pair, venue, start_utc, end_utc)
