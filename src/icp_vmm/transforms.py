#!/usr/bin/env python3
"""
Data Transforms for ICP-VMM Analysis

Handles return series construction, alignment, and preprocessing.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms tick data for ICP-VMM analysis."""

    def __init__(self, winsorize_pct: float = 0.001, aggregation_seconds: int = 2):
        self.winsorize_pct = winsorize_pct
        self.aggregation_seconds = aggregation_seconds

    def construct_returns(self, prices: pd.Series) -> pd.Series:
        """
        Construct log returns from price series.

        Args:
            prices: Price series

        Returns:
            Log returns series
        """
        log_prices = np.log(prices)
        returns = log_prices.diff()
        return returns.dropna()

    def winsorize_returns(self, returns: pd.Series) -> pd.Series:
        """
        Winsorize extreme returns.

        Args:
            returns: Returns series

        Returns:
            Winsorized returns
        """
        lower_bound = returns.quantile(self.winsorize_pct)
        upper_bound = returns.quantile(1 - self.winsorize_pct)

        return returns.clip(lower_bound, upper_bound)

    def align_venue_data(self, venue_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Align data across venues by timestamp.

        Args:
            venue_data: Dict of venue DataFrames

        Returns:
            Aligned venue data
        """
        aligned_data = {}

        # Get common timestamp range
        all_timestamps = []
        for venue, df in venue_data.items():
            if "ts_exchange" in df.columns:
                all_timestamps.extend(df["ts_exchange"].tolist())

        if not all_timestamps:
            return aligned_data

        min_ts = min(all_timestamps)
        max_ts = max(all_timestamps)

        # Align each venue to common range
        for venue, df in venue_data.items():
            if "ts_exchange" in df.columns:
                mask = (df["ts_exchange"] >= min_ts) & (df["ts_exchange"] <= max_ts)
                aligned_data[venue] = df[mask].copy()

        return aligned_data

    def aggregate_microstructure(
        self, data: pd.DataFrame, timestamp_col: str = "ts_exchange"
    ) -> pd.DataFrame:
        """
        Aggregate data to reduce microstructure noise.

        Args:
            data: Tick data
            timestamp_col: Timestamp column name

        Returns:
            Aggregated data
        """
        if timestamp_col not in data.columns:
            return data

        # Round timestamps to aggregation interval
        data = data.copy()
        data[timestamp_col] = data[timestamp_col].dt.floor(f"{self.aggregation_seconds}s")

        # Aggregate by timestamp - only use available columns
        agg_dict = {
            "last_px": "last",
            "best_bid": "last",
            "best_ask": "last",
            "bid_sz": "mean",
            "ask_sz": "mean",
        }

        # Add optional columns if they exist
        if "spread_bps" in data.columns:
            agg_dict["spread_bps"] = "mean"
        if "imbalance" in data.columns:
            agg_dict["imbalance"] = "mean"
        if "trade_sz" in data.columns:
            agg_dict["trade_sz"] = "mean"

        agg_data = data.groupby(timestamp_col).agg(agg_dict).reset_index()

        return agg_data

    def handle_eth_schema_incomplete(
        self, data: pd.DataFrame, continuous_metrics: Dict
    ) -> Tuple[pd.DataFrame, Dict, List[str]]:
        """
        Handle ETH schema incompleteness gracefully.

        Args:
            data: Tick data
            continuous_metrics: Continuous metrics

        Returns:
            Tuple of (processed_data, processed_metrics, warnings)
        """
        warnings = []
        processed_data = data.copy()
        processed_metrics = continuous_metrics.copy()  # noqa: F841

        # Check for missing fields
        missing_fields = []
        required_fields = ["spread_bps", "bid_sz", "ask_sz", "imbalance"]

        for field in required_fields:
            if field not in data.columns:
                missing_fields.append(field)

        if missing_fields:
            warnings.append(f"ETH schema incomplete: missing {missing_fields}")

            # Create dummy fields for missing data
            for field in missing_fields:
                if field == "spread_bps":
                    processed_data[field] = 0.0
                elif field in ["bid_sz", "ask_sz", "imbalance"]:
                    processed_data[field] = 1.0

        # Check continuous metrics completeness
        missing_metrics = []
        required_metrics = [
            "liquidity_ratio",
            "liquidity_volatility",
            "leadership_shares",
        ]

        for metric in required_metrics:
            if metric not in continuous_metrics:
                missing_metrics.append(metric)

        if missing_metrics:
            warnings.append(f"Missing continuous metrics: {missing_metrics}")

            # Create dummy metrics
            for metric in missing_metrics:
                if metric == "liquidity_ratio":
                    processed_metrics[metric] = pd.Series([1.0] * len(data))
                elif metric == "liquidity_volatility":
                    processed_metrics[metric] = pd.Series([0.1] * len(data))
                elif metric == "leadership_shares":
                    processed_metrics[metric] = pd.Series([0.5] * len(data))

        return processed_data, processed_metrics, warnings

    def prepare_analysis_data(
        self, venue_data: Dict[str, pd.DataFrame], continuous_metrics: Dict
    ) -> Tuple[Dict[str, pd.DataFrame], Dict, List[str]]:
        """
        Prepare data for ICP-VMM analysis.

        Args:
            venue_data: Dict of venue DataFrames
            continuous_metrics: Continuous metrics

        Returns:
            Tuple of (prepared_data, prepared_metrics, warnings)
        """
        warnings = []
        prepared_data = {}

        # Align venue data
        aligned_data = self.align_venue_data(venue_data)

        # Process each venue
        for venue, data in aligned_data.items():
            # Handle ETH schema incompleteness
            if venue == "ETH-USD":
                processed_data, processed_metrics, eth_warnings = self.handle_eth_schema_incomplete(
                    data, continuous_metrics
                )
                warnings.extend(eth_warnings)
            else:
                processed_data = data.copy()
                processed_metrics = continuous_metrics.copy()  # noqa: F841

            # Aggregate microstructure noise
            if len(processed_data) > 0:
                aggregated_data = self.aggregate_microstructure(processed_data)
                prepared_data[venue] = aggregated_data
            else:
                warnings.append(f"No data for venue {venue}")

        return prepared_data, continuous_metrics, warnings
