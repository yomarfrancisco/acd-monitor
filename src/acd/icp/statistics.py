"""
Enhanced Statistical Methods for ICP Analysis

Implements power analysis, FDR control, and advanced statistical testing
for court/regulator-ready coordination risk analytics.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm

logger = logging.getLogger(__name__)


@dataclass
class PowerAnalysisConfig:
    """Configuration for power analysis"""

    # Effect size parameters
    effect_size_threshold: float = 0.2  # Minimum detectable effect size
    power_threshold: float = 0.8  # Minimum statistical power
    significance_level: float = 0.05  # Type I error rate

    # Sample size parameters
    min_samples_per_env: int = 1000  # Minimum samples per environment
    max_samples_per_env: int = 10000  # Maximum samples per environment

    # Bootstrap parameters
    n_bootstrap: int = 1000  # Number of bootstrap samples
    confidence_level: float = 0.95  # Confidence level for intervals


@dataclass
class FDRConfig:
    """Configuration for False Discovery Rate control"""

    # FDR parameters
    fdr_level: float = 0.1  # FDR control level (Benjamini-Hochberg)
    method: str = "bh"  # FDR control method

    # Multiple testing parameters
    n_tests: int = 1  # Number of simultaneous tests
    independence_assumption: bool = False  # Whether tests are independent


@dataclass
class StatisticalResults:
    """Results from enhanced statistical analysis"""

    # Test results
    test_statistic: float
    p_value: float
    adjusted_p_value: float
    reject_h0: bool

    # Power analysis
    effect_size: float
    statistical_power: float
    required_sample_size: int

    # Confidence intervals
    confidence_interval: Tuple[float, float]
    bootstrap_ci: Tuple[float, float]

    # FDR control
    fdr_controlled: bool
    fdr_adjusted_p_value: float


class EnhancedStatistics:
    """
    Enhanced statistical methods for ICP analysis

    Implements power analysis, FDR control, and advanced hypothesis testing
    for court/regulator-ready coordination risk analytics.
    """

    def __init__(self, power_config: PowerAnalysisConfig, fdr_config: FDRConfig):
        self.power_config = power_config
        self.fdr_config = fdr_config

    def analyze_invariance_with_rigor(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> StatisticalResults:
        """
        Enhanced invariance analysis with statistical rigor

        Args:
            environment_data: Dictionary of environment-partitioned data
            price_columns: List of price column names

        Returns:
            StatisticalResults with comprehensive analysis
        """
        logger.info("Running enhanced invariance analysis with statistical rigor")

        # Basic invariance test
        test_statistic, p_value = self._test_invariance_ks(environment_data, price_columns)

        # Calculate effect size
        effect_size = self._calculate_effect_size(environment_data, price_columns)

        # Power analysis
        statistical_power = self._calculate_statistical_power(effect_size, environment_data)
        required_sample_size = self._calculate_required_sample_size(effect_size)

        # Bootstrap confidence intervals
        bootstrap_ci = self._bootstrap_confidence_interval(environment_data, price_columns)

        # FDR control
        fdr_adjusted_p_value = self._apply_fdr_control([p_value])
        fdr_controlled = fdr_adjusted_p_value < self.fdr_config.fdr_level

        # Decision
        reject_h0 = p_value < self.power_config.significance_level and fdr_controlled

        return StatisticalResults(
            test_statistic=test_statistic,
            p_value=p_value,
            adjusted_p_value=fdr_adjusted_p_value,
            reject_h0=reject_h0,
            effect_size=effect_size,
            statistical_power=statistical_power,
            required_sample_size=required_sample_size,
            confidence_interval=self._calculate_confidence_interval(test_statistic),
            bootstrap_ci=bootstrap_ci,
            fdr_controlled=fdr_controlled,
            fdr_adjusted_p_value=fdr_adjusted_p_value,
        )

    def _test_invariance_ks(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> Tuple[float, float]:
        """
        Kolmogorov-Smirnov test for invariance across environments

        Returns:
            Tuple of (test_statistic, p_value)
        """
        # Fit models for each environment
        environment_residuals = {}

        for env_label, env_data in environment_data.items():
            # Prepare features and target
            target_col = price_columns[0]
            feature_cols = price_columns[1:]

            X = env_data[feature_cols].values
            y = env_data[target_col].values

            # Fit linear model
            from sklearn.linear_model import LinearRegression

            model = LinearRegression()
            model.fit(X, y)

            # Calculate residuals
            y_pred = model.predict(X)
            residuals = y - y_pred
            environment_residuals[env_label] = residuals

        # Test for differences in residual distributions
        env_labels = list(environment_residuals.keys())
        max_ks_statistic = 0.0
        p_values = []

        for i in range(len(env_labels)):
            for j in range(i + 1, len(env_labels)):
                env1, env2 = env_labels[i], env_labels[j]
                residuals1 = environment_residuals[env1]
                residuals2 = environment_residuals[env2]

                # Kolmogorov-Smirnov test
                ks_statistic, p_value = stats.ks_2samp(residuals1, residuals2)
                max_ks_statistic = max(max_ks_statistic, ks_statistic)
                p_values.append(p_value)

        # Conservative p-value for multiple comparisons
        if p_values:
            min_p_value = min(p_values)
            # Bonferroni correction
            corrected_p_value = min(1.0, min_p_value * len(p_values))
        else:
            corrected_p_value = 1.0

        return max_ks_statistic, corrected_p_value

    def _calculate_effect_size(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> float:
        """Calculate Cohen's d effect size for environment differences"""

        # Calculate mean residuals for each environment
        env_means = []
        for env_data in environment_data.values():
            target_col = price_columns[0]
            feature_cols = price_columns[1:]

            X = env_data[feature_cols].values
            y = env_data[target_col].values

            from sklearn.linear_model import LinearRegression

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            residuals = y - y_pred

            env_means.append(np.mean(residuals))

        if len(env_means) < 2:
            return 0.0

        # Calculate effect size (Cohen's d)
        pooled_std = np.std(env_means)
        if pooled_std == 0:
            return 0.0

        effect_size = (np.max(env_means) - np.min(env_means)) / pooled_std
        return effect_size

    def _calculate_statistical_power(
        self, effect_size: float, environment_data: Dict[str, pd.DataFrame]
    ) -> float:
        """
        Calculate statistical power for the test

        Uses Cohen's power analysis for two-sample t-test
        """
        n_environments = len(environment_data)
        avg_sample_size = np.mean([len(df) for df in environment_data.values()])

        # Calculate power using normal approximation
        # For two-sample t-test with equal sample sizes
        n_per_group = avg_sample_size / n_environments

        # Non-centrality parameter
        ncp = effect_size * np.sqrt(n_per_group / 2)

        # Critical value for two-tailed test
        critical_value = norm.ppf(1 - self.power_config.significance_level / 2)

        # Power calculation
        power = 1 - norm.cdf(critical_value - ncp) + norm.cdf(-critical_value - ncp)

        return min(0.99, max(0.01, power))

    def _calculate_required_sample_size(self, effect_size: float) -> int:
        """
        Calculate required sample size for desired power

        Uses Cohen's sample size calculation
        """
        if effect_size < self.power_config.effect_size_threshold:
            return self.power_config.min_samples_per_env

        # Sample size calculation for two-sample t-test
        # n = 2 * (Z_alpha/2 + Z_beta)^2 / effect_size^2

        z_alpha = norm.ppf(1 - self.power_config.significance_level / 2)
        z_beta = norm.ppf(self.power_config.power_threshold)

        n_per_group = 2 * (z_alpha + z_beta) ** 2 / (effect_size**2)
        total_n = int(n_per_group * 2)  # Two groups

        return max(
            self.power_config.min_samples_per_env,
            min(total_n, self.power_config.max_samples_per_env),
        )

    def _bootstrap_confidence_interval(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> Tuple[float, float]:
        """Calculate bootstrap confidence interval for the test statistic"""

        bootstrap_stats = []

        for _ in range(self.power_config.n_bootstrap):
            # Bootstrap sample
            bootstrap_data = {}
            for env_label, env_data in environment_data.items():
                bootstrap_sample = env_data.sample(n=len(env_data), replace=True)
                bootstrap_data[env_label] = bootstrap_sample

            # Re-run analysis on bootstrap sample
            try:
                test_stat, _ = self._test_invariance_ks(bootstrap_data, price_columns)
                bootstrap_stats.append(test_stat)
            except (ValueError, KeyError):
                continue

        if not bootstrap_stats:
            return (0.0, 1.0)

        # Calculate confidence interval
        alpha = 1 - self.power_config.confidence_level
        lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
        upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

        return (lower, upper)

    def _calculate_confidence_interval(self, test_statistic: float) -> Tuple[float, float]:
        """Calculate confidence interval for the test statistic"""

        # Simplified confidence interval calculation
        margin_of_error = 1.96 * np.sqrt(test_statistic * (1 - test_statistic) / 100)

        lower = max(0, test_statistic - margin_of_error)
        upper = min(1, test_statistic + margin_of_error)

        return (lower, upper)

    def _apply_fdr_control(self, p_values: List[float]) -> float:
        """
        Apply Benjamini-Hochberg FDR control

        Args:
            p_values: List of p-values to adjust

        Returns:
            Adjusted p-value
        """
        if not p_values:
            return 1.0

        p_values = np.array(p_values)
        n_tests = len(p_values)

        # Sort p-values
        sorted_indices = np.argsort(p_values)
        sorted_p_values = p_values[sorted_indices]

        # Benjamini-Hochberg procedure
        bh_critical_values = (np.arange(1, n_tests + 1) / n_tests) * self.fdr_config.fdr_level

        # Find largest k such that P(k) <= (k/n) * alpha
        significant_indices = np.where(sorted_p_values <= bh_critical_values)[0]

        if len(significant_indices) > 0:
            # Return the smallest significant p-value
            return sorted_p_values[significant_indices[0]]
        else:
            # No significant results after FDR control
            return min(1.0, sorted_p_values[0] * n_tests)


def run_enhanced_statistical_analysis(
    environment_data: Dict[str, pd.DataFrame],
    price_columns: List[str],
    power_config: Optional[PowerAnalysisConfig] = None,
    fdr_config: Optional[FDRConfig] = None,
) -> StatisticalResults:
    """
    Convenience function for enhanced statistical analysis

    Args:
        environment_data: Dictionary of environment-partitioned data
        price_columns: List of price column names
        power_config: Optional power analysis configuration
        fdr_config: Optional FDR control configuration

    Returns:
        StatisticalResults with comprehensive analysis
    """
    if power_config is None:
        power_config = PowerAnalysisConfig()

    if fdr_config is None:
        fdr_config = FDRConfig()

    stats_engine = EnhancedStatistics(power_config, fdr_config)
    return stats_engine.analyze_invariance_with_rigor(environment_data, price_columns)


if __name__ == "__main__":
    # Example usage
    from ..data.synthetic_crypto import generate_validation_datasets

    # Generate test data
    competitive_data, coordinated_data = generate_validation_datasets()

    # Partition data by environments
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]
    env_cols = ["volatility_regime", "market_condition"]

    # Create environment data
    env_labels = competitive_data[env_cols].apply(
        lambda row: "_".join([str(val) for val in row]), axis=1
    )

    environment_data = {}
    for env_label, group in competitive_data.groupby(env_labels):
        if len(group) >= 100:  # Minimum sample size
            environment_data[env_label] = group

    # Run enhanced analysis
    result = run_enhanced_statistical_analysis(environment_data, price_cols)

    print("Enhanced Statistical Analysis Results:")
    print(f"Test statistic: {result.test_statistic:.4f}")
    print(f"P-value: {result.p_value:.4f}")
    print(f"FDR adjusted p-value: {result.fdr_adjusted_p_value:.4f}")
    print(f"Reject H0: {result.reject_h0}")
    print(f"Effect size: {result.effect_size:.4f}")
    print(f"Statistical power: {result.statistical_power:.4f}")
    print(f"Required sample size: {result.required_sample_size}")
    print(f"FDR controlled: {result.fdr_controlled}")
