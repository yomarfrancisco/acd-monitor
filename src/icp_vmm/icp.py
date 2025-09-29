#!/usr/bin/env python3
"""
Invariance-Conditional Pricing (ICP) Tests

Tests parameter stability across market environments.
"""

import pandas as pd
import numpy as np
from typing import Dict
from scipy import stats
from scipy.stats import chi2_contingency, ks_2samp
from statsmodels.stats.multitest import multipletests
import logging

logger = logging.getLogger(__name__)


class ICPTester:
    """Tests invariance of parameters across market environments."""

    def __init__(self, fdr_alpha: float = 0.05, bootstrap_samples: int = 500):
        self.fdr_alpha = fdr_alpha
        self.bootstrap_samples = bootstrap_samples

    def test_parameter_stability(
        self, env_data: Dict[str, pd.DataFrame], parameter_name: str
    ) -> Dict:
        """
        Test stability of parameters across environments.

        Args:
            env_data: Dict of environment DataFrames
            parameter_name: Name of parameter to test

        Returns:
            Parameter stability test results
        """
        try:
            if len(env_data) < 2:
                return {"error": "insufficient_environments"}

            # Extract parameter values by environment
            env_params = {}
            for env, data in env_data.items():
                if parameter_name in data.columns:
                    env_params[env] = data[parameter_name].dropna()

            if len(env_params) < 2:
                return {"error": "insufficient_parameter_data"}

            # Perform Kruskal-Wallis test (non-parametric ANOVA)
            groups = list(env_params.values())
            h_stat, p_value = stats.kruskal(*groups)

            # Calculate effect size (eta-squared)
            n_total = sum(len(group) for group in groups)
            eta_squared = (h_stat - len(groups) + 1) / (n_total - len(groups))

            results = {
                "test": "kruskal_wallis",
                "statistic": h_stat,
                "p_value": p_value,
                "eta_squared": eta_squared,
                "significant": p_value < self.fdr_alpha,
                "environments": list(env_params.keys()),
                "sample_sizes": {env: len(data) for env, data in env_params.items()},
            }

        except Exception as e:
            logger.warning(f"Parameter stability test failed: {e}")
            results = {"error": str(e)}

        return results

    def test_leadership_stability(self, env_leadership: Dict[str, pd.Series]) -> Dict:
        """
        Test stability of leadership shares across environments.

        Args:
            env_leadership: Dict of environment leadership series

        Returns:
            Leadership stability test results
        """
        try:
            if len(env_leadership) < 2:
                return {"error": "insufficient_environments"}

            # Create contingency table for chi-square test
            contingency_data = []
            env_names = []

            for env, leadership in env_leadership.items():
                if len(leadership) > 0:
                    # Bin leadership into categories
                    leadership_bins = pd.cut(leadership, bins=3, labels=["low", "mid", "high"])
                    contingency_data.append(leadership_bins.value_counts())
                    env_names.append(env)

            if len(contingency_data) < 2:
                return {"error": "insufficient_leadership_data"}

            # Create contingency table
            contingency_table = pd.DataFrame(contingency_data, index=env_names).fillna(0)

            # Perform chi-square test
            chi2_stat, p_value, dof, expected = chi2_contingency(contingency_table)

            # Calculate Cramér's V (effect size)
            n = contingency_table.sum().sum()
            cramers_v = np.sqrt(chi2_stat / (n * (min(contingency_table.shape) - 1)))

            results = {
                "test": "chi_square",
                "statistic": chi2_stat,
                "p_value": p_value,
                "dof": dof,
                "cramers_v": cramers_v,
                "significant": p_value < self.fdr_alpha,
                "contingency_table": contingency_table.to_dict(),
                "environments": env_names,
            }

        except Exception as e:
            logger.warning(f"Leadership stability test failed: {e}")
            results = {"error": str(e)}

        return results

    def test_residual_stability(self, env_residuals: Dict[str, pd.Series]) -> Dict:
        """
        Test stability of residual distributions across environments.

        Args:
            env_residuals: Dict of environment residual series

        Returns:
            Residual stability test results
        """
        try:
            if len(env_residuals) < 2:
                return {"error": "insufficient_environments"}

            # Perform pairwise Kolmogorov-Smirnov tests
            env_names = list(env_residuals.keys())
            ks_results = {}

            for i, env1 in enumerate(env_names):
                for env2 in env_names[i + 1 :]:
                    if len(env_residuals[env1]) > 0 and len(env_residuals[env2]) > 0:
                        ks_stat, p_value = ks_2samp(env_residuals[env1], env_residuals[env2])
                        ks_results[f"{env1}_{env2}"] = {
                            "statistic": ks_stat,
                            "p_value": p_value,
                            "significant": p_value < self.fdr_alpha,
                        }

            # Calculate overall significance
            p_values = [result["p_value"] for result in ks_results.values()]
            if p_values:
                # Apply FDR correction
                _, p_corrected, _, _ = multipletests(
                    p_values, alpha=self.fdr_alpha, method="fdr_bh"
                )

                # Count significant tests
                n_significant = sum(1 for p in p_corrected if p < self.fdr_alpha)
                overall_significant = n_significant > 0
            else:
                overall_significant = False

            results = {
                "test": "kolmogorov_smirnov",
                "pairwise_results": ks_results,
                "overall_significant": overall_significant,
                "n_tests": len(ks_results),
                "n_significant": n_significant if p_values else 0,
                "environments": env_names,
            }

        except Exception as e:
            logger.warning(f"Residual stability test failed: {e}")
            results = {"error": str(e)}

        return results

    def bootstrap_confidence_interval(
        self, data: pd.Series, statistic_func, confidence_level: float = 0.95
    ) -> Dict:
        """
        Calculate bootstrap confidence interval for a statistic.

        Args:
            data: Data series
            statistic_func: Function to calculate statistic
            confidence_level: Confidence level

        Returns:
            Bootstrap CI results
        """
        try:
            if len(data) < 10:
                return {"error": "insufficient_data"}

            # Bootstrap samples
            bootstrap_stats = []
            n = len(data)

            for _ in range(self.bootstrap_samples):
                bootstrap_sample = data.sample(n=n, replace=True)
                bootstrap_stat = statistic_func(bootstrap_sample)
                bootstrap_stats.append(bootstrap_stat)

            # Calculate confidence interval
            alpha = 1 - confidence_level
            lower_percentile = (alpha / 2) * 100
            upper_percentile = (1 - alpha / 2) * 100

            ci_lower = np.percentile(bootstrap_stats, lower_percentile)
            ci_upper = np.percentile(bootstrap_stats, upper_percentile)

            results = {
                "bootstrap_samples": self.bootstrap_samples,
                "confidence_level": confidence_level,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "bootstrap_stats": bootstrap_stats,
            }

        except Exception as e:
            logger.warning(f"Bootstrap CI calculation failed: {e}")
            results = {"error": str(e)}

        return results

    def run_all_icp_tests(
        self,
        env_data: Dict[str, pd.DataFrame],
        env_leadership: Dict[str, pd.Series],
        env_residuals: Dict[str, pd.Series],
    ) -> Dict:
        """
        Run all ICP invariance tests.

        Args:
            env_data: Dict of environment DataFrames
            env_leadership: Dict of environment leadership series
            env_residuals: Dict of environment residual series

        Returns:
            Complete ICP test results
        """
        results = {
            "parameter_tests": {},
            "leadership_tests": {},
            "residual_tests": {},
            "overall": {"status": "INSUFFICIENT", "significant_tests": 0},
        }

        try:
            # Test parameter stability for each parameter
            parameter_tests = {}
            for env, data in env_data.items():
                for col in data.columns:
                    if col not in [
                        "ts_exchange",
                        "session",
                        "vwap_side",
                        "hl_bucket",
                        "liquidity_regime",
                        "leadership_regime",
                    ]:
                        if col not in parameter_tests:
                            parameter_tests[col] = {}
                        parameter_tests[col][env] = data[col].dropna()

            for param, env_data_dict in parameter_tests.items():
                if len(env_data_dict) >= 2:
                    test_result = self.test_parameter_stability(env_data_dict, param)
                    results["parameter_tests"][param] = test_result

            # Test leadership stability
            if len(env_leadership) >= 2:
                leadership_result = self.test_leadership_stability(env_leadership)
                results["leadership_tests"] = leadership_result

            # Test residual stability
            if len(env_residuals) >= 2:
                residual_result = self.test_residual_stability(env_residuals)
                results["residual_tests"] = residual_result

            # Calculate overall significance
            significant_tests = 0
            total_tests = 0

            # Count parameter tests
            for param_result in results["parameter_tests"].values():
                if "significant" in param_result:
                    total_tests += 1
                    if param_result["significant"]:
                        significant_tests += 1

            # Count leadership tests
            if "significant" in results["leadership_tests"]:
                total_tests += 1
                if results["leadership_tests"]["significant"]:
                    significant_tests += 1

            # Count residual tests
            if "overall_significant" in results["residual_tests"]:
                total_tests += 1
                if results["residual_tests"]["overall_significant"]:
                    significant_tests += 1

            # Determine overall status
            if total_tests == 0:
                status = "INSUFFICIENT"
            elif significant_tests == 0:
                status = "INVARIANT"
            else:
                status = "VARIANT"

            results["overall"] = {
                "status": status,
                "significant_tests": significant_tests,
                "total_tests": total_tests,
            }

        except Exception as e:
            logger.error(f"ICP tests failed: {e}")
            results["error"] = str(e)
            results["overall"]["status"] = "ERROR"

        return results
