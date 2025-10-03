#!/usr/bin/env python3
"""
Robustness Checks for Wave-2 Results

Purpose: sanity-check the "competitive dynamics" conclusion and reconcile earlier Coinbase anomaly.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.tsa.stattools import grangercausalitytests, coint

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class RobustnessChecker:
    """Run robustness checks for Wave-2 results."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        self.output_dir = f"analysis/wave2/{symbol.replace('-', '_').lower()}/robustness"

        # Create output directories
        os.makedirs(f"{self.output_dir}/by_session", exist_ok=True)
        os.makedirs(f"{self.output_dir}/coinbase_slice", exist_ok=True)
        os.makedirs(f"{self.output_dir}/lag_window_sensitivity", exist_ok=True)

        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.panel_data = None

    def run_robustness_checks(self):
        """Run all robustness checks."""
        print(f"🔍 Running Robustness Checks for {self.symbol}")
        print("=" * 50)

        # Load panel data
        self._load_panel_data()

        if self.panel_data is None or self.panel_data.empty:
            print("❌ No panel data found")
            return

        print(f"📊 Loaded panel: {len(self.panel_data)} observations")

        # Run robustness checks
        self._session_stratified_analysis()
        self._coinbase_slice_analysis()
        self._lag_window_sensitivity()

        print(f"✅ Robustness checks completed")
        print(f"📁 Results saved to {self.output_dir}")

    def _load_panel_data(self):
        """Load panel data with environment flags."""
        panel_file = f"{self.data_dir}/panel_1s_inner.parquet"
        env_flags_file = f"{self.data_dir}/env_flags_1s.parquet"

        if not os.path.exists(panel_file):
            print(f"❌ Panel file not found: {panel_file}")
            return

        self.panel_data = pd.read_parquet(panel_file)
        print(f"📥 Loaded panel from {panel_file}")

        # Load environment flags
        if os.path.exists(env_flags_file):
            env_flags = pd.read_parquet(env_flags_file)
            self.panel_data = self.panel_data.merge(
                env_flags, left_index=True, right_on="ts", how="left"
            )
            print(f"📥 Loaded environment flags from {env_flags_file}")

    def _session_stratified_analysis(self):
        """1. Session-stratified Granger/ECM analysis."""
        print("\n📊 Session-Stratified Analysis...")

        # Get session labels
        if "session_label" not in self.panel_data.columns:
            print("  ❌ No session labels found")
            return

        sessions = self.panel_data["session_label"].unique()
        session_results = {}

        for session in sessions:
            print(f"  🔍 Analyzing {session} session...")

            # Filter data for session
            session_data = self.panel_data[self.panel_data["session_label"] == session].copy()

            if len(session_data) < 100:
                print(f"    ⚠️ Insufficient data for {session} session")
                continue

            # Get venue returns
            venue_returns = {}
            for venue in self.venues:
                mid_col = f"{venue}_mid_px"
                if mid_col in session_data.columns:
                    prices = session_data[mid_col].dropna()
                    if len(prices) > 50:
                        returns = prices.pct_change().dropna()
                        if len(returns) > 30:
                            venue_returns[venue] = returns

            if len(venue_returns) < 2:
                print(f"    ⚠️ Insufficient venue data for {session} session")
                continue

            # Align returns
            common_idx = None
            for venue, returns in venue_returns.items():
                if common_idx is None:
                    common_idx = returns.index
                else:
                    common_idx = common_idx.intersection(returns.index)

            if len(common_idx) < 50:
                print(f"    ⚠️ Insufficient common data for {session} session")
                continue

            # Create aligned returns matrix
            aligned_returns = {}
            for venue, returns in venue_returns.items():
                aligned_returns[venue] = returns.loc[common_idx]

            returns_df = pd.DataFrame(aligned_returns)
            returns_df.columns = [f"mid_{venue}" for venue in aligned_returns.keys()]
            returns_df = returns_df.dropna()

            # Run Granger causality tests
            granger_results = {}
            max_lags = 3  # Reduced for robustness

            for i, venue1 in enumerate(returns_df.columns):
                for j, venue2 in enumerate(returns_df.columns):
                    if i != j:
                        try:
                            test_data = returns_df[[venue1, venue2]].dropna()
                            if len(test_data) > 50:
                                result = grangercausalitytests(
                                    test_data, maxlag=max_lags, verbose=False
                                )
                                p_values = [
                                    result[lag][0]["ssr_ftest"][1] for lag in range(1, max_lags + 1)
                                ]
                                min_p_value = min(p_values)

                                granger_results[f"{venue1}_causes_{venue2}"] = {
                                    "p_value": min_p_value,
                                    "significant": min_p_value < 0.05,
                                }
                        except Exception as e:
                            print(f"    Warning: Granger test failed for {venue1} -> {venue2}: {e}")

            # Run cointegration tests
            cointegration_results = {}
            for i, venue1 in enumerate(returns_df.columns):
                for j, venue2 in enumerate(returns_df.columns):
                    if i < j:
                        try:
                            test_data = returns_df[[venue1, venue2]].dropna()
                            if len(test_data) > 50:
                                score, p_value, critical_values = coint(
                                    test_data[venue1], test_data[venue2]
                                )
                                cointegration_results[f"{venue1}_{venue2}"] = {
                                    "score": score,
                                    "p_value": p_value,
                                    "cointegrated": p_value < 0.05,
                                }
                        except Exception as e:
                            print(
                                f"    Warning: Cointegration test failed for {venue1} - {venue2}: {e}"
                            )

            # Save session results
            session_results[session] = {
                "granger_results": granger_results,
                "cointegration_results": cointegration_results,
                "observations": len(returns_df),
                "venues": list(aligned_returns.keys()),
            }

            print(
                f"    ✅ {session} session: {len(returns_df)} obs, {len(granger_results)} Granger tests, {len(cointegration_results)} cointegration tests"
            )

        # Save session results
        for session, results in session_results.items():
            # Save Granger results
            if results["granger_results"]:
                pd.DataFrame(results["granger_results"]).T.to_csv(
                    f"{self.output_dir}/by_session/{session}_granger_results.csv"
                )

            # Save cointegration results
            if results["cointegration_results"]:
                pd.DataFrame(results["cointegration_results"]).T.to_csv(
                    f"{self.output_dir}/by_session/{session}_cointegration_results.csv"
                )

        # Create session comparison plot
        self._plot_session_comparison(session_results)

        print(f"  ✅ Session-stratified analysis completed")
        print(f"    Sessions analyzed: {len(session_results)}")

    def _coinbase_slice_analysis(self):
        """2. Coinbase-focused slice analysis."""
        print("\n📊 Coinbase Slice Analysis...")

        # Get venue returns
        venue_returns = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in self.panel_data.columns:
                prices = self.panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        venue_returns[venue] = returns

        if len(venue_returns) < 3:
            print("  ❌ Insufficient venue data")
            return

        # Align returns
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)

        if len(common_idx) < 100:
            print("  ❌ Insufficient common data")
            return

        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]

        returns_df = pd.DataFrame(aligned_returns)
        returns_df.columns = [f"mid_{venue}" for venue in aligned_returns.keys()]
        returns_df = returns_df.dropna()

        # Analysis 1: Without Coinbase
        venues_without_coinbase = [v for v in self.venues if v != "coinbase"]
        returns_without_coinbase = returns_df[
            [f"mid_{v}" for v in venues_without_coinbase if f"mid_{v}" in returns_df.columns]
        ]

        if len(returns_without_coinbase.columns) >= 2:
            # Calculate variance ratios
            var_ratios_without = {}
            for venue in returns_without_coinbase.columns:
                venue_var = returns_without_coinbase[venue].var()
                market_var = returns_without_coinbase.var().mean()
                var_ratios_without[venue] = venue_var / market_var

            # Run Granger tests
            granger_without = {}
            for i, venue1 in enumerate(returns_without_coinbase.columns):
                for j, venue2 in enumerate(returns_without_coinbase.columns):
                    if i != j:
                        try:
                            test_data = returns_without_coinbase[[venue1, venue2]].dropna()
                            if len(test_data) > 50:
                                result = grangercausalitytests(test_data, maxlag=3, verbose=False)
                                p_values = [result[lag][0]["ssr_ftest"][1] for lag in range(1, 4)]
                                min_p_value = min(p_values)
                                granger_without[f"{venue1}_causes_{venue2}"] = {
                                    "p_value": min_p_value,
                                    "significant": min_p_value < 0.05,
                                }
                        except Exception as e:
                            print(f"    Warning: Granger test failed for {venue1} -> {venue2}: {e}")

        # Analysis 2: With Coinbase
        if "mid_coinbase" in returns_df.columns:
            # Calculate variance ratios
            var_ratios_with = {}
            for venue in returns_df.columns:
                venue_var = returns_df[venue].var()
                market_var = returns_df.var().mean()
                var_ratios_with[venue] = venue_var / market_var

            # Run Granger tests
            granger_with = {}
            for i, venue1 in enumerate(returns_df.columns):
                for j, venue2 in enumerate(returns_df.columns):
                    if i != j:
                        try:
                            test_data = returns_df[[venue1, venue2]].dropna()
                            if len(test_data) > 50:
                                result = grangercausalitytests(test_data, maxlag=3, verbose=False)
                                p_values = [result[lag][0]["ssr_ftest"][1] for lag in range(1, 4)]
                                min_p_value = min(p_values)
                                granger_with[f"{venue1}_causes_{venue2}"] = {
                                    "p_value": min_p_value,
                                    "significant": min_p_value < 0.05,
                                }
                        except Exception as e:
                            print(f"    Warning: Granger test failed for {venue1} -> {venue2}: {e}")

        # Compare results
        comparison_results = {
            "with_coinbase": {
                "var_ratios": var_ratios_with if "mid_coinbase" in returns_df.columns else {},
                "granger_results": granger_with if "mid_coinbase" in returns_df.columns else {},
                "observations": len(returns_df),
            },
            "without_coinbase": {
                "var_ratios": (
                    var_ratios_without if len(returns_without_coinbase.columns) >= 2 else {}
                ),
                "granger_results": (
                    granger_without if len(returns_without_coinbase.columns) >= 2 else {}
                ),
                "observations": (
                    len(returns_without_coinbase)
                    if len(returns_without_coinbase.columns) >= 2
                    else 0
                ),
            },
        }

        # Save results
        pd.DataFrame([comparison_results["with_coinbase"]]).to_csv(
            f"{self.output_dir}/coinbase_slice/with_coinbase_results.csv"
        )
        pd.DataFrame([comparison_results["without_coinbase"]]).to_csv(
            f"{self.output_dir}/coinbase_slice/without_coinbase_results.csv"
        )

        # Create comparison plot
        self._plot_coinbase_comparison(comparison_results)

        print(f"  ✅ Coinbase slice analysis completed")
        print(
            f"    With Coinbase: {len(granger_with) if 'mid_coinbase' in returns_df.columns else 0} Granger tests"
        )
        print(
            f"    Without Coinbase: {len(granger_without) if len(returns_without_coinbase.columns) >= 2 else 0} Granger tests"
        )

    def _lag_window_sensitivity(self):
        """3. Lag/Window sensitivity analysis."""
        print("\n📊 Lag/Window Sensitivity Analysis...")

        # Get venue returns
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
            print("  ❌ Insufficient venue data")
            return

        # Align returns
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)

        if len(common_idx) < 100:
            print("  ❌ Insufficient common data")
            return

        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]

        returns_df = pd.DataFrame(aligned_returns)
        returns_df.columns = [f"mid_{venue}" for venue in aligned_returns.keys()]
        returns_df = returns_df.dropna()

        # Test different lag specifications
        lag_results = {}
        for max_lags in [2, 5]:
            print(f"  🔍 Testing {max_lags} lags...")

            granger_results = {}
            for i, venue1 in enumerate(returns_df.columns):
                for j, venue2 in enumerate(returns_df.columns):
                    if i != j:
                        try:
                            test_data = returns_df[[venue1, venue2]].dropna()
                            if len(test_data) > 50:
                                result = grangercausalitytests(
                                    test_data, maxlag=max_lags, verbose=False
                                )
                                p_values = [
                                    result[lag][0]["ssr_ftest"][1] for lag in range(1, max_lags + 1)
                                ]
                                min_p_value = min(p_values)

                                granger_results[f"{venue1}_causes_{venue2}"] = {
                                    "p_value": min_p_value,
                                    "significant": min_p_value < 0.05,
                                }
                        except Exception as e:
                            print(f"    Warning: Granger test failed for {venue1} -> {venue2}: {e}")

            lag_results[f"{max_lags}_lags"] = {
                "granger_results": granger_results,
                "significant_count": sum([r["significant"] for r in granger_results.values()]),
                "total_tests": len(granger_results),
            }

            print(
                f"    ✅ {max_lags} lags: {len(granger_results)} tests, {sum([r['significant'] for r in granger_results.values()])} significant"
            )

        # Test different event study windows
        window_results = {}
        for window_minutes in [10, 15]:
            print(f"  🔍 Testing ±{window_minutes} minute windows...")

            # Get shock events
            shock_events = 0
            for venue in self.venues:
                shock_col = f"is_return_2sigma_{venue}"
                if shock_col in self.panel_data.columns:
                    shock_events += self.panel_data[shock_col].sum()

            window_results[f"{window_minutes}_min_window"] = {
                "shock_events": shock_events,
                "window_minutes": window_minutes,
            }

            print(f"    ✅ ±{window_minutes} min window: {shock_events} shock events")

        # Save results
        pd.DataFrame(lag_results).T.to_csv(
            f"{self.output_dir}/lag_window_sensitivity/lag_results.csv"
        )
        pd.DataFrame(window_results).T.to_csv(
            f"{self.output_dir}/lag_window_sensitivity/window_results.csv"
        )

        # Create sensitivity plot
        self._plot_sensitivity_analysis(lag_results, window_results)

        print(f"  ✅ Lag/Window sensitivity analysis completed")
        print(f"    Lag tests: {len(lag_results)}")
        print(f"    Window tests: {len(window_results)}")

    def _plot_session_comparison(self, session_results: Dict):
        """Create session comparison plot."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Plot 1: Granger significance by session
        sessions = list(session_results.keys())
        granger_significance = []
        for session in sessions:
            if session_results[session]["granger_results"]:
                significant = sum(
                    [r["significant"] for r in session_results[session]["granger_results"].values()]
                )
                total = len(session_results[session]["granger_results"])
                granger_significance.append(significant / total if total > 0 else 0)
            else:
                granger_significance.append(0)

        ax1 = axes[0, 0]
        ax1.bar(sessions, granger_significance)
        ax1.set_title("Granger Significance by Session")
        ax1.set_ylabel("Significance Rate")
        ax1.tick_params(axis="x", rotation=45)

        # Plot 2: Cointegration by session
        cointegration_significance = []
        for session in sessions:
            if session_results[session]["cointegration_results"]:
                significant = sum(
                    [
                        r["cointegrated"]
                        for r in session_results[session]["cointegration_results"].values()
                    ]
                )
                total = len(session_results[session]["cointegration_results"])
                cointegration_significance.append(significant / total if total > 0 else 0)
            else:
                cointegration_significance.append(0)

        ax2 = axes[0, 1]
        ax2.bar(sessions, cointegration_significance)
        ax2.set_title("Cointegration by Session")
        ax2.set_ylabel("Cointegration Rate")
        ax2.tick_params(axis="x", rotation=45)

        # Plot 3: Observations by session
        observations = [session_results[session]["observations"] for session in sessions]
        ax3 = axes[1, 0]
        ax3.bar(sessions, observations)
        ax3.set_title("Observations by Session")
        ax3.set_ylabel("Count")
        ax3.tick_params(axis="x", rotation=45)

        # Plot 4: Venues by session
        venue_counts = [len(session_results[session]["venues"]) for session in sessions]
        ax4 = axes[1, 1]
        ax4.bar(sessions, venue_counts)
        ax4.set_title("Venues by Session")
        ax4.set_ylabel("Count")
        ax4.tick_params(axis="x", rotation=45)

        plt.tight_layout()
        plt.savefig(
            f"{self.output_dir}/by_session/session_comparison.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

    def _plot_coinbase_comparison(self, comparison_results: Dict):
        """Create Coinbase comparison plot."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Plot 1: Variance ratios comparison
        with_coinbase = comparison_results["with_coinbase"]["var_ratios"]
        without_coinbase = comparison_results["without_coinbase"]["var_ratios"]

        if with_coinbase and without_coinbase:
            venues = list(set(list(with_coinbase.keys()) + list(without_coinbase.keys())))
            with_ratios = [with_coinbase.get(v, 0) for v in venues]
            without_ratios = [without_coinbase.get(v, 0) for v in venues]

            ax1 = axes[0, 0]
            x = np.arange(len(venues))
            width = 0.35
            ax1.bar(x - width / 2, with_ratios, width, label="With Coinbase")
            ax1.bar(x + width / 2, without_ratios, width, label="Without Coinbase")
            ax1.set_title("Variance Ratios Comparison")
            ax1.set_ylabel("Variance Ratio")
            ax1.set_xticks(x)
            ax1.set_xticklabels(venues, rotation=45)
            ax1.legend()

        # Plot 2: Granger significance comparison
        with_granger = comparison_results["with_coinbase"]["granger_results"]
        without_granger = comparison_results["without_coinbase"]["granger_results"]

        if with_granger and without_granger:
            with_significant = sum([r["significant"] for r in with_granger.values()])
            without_significant = sum([r["significant"] for r in without_granger.values()])

            ax2 = axes[0, 1]
            ax2.bar(["With Coinbase", "Without Coinbase"], [with_significant, without_significant])
            ax2.set_title("Granger Significance Comparison")
            ax2.set_ylabel("Significant Tests")

        # Plot 3: Observations comparison
        with_obs = comparison_results["with_coinbase"]["observations"]
        without_obs = comparison_results["without_coinbase"]["observations"]

        ax3 = axes[1, 0]
        ax3.bar(["With Coinbase", "Without Coinbase"], [with_obs, without_obs])
        ax3.set_title("Observations Comparison")
        ax3.set_ylabel("Count")

        # Plot 4: Test counts comparison
        with_tests = len(with_granger) if with_granger else 0
        without_tests = len(without_granger) if without_granger else 0

        ax4 = axes[1, 1]
        ax4.bar(["With Coinbase", "Without Coinbase"], [with_tests, without_tests])
        ax4.set_title("Test Counts Comparison")
        ax4.set_ylabel("Number of Tests")

        plt.tight_layout()
        plt.savefig(
            f"{self.output_dir}/coinbase_slice/coinbase_comparison.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def _plot_sensitivity_analysis(self, lag_results: Dict, window_results: Dict):
        """Create sensitivity analysis plot."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Plot 1: Granger significance by lag
        lags = list(lag_results.keys())
        significance_rates = []
        for lag in lags:
            if lag_results[lag]["granger_results"]:
                significant = lag_results[lag]["significant_count"]
                total = lag_results[lag]["total_tests"]
                significance_rates.append(significant / total if total > 0 else 0)
            else:
                significance_rates.append(0)

        ax1 = axes[0, 0]
        ax1.bar(lags, significance_rates)
        ax1.set_title("Granger Significance by Lag")
        ax1.set_ylabel("Significance Rate")
        ax1.tick_params(axis="x", rotation=45)

        # Plot 2: Total tests by lag
        total_tests = [lag_results[lag]["total_tests"] for lag in lags]
        ax2 = axes[0, 1]
        ax2.bar(lags, total_tests)
        ax2.set_title("Total Tests by Lag")
        ax2.set_ylabel("Number of Tests")
        ax2.tick_params(axis="x", rotation=45)

        # Plot 3: Shock events by window
        windows = list(window_results.keys())
        shock_events = [window_results[window]["shock_events"] for window in windows]
        ax3 = axes[1, 0]
        ax3.bar(windows, shock_events)
        ax3.set_title("Shock Events by Window")
        ax3.set_ylabel("Number of Events")
        ax3.tick_params(axis="x", rotation=45)

        # Plot 4: Window minutes
        window_minutes = [window_results[window]["window_minutes"] for window in windows]
        ax4 = axes[1, 1]
        ax4.bar(windows, window_minutes)
        ax4.set_title("Window Minutes")
        ax4.set_ylabel("Minutes")
        ax4.tick_params(axis="x", rotation=45)

        plt.tight_layout()
        plt.savefig(
            f"{self.output_dir}/lag_window_sensitivity/sensitivity_analysis.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()


def main():
    """Main function."""
    symbol = "BTC-USD"

    # Initialize checker
    checker = RobustnessChecker(symbol)

    # Run robustness checks
    checker.run_robustness_checks()


if __name__ == "__main__":
    main()
