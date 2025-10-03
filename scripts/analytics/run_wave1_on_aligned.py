#!/usr/bin/env python3
"""
Re-run Wave-1 Tests on Aligned Panel Data

Executes variance ratio, cross-correlation, and PCA tests on aligned panel data
to investigate if Coinbase anomaly persists after proper alignment.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class AlignedWave1Tester:
    """Run Wave-1 tests on aligned panel data."""

    def __init__(
        self, symbol: str, grid_freq: str = "1S", join_type: str = "inner", winsor_pct: float = 0.5
    ):
        self.symbol = symbol
        self.grid_freq = grid_freq
        self.join_type = join_type
        self.winsor_pct = winsor_pct
        self.output_dir = f"analysis/wave1/{symbol.replace('-', '_').lower()}/aligned"
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.panel_data = None
        self.results = {}

    def run_aligned_tests(self):
        """Run Wave-1 tests on aligned panel data."""
        print(f"🔄 Aligned Wave-1 Tests for {self.symbol}")
        print("=" * 50)

        # Load aligned panel
        self._load_aligned_panel()

        if self.panel_data is None or self.panel_data.empty:
            print("❌ No aligned panel data found")
            return

        print(f"📊 Loaded aligned panel: {len(self.panel_data)} observations")

        # Run tests
        self._test_variance_ratios()
        self._test_cross_correlations()
        self._test_pca_analysis()

        # Save results
        self._save_results()

        print(f"✅ Aligned Wave-1 tests complete")
        print(f"📁 Results saved to {self.output_dir}")

    def _load_aligned_panel(self):
        """Load aligned panel data."""
        panel_file = f"{self.data_dir}/panel_{self.grid_freq}_{self.join_type}.parquet"

        if not os.path.exists(panel_file):
            print(f"❌ Panel file not found: {panel_file}")
            return

        self.panel_data = pd.read_parquet(panel_file)
        print(f"📥 Loaded panel from {panel_file}")

    def _test_variance_ratios(self):
        """Test variance ratios on aligned data."""
        print("\n📈 Variance Ratio Test on Aligned Data")

        vr_results = {}

        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col not in self.panel_data.columns:
                continue

            # Get price series
            prices = self.panel_data[mid_col].dropna()
            if len(prices) < 100:
                continue

            # Calculate returns
            returns = prices.pct_change().dropna()
            if len(returns) < 50:
                continue

            # Variance ratios for different lags
            lags = [2, 4, 8, 16, 32]
            vr_values = {}

            for lag in lags:
                if len(returns) < lag * 10:
                    continue

                # Calculate variance ratio
                n = len(returns)
                k_returns = []
                for i in range(lag, n):
                    k_returns.append(returns.iloc[i - lag + 1 : i + 1].sum())

                if len(k_returns) > 10:
                    var_k = np.var(k_returns)
                    var_1 = np.var(returns.iloc[lag:])
                    vr = var_k / (lag * var_1) if var_1 > 0 else np.nan
                    vr_values[f"vr_{lag}"] = vr

            vr_results[venue] = vr_values

        # Create variance ratio comparison plot
        self._plot_variance_ratios(vr_results)

        # Save results
        vr_df = pd.DataFrame(vr_results).T
        vr_df.to_csv(f"{self.output_dir}/VR_results.csv")

        self.results["variance_ratios"] = vr_results
        print(f"  ✅ Variance ratio test complete")
        print(f"    Results: {self.output_dir}/VR_results.csv")

    def _test_cross_correlations(self):
        """Test cross-correlations on aligned data."""
        print("\n🔗 Cross-Correlation Test on Aligned Data")

        # Get price returns for all venues
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
            print("  ❌ Insufficient venue data for cross-correlation")
            return

        # Align returns to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)

        if len(common_idx) < 50:
            print("  ❌ Insufficient common observations")
            return

        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]

        returns_df = pd.DataFrame(aligned_returns)
        returns_df = returns_df.dropna()

        if len(returns_df) < 50:
            print("  ❌ Insufficient data after alignment")
            return

        # Calculate correlation matrix
        corr_matrix = returns_df.corr()

        # Create correlation heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap="RdBu_r", center=0, square=True, fmt=".3f")
        plt.title(f"{self.symbol} - Cross-Correlations (Aligned Data)")
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/XCorr_heatmap.png", dpi=300, bbox_inches="tight")
        plt.close()

        # Save correlation matrix
        corr_matrix.to_csv(f"{self.output_dir}/XCorr_results.csv")

        self.results["cross_correlations"] = corr_matrix.to_dict()
        print(f"  ✅ Cross-correlation test complete")
        print(f"    Results: {self.output_dir}/XCorr_results.csv")

    def _test_pca_analysis(self):
        """Test PCA analysis on aligned data."""
        print("\n🎯 PCA Analysis on Aligned Data")

        # Get price returns for all venues
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
            print("  ❌ Need at least 3 venues for PCA")
            return

        # Align returns to common time index
        common_idx = None
        for venue, returns in venue_returns.items():
            if common_idx is None:
                common_idx = returns.index
            else:
                common_idx = common_idx.intersection(returns.index)

        if len(common_idx) < 50:
            print("  ❌ Insufficient common observations")
            return

        # Create aligned returns matrix
        aligned_returns = {}
        for venue, returns in venue_returns.items():
            aligned_returns[venue] = returns.loc[common_idx]

        returns_df = pd.DataFrame(aligned_returns)
        returns_df = returns_df.dropna()

        if len(returns_df) < 50:
            print("  ❌ Insufficient data after alignment")
            return

        # Standardize returns
        scaler = StandardScaler()
        returns_std = scaler.fit_transform(returns_df)

        # Perform PCA
        pca = PCA()
        pca_result = pca.fit_transform(returns_std)

        # Create PCA plots
        self._plot_pca_results(pca, returns_df.columns)

        # Save PCA results
        pca_results = {
            "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
            "cumulative_variance_ratio": np.cumsum(pca.explained_variance_ratio_).tolist(),
            "components": pca.components_.tolist(),
            "first_component_loadings": {
                venue: loading for venue, loading in zip(returns_df.columns, pca.components_[0])
            },
        }

        with open(f"{self.output_dir}/PCA_summary.json", "w") as f:
            json.dump(pca_results, f, indent=2, default=str)

        self.results["pca_analysis"] = pca_results
        print(f"  ✅ PCA analysis complete")
        print(f"    Results: {self.output_dir}/PCA_summary.json")

    def _plot_variance_ratios(self, vr_results: Dict):
        """Plot variance ratio comparison."""
        # Create variance ratio comparison
        vr_df = pd.DataFrame(vr_results).T

        plt.figure(figsize=(12, 8))
        vr_df.plot(kind="bar", ax=plt.gca())
        plt.title(f"{self.symbol} - Variance Ratios (Aligned Data)")
        plt.xlabel("Venue")
        plt.ylabel("Variance Ratio")
        plt.xticks(rotation=45)
        plt.legend(title="Lag", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/VR_comparison.png", dpi=300, bbox_inches="tight")
        plt.close()

    def _plot_pca_results(self, pca: PCA, venue_names: List[str]):
        """Plot PCA results."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # Explained variance
        axes[0, 0].bar(
            range(1, len(pca.explained_variance_ratio_) + 1), pca.explained_variance_ratio_
        )
        axes[0, 0].set_title("Explained Variance by Component")
        axes[0, 0].set_xlabel("Component")
        axes[0, 0].set_ylabel("Explained Variance Ratio")
        axes[0, 0].grid(True, alpha=0.3)

        # Cumulative variance
        axes[0, 1].plot(
            range(1, len(pca.explained_variance_ratio_) + 1),
            np.cumsum(pca.explained_variance_ratio_),
            "o-",
        )
        axes[0, 1].set_title("Cumulative Variance Explained")
        axes[0, 1].set_xlabel("Component")
        axes[0, 1].set_ylabel("Cumulative Variance Ratio")
        axes[0, 1].grid(True, alpha=0.3)

        # First component loadings
        first_component = pca.components_[0]
        axes[1, 0].bar(venue_names, first_component, color="lightcoral")
        axes[1, 0].set_title("First Component Loadings (Coordination Factor)")
        axes[1, 0].set_xlabel("Venue")
        axes[1, 0].set_ylabel("Loading")
        axes[1, 0].tick_params(axis="x", rotation=45)
        axes[1, 0].grid(True, alpha=0.3)

        # Component loadings heatmap
        components_df = pd.DataFrame(
            pca.components_,
            columns=venue_names,
            index=[f"PC{i+1}" for i in range(len(pca.components_))],
        )
        sns.heatmap(components_df, annot=True, cmap="RdBu_r", center=0, ax=axes[1, 1])
        axes[1, 1].set_title("Component Loadings Heatmap")

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/PCA_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

    def _save_results(self):
        """Save all test results."""
        results_data = {
            "symbol": self.symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "alignment_params": {
                "grid_freq": self.grid_freq,
                "join_type": self.join_type,
                "winsor_pct": self.winsor_pct,
            },
            "tests": self.results,
            "summary": self._generate_summary(),
        }

        with open(f"{self.output_dir}/aligned_wave1_results.json", "w") as f:
            json.dump(results_data, f, indent=2, default=str)

        # Create summary report
        self._create_summary_report()

    def _generate_summary(self) -> str:
        """Generate overall summary."""
        summary_parts = []

        # Variance ratio summary
        if "variance_ratios" in self.results:
            vr_data = self.results["variance_ratios"]
            coinbase_vr = vr_data.get("coinbase", {}).get("vr_2", np.nan)
            other_vr = [
                vr_data.get(venue, {}).get("vr_2", np.nan)
                for venue in ["binance", "kraken", "okx", "bybit"]
                if venue in vr_data
            ]
            other_vr = [v for v in other_vr if not np.isnan(v)]

            if not np.isnan(coinbase_vr) and other_vr:
                avg_other_vr = np.mean(other_vr)
                if coinbase_vr > avg_other_vr * 2:
                    summary_parts.append(
                        f"Coinbase anomaly PERSISTS: VR={coinbase_vr:.3f} vs others={avg_other_vr:.3f}"
                    )
                else:
                    summary_parts.append(
                        f"Coinbase anomaly RESOLVED: VR={coinbase_vr:.3f} vs others={avg_other_vr:.3f}"
                    )

        # Cross-correlation summary
        if "cross_correlations" in self.results:
            corr_data = self.results["cross_correlations"]
            high_corr_pairs = []
            for venue1 in corr_data:
                for venue2 in corr_data[venue1]:
                    if venue1 != venue2 and abs(corr_data[venue1][venue2]) > 0.8:
                        high_corr_pairs.append(f"{venue1}-{venue2}")
            if high_corr_pairs:
                summary_parts.append(f"High correlations: {', '.join(high_corr_pairs)}")

        # PCA summary
        if "pca_analysis" in self.results:
            pca_data = self.results["pca_analysis"]
            first_component = pca_data.get("explained_variance_ratio", [0])[0]
            if first_component > 0.5:
                summary_parts.append(f"Dominant first component: {first_component:.1%}")
            else:
                summary_parts.append(f"Distributed variance: {first_component:.1%}")

        return " | ".join(summary_parts) if summary_parts else "No significant patterns detected"

    def _create_summary_report(self):
        """Create summary report."""
        report = f"""# Aligned Wave-1 Test Results - {self.symbol}

## Test Parameters
- **Grid Frequency**: {self.grid_freq}
- **Join Type**: {self.join_type}
- **Winsorization**: {self.winsor_pct}%

## Key Findings

### Variance Ratio Analysis
"""

        if "variance_ratios" in self.results:
            vr_data = self.results["variance_ratios"]
            for venue, vr_values in vr_data.items():
                vr_2 = vr_values.get("vr_2", np.nan)
                if not np.isnan(vr_2):
                    report += f"- **{venue}**: VR={vr_2:.3f}\n"

        report += f"""
### Cross-Correlation Analysis
- **Correlation Matrix**: See XCorr_results.csv
- **Heatmap**: XCorr_heatmap.png

### PCA Analysis
- **Explained Variance**: See PCA_summary.json
- **Component Loadings**: PCA_analysis.png

## Conclusion
{self._generate_summary()}

## Files Generated
- `VR_results.csv` - Variance ratio results
- `XCorr_results.csv` - Cross-correlation matrix
- `PCA_summary.json` - PCA analysis results
- Various PNG plots for visualization
"""

        with open(f"{self.output_dir}/PCA_summary.md", "w") as f:
            f.write(report)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run Wave-1 Tests on Aligned Panel")
    parser.add_argument("--symbol", default="BTC-USD", help="Symbol to analyze")
    parser.add_argument("--grid", default="1S", help="Grid frequency")
    parser.add_argument("--join", default="inner", help="Join type")
    parser.add_argument("--winsor", type=float, default=0.5, help="Winsorization percentage")

    args = parser.parse_args()

    # Initialize tester
    tester = AlignedWave1Tester(args.symbol, args.grid, args.join, args.winsor)

    # Run tests
    tester.run_aligned_tests()


if __name__ == "__main__":
    main()
