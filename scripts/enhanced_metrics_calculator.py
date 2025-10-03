#!/usr/bin/env python3
"""
Enhanced Metrics Calculator
Implements advanced liquidity metrics and leadership shares calculations
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class EnhancedMetricsCalculator:
    """Enhanced metrics calculator for liquidity and leadership analysis"""

    def calculate_advanced_liquidity_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate advanced liquidity metrics from bid/ask data"""
        if len(df) == 0:
            return {
                "liquidity_score": np.nan,
                "depth_imbalance": np.nan,
                "liquidity_volatility": np.nan,
                "market_impact": np.nan,
                "liquidity_ratio": np.nan,
            }

        # Basic liquidity score (average depth)
        avg_bid_size = df["bid_sz"].mean()
        avg_ask_size = df["ask_sz"].mean()
        liquidity_score = (avg_bid_size + avg_ask_size) / 2

        # Depth imbalance
        depth_imbalance = (
            (avg_bid_size - avg_ask_size) / (avg_bid_size + avg_ask_size)
            if (avg_bid_size + avg_ask_size) > 0
            else 0
        )

        # Liquidity volatility (how much depth changes)
        liquidity_volatility = np.std(df["bid_sz"] + df["ask_sz"])

        # Market impact (spread sensitivity to size)
        if len(df) > 1:
            size_changes = df["last_sz"].diff().abs()
            spread_changes = df["spread_bps"].diff().abs()
            if size_changes.sum() > 0:
                market_impact = (size_changes * spread_changes).sum() / size_changes.sum()
            else:
                market_impact = 0
        else:
            market_impact = 0

        # Liquidity ratio (depth vs volume)
        total_volume = df["last_sz"].sum()
        total_depth = (df["bid_sz"] + df["ask_sz"]).sum()
        liquidity_ratio = total_depth / total_volume if total_volume > 0 else 0

        return {
            "liquidity_score": liquidity_score,
            "depth_imbalance": depth_imbalance,
            "liquidity_volatility": liquidity_volatility,
            "market_impact": market_impact,
            "liquidity_ratio": liquidity_ratio,
        }

    def calculate_advanced_leadership_shares(
        self, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate advanced leadership shares with multiple weighting schemes"""
        if len(data) == 0:
            return {}

        venues = list(data.keys())
        results = {}

        # 1. Volume-weighted leadership
        venue_volumes = {}
        for venue, df in data.items():
            if len(df) > 0:
                venue_volumes[venue] = df["last_sz"].sum()
            else:
                venue_volumes[venue] = 0

        total_volume = sum(venue_volumes.values())
        volume_shares = {
            venue: vol / total_volume if total_volume > 0 else 0
            for venue, vol in venue_volumes.items()
        }

        # 2. Price impact leadership (who moves prices most)
        price_impact = {}
        for venue in venues:
            if venue in data and len(data[venue]) > 0:
                df = data[venue]
                # Calculate price impact as correlation between volume and price changes
                if len(df) > 1:
                    volume_changes = df["last_sz"].diff().abs()
                    price_changes = df["last_px"].pct_change().abs()
                    if volume_changes.sum() > 0 and price_changes.sum() > 0:
                        price_impact[venue] = (
                            volume_changes * price_changes
                        ).sum() / volume_changes.sum()
                    else:
                        price_impact[venue] = 0
                else:
                    price_impact[venue] = 0
            else:
                price_impact[venue] = 0

        # Normalize price impact
        total_impact = sum(price_impact.values())
        impact_shares = {
            venue: impact / total_impact if total_impact > 0 else 0
            for venue, impact in price_impact.items()
        }

        # 3. Information leadership (who leads price discovery)
        info_leadership = {}
        for venue in venues:
            if venue in data and len(data[venue]) > 0:
                df = data[venue]
                # Information leadership as price variance contribution
                if len(df) > 1:
                    price_returns = df["last_px"].pct_change().dropna()
                    info_leadership[venue] = price_returns.var() if len(price_returns) > 0 else 0
                else:
                    info_leadership[venue] = 0
            else:
                info_leadership[venue] = 0

        # Normalize information leadership
        total_info = sum(info_leadership.values())
        info_shares = {
            venue: info / total_info if total_info > 0 else 0
            for venue, info in info_leadership.items()
        }

        # 4. Combined leadership score
        combined_shares = {}
        for venue in venues:
            combined_shares[venue] = (
                0.4 * volume_shares.get(venue, 0)
                + 0.3 * impact_shares.get(venue, 0)
                + 0.3 * info_shares.get(venue, 0)
            )

        results = {
            "volume_weighted": volume_shares,
            "price_impact": impact_shares,
            "information_leadership": info_shares,
            "combined_leadership": combined_shares,
        }

        return results

    def calculate_venue_specialization(
        self, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate venue specialization metrics"""
        if len(data) == 0:
            return {}

        venues = list(data.keys())
        specialization = {}

        for venue in venues:
            if venue not in data or len(data[venue]) == 0:
                specialization[venue] = {
                    "spread_specialist": 0,
                    "volume_specialist": 0,
                    "volatility_specialist": 0,
                    "liquidity_specialist": 0,
                }
                continue

            df = data[venue]

            # Spread specialist (lowest average spread)
            avg_spread = df["spread_bps"].mean()

            # Volume specialist (highest volume)
            total_volume = df["last_sz"].sum()

            # Volatility specialist (highest price volatility)
            if len(df) > 1:
                price_volatility = df["last_px"].pct_change().std()
            else:
                price_volatility = 0

            # Liquidity specialist (highest depth)
            avg_depth = (df["bid_sz"] + df["ask_sz"]).mean()

            specialization[venue] = {
                "spread_specialist": (
                    1 / (1 + avg_spread) if avg_spread > 0 else 0
                ),  # Inverse spread
                "volume_specialist": total_volume,
                "volatility_specialist": price_volatility,
                "liquidity_specialist": avg_depth,
            }

        # Normalize specialization scores
        for metric in [
            "spread_specialist",
            "volume_specialist",
            "volatility_specialist",
            "liquidity_specialist",
        ]:
            values = [specialization[venue][metric] for venue in venues]
            total = sum(values)
            if total > 0:
                for venue in venues:
                    specialization[venue][metric] = specialization[venue][metric] / total

        return specialization

    def calculate_market_microstructure_metrics(
        self, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """Calculate market microstructure metrics"""
        if len(data) == 0:
            return {}

        # Cross-venue spread analysis
        spread_analysis = {}
        for venue, df in data.items():
            if len(df) > 0:
                spread_analysis[venue] = {
                    "mean_spread": df["spread_bps"].mean(),
                    "spread_volatility": df["spread_bps"].std(),
                    "spread_trend": df["spread_bps"].diff().mean(),
                }

        # Market fragmentation analysis
        fragmentation = {
            "venue_count": len(data),
            "active_venues": sum(1 for df in data.values() if len(df) > 0),
            "venue_dominance": (
                max(len(df) for df in data.values()) / sum(len(df) for df in data.values())
                if sum(len(df) for df in data.values()) > 0
                else 0
            ),
        }

        # Price discovery analysis
        price_discovery = {}
        for venue, df in data.items():
            if len(df) > 1:
                price_changes = df["last_px"].pct_change().dropna()
                price_discovery[venue] = {
                    "price_volatility": price_changes.std(),
                    "price_trend": price_changes.mean(),
                    "price_autocorrelation": (
                        price_changes.autocorr() if len(price_changes) > 1 else 0
                    ),
                }
            else:
                price_discovery[venue] = {
                    "price_volatility": 0,
                    "price_trend": 0,
                    "price_autocorrelation": 0,
                }

        return {
            "spread_analysis": spread_analysis,
            "fragmentation": fragmentation,
            "price_discovery": price_discovery,
        }


def main():
    """Test the enhanced metrics calculator"""
    import json

    # This would be called from the continuous measurement system
    calculator = EnhancedMetricsCalculator()

    # Example usage (would be integrated into continuous_measurement.py)
    print("Enhanced metrics calculator ready for integration")
    print("Available methods:")
    print("- calculate_advanced_liquidity_metrics()")
    print("- calculate_advanced_leadership_shares()")
    print("- calculate_venue_specialization()")
    print("- calculate_market_microstructure_metrics()")


if __name__ == "__main__":
    main()
