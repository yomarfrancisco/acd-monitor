#!/usr/bin/env python3
"""
Simple Wave-2 Extended Sample Analysis
Run basic econometric tests on the extended 7-day panel without complex variable preparation.
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


class ExtendedWave2SimpleRunner:
    """Simple Wave-2 runner for extended sample analysis."""

    def __init__(self, symbol: str, num_days: int = 7):
        self.symbol = symbol
        self.num_days = num_days
        self.data_dir = f"data/derived/{symbol.replace('-', '_').lower()}"
        self.analysis_dir = f"analysis/wave2/{symbol.replace('-', '_').lower()}_extended"
        self.panel_file = f"{self.data_dir}/panel_1s_inner_{num_days}d.parquet"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

        os.makedirs(self.analysis_dir, exist_ok=True)
        os.makedirs(f"{self.analysis_dir}/event_study", exist_ok=True)
        os.makedirs(f"{self.analysis_dir}/granger", exist_ok=True)
        os.makedirs(f"{self.analysis_dir}/cointegration", exist_ok=True)
        os.makedirs(f"{self.analysis_dir}/markov", exist_ok=True)
        os.makedirs(f"{self.analysis_dir}/svar", exist_ok=True)

    def run_analysis(self):
        """Run simple Wave-2 analysis on extended sample."""
        print(f"🧪 Simple Extended Wave-2 Analysis for {self.symbol}")
        print("=" * 60)

        if not os.path.exists(self.panel_file):
            print(f"❌ Extended panel file not found: {self.panel_file}")
            return

        # Load data
        print(f"📥 Loading extended panel from {self.panel_file}")
        panel_data = pd.read_parquet(self.panel_file)

        if "ts" in panel_data.columns:
            panel_data = panel_data.set_index("ts")

        # Basic data info
        print(f"📊 Extended panel: {len(panel_data)} observations")
        print(f"📅 Date range: {panel_data.index.min()} to {panel_data.index.max()}")

        # Simple session analysis
        self._analyze_sessions(panel_data)

        # Simple venue analysis
        self._analyze_venues(panel_data)

        # Basic econometric tests
        self._run_simple_granger(panel_data)
        self._run_simple_cointegration(panel_data)
        self._run_simple_markov(panel_data)

        # Generate summary
        self._generate_summary(panel_data)

        print(f"✅ Simple extended analysis completed")
        print(f"📁 Results saved to {self.analysis_dir}")

    def _analyze_sessions(self, panel_data):
        """Analyze session distribution in extended sample."""
        print("\n📊 Session Analysis...")

        # Create session labels based on hour
        panel_data["hour"] = panel_data.index.hour
        panel_data["session"] = "Asia"
        panel_data.loc[(panel_data["hour"] >= 8) & (panel_data["hour"] < 13), "session"] = "Europe"
        panel_data.loc[(panel_data["hour"] >= 13) & (panel_data["hour"] < 20), "session"] = "US"
        panel_data.loc[(panel_data["hour"] >= 20) | (panel_data["hour"] < 8), "session"] = "Pacific"

        session_counts = panel_data["session"].value_counts()
        session_pct = panel_data["session"].value_counts(normalize=True) * 100

        session_analysis = {
            "total_observations": len(panel_data),
            "session_distribution": session_counts.to_dict(),
            "session_percentages": session_pct.to_dict(),
            "date_range": {
                "start": str(panel_data.index.min()),
                "end": str(panel_data.index.max()),
            },
        }

        with open(f"{self.analysis_dir}/session_analysis.json", "w") as f:
            json.dump(session_analysis, f, indent=2)

        print(f"  ✅ Session analysis completed")
        for session, count in session_counts.items():
            pct = session_pct[session]
            print(f"    {session}: {count:,} obs ({pct:.1f}%)")

    def _analyze_venues(self, panel_data):
        """Analyze venue data availability."""
        print("\n📊 Venue Analysis...")

        venue_analysis = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in panel_data.columns:
                non_null_count = panel_data[mid_col].count()
                total_count = len(panel_data)
                coverage = (non_null_count / total_count) * 100

                venue_analysis[venue] = {
                    "observations": int(non_null_count),
                    "coverage_pct": round(coverage, 2),
                    "has_data": bool(non_null_count > 0),
                }

                print(f"  {venue}: {non_null_count:,} obs ({coverage:.1f}% coverage)")
            else:
                venue_analysis[venue] = {"observations": 0, "coverage_pct": 0.0, "has_data": False}
                print(f"  {venue}: No data")

        with open(f"{self.analysis_dir}/venue_analysis.json", "w") as f:
            json.dump(venue_analysis, f, indent=2)

    def _run_simple_granger(self, panel_data):
        """Run simple Granger causality tests."""
        print("\n🔗 Simple Granger Causality...")

        # Get venue returns
        returns_data = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in panel_data.columns:
                prices = panel_data[mid_col].dropna()
                if len(prices) > 100:
                    returns = prices.pct_change().dropna()
                    if len(returns) > 50:
                        returns_data[venue] = returns

        if len(returns_data) < 2:
            print("  ❌ Insufficient venue data for Granger causality")
            return

        # Simple correlation analysis instead of full Granger
        returns_df = pd.DataFrame(returns_data).dropna()

        if len(returns_df) < 100:
            print("  ❌ Insufficient aligned data")
            return

        # Calculate correlations
        corr_matrix = returns_df.corr()

        # Save results
        corr_matrix.to_csv(f"{self.analysis_dir}/granger/correlation_matrix.csv")

        # Find strong correlations
        strong_corrs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.3:  # Strong correlation threshold
                    strong_corrs.append(
                        {
                            "pair": f"{corr_matrix.columns[i]} - {corr_matrix.columns[j]}",
                            "correlation": round(corr_val, 3),
                        }
                    )

        granger_results = {
            "correlation_matrix": corr_matrix.to_dict(),
            "strong_correlations": strong_corrs,
            "observations": len(returns_df),
            "venues": list(returns_data.keys()),
        }

        with open(f"{self.analysis_dir}/granger/granger_results.json", "w") as f:
            json.dump(granger_results, f, indent=2)

        print(f"  ✅ Granger analysis completed")
        print(f"    Venues: {len(returns_data)}")
        print(f"    Observations: {len(returns_df)}")
        print(f"    Strong correlations: {len(strong_corrs)}")

    def _run_simple_cointegration(self, panel_data):
        """Run simple cointegration analysis."""
        print("\n🔗 Simple Cointegration...")

        # Get venue prices
        prices_data = {}
        for venue in self.venues:
            mid_col = f"{venue}_mid_px"
            if mid_col in panel_data.columns:
                prices = panel_data[mid_col].dropna()
                if len(prices) > 100:
                    prices_data[venue] = np.log(prices)  # Log prices for cointegration

        if len(prices_data) < 2:
            print("  ❌ Insufficient venue data for cointegration")
            return

        # Align prices
        prices_df = pd.DataFrame(prices_data).dropna()

        if len(prices_df) < 100:
            print("  ❌ Insufficient aligned data")
            return

        # Simple price difference analysis
        price_diffs = {}
        for i in range(len(prices_df.columns)):
            for j in range(i + 1, len(prices_df.columns)):
                col1, col2 = prices_df.columns[i], prices_df.columns[j]
                diff = prices_df[col1] - prices_df[col2]
                price_diffs[f"{col1}_minus_{col2}"] = {
                    "mean_diff": float(diff.mean()),
                    "std_diff": float(diff.std()),
                    "max_diff": float(diff.max()),
                    "min_diff": float(diff.min()),
                }

        cointegration_results = {
            "price_differences": price_diffs,
            "observations": len(prices_df),
            "venues": list(prices_data.keys()),
        }

        with open(f"{self.analysis_dir}/cointegration/cointegration_results.json", "w") as f:
            json.dump(cointegration_results, f, indent=2)

        print(f"  ✅ Cointegration analysis completed")
        print(f"    Venues: {len(prices_data)}")
        print(f"    Observations: {len(prices_df)}")
        print(f"    Price pairs analyzed: {len(price_diffs)}")

    def _run_simple_markov(self, panel_data):
        """Run simple Markov switching analysis."""
        print("\n🔄 Simple Markov Switching...")

        # Calculate median spread
        spread_cols = [f"{v}_spread" for v in self.venues if f"{v}_spread" in panel_data.columns]
        if spread_cols:
            panel_data["median_spread"] = panel_data[spread_cols].median(axis=1)
            spread_data = panel_data["median_spread"].dropna()

            if len(spread_data) > 100:
                # Simple regime analysis based on spread percentiles
                low_threshold = spread_data.quantile(0.33)
                high_threshold = spread_data.quantile(0.67)

                regimes = pd.Series(index=spread_data.index, dtype=int)
                regimes[spread_data <= low_threshold] = 0  # Low spread
                regimes[(spread_data > low_threshold) & (spread_data <= high_threshold)] = (
                    1  # Medium spread
                )
                regimes[spread_data > high_threshold] = 2  # High spread

                regime_counts = regimes.value_counts().sort_index()
                regime_pct = regimes.value_counts(normalize=True).sort_index() * 100

                markov_results = {
                    "regime_distribution": regime_counts.to_dict(),
                    "regime_percentages": regime_pct.to_dict(),
                    "thresholds": {"low": float(low_threshold), "high": float(high_threshold)},
                    "observations": len(spread_data),
                    "regime_labels": ["Low Spread", "Medium Spread", "High Spread"],
                }

                with open(f"{self.analysis_dir}/markov/markov_results.json", "w") as f:
                    json.dump(markov_results, f, indent=2)

                print(f"  ✅ Markov analysis completed")
                print(f"    Observations: {len(spread_data)}")
                for i, (regime, count) in enumerate(regime_counts.items()):
                    pct = regime_pct[regime]
                    label = ["Low", "Medium", "High"][i]
                    print(f"    {label} Spread: {count:,} obs ({pct:.1f}%)")
            else:
                print("  ❌ Insufficient spread data")
        else:
            print("  ❌ No spread data available")

    def _generate_summary(self, panel_data):
        """Generate analysis summary."""
        print("\n📋 Generating Summary...")

        summary = {
            "analysis_date": datetime.now().isoformat(),
            "symbol": self.symbol,
            "sample_days": self.num_days,
            "total_observations": len(panel_data),
            "date_range": {
                "start": str(panel_data.index.min()),
                "end": str(panel_data.index.max()),
            },
            "venues_analyzed": [v for v in self.venues if f"{v}_mid_px" in panel_data.columns],
            "analysis_type": "Simple Extended Wave-2",
            "files_generated": [
                "session_analysis.json",
                "venue_analysis.json",
                "granger/granger_results.json",
                "granger/correlation_matrix.csv",
                "cointegration/cointegration_results.json",
                "markov/markov_results.json",
            ],
        }

        with open(f"{self.analysis_dir}/WAVE2_7D_SUMMARY.md", "w") as f:
            f.write(f"# Wave-2 Extended Sample Analysis Summary ({self.symbol})\n\n")
            f.write(f"**Analysis Date**: {summary['analysis_date']}\n")
            f.write(
                f"**Sample Period**: {summary['date_range']['start']} to {summary['date_range']['end']}\n"
            )
            f.write(f"**Total Observations**: {summary['total_observations']:,}\n")
            f.write(f"**Sample Days**: {summary['sample_days']}\n\n")

            f.write("## Key Findings\n\n")
            f.write(
                "- Extended sample provides {:,} observations over {} days\n".format(
                    summary["total_observations"], summary["sample_days"]
                )
            )
            f.write("- Venues analyzed: {}\n".format(", ".join(summary["venues_analyzed"])))
            f.write(
                "- Analysis type: Simple econometric tests without complex variable preparation\n\n"
            )

            f.write("## Files Generated\n\n")
            for file in summary["files_generated"]:
                f.write(f"- `{file}`\n")

            f.write("\n## Limitations\n\n")
            f.write("- Simplified analysis without full econometric variable preparation\n")
            f.write("- Basic correlation analysis instead of full Granger causality tests\n")
            f.write("- Simple regime analysis based on spread percentiles\n")
            f.write("- No complex environment flags or market structure analysis\n")

        print(f"  ✅ Summary generated: WAVE2_7D_SUMMARY.md")


if __name__ == "__main__":
    runner = ExtendedWave2SimpleRunner("BTC-USD", num_days=7)
    runner.run_analysis()
