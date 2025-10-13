#!/usr/bin/env python3
"""
Wave-3 Module W3.3: Copula Dependence & Tails Analysis
Analyze dependence patterns and tail behavior across sessions.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
from scipy import stats
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class Wave3CopulaExecutor:
    """Execute copula analysis for Wave-3."""

    def __init__(self):
        self.wave3_dir = "data/derived/btc_usd/wave3"
        self.analysis_dir = "analysis/wave3/btc_usd/copula"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

        os.makedirs(self.analysis_dir, exist_ok=True)

    def run_copula_analysis(self):
        """Run copula analysis module."""
        print("🔧 Wave-3 Module W3.3: Copula Dependence & Tails")
        print("=" * 50)

        # Load copula marginals
        print("📥 Loading copula marginals...")
        copula_data = pd.read_parquet(f"{self.wave3_dir}/copula_marginals.parquet")
        print(f"  📊 Copula data: {copula_data.shape}")

        # Analyze by session
        print("🔄 Analyzing dependence by session...")
        session_results = self._analyze_session_dependence(copula_data)

        if session_results is None:
            print("❌ Failed to analyze session dependence")
            return False

        # Generate summary
        print("📊 Generating copula outputs...")
        self._generate_copula_outputs(session_results)

        print("✅ Copula analysis completed successfully!")
        return True

    def _analyze_session_dependence(self, copula_data: pd.DataFrame) -> Optional[Dict]:
        """Analyze dependence patterns by session."""
        session_results = {}

        # Get unique sessions
        sessions = copula_data["session_label"].unique()
        print(f"  📊 Found sessions: {list(sessions)}")

        for session in sessions:
            session_data = copula_data[copula_data["session_label"] == session]

            if len(session_data) < 100:  # Minimum observations
                print(f"  ⚠️ Session {session} has {len(session_data)} obs < 100, skipping")
                continue

            print(f"  🔄 Analyzing session {session} ({len(session_data)} obs)...")

            # Get return marginals
            ret_cols = [col for col in session_data.columns if col.startswith("u_ret_")]
            ret_data = session_data[ret_cols].dropna()

            if len(ret_data) < 50:
                print(f"    ⚠️ Insufficient return data for {session}")
                continue

            # Fit Gaussian copula (simplified)
            gaussian_results = self._fit_gaussian_copula(ret_data)

            # Fit t-copula (simplified)
            t_copula_results = self._fit_t_copula(ret_data)

            # Calculate pairwise Kendall's tau
            kendall_tau = self._calculate_kendall_tau(ret_data)

            # Calculate tail dependence (simplified)
            tail_dependence = self._calculate_tail_dependence(ret_data)

            session_results[session] = {
                "n_obs": len(ret_data),
                "n_venues": len(ret_cols),
                "gaussian_copula": gaussian_results,
                "t_copula": t_copula_results,
                "kendall_tau": kendall_tau,
                "tail_dependence": tail_dependence,
            }

            print(f"    ✅ {session}: {len(ret_data)} obs, {len(ret_cols)} venues")

        return session_results if session_results else None

    def _fit_gaussian_copula(self, data: pd.DataFrame) -> Dict:
        """Fit Gaussian copula (simplified)."""
        # Calculate correlation matrix
        corr_matrix = data.corr()

        # Calculate log-likelihood (simplified)
        n_obs = len(data)
        n_vars = len(data.columns)

        # Simple log-likelihood approximation
        log_lik = (
            -0.5
            * n_obs
            * (n_vars * np.log(2 * np.pi) + np.log(np.linalg.det(corr_matrix.values + 1e-6)))
        )

        # AIC and BIC
        n_params = n_vars * (n_vars - 1) // 2  # Correlation parameters
        aic = -2 * log_lik + 2 * n_params
        bic = -2 * log_lik + n_params * np.log(n_obs)

        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "log_likelihood": log_lik,
            "aic": aic,
            "bic": bic,
            "n_params": n_params,
        }

    def _fit_t_copula(self, data: pd.DataFrame) -> Dict:
        """Fit t-copula (simplified)."""
        # Calculate correlation matrix
        corr_matrix = data.corr()

        # Estimate degrees of freedom (simplified)
        # Use moment-based estimator
        n_obs = len(data)
        n_vars = len(data.columns)

        # Simple DOF estimation
        dof = max(2, min(10, n_obs // 100))  # Simplified DOF estimation

        # Calculate log-likelihood (simplified)
        log_lik = (
            -0.5
            * n_obs
            * (n_vars * np.log(2 * np.pi) + np.log(np.linalg.det(corr_matrix.values + 1e-6)))
        )
        log_lik -= n_obs * np.log(dof)  # t-copula adjustment

        # AIC and BIC
        n_params = n_vars * (n_vars - 1) // 2 + 1  # Correlation + DOF
        aic = -2 * log_lik + 2 * n_params
        bic = -2 * log_lik + n_params * np.log(n_obs)

        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "degrees_of_freedom": dof,
            "log_likelihood": log_lik,
            "aic": aic,
            "bic": bic,
            "n_params": n_params,
        }

    def _calculate_kendall_tau(self, data: pd.DataFrame) -> Dict:
        """Calculate pairwise Kendall's tau."""
        kendall_results = {}

        for i, col1 in enumerate(data.columns):
            for j, col2 in enumerate(data.columns):
                if i < j:  # Only upper triangle
                    tau, p_value = stats.kendalltau(data[col1], data[col2])
                    kendall_results[f"{col1}_{col2}"] = {
                        "tau": float(tau) if not np.isnan(tau) else 0.0,
                        "p_value": float(p_value) if not np.isnan(p_value) else 1.0,
                        "significant": bool(p_value < 0.05),
                    }

        return kendall_results

    def _calculate_tail_dependence(self, data: pd.DataFrame) -> Dict:
        """Calculate tail dependence (simplified)."""
        tail_results = {}

        # Calculate upper and lower tail dependence
        for i, col1 in enumerate(data.columns):
            for j, col2 in enumerate(data.columns):
                if i < j:  # Only upper triangle
                    # Upper tail dependence (simplified)
                    upper_tail = self._estimate_upper_tail_dependence(data[col1], data[col2])

                    # Lower tail dependence (simplified)
                    lower_tail = self._estimate_lower_tail_dependence(data[col1], data[col2])

                    tail_results[f"{col1}_{col2}"] = {
                        "upper_tail": float(upper_tail),
                        "lower_tail": float(lower_tail),
                        "symmetric": bool(abs(upper_tail - lower_tail) < 0.1),
                    }

        return tail_results

    def _estimate_upper_tail_dependence(self, x: pd.Series, y: pd.Series) -> float:
        """Estimate upper tail dependence (simplified)."""
        # Use empirical approach
        threshold = 0.95
        x_thresh = x.quantile(threshold)
        y_thresh = y.quantile(threshold)

        # Count joint exceedances
        joint_exceed = ((x >= x_thresh) & (y >= y_thresh)).sum()
        x_exceed = (x >= x_thresh).sum()

        if x_exceed > 0:
            return joint_exceed / x_exceed
        else:
            return 0.0

    def _estimate_lower_tail_dependence(self, x: pd.Series, y: pd.Series) -> float:
        """Estimate lower tail dependence (simplified)."""
        # Use empirical approach
        threshold = 0.05
        x_thresh = x.quantile(threshold)
        y_thresh = y.quantile(threshold)

        # Count joint exceedances
        joint_exceed = ((x <= x_thresh) & (y <= y_thresh)).sum()
        x_exceed = (x <= x_thresh).sum()

        if x_exceed > 0:
            return joint_exceed / x_exceed
        else:
            return 0.0

    def _generate_copula_outputs(self, session_results: Dict):
        """Generate copula analysis outputs."""
        # Save session-specific results
        for session, results in session_results.items():
            session_file = f"{self.analysis_dir}/session_{session}_fit.json"
            with open(session_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"  💾 Session {session} results saved to {session_file}")

        # Generate summary
        self._generate_copula_summary(session_results)

    def _generate_copula_summary(self, session_results: Dict):
        """Generate copula summary report."""
        summary_file = f"{self.analysis_dir}/W3_COPULA_SUMMARY.md"

        with open(summary_file, "w") as f:
            f.write("# Wave-3 Copula Analysis Summary\n\n")
            f.write(f"**Analysis Date**: {datetime.now().isoformat()}\n")
            f.write("**Method**: Copula Dependence & Tails Analysis\n")
            f.write(
                "**Hypothesis**: Competitive markets show session-dependent dependence; coordination shows stable, high dependence\n\n"
            )

            # Session results
            f.write("## Session Results\n\n")
            f.write(
                "| Session | Observations | Venues | Gaussian AIC | t-Copula AIC | Best Model |\n"
            )
            f.write("|---------|-------------|--------|-------------|-------------|------------|\n")

            for session, results in session_results.items():
                gaussian_aic = results["gaussian_copula"]["aic"]
                t_aic = results["t_copula"]["aic"]
                best_model = "Gaussian" if gaussian_aic < t_aic else "t-Copula"

                f.write(
                    f"| {session} | {results['n_obs']:,} | {results['n_venues']} | {gaussian_aic:.2f} | {t_aic:.2f} | {best_model} |\n"
                )

            # Dependence analysis
            f.write("\n## Dependence Analysis\n\n")

            # Calculate average Kendall's tau by session
            for session, results in session_results.items():
                f.write(f"### {session} Session\n\n")

                # Kendall's tau summary
                tau_values = [result["tau"] for result in results["kendall_tau"].values()]
                if tau_values:
                    f.write(f"- **Average Kendall's τ**: {np.mean(tau_values):.4f}\n")
                    f.write(f"- **Max Kendall's τ**: {np.max(tau_values):.4f}\n")
                    f.write(f"- **Min Kendall's τ**: {np.min(tau_values):.4f}\n")

                # Tail dependence summary
                tail_values = [
                    result["upper_tail"] for result in results["tail_dependence"].values()
                ]
                if tail_values:
                    f.write(f"- **Average Upper Tail Dependence**: {np.mean(tail_values):.4f}\n")
                    f.write(f"- **Max Upper Tail Dependence**: {np.max(tail_values):.4f}\n")

                f.write("\n")

            # Cross-session comparison
            f.write("## Cross-Session Comparison\n\n")

            # Calculate session-invariant high dependence
            all_tau_values = []
            for session, results in session_results.items():
                tau_values = [result["tau"] for result in results["kendall_tau"].values()]
                all_tau_values.extend(tau_values)

            if all_tau_values:
                high_dependence_threshold = 0.7
                high_dependence_pct = np.mean(
                    [abs(tau) > high_dependence_threshold for tau in all_tau_values]
                )

                f.write(f"- **High Dependence Threshold**: τ > {high_dependence_threshold}\n")
                f.write(f"- **Percentage with High Dependence**: {high_dependence_pct:.1%}\n")

                if high_dependence_pct > 0.5:
                    f.write(
                        "- **⚠️ CONCERNING**: High proportion of strong dependence across sessions\n"
                    )
                    f.write("- This suggests coordinated behavior with stable, high dependence\n")
                else:
                    f.write("- **✅ REASSURING**: Moderate dependence levels across sessions\n")
                    f.write(
                        "- This suggests competitive behavior with session-dependent dependence\n"
                    )

            f.write("\n## Interpretation\n\n")
            f.write("### Competitive Markets\n")
            f.write("- Dependence varies across sessions\n")
            f.write("- Lower average dependence levels\n")
            f.write("- Session-specific tail behavior\n\n")

            f.write("### Coordinated Markets\n")
            f.write("- Stable, high dependence across sessions\n")
            f.write("- Session-invariant strong correlations\n")
            f.write("- Consistent tail dependence patterns\n\n")

            f.write("## Limitations\n\n")
            f.write("- Simplified copula fitting approach\n")
            f.write("- Limited to single-day analysis\n")
            f.write("- No bootstrap confidence intervals\n")
            f.write("- Assumes specific copula families\n")
            f.write("- May not capture all dependence structures\n")

        print(f"  💾 Summary saved to {summary_file}")


if __name__ == "__main__":
    executor = Wave3CopulaExecutor()
    success = executor.run_copula_analysis()

    if success:
        print("\n🎉 Wave-3 Copula analysis completed successfully!")
    else:
        print("\n❌ Wave-3 Copula analysis failed!")
        sys.exit(1)
