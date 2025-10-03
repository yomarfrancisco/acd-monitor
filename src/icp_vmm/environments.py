#!/usr/bin/env python3
"""
Environment Labeling for ICP-VMM Analysis

Labels observations by market environment for invariance testing.
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class EnvironmentLabeler:
    """Labels observations by market environment for ICP-VMM analysis."""

    def __init__(self, min_obs_per_env: int = 5):
        self.min_obs_per_env = min_obs_per_env

    def label_session(self, timestamps: pd.Series) -> pd.Series:
        """
        Label observations by trading session.

        Args:
            timestamps: UTC timestamps

        Returns:
            Series with labels: {asia, europe, us, overlap}
        """
        labels = []

        for ts in timestamps:
            hour = ts.hour

            if 0 <= hour < 8:
                labels.append("asia")
            elif 8 <= hour < 16:
                labels.append("europe")
            elif 16 <= hour < 24:
                labels.append("us")
            else:
                labels.append("overlap")

        return pd.Series(labels, index=timestamps.index)

    def label_vwap_side(self, prices: pd.Series, daily_vwap: float) -> pd.Series:
        """
        Label observations by VWAP side.

        Args:
            prices: Price series
            daily_vwap: Daily VWAP value

        Returns:
            Series with labels: {below, above}
        """
        return pd.Series(
            ["below" if px < daily_vwap else "above" for px in prices],
            index=prices.index,
        )

    def label_high_low(self, prices: pd.Series, day_high: float, day_low: float) -> pd.Series:
        """
        Label observations by high/low proximity.

        Args:
            prices: Price series
            day_high: Daily high
            day_low: Daily low

        Returns:
            Series with labels: {near_high, mid, near_low}
        """
        range_size = day_high - day_low
        if range_size == 0:
            return pd.Series(["mid"] * len(prices), index=prices.index)

        # Define proximity thresholds (top/bottom 20% of range)
        high_threshold = day_high - 0.2 * range_size
        low_threshold = day_low + 0.2 * range_size

        labels = []
        for px in prices:
            if px >= high_threshold:
                labels.append("near_high")
            elif px <= low_threshold:
                labels.append("near_low")
            else:
                labels.append("mid")

        return pd.Series(labels, index=prices.index)

    def label_liquidity(
        self, liquidity_ratio: pd.Series, liquidity_volatility: pd.Series
    ) -> pd.Series:
        """
        Label observations by liquidity regime.

        Args:
            liquidity_ratio: Liquidity ratio series
            liquidity_volatility: Liquidity volatility series

        Returns:
            Series with labels: {thin, normal, deep}
        """
        # Use percentiles for regime classification
        ratio_q33 = liquidity_ratio.quantile(0.33)
        ratio_q67 = liquidity_ratio.quantile(0.67)
        vol_q67 = liquidity_volatility.quantile(0.67)

        labels = []
        for i, (ratio, vol) in enumerate(zip(liquidity_ratio, liquidity_volatility)):
            if ratio < ratio_q33 or vol > vol_q67:
                labels.append("thin")
            elif ratio > ratio_q67:
                labels.append("deep")
            else:
                labels.append("normal")

        return pd.Series(labels, index=liquidity_ratio.index)

    def label_leadership(self, leadership_shares: pd.Series) -> pd.Series:
        """
        Label observations by leadership concentration.

        Args:
            leadership_shares: Leadership share series (HHI or max share)

        Returns:
            Series with labels: {concentrated, diffuse}
        """
        # Use median as threshold
        threshold = leadership_shares.median()

        return pd.Series(
            ["concentrated" if share > threshold else "diffuse" for share in leadership_shares],
            index=leadership_shares.index,
        )

    def label_all_environments(self, data: pd.DataFrame, continuous_metrics: Dict) -> pd.DataFrame:
        """
        Apply all environment labels to the dataset.

        Args:
            data: Tick data with timestamps and prices
            continuous_metrics: Continuous metrics dict

        Returns:
            DataFrame with all environment labels
        """
        labeled_data = data.copy()

        # Session labeling
        if "ts_exchange" in data.columns:
            labeled_data["session"] = self.label_session(data["ts_exchange"])

        # VWAP side labeling
        if "last_px" in data.columns and "daily_vwap" in continuous_metrics:
            labeled_data["vwap_side"] = self.label_vwap_side(
                data["last_px"], continuous_metrics["daily_vwap"]
            )

        # High/Low proximity labeling
        if (
            "last_px" in data.columns
            and "day_high" in continuous_metrics
            and "day_low" in continuous_metrics
        ):
            labeled_data["hl_bucket"] = self.label_high_low(
                data["last_px"],
                continuous_metrics["day_high"],
                continuous_metrics["day_low"],
            )

        # Liquidity regime labeling
        if "liquidity_ratio" in continuous_metrics and "liquidity_volatility" in continuous_metrics:
            labeled_data["liquidity_regime"] = self.label_liquidity(
                continuous_metrics["liquidity_ratio"],
                continuous_metrics["liquidity_volatility"],
            )

        # Leadership regime labeling
        if "leadership_shares" in continuous_metrics:
            labeled_data["leadership_regime"] = self.label_leadership(
                continuous_metrics["leadership_shares"]
            )

        return labeled_data

    def get_environment_counts(self, labeled_data: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Get observation counts per environment.

        Args:
            labeled_data: Data with environment labels

        Returns:
            Dict with counts per environment
        """
        env_columns = [
            "session",
            "vwap_side",
            "hl_bucket",
            "liquidity_regime",
            "leadership_regime",
        ]
        counts = {}

        for col in env_columns:
            if col in labeled_data.columns:
                counts[col] = labeled_data[col].value_counts().to_dict()

        return counts

    def validate_environment_balance(
        self, counts: Dict[str, Dict[str, int]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate environment balance for sufficient observations.

        Args:
            counts: Environment counts dict

        Returns:
            Tuple of (is_balanced, warnings)
        """
        warnings = []
        is_balanced = True

        for env_type, env_counts in counts.items():
            total_obs = sum(env_counts.values())
            min_obs = min(env_counts.values()) if env_counts else 0

            if total_obs < self.min_obs_per_env * 2:
                warnings.append(f"{env_type}: insufficient total observations ({total_obs})")
                is_balanced = False
            elif min_obs < self.min_obs_per_env:
                warnings.append(f"{env_type}: some bins have < {self.min_obs_per_env} obs")
                is_balanced = False

        return is_balanced, warnings
