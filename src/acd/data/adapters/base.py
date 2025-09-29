"""
Base adapter interface for market data access.
"""

from abc import ABC, abstractmethod

# from typing import Dict, Any, Optional  # Unused for now
import pandas as pd
from datetime import datetime


class BaseBarsAdapter(ABC):
    """
    Abstract base class for market data adapters.

    All adapters must implement the get() method to return standardized
    OHLCV data with consistent schema.
    """

    @abstractmethod
    def get(
        self, pair: str, venue: str, start_utc: datetime, end_utc: datetime, tz: str = "UTC"
    ) -> pd.DataFrame:
        """
        Get market data for the specified parameters.

        Args:
            pair: Trading pair (e.g., 'BTC-USD')
            venue: Exchange venue (e.g., 'binance')
            start_utc: Start datetime in UTC
            end_utc: End datetime in UTC
            tz: Timezone for output (default: 'UTC')

        Returns:
            DataFrame with columns: [time, open, high, low, close, volume]
        """
        pass

    def _standardize_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame schema to [time, open, high, low, close, volume].

        Args:
            df: Input DataFrame

        Returns:
            Standardized DataFrame
        """
        required_columns = ["time", "open", "high", "low", "close", "volume"]

        # Ensure all required columns exist
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Select and reorder columns
        return df[required_columns].copy()

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate data quality and log issues.

        Args:
            df: Input DataFrame

        Returns:
            Validated DataFrame
        """
        if df.empty:
            return df

        # Check for required columns
        required_columns = ["time", "open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Validate OHLC relationships
        invalid_ohlc = df[
            (df["high"] < df["low"])
            | (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
        ]

        if not invalid_ohlc.empty:
            print(f"[DATA:validation:ohlc] Found {len(invalid_ohlc)} invalid OHLC bars")

        # Check for negative volumes
        negative_volume = df[df["volume"] < 0]
        if not negative_volume.empty:
            print(f"[DATA:validation:volume] Found {len(negative_volume)} negative volume bars")

        return df
