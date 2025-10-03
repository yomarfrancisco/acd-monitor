#!/usr/bin/env python3
"""
Compute Market Structure for Extended Panel

Reuse existing script logic to compute market structure on the 7-day extended panel.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class ExtendedMarketStructureComputer:
    """Compute market structure for extended panel."""

    def __init__(self):
        self.data_dir = "data/derived/btc_usd"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

    def compute_extended_market_structure(self):
        """Compute market structure for extended panel."""
        print(f"🔧 Computing Market Structure for Extended Panel")
        print("=" * 50)

        # Check if already exists
        output_file = f"{self.data_dir}/market_structure_7d.parquet"
        if os.path.exists(output_file):
            print(f"⚠️ Market structure already exists: {output_file}")
            print("  Skipping computation to avoid duplication")
            return

        # Load extended panel
        panel_file = f"{self.data_dir}/panel_1s_inner_7d_aligned.parquet"
        if not os.path.exists(panel_file):
            print(f"❌ Extended panel file not found: {panel_file}")
            return

        panel_data = pd.read_parquet(panel_file)
        print(f"📊 Loaded extended panel: {len(panel_data)} observations")
        print(f"📅 Date range: {panel_data.index.min()} to {panel_data.index.max()}")

        # Compute market structure
        market_structure = self._compute_market_structure(panel_data)

        # Save market structure
        market_structure.to_parquet(output_file)
        print(f"💾 Market structure saved to {output_file}")
        print(f"  Rows: {len(market_structure)}")
        print(f"  Columns: {len(market_structure.columns)}")

        # Print QC statistics
        self._print_qc_stats(market_structure)

        print(f"✅ Extended market structure computed")

    def _compute_market_structure(self, panel_data):
        """Compute market structure from panel data."""
        print("🔄 Computing market structure...")

        # Calculate median mid price across venues
        mid_columns = [
            f"{venue}_mid_px" for venue in self.venues if f"{venue}_mid_px" in panel_data.columns
        ]

        if not mid_columns:
            print("❌ No mid price columns found")
            return pd.DataFrame()

        # Calculate median mid price
        mid_prices = panel_data[mid_columns].dropna()
        median_mid = mid_prices.median(axis=1)

        print(f"  📊 Median mid price: {len(median_mid)} observations")

        # Create 5-second bars
        print("  📊 Creating 5-second bars...")
        bars_5s = (
            median_mid.resample("5S")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
        )

        # Rename columns
        bars_5s.columns = ["open", "high", "low", "close"]

        print(f"  📊 5-second bars: {len(bars_5s)} bars")

        # Compute ATR14
        print("  📊 Computing ATR14...")
        bars_5s["atr14"] = self._compute_atr14(bars_5s)

        # Compute fractal swings
        print("  📊 Computing fractal swings...")
        bars_5s["swing_high"] = self._compute_swing_highs(bars_5s)
        bars_5s["swing_low"] = self._compute_swing_lows(bars_5s)

        # Compute BOS/CHoCH
        print("  📊 Computing BOS/CHoCH...")
        bars_5s = self._compute_bos_choch(bars_5s)

        # Add bar timestamps
        bars_5s["bar_ts"] = bars_5s.index

        return bars_5s

    def _compute_atr14(self, bars):
        """Compute ATR14 on 5-second bars."""
        high_low = bars["high"] - bars["low"]
        high_close = np.abs(bars["high"] - bars["close"].shift(1))
        low_close = np.abs(bars["low"] - bars["close"].shift(1))

        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr14 = true_range.rolling(window=14, min_periods=1).mean()

        return atr14

    def _compute_swing_highs(self, bars):
        """Compute swing highs with k=2."""
        swing_highs = pd.Series(0, index=bars.index)

        for i in range(2, len(bars) - 2):
            if (
                bars["high"].iloc[i] > bars["high"].iloc[i - 1]
                and bars["high"].iloc[i] > bars["high"].iloc[i - 2]
                and bars["high"].iloc[i] > bars["high"].iloc[i + 1]
                and bars["high"].iloc[i] > bars["high"].iloc[i + 2]
            ):
                swing_highs.iloc[i] = 1

        return swing_highs

    def _compute_swing_lows(self, bars):
        """Compute swing lows with k=2."""
        swing_lows = pd.Series(0, index=bars.index)

        for i in range(2, len(bars) - 2):
            if (
                bars["low"].iloc[i] < bars["low"].iloc[i - 1]
                and bars["low"].iloc[i] < bars["low"].iloc[i - 2]
                and bars["low"].iloc[i] < bars["low"].iloc[i + 1]
                and bars["low"].iloc[i] < bars["low"].iloc[i + 2]
            ):
                swing_lows.iloc[i] = 1

        return swing_lows

    def _compute_bos_choch(self, bars):
        """Compute BOS and CHoCH logic."""
        # Initialize columns
        bars["bos_up"] = 0
        bars["bos_dn"] = 0
        bars["choch_up"] = 0
        bars["choch_dn"] = 0
        bars["structure_state"] = "neutral"
        bars["last_swing_high"] = np.nan
        bars["last_swing_low"] = np.nan

        # Initialize tracking variables
        last_swing_high = None
        last_swing_low = None
        structure_state = "neutral"

        for i in range(len(bars)):
            current_high = bars["high"].iloc[i]
            current_low = bars["low"].iloc[i]
            current_close = bars["close"].iloc[i]
            current_atr = bars["atr14"].iloc[i]

            # Update swing highs
            if bars["swing_high"].iloc[i] == 1:
                last_swing_high = current_high
                bars["last_swing_high"].iloc[i] = current_high

            # Update swing lows
            if bars["swing_low"].iloc[i] == 1:
                last_swing_low = current_low
                bars["last_swing_low"].iloc[i] = current_low

            # BOS logic
            if last_swing_high is not None and current_close > last_swing_high + 0.25 * current_atr:
                bars["bos_up"].iloc[i] = 1
                if structure_state == "down":
                    bars["choch_up"].iloc[i] = 1
                structure_state = "up"

            if last_swing_low is not None and current_close < last_swing_low - 0.25 * current_atr:
                bars["bos_dn"].iloc[i] = 1
                if structure_state == "up":
                    bars["choch_dn"].iloc[i] = 1
                structure_state = "down"

            bars["structure_state"].iloc[i] = structure_state

        return bars

    def _print_qc_stats(self, market_structure):
        """Print QC statistics."""
        print("\n📊 QC Statistics:")
        print("=" * 30)

        # Basic stats
        print(f"Total bars: {len(market_structure):,}")
        print(f"Date range: {market_structure.index.min()} to {market_structure.index.max()}")

        # BOS events
        bos_up_count = market_structure["bos_up"].sum()
        bos_dn_count = market_structure["bos_dn"].sum()
        print(f"\nBOS events:")
        print(f"  Up: {bos_up_count:,}")
        print(f"  Down: {bos_dn_count:,}")

        # CHoCH events
        choch_up_count = market_structure["choch_up"].sum()
        choch_dn_count = market_structure["choch_dn"].sum()
        print(f"\nCHoCH events:")
        print(f"  Up: {choch_up_count:,}")
        print(f"  Down: {choch_dn_count:,}")

        # Swing events
        swing_high_count = market_structure["swing_high"].sum()
        swing_low_count = market_structure["swing_low"].sum()
        print(f"\nSwing events:")
        print(f"  Highs: {swing_high_count:,}")
        print(f"  Lows: {swing_low_count:,}")

        # Structure states
        state_counts = market_structure["structure_state"].value_counts()
        print(f"\nStructure states:")
        for state, count in state_counts.items():
            pct = count / len(market_structure) * 100
            print(f"  {state}: {count:,} ({pct:.1f}%)")

        # ATR statistics
        atr_stats = market_structure["atr14"].describe()
        print(f"\nATR14 statistics:")
        print(f"  Mean: {atr_stats['mean']:.6f}")
        print(f"  Std: {atr_stats['std']:.6f}")
        print(f"  Min: {atr_stats['min']:.6f}")
        print(f"  Max: {atr_stats['max']:.6f}")


def main():
    """Main function."""
    computer = ExtendedMarketStructureComputer()
    computer.compute_extended_market_structure()


if __name__ == "__main__":
    main()
