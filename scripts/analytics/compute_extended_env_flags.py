#!/usr/bin/env python3
"""
Compute Environment Flags for Extended Panel

Reuse existing script logic to compute environment flags on the 7-day extended panel.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class ExtendedEnvFlagsComputer:
    """Compute environment flags for extended panel."""

    def __init__(self):
        self.data_dir = "data/derived/btc_usd"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

    def compute_extended_env_flags(self):
        """Compute environment flags for extended panel."""
        print(f"🔧 Computing Environment Flags for Extended Panel")
        print("=" * 50)

        # Check if already exists
        output_file = f"{self.data_dir}/env_flags_1s_7d.parquet"
        if os.path.exists(output_file):
            print(f"⚠️ Environment flags already exist: {output_file}")
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

        # Initialize flags DataFrame
        flags_df = pd.DataFrame(index=panel_data.index)
        flags_df["ts"] = panel_data.index

        # Compute session flags
        print("\n🕐 Computing session flags...")
        self._compute_session_flags(flags_df)
        print("  ✅ Session flags computed")

        # Compute shock flags
        print("\n⚡ Computing shock flags...")
        self._compute_shock_flags(panel_data, flags_df)
        print("  ✅ Shock flags computed")

        # Compute liquidity proxies
        print("\n💧 Computing liquidity proxies...")
        self._compute_liquidity_proxies(panel_data, flags_df)
        print("  ✅ Liquidity proxies computed")

        # Save flags
        flags_df.to_parquet(output_file)
        print(f"💾 Environment flags saved to {output_file}")
        print(f"  Rows: {len(flags_df)}")
        print(f"  Columns: {len(flags_df.columns)}")

        # Print QC statistics
        self._print_qc_stats(flags_df)

        print(f"✅ Extended environment flags computed")

    def _compute_session_flags(self, flags_df):
        """Compute session labels and transition flags."""

        # Session labels
        def get_session_label(hour):
            if 0 <= hour < 8:
                return "Asia"
            elif 8 <= hour < 13:
                return "Europe"
            elif 13 <= hour < 20:
                return "US"
            else:
                return "Pacific"

        flags_df["session_label"] = flags_df.index.hour.map(get_session_label)

        # Session transitions
        transition_times = [0, 8, 13, 20]  # UTC hours
        flags_df["is_session_transition"] = 0

        for hour in transition_times:
            # Flag ±5 minutes around transition
            mask = (flags_df.index.hour == hour) & (flags_df.index.minute <= 5)
            flags_df.loc[mask, "is_session_transition"] = 1

        # NY open window
        flags_df["is_ny_open"] = 0
        ny_mask = (
            (flags_df.index.hour == 13)
            & (flags_df.index.minute >= 30)
            & (flags_df.index.minute <= 45)
        )
        flags_df.loc[ny_mask, "is_ny_open"] = 1

        # VWAP reset window
        flags_df["is_vwap_reset_window"] = 0
        vwap_mask = (flags_df.index.hour == 0) & (flags_df.index.minute <= 5)
        flags_df.loc[vwap_mask, "is_vwap_reset_window"] = 1

    def _compute_shock_flags(self, panel_data, flags_df):
        """Compute return and VWAP deviation shock flags."""
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in panel_data.columns:
                # Return 2-sigma flags
                returns = np.log(panel_data[mid_col]).diff().fillna(0)
                rolling_std = returns.rolling(window=1800, min_periods=900).std()
                flags_df[f"is_return_2sigma_{venue}"] = (returns.abs() > 2 * rolling_std).astype(
                    int
                )

                # VWAP deviation 2-sigma flags
                # Simple VWAP as mean of mid prices
                daily_vwap = panel_data[mid_col].resample("D").mean()
                daily_vwap = daily_vwap.reindex(panel_data.index, method="ffill")

                deviations = panel_data[mid_col] - daily_vwap
                deviation_std = deviations.rolling(window=1800, min_periods=900).std()
                flags_df[f"is_vwap_dev_2sigma_{venue}"] = (
                    deviations.abs() > 2 * deviation_std
                ).astype(int)

    def _compute_liquidity_proxies(self, panel_data, flags_df):
        """Compute liquidity proxies."""
        for venue in self.venues:
            bid_col = f"{venue}_best_bid"
            ask_col = f"{venue}_best_ask"

            if bid_col in panel_data.columns and ask_col in panel_data.columns:
                # Spread
                flags_df[f"spread_{venue}"] = panel_data[ask_col] - panel_data[bid_col]

    def _print_qc_stats(self, flags_df):
        """Print QC statistics."""
        print("\n📊 QC Statistics:")
        print("=" * 30)

        # Session distribution
        session_counts = flags_df["session_label"].value_counts()
        print("Session distribution:")
        for session, count in session_counts.items():
            pct = count / len(flags_df) * 100
            print(f"  {session}: {count:,} ({pct:.1f}%)")

        # Shock events
        shock_events = {}
        for venue in self.venues:
            return_col = f"is_return_2sigma_{venue}"
            vwap_col = f"is_vwap_dev_2sigma_{venue}"

            if return_col in flags_df.columns:
                shock_events[f"{venue}_return"] = flags_df[return_col].sum()
            if vwap_col in flags_df.columns:
                shock_events[f"{venue}_vwap"] = flags_df[vwap_col].sum()

        print(f"\nShock events:")
        for event, count in shock_events.items():
            print(f"  {event}: {count:,}")

        # Transition events
        transition_events = flags_df["is_session_transition"].sum()
        ny_open_events = flags_df["is_ny_open"].sum()
        vwap_reset_events = flags_df["is_vwap_reset_window"].sum()

        print(f"\nTransition events:")
        print(f"  Session transitions: {transition_events:,}")
        print(f"  NY open windows: {ny_open_events:,}")
        print(f"  VWAP reset windows: {vwap_reset_events:,}")

        # Coverage
        total_obs = len(flags_df)
        coverage_pct = (
            (total_obs - flags_df.isna().sum().sum() / len(flags_df.columns)) / total_obs * 100
        )
        print(f"\nCoverage: {coverage_pct:.1f}%")


def main():
    """Main function."""
    computer = ExtendedEnvFlagsComputer()
    computer.compute_extended_env_flags()


if __name__ == "__main__":
    main()
