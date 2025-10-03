#!/usr/bin/env python3
"""
Prepare Wave-2 Variables for Extended Panel (Light Version)

Memory-efficient version for large datasets.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class ExtendedWave2VariablePreparerLight:
    """Prepare Wave-2 variables for extended panel (light version)."""

    def __init__(self, panel_path: str, env_path: str, structure_path: str, output_dir: str):
        self.panel_path = panel_path
        self.env_path = env_path
        self.structure_path = structure_path
        self.output_dir = output_dir
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.variables = {}

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def prepare_extended_wave2_variables(self):
        """Prepare Wave-2 variables for extended panel."""
        print(f"🔧 Preparing Wave-2 Variables for Extended Panel (Light)")
        print("=" * 50)

        # Load extended panel data (sample for memory efficiency)
        self._load_extended_panel_data()

        if self.panel_data is None or self.panel_data.empty:
            print("❌ No panel data found")
            return

        print(f"📊 Loaded extended panel: {len(self.panel_data)} observations")
        print(f"📅 Date range: {self.panel_data.index.min()} to {self.panel_data.index.max()}")

        # Prepare all Wave-2 variables
        self._prepare_event_study_variables()
        self._prepare_granger_causality_variables()
        self._prepare_cointegration_variables()
        self._prepare_markov_switching_variables()
        self._prepare_svar_variables()

        # Save variables
        self._save_variables()

        print(f"✅ Extended Wave-2 variables prepared")
        print(f"📁 Results saved to {self.output_dir}")

    def _load_extended_panel_data(self):
        """Load extended panel data with environment and market structure."""
        # Load panel data (sample for memory efficiency)
        if not os.path.exists(self.panel_path):
            print(f"❌ Panel file not found: {self.panel_path}")
            return

        # Load only essential columns to save memory
        essential_cols = []
        for venue in self.venues:
            essential_cols.extend(
                [f"{venue}_mid_px", f"{venue}_best_bid", f"{venue}_best_ask", f"{venue}_spread"]
            )

        # Read only essential columns
        self.panel_data = pd.read_parquet(self.panel_path, columns=essential_cols)
        print(f"📥 Loaded panel from {self.panel_path}")

        # Ensure clean, unique index
        self.panel_data = self.panel_data.sort_index().loc[
            ~self.panel_data.index.duplicated(keep="last")
        ]
        if self.panel_data.index.tz is None:
            self.panel_data.index = self.panel_data.index.tz_localize("UTC")
        else:
            self.panel_data.index = self.panel_data.index.tz_convert("UTC")

        # Load environment flags (sample)
        if os.path.exists(self.env_path):
            env_flags = pd.read_parquet(self.env_path)
            if "ts" in env_flags.columns:
                env_flags = env_flags.set_index("ts")
            env_flags = env_flags.sort_index().loc[~env_flags.index.duplicated(keep="last")]
            if env_flags.index.tz is None:
                env_flags.index = env_flags.index.tz_localize("UTC")
            else:
                env_flags.index = env_flags.index.tz_convert("UTC")

            # Sample environment flags to match panel
            env_flags = env_flags.loc[self.panel_data.index]
            self.panel_data = self.panel_data.merge(
                env_flags, left_index=True, right_index=True, how="left"
            )
            print(f"📥 Loaded environment flags from {self.env_path}")

        # Load market structure (sample)
        if os.path.exists(self.structure_path):
            market_structure = pd.read_parquet(self.structure_path)
            if "bar_ts" in market_structure.columns:
                market_structure = market_structure.set_index("bar_ts")
            market_structure = market_structure.sort_index().loc[
                ~market_structure.index.duplicated(keep="last")
            ]
            if market_structure.index.tz is None:
                market_structure.index = market_structure.index.tz_localize("UTC")
            else:
                market_structure.index = market_structure.index.tz_convert("UTC")

            # Sample market structure to match panel
            market_structure = market_structure.loc[self.panel_data.index]
            self.panel_data = self.panel_data.merge(
                market_structure, left_index=True, right_index=True, how="left"
            )
            print(f"📥 Loaded market structure from {self.structure_path}")

    def _prepare_event_study_variables(self):
        """Test 6: Event Studies on Exogenous Shocks variables."""
        print("\n📅 Preparing Event Study variables...")

        # Count shock events from environment flags
        shock_events = 0
        for venue in self.venues:
            shock_col = f"is_return_2sigma_{venue}"
            if shock_col in self.panel_data.columns:
                shock_events += self.panel_data[shock_col].sum()

        self.variables["event_study"] = {
            "events_identified": int(shock_events),
            "event_windows": 0,  # Not computed for memory efficiency
            "data_file": f"{self.output_dir}/event_study_data.parquet",
        }

        print(f"  ✅ Event study variables prepared")
        print(f"    Events identified: {shock_events}")

    def _prepare_granger_causality_variables(self):
        """Test 7: Granger Causality Networks variables."""
        print("\n🔗 Preparing Granger Causality variables...")

        # Get aligned returns for all venues
        venue_returns = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_returns[venue] = returns

        if len(venue_returns) < 2:
            print("  ❌ Insufficient venue data for Granger causality")
            self.variables["granger_causality"] = {"venues_available": 0}
            return

        # Align returns to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)

        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables["granger_causality"] = {"venues_available": 0}
            return

        # Create aligned returns matrix with clean index
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            venue_returns_aligned = returns.loc[common_idx]
            # Ensure unique index
            venue_returns_aligned = venue_returns_aligned[
                ~venue_returns_aligned.index.duplicated(keep="last")
            ]
            aligned_returns[venue] = venue_returns_aligned

        # Create DataFrame with flat column names
        returns_df = pd.DataFrame(aligned_returns)
        returns_df.columns = [f"mid_{venue}" for venue in aligned_returns.keys()]
        returns_df = returns_df.dropna()

        if len(returns_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables["granger_causality"] = {"venues_available": 0}
            return

        self.variables["granger_causality"] = {
            "venues_available": len(venue_returns),
            "observations": len(returns_df),
            "max_lags": 5,  # Default lags for Granger
            "data_head": returns_df.head().to_dict(),
        }
        print(f"  ✅ Granger causality variables prepared")
        print(f"    Venues: {len(venue_returns)}")
        print(f"    Observations: {len(returns_df)}")
        print(f"    Max lags: 5")

    def _prepare_cointegration_variables(self):
        """Test 8: Cointegration & Error Correction Models variables."""
        print("\n🔗 Preparing Cointegration variables...")

        # Get aligned price levels for all venues
        venue_prices = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    # Use log prices for cointegration
                    log_prices = np.log(prices)
                    if len(log_prices) > 50:
                        venue_prices[venue] = log_prices

        if len(venue_prices) < 2:
            print("  ❌ Insufficient venue data for cointegration")
            self.variables["cointegration"] = {"venues_available": 0}
            return

        # Align prices to common time index
        common_idx = None
        for venue, prices in venue_prices.items():
            if common_idx is None:
                common_idx = prices.index
            else:
                common_idx = common_idx.intersection(prices.index)

        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables["cointegration"] = {"venues_available": 0}
            return

        # Create aligned prices matrix
        aligned_prices = {}
        for venue, prices in venue_prices.items():
            venue_prices_aligned = prices.loc[common_idx]
            # Ensure unique index
            venue_prices_aligned = venue_prices_aligned[
                ~venue_prices_aligned.index.duplicated(keep="last")
            ]
            aligned_prices[venue] = venue_prices_aligned

        prices_df = pd.DataFrame(aligned_prices)
        prices_df.columns = [f"mid_{venue}" for venue in aligned_prices.keys()]
        prices_df = prices_df.dropna()

        if len(prices_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables["cointegration"] = {"venues_available": 0}
            return

        self.variables["cointegration"] = {
            "venues_available": len(venue_prices),
            "observations": len(prices_df),
            "data_head": prices_df.head().to_dict(),
        }
        print(f"  ✅ Cointegration variables prepared")
        print(f"    Venues: {len(venue_prices)}")
        print(f"    Observations: {len(prices_df)}")

    def _prepare_markov_switching_variables(self):
        """Test 9: Markov Switching Regimes variables."""
        print("\n🔄 Preparing Markov Switching variables...")

        # Get venue returns and spreads
        venue_data = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            spread_col = f"{venue}_spread"

            if mid_col in self.panel_data.columns and spread_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                spreads = self.panel_data[spread_col].dropna()

                if len(prices) > 100 and len(spreads) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_data[venue] = {"returns": returns, "spreads": spreads}

        if len(venue_data) < 2:
            print("  ❌ Insufficient venue data for Markov switching")
            self.variables["markov_switching"] = {"venues_available": 0}
            return

        # Align data to common time index
        common_idx = None
        for venue, data in venue_data.items():
            if common_idx is None:
                common_idx = data["returns"].index
            else:
                common_idx = common_idx.intersection(data["returns"].index)

        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables["markov_switching"] = {"venues_available": 0}
            return

        # Create aligned data
        markov_data = {}
        for venue, data in venue_data.items():
            aligned_returns = data["returns"].loc[common_idx]
            aligned_spreads = data["spreads"].loc[common_idx]

            # Ensure unique index
            aligned_returns = aligned_returns[~aligned_returns.index.duplicated(keep="last")]
            aligned_spreads = aligned_spreads[~aligned_spreads.index.duplicated(keep="last")]

            markov_data[f"{venue}_returns"] = aligned_returns
            markov_data[f"{venue}_spreads"] = aligned_spreads

        markov_df = pd.DataFrame(markov_data)
        markov_df = markov_df.dropna()

        if len(markov_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables["markov_switching"] = {"venues_available": 0}
            return

        self.variables["markov_switching"] = {
            "venues_available": len(venue_data),
            "observations": len(markov_df),
            "data_head": markov_df.head().to_dict(),
        }
        print(f"  ✅ Markov switching variables prepared")
        print(f"    Venues: {len(venue_data)}")
        print(f"    Observations: {len(markov_df)}")

    def _prepare_svar_variables(self):
        """Test 10: Structural VAR variables."""
        print("\n📊 Preparing SVAR variables...")

        # Get aligned returns for all venues
        venue_returns = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_returns[venue] = returns

        if len(venue_returns) < 2:
            print("  ❌ Insufficient venue data for SVAR")
            self.variables["svar"] = {"venues_available": 0}
            return

        # Align returns to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)

        if len(common_idx) < 100:
            print("  ❌ Insufficient common observations")
            self.variables["svar"] = {"venues_available": 0}
            return

        # Create aligned returns matrix with clean index
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            venue_returns_aligned = returns.loc[common_idx]
            # Ensure unique index
            venue_returns_aligned = venue_returns_aligned[
                ~venue_returns_aligned.index.duplicated(keep="last")
            ]
            aligned_returns[venue] = venue_returns_aligned

        # Create DataFrame with flat column names
        returns_df = pd.DataFrame(aligned_returns)
        returns_df.columns = [f"mid_{venue}" for venue in aligned_returns.keys()]
        returns_df = returns_df.dropna()

        if len(returns_df) < 100:
            print("  ❌ Insufficient data after alignment")
            self.variables["svar"] = {"venues_available": 0}
            return

        # Add exogenous variables if available
        exogenous_vars = []
        if "is_session_transition" in self.panel_data.columns:
            exogenous_vars.append("is_session_transition")
        if "is_ny_open" in self.panel_data.columns:
            exogenous_vars.append("is_ny_open")
        if "is_vwap_reset_window" in self.panel_data.columns:
            exogenous_vars.append("is_vwap_reset_window")

        self.variables["svar"] = {
            "venues_available": len(venue_returns),
            "observations": len(returns_df),
            "exogenous_vars": exogenous_vars,
            "max_lags": 5,
            "data_head": returns_df.head().to_dict(),
        }
        print(f"  ✅ SVAR variables prepared")
        print(f"    Venues: {len(venue_returns)}")
        print(f"    Observations: {len(returns_df)}")
        print(f"    Exogenous vars: {exogenous_vars}")
        print(f"    Max lags: 5")

    def _save_variables(self):
        """Save all prepared variables."""
        # Save variables JSON
        variables_file = f"{self.output_dir}/wave2_variables.json"
        with open(variables_file, "w") as f:
            json.dump(self.variables, f, indent=2, default=str)

        print(f"💾 Variables saved to {variables_file}")


def main():
    """Main function."""
    # Set paths
    panel_path = "data/derived/btc_usd/panel_1s_inner_7d_aligned.parquet"
    env_path = "data/derived/btc_usd/env_flags_1s_7d.parquet"
    structure_path = "data/derived/btc_usd/market_structure_7d.parquet"
    output_dir = "analysis/wave2/btc_usd_extended"

    # Initialize preparer
    preparer = ExtendedWave2VariablePreparerLight(panel_path, env_path, structure_path, output_dir)

    # Prepare variables
    preparer.prepare_extended_wave2_variables()


if __name__ == "__main__":
    main()
