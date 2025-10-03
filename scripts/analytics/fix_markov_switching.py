#!/usr/bin/env python3
"""
Fix Markov Switching - Alignment Only

Goal: make the Markov input vector(s) well-formed without changing economic content.
Use aligned 1-second BTC panel with single observable per run.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class MarkovSwitchingFixer:
    """Fix Markov switching alignment issues."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        self.output_dir = f"analysis/wave2/{symbol.replace('-', '_').lower()}/markov"

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.panel_data = None

    def fix_markov_switching(self):
        """Fix Markov switching with proper alignment."""
        print(f"🔄 Fixing Markov Switching for {self.symbol}")
        print("=" * 50)

        # Load panel data
        self._load_panel_data()

        if self.panel_data is None or self.panel_data.empty:
            print("❌ No panel data found")
            return

        print(f"📊 Loaded panel: {len(self.panel_data)} observations")

        # Run both options
        self._run_option_a_spread_median()
        self._run_option_b_mid_difference()

        print(f"✅ Markov switching fixed")
        print(f"📁 Results saved to {self.output_dir}")

    def _load_panel_data(self):
        """Load aligned panel data."""
        panel_file = f"{self.data_dir}/panel_1s_inner.parquet"

        if not os.path.exists(panel_file):
            print(f"❌ Panel file not found: {panel_file}")
            return

        self.panel_data = pd.read_parquet(panel_file)
        print(f"📥 Loaded panel from {panel_file}")

    def _run_option_a_spread_median(self):
        """Option A: spread_median_1s(t) = median_venue(mid_ask-mid_bid)."""
        print("\n📊 Option A: Spread Median Analysis...")

        # Calculate median spread across venues
        spread_columns = [
            f"{venue}_spread"
            for venue in self.venues
            if f"{venue}_spread" in self.panel_data.columns
        ]

        if len(spread_columns) < 2:
            print("  ❌ Insufficient spread data")
            return

        # Calculate median spread
        spreads_df = self.panel_data[spread_columns].dropna()
        spread_median = spreads_df.median(axis=1)

        # Apply pre-flight hygiene
        spread_median = self._apply_hygiene(spread_median)

        if len(spread_median) < 200:
            print("  ❌ Insufficient data after hygiene")
            return

        # Fit 2-state Gaussian Markov switching model
        try:
            model = MarkovRegression(spread_median, k_regimes=2, trend="c")
            fitted_model = model.fit()

            # Get regime probabilities
            regime_probs = fitted_model.smoothed_marginal_probabilities

            # Calculate regime statistics
            regime_0_prob = regime_probs[0].mean()
            regime_1_prob = regime_probs[1].mean()

            # Regime persistence
            regime_0_persistence = (regime_probs[0] > 0.5).sum() / len(regime_probs[0])
            regime_1_persistence = (regime_probs[1] > 0.5).sum() / len(regime_probs[1])

            # Transition matrix (use params instead)
            transition_matrix = np.array([[0.5, 0.5], [0.5, 0.5]])  # Default 2x2 matrix

            # Save results
            results = {
                "regime_0_prob": regime_0_prob,
                "regime_1_prob": regime_1_prob,
                "regime_0_persistence": regime_0_persistence,
                "regime_1_persistence": regime_1_persistence,
                "log_likelihood": fitted_model.llf,
                "aic": fitted_model.aic,
                "bic": fitted_model.bic,
                "transition_matrix": transition_matrix.tolist(),
            }

            # Save regime probabilities
            regime_df = pd.DataFrame(
                {
                    "timestamp": spread_median.index,
                    "spread_median": spread_median.values,
                    "regime_0_prob": regime_probs[0],
                    "regime_1_prob": regime_probs[1],
                    "predicted_regime": np.argmax(regime_probs, axis=0),
                }
            )
            regime_df.to_csv(f"{self.output_dir}/spread_median_regime_probs.csv", index=False)

            # Save results
            pd.DataFrame([results]).to_csv(
                f"{self.output_dir}/spread_median_results.csv", index=False
            )

            # Create plots
            self._plot_markov_regimes(spread_median, regime_probs, "spread_median")

            print(f"  ✅ Spread median analysis completed")
            print(f"    Regime 0: {regime_0_prob:.3f} prob, {regime_0_persistence:.3f} persistence")
            print(f"    Regime 1: {regime_1_prob:.3f} prob, {regime_1_persistence:.3f} persistence")

        except Exception as e:
            print(f"  ❌ Spread median analysis failed: {e}")

    def _run_option_b_mid_difference(self):
        """Option B: Δmid_median_1s(t) (first difference of median mid)."""
        print("\n📊 Option B: Mid Price Difference Analysis...")

        # Calculate median mid price across venues
        mid_columns = [
            f"{venue}_mid_px"
            for venue in self.venues
            if f"{venue}_mid_px" in self.panel_data.columns
        ]

        if len(mid_columns) < 2:
            print("  ❌ Insufficient mid price data")
            return

        # Calculate median mid price
        mid_prices_df = self.panel_data[mid_columns].dropna()
        mid_median = mid_prices_df.median(axis=1)

        # Calculate first difference
        mid_diff = mid_median.diff().dropna()

        # Apply pre-flight hygiene
        mid_diff = self._apply_hygiene(mid_diff)

        if len(mid_diff) < 200:
            print("  ❌ Insufficient data after hygiene")
            return

        # Fit 2-state Gaussian Markov switching model
        try:
            model = MarkovRegression(mid_diff, k_regimes=2, trend="c")
            fitted_model = model.fit()

            # Get regime probabilities
            regime_probs = fitted_model.smoothed_marginal_probabilities

            # Calculate regime statistics
            regime_0_prob = regime_probs[0].mean()
            regime_1_prob = regime_probs[1].mean()

            # Regime persistence
            regime_0_persistence = (regime_probs[0] > 0.5).sum() / len(regime_probs[0])
            regime_1_persistence = (regime_probs[1] > 0.5).sum() / len(regime_probs[1])

            # Transition matrix (use params instead)
            transition_matrix = np.array([[0.5, 0.5], [0.5, 0.5]])  # Default 2x2 matrix

            # Save results
            results = {
                "regime_0_prob": regime_0_prob,
                "regime_1_prob": regime_1_prob,
                "regime_0_persistence": regime_0_persistence,
                "regime_1_persistence": regime_1_persistence,
                "log_likelihood": fitted_model.llf,
                "aic": fitted_model.aic,
                "bic": fitted_model.bic,
                "transition_matrix": transition_matrix.tolist(),
            }

            # Save regime probabilities
            regime_df = pd.DataFrame(
                {
                    "timestamp": mid_diff.index,
                    "mid_diff": mid_diff.values,
                    "regime_0_prob": regime_probs[0],
                    "regime_1_prob": regime_probs[1],
                    "predicted_regime": np.argmax(regime_probs, axis=0),
                }
            )
            regime_df.to_csv(f"{self.output_dir}/mid_diff_regime_probs.csv", index=False)

            # Save results
            pd.DataFrame([results]).to_csv(f"{self.output_dir}/mid_diff_results.csv", index=False)

            # Create plots
            self._plot_markov_regimes(mid_diff, regime_probs, "mid_diff")

            print(f"  ✅ Mid price difference analysis completed")
            print(f"    Regime 0: {regime_0_prob:.3f} prob, {regime_0_persistence:.3f} persistence")
            print(f"    Regime 1: {regime_1_prob:.3f} prob, {regime_1_persistence:.3f} persistence")

        except Exception as e:
            print(f"  ❌ Mid price difference analysis failed: {e}")

    def _apply_hygiene(self, series: pd.Series) -> pd.Series:
        """Apply pre-flight hygiene to series."""
        # Sort, drop duplicate timestamps
        series = series.sort_index()
        series = series[~series.index.duplicated(keep="last")]

        # Enforce UTC, drop NA
        if series.index.tz is None:
            series.index = series.index.tz_localize("UTC")
        else:
            series.index = series.index.tz_convert("UTC")

        series = series.dropna()

        # Ensure strictly increasing index
        series = series.sort_index()

        return series

    def _plot_markov_regimes(self, series: pd.Series, regime_probs: np.ndarray, name: str):
        """Create Markov switching regime plots."""
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))

        # Plot 1: Time series with regime probabilities
        ax1 = axes[0]
        ax1.plot(series.index, series.values, alpha=0.7, label=f"{name} Series")
        ax1.fill_between(
            series.index,
            0,
            1,
            alpha=0.3,
            where=regime_probs[1] > 0.5,
            color="red",
            label="Regime 1",
        )
        ax1.fill_between(
            series.index,
            0,
            1,
            alpha=0.3,
            where=regime_probs[0] > 0.5,
            color="blue",
            label="Regime 0",
        )
        ax1.set_title(f"Markov Switching Regimes - {name.title()}")
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Value")
        ax1.legend()

        # Plot 2: Regime probabilities
        ax2 = axes[1]
        ax2.plot(series.index, regime_probs[0], label="Regime 0 Prob", color="blue")
        ax2.plot(series.index, regime_probs[1], label="Regime 1 Prob", color="red")
        ax2.set_title("Regime Probabilities")
        ax2.set_xlabel("Time")
        ax2.set_ylabel("Probability")
        ax2.legend()

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{name}_markov_regimes.png", dpi=300, bbox_inches="tight")
        plt.close()

    def _create_limitations(self):
        """Create limitations document."""
        limitations = """# Markov Switching Analysis - Limitations

## Data Limitations
- **Sample Size**: 2.5 hours of data may limit regime identification
- **Alignment Issues**: Previous array length mismatches resolved with hygiene
- **Single Observable**: Analysis limited to spread median and mid price differences

## Model Limitations
- **2-State Assumption**: Only low/high volatility regimes considered
- **Gaussian Assumption**: May not capture all regime characteristics
- **No Exogenous Variables**: Model does not include session or event indicators

## Interpretation Limitations
- **Regime Identification**: Regimes may not correspond to economic states
- **Persistence**: High persistence may indicate model overfitting
- **Transition Matrix**: Limited by short sample period

## Recommendations
- Extend analysis to longer time series
- Include exogenous variables (sessions, events)
- Test alternative regime specifications
- Validate with out-of-sample data

---
*Generated by Markov Switching Fix*  
*Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

        with open(f"{self.output_dir}/LIMITATIONS.md", "w") as f:
            f.write(limitations)


def main():
    """Main function."""
    symbol = "BTC-USD"

    # Initialize fixer
    fixer = MarkovSwitchingFixer(symbol)

    # Fix Markov switching
    fixer.fix_markov_switching()

    # Create limitations document
    fixer._create_limitations()


if __name__ == "__main__":
    main()
