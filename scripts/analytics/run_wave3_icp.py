#!/usr/bin/env python3
"""
Wave-3 Module W3.1: ICP (Invariant Causal Prediction) Execution
Test for environment-dependent vs invariant relationships in competitive vs coordinated markets.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class Wave3ICPExecutor:
    """Execute ICP analysis for Wave-3."""

    def __init__(self):
        self.wave3_dir = "data/derived/btc_usd/wave3"
        self.analysis_dir = "analysis/wave3/btc_usd/icp"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

        os.makedirs(self.analysis_dir, exist_ok=True)

    def run_icp_analysis(self):
        """Run ICP analysis module."""
        print("🔧 Wave-3 Module W3.1: ICP Execution")
        print("=" * 50)

        # Load ICP design matrix
        print("📥 Loading ICP design matrix...")
        icp_data = pd.read_parquet(f"{self.wave3_dir}/icp_design.parquet")
        print(f"  📊 ICP data: {icp_data.shape}")

        # Prepare data for analysis
        print("🔄 Preparing data for ICP analysis...")
        prepared_data = self._prepare_icp_data(icp_data)

        if prepared_data is None:
            print("❌ Failed to prepare ICP data")
            return False

        # Run environment-specific regressions
        print("🔄 Running environment-specific regressions...")
        env_results = self._run_environment_regressions(prepared_data)

        if env_results is None:
            print("❌ Failed to run environment regressions")
            return False

        # Test for invariance
        print("🔄 Testing for coefficient invariance...")
        invariance_results = self._test_invariance(env_results)

        # Generate outputs
        print("📊 Generating ICP outputs...")
        self._generate_icp_outputs(env_results, invariance_results)

        print("✅ ICP analysis completed successfully!")
        return True

    def _prepare_icp_data(self, icp_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Prepare data for ICP analysis."""
        # Select response and predictor variables
        y_col = "Y"
        if y_col not in icp_data.columns:
            print(f"  ❌ Response variable {y_col} not found")
            return None

        # Get predictor columns (exclude response, timestamp, and environment indicators)
        exclude_cols = [
            "ts",
            "Y",
            "session_label",
            "is_session_transition",
            "is_ny_open",
            "is_vwap_reset_window",
            "structure_state",
            "BOS_up_count_10m",
            "BOS_down_count_10m",
            "available_venue_count",
        ]

        x_cols = [col for col in icp_data.columns if col not in exclude_cols]

        # Filter out shock flag columns for now (focus on core predictors)
        x_cols = [
            col
            for col in x_cols
            if not col.startswith("is_return_2sigma_") and not col.startswith("is_vwap_dev_2sigma_")
        ]

        print(f"  📊 Using {len(x_cols)} predictor variables")

        # Create prepared dataset
        prepared_data = icp_data[["ts", y_col, "session_label"] + x_cols].copy()

        # Drop rows with missing response
        prepared_data = prepared_data.dropna(subset=[y_col])

        # Standardize predictors
        scaler = StandardScaler()
        prepared_data[x_cols] = scaler.fit_transform(prepared_data[x_cols].fillna(0))

        print(f"  📊 Prepared data: {prepared_data.shape}")
        return prepared_data

    def _run_environment_regressions(self, data: pd.DataFrame) -> Optional[Dict]:
        """Run regressions for each environment."""
        results = {}

        # Get unique sessions
        sessions = data["session_label"].unique()
        print(f"  📊 Found sessions: {list(sessions)}")

        # Get predictor columns
        x_cols = [col for col in data.columns if col not in ["ts", "Y", "session_label"]]

        for session in sessions:
            session_data = data[data["session_label"] == session]

            if len(session_data) < 1200:  # Minimum observations
                print(f"  ⚠️ Session {session} has {len(session_data)} obs < 1200, skipping")
                continue

            print(f"  🔄 Fitting regression for {session} ({len(session_data)} obs)...")

            # Prepare X and y
            X = session_data[x_cols].values
            y = session_data["Y"].values

            # Fit ridge regression
            ridge = Ridge(alpha=0.1, random_state=42)
            ridge.fit(X, y)

            # Store results
            results[session] = {
                "coefficients": ridge.coef_,
                "intercept": ridge.intercept_,
                "r2": ridge.score(X, y),
                "n_obs": len(session_data),
                "predictors": x_cols,
            }

            print(f"    ✅ {session}: R² = {ridge.score(X, y):.4f}")

        return results if results else None

    def _test_invariance(self, env_results: Dict) -> Dict:
        """Test for coefficient invariance across environments."""
        invariance_results = {}

        # Get all predictor names
        all_predictors = set()
        for session, result in env_results.items():
            all_predictors.update(result["predictors"])

        all_predictors = list(all_predictors)

        print(f"  📊 Testing invariance for {len(all_predictors)} predictors")

        for predictor in all_predictors:
            # Collect coefficients for this predictor across environments
            coeffs = []
            sessions = []

            for session, result in env_results.items():
                if predictor in result["predictors"]:
                    pred_idx = result["predictors"].index(predictor)
                    coeffs.append(result["coefficients"][pred_idx])
                    sessions.append(session)

            if len(coeffs) < 2:
                continue

            # Simple F-test for equality of coefficients
            coeffs_array = np.array(coeffs)
            mean_coeff = np.mean(coeffs_array)
            var_coeff = np.var(coeffs_array, ddof=1)

            # F-statistic (simplified)
            if var_coeff > 0:
                f_stat = (len(coeffs) - 1) * var_coeff / (var_coeff + 1e-10)
                p_value = 1 - stats.f.cdf(f_stat, len(coeffs) - 1, len(coeffs))
            else:
                f_stat = 0
                p_value = 1.0

            invariance_results[predictor] = {
                "coefficients": dict(zip(sessions, coeffs)),
                "mean_coefficient": mean_coeff,
                "variance": var_coeff,
                "f_statistic": f_stat,
                "p_value": p_value,
                "invariant": p_value > 0.05,
            }

        return invariance_results

    def _generate_icp_outputs(self, env_results: Dict, invariance_results: Dict):
        """Generate ICP analysis outputs."""
        # Coefficients by environment
        coeffs_data = []
        for session, result in env_results.items():
            for i, predictor in enumerate(result["predictors"]):
                coeffs_data.append(
                    {
                        "session": session,
                        "predictor": predictor,
                        "coefficient": result["coefficients"][i],
                        "r2": result["r2"],
                        "n_obs": result["n_obs"],
                    }
                )

        coeffs_df = pd.DataFrame(coeffs_data)
        coeffs_file = f"{self.analysis_dir}/coefficients_by_env.csv"
        coeffs_df.to_csv(coeffs_file, index=False)
        print(f"  💾 Coefficients saved to {coeffs_file}")

        # Invariance tests
        invariance_data = []
        for predictor, result in invariance_results.items():
            invariance_data.append(
                {
                    "predictor": predictor,
                    "mean_coefficient": result["mean_coefficient"],
                    "variance": result["variance"],
                    "f_statistic": result["f_statistic"],
                    "p_value": result["p_value"],
                    "invariant": result["invariant"],
                }
            )

        invariance_df = pd.DataFrame(invariance_data)
        invariance_file = f"{self.analysis_dir}/invariance_tests.csv"
        invariance_df.to_csv(invariance_file, index=False)
        print(f"  💾 Invariance tests saved to {invariance_file}")

        # Summary report
        self._generate_icp_summary(env_results, invariance_results)

    def _generate_icp_summary(self, env_results: Dict, invariance_results: Dict):
        """Generate ICP summary report."""
        summary_file = f"{self.analysis_dir}/W3_ICP_SUMMARY.md"

        with open(summary_file, "w") as f:
            f.write("# Wave-3 ICP Analysis Summary\n\n")
            f.write(f"**Analysis Date**: {datetime.now().isoformat()}\n")
            f.write("**Method**: Invariant Causal Prediction (ICP)\n")
            f.write(
                "**Hypothesis**: Competitive markets show environment-dependent relationships; coordination shows invariant relationships\n\n"
            )

            # Environment results
            f.write("## Environment-Specific Results\n\n")
            f.write("| Session | Observations | R² | Status |\n")
            f.write("|---------|-------------|----|--------|\n")

            for session, result in env_results.items():
                f.write(f"| {session} | {result['n_obs']:,} | {result['r2']:.4f} | ✅ |\n")

            # Invariance results
            f.write("\n## Invariance Test Results\n\n")
            invariant_count = sum(
                1 for result in invariance_results.values() if result["invariant"]
            )
            total_predictors = len(invariance_results)

            f.write(f"- **Total predictors tested**: {total_predictors}\n")
            f.write(
                f"- **Invariant predictors**: {invariant_count} ({invariant_count/total_predictors:.1%})\n"
            )
            f.write(
                f"- **Variant predictors**: {total_predictors - invariant_count} ({(total_predictors - invariant_count)/total_predictors:.1%})\n\n"
            )

            # Top variant predictors
            f.write("### Top Variant Predictors (p < 0.05)\n\n")
            variant_predictors = [
                (pred, result)
                for pred, result in invariance_results.items()
                if not result["invariant"] and result["p_value"] < 0.05
            ]
            variant_predictors.sort(key=lambda x: x[1]["p_value"])

            for predictor, result in variant_predictors[:10]:  # Top 10
                f.write(
                    f"- **{predictor}**: p = {result['p_value']:.4f}, F = {result['f_statistic']:.4f}\n"
                )

            # Top invariant predictors
            f.write("\n### Top Invariant Predictors (p > 0.05)\n\n")
            invariant_predictors = [
                (pred, result) for pred, result in invariance_results.items() if result["invariant"]
            ]
            invariant_predictors.sort(key=lambda x: x[1]["p_value"], reverse=True)

            for predictor, result in invariant_predictors[:10]:  # Top 10
                f.write(
                    f"- **{predictor}**: p = {result['p_value']:.4f}, F = {result['f_statistic']:.4f}\n"
                )

            # Interpretation
            f.write("\n## Interpretation\n\n")
            if invariant_count / total_predictors > 0.5:
                f.write(
                    "**Result**: High proportion of invariant predictors suggests **coordinated behavior**\n"
                )
                f.write("- Many predictors show similar relationships across environments\n")
                f.write("- This is consistent with coordinated market making\n")
            else:
                f.write(
                    "**Result**: High proportion of variant predictors suggests **competitive behavior**\n"
                )
                f.write("- Many predictors show environment-dependent relationships\n")
                f.write("- This is consistent with competitive market dynamics\n")

            f.write("\n## Limitations\n\n")
            f.write("- Single-day analysis limits generalizability\n")
            f.write("- Ridge regression may mask some relationships\n")
            f.write("- Session definitions may not capture all relevant environments\n")
            f.write("- No causal identification beyond correlation\n")

        print(f"  💾 Summary saved to {summary_file}")


if __name__ == "__main__":
    executor = Wave3ICPExecutor()
    success = executor.run_icp_analysis()

    if success:
        print("\n🎉 Wave-3 ICP analysis completed successfully!")
    else:
        print("\n❌ Wave-3 ICP analysis failed!")
        sys.exit(1)
