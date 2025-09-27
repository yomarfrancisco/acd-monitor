"""
Invariant Causal Prediction (ICP) Engine

Implements Brief 55+ ICP methodology for detecting environment-invariant
vs. environment-sensitive pricing relationships in crypto markets.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression

from .statistics import EnhancedStatistics, FDRConfig, PowerAnalysisConfig, StatisticalResults

logger = logging.getLogger(__name__)


@dataclass
class ICPConfig:
    """Configuration for ICP analysis"""

    # Statistical parameters
    significance_level: float = 0.05
    power_threshold: float = 0.8
    effect_size_threshold: float = 0.2
    min_samples_per_env: int = 500

    # Bootstrap parameters
    n_bootstrap: int = 1000
    bootstrap_confidence: float = 0.95

    # Environment partitioning
    environment_columns: List[str] = None  # Will be set based on data


@dataclass
class ICPResult:
    """Results from ICP analysis"""

    # Test results
    test_statistic: float
    p_value: float
    reject_h0: bool
    effect_size: float
    power: float

    # Environment analysis
    n_environments: int
    environment_sizes: Dict[str, int]

    # Confidence intervals
    confidence_interval: Tuple[float, float]
    bootstrap_ci: Tuple[float, float]

    # Model diagnostics
    r_squared: float
    residual_normality: float  # p-value from normality test
    heteroscedasticity: float  # p-value from heteroscedasticity test


class ICPEngine:
    """
    Invariant Causal Prediction Engine

    Tests whether pricing relationships remain invariant across different
    market environments (competitive) or become environment-invariant (coordinated).
    """

    def __init__(self, config: ICPConfig):
        self.config = config

        # Initialize enhanced statistics
        power_config = PowerAnalysisConfig(
            effect_size_threshold=config.effect_size_threshold,
            power_threshold=config.power_threshold,
            significance_level=config.significance_level,
            min_samples_per_env=config.min_samples_per_env,
            n_bootstrap=config.n_bootstrap,
            confidence_level=config.bootstrap_confidence,
        )

        fdr_config = FDRConfig(fdr_level=0.1, method="bh")  # 10% FDR control

        self.enhanced_stats = EnhancedStatistics(power_config, fdr_config)

    def analyze_invariance(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_columns: Optional[List[str]] = None,
    ) -> ICPResult:
        """
        Main ICP analysis method

        Args:
            data: DataFrame with price and environment data
            price_columns: List of price column names
            environment_columns: List of environment column names

        Returns:
            ICPResult with test statistics and diagnostics
        """
        logger.info("Starting ICP invariance analysis")

        # Set environment columns if not provided
        if environment_columns is None:
            environment_columns = self._detect_environment_columns(data)

        self.config.environment_columns = environment_columns

        # Validate input data
        self._validate_input(data, price_columns, environment_columns)

        # Partition data by environments
        environment_data = self._partition_by_environments(data, environment_columns)

        # Test for invariance
        test_result = self._test_invariance(environment_data, price_columns)

        # Calculate effect size and power
        effect_size = self._calculate_effect_size(environment_data, price_columns)
        power = self._calculate_power(effect_size, environment_data)

        # Bootstrap confidence intervals
        bootstrap_ci = self._bootstrap_confidence_interval(data, price_columns, environment_columns)

        # Model diagnostics
        diagnostics = self._calculate_diagnostics(environment_data, price_columns)

        return ICPResult(
            test_statistic=test_result["test_statistic"],
            p_value=test_result["p_value"],
            reject_h0=test_result["p_value"] < self.config.significance_level,
            effect_size=effect_size,
            power=power,
            n_environments=len(environment_data),
            environment_sizes={env: len(df) for env, df in environment_data.items()},
            confidence_interval=test_result["confidence_interval"],
            bootstrap_ci=bootstrap_ci,
            r_squared=diagnostics["r_squared"],
            residual_normality=diagnostics["residual_normality"],
            heteroscedasticity=diagnostics["heteroscedasticity"],
        )

    def analyze_invariance_enhanced(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_columns: Optional[List[str]] = None,
    ) -> StatisticalResults:
        """
        Enhanced ICP analysis with statistical rigor

        Uses power analysis, FDR control, and advanced statistical testing
        for court/regulator-ready coordination risk analytics.

        Args:
            data: DataFrame with price and environment data
            price_columns: List of price column names
            environment_columns: List of environment column names

        Returns:
            StatisticalResults with comprehensive analysis
        """
        logger.info("Starting enhanced ICP invariance analysis")

        # Set environment columns if not provided
        if environment_columns is None:
            environment_columns = self._detect_environment_columns(data)

        # Validate input data
        self._validate_input(data, price_columns, environment_columns)

        # Partition data by environments
        environment_data = self._partition_by_environments(data, environment_columns)

        # Run enhanced statistical analysis
        return self.enhanced_stats.analyze_invariance_with_rigor(environment_data, price_columns)

    def _detect_environment_columns(self, data: pd.DataFrame) -> List[str]:
        """Detect environment columns in the data"""
        potential_env_cols = []

        for col in data.columns:
            if col.endswith("_regime") or col.endswith("_condition"):
                potential_env_cols.append(col)
            elif data[col].dtype == "object" and data[col].nunique() < 10:
                potential_env_cols.append(col)

        if not potential_env_cols:
            raise ValueError("No environment columns detected in data")

        logger.info(f"Detected environment columns: {potential_env_cols}")
        return potential_env_cols

    def _validate_input(
        self, data: pd.DataFrame, price_columns: List[str], environment_columns: List[str]
    ) -> None:
        """Validate input data requirements"""

        # Check required columns exist
        missing_price_cols = [col for col in price_columns if col not in data.columns]
        if missing_price_cols:
            raise ValueError(f"Missing price columns: {missing_price_cols}")

        missing_env_cols = [col for col in environment_columns if col not in data.columns]
        if missing_env_cols:
            raise ValueError(f"Missing environment columns: {missing_env_cols}")

        # Check minimum sample size
        if len(data) < self.config.min_samples_per_env * 2:
            raise ValueError(
                f"Insufficient data: {len(data)} < {self.config.min_samples_per_env * 2}"
            )

        # Check for missing values
        if data[price_columns + environment_columns].isnull().any().any():
            raise ValueError("Data contains missing values")

    def _partition_by_environments(
        self, data: pd.DataFrame, environment_columns: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """Partition data by environment combinations"""

        # Create environment labels
        env_labels = data[environment_columns].apply(
            lambda row: "_".join([str(val) for val in row]), axis=1
        )

        # Group by environment
        environment_data = {}
        for env_label, group in data.groupby(env_labels):
            if len(group) >= self.config.min_samples_per_env:
                environment_data[env_label] = group.copy()
            else:
                logger.warning(f"Environment {env_label} has insufficient data: {len(group)}")

        if len(environment_data) < 2:
            raise ValueError("Need at least 2 environments with sufficient data")

        logger.info(f"Partitioned data into {len(environment_data)} environments")
        return environment_data

    def _test_invariance(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> Dict[str, float]:
        """
        Test for invariance across environments using Kolmogorov-Smirnov test

        H₀: P(Y|X_S, E=e) = P(Y|X_S) ∀e (invariant)
        H₁: ∃e₁,e₂: P(Y|X_S, E=e₁) ≠ P(Y|X_S, E=e₂) (environment-sensitive)
        """

        # Calculate correlation matrices for each environment
        environment_correlations = {}

        for env_label, env_data in environment_data.items():
            # Calculate correlation matrix between all price columns
            price_data = env_data[price_columns].values
            corr_matrix = np.corrcoef(price_data.T)

            # Store upper triangular part (excluding diagonal)
            n_prices = len(price_columns)
            correlations = []
            for i in range(n_prices):
                for j in range(i + 1, n_prices):
                    correlations.append(corr_matrix[i, j])

            environment_correlations[env_label] = np.array(correlations)

        # Test for differences in correlation patterns across environments
        env_labels = list(environment_correlations.keys())

        if len(env_labels) < 2:
            # Not enough environments to test
            return {"test_statistic": 0.0, "p_value": 1.0, "confidence_interval": (0.0, 0.0)}

        # Compare correlation patterns between environments
        max_ks_statistic = 0.0
        min_p_value = 1.0

        for i in range(len(env_labels)):
            for j in range(i + 1, len(env_labels)):
                env1, env2 = env_labels[i], env_labels[j]
                corr1 = environment_correlations[env1]
                corr2 = environment_correlations[env2]

                # Kolmogorov-Smirnov test on correlation distributions
                ks_statistic, p_value = stats.ks_2samp(corr1, corr2)
                max_ks_statistic = max(max_ks_statistic, ks_statistic)
                min_p_value = min(min_p_value, p_value)

        # Calculate p-value for the maximum statistic
        # This is a conservative approach for multiple comparisons
        p_value = 1 - (1 - min_p_value) ** (len(env_labels) * (len(env_labels) - 1) / 2)

        # Calculate confidence interval for the test statistic
        confidence_interval = self._calculate_confidence_interval(
            max_ks_statistic, len(environment_data)
        )

        return {
            "test_statistic": max_ks_statistic,
            "p_value": p_value,
            "confidence_interval": confidence_interval,
        }

    def _calculate_effect_size(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> float:
        """Calculate effect size (Cohen's d) for environment differences"""

        # Calculate mean residuals for each environment
        env_means = []
        for env_data in environment_data.values():
            target_col = price_columns[0]
            feature_cols = price_columns[1:]

            X = env_data[feature_cols].values
            y = env_data[target_col].values

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            residuals = y - y_pred

            env_means.append(np.mean(residuals))

        # Calculate effect size
        if len(env_means) < 2:
            return 0.0

        pooled_std = np.std(env_means)
        if pooled_std == 0:
            return 0.0

        effect_size = (np.max(env_means) - np.min(env_means)) / pooled_std
        return effect_size

    def _calculate_power(
        self, effect_size: float, environment_data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calculate statistical power for the test"""

        # Simplified power calculation
        # In practice, this would use more sophisticated methods
        len(environment_data)
        avg_sample_size = np.mean([len(df) for df in environment_data.values()])

        # Approximate power calculation
        if effect_size >= self.config.effect_size_threshold:
            power = min(0.95, 0.5 + 0.3 * np.log(avg_sample_size / 1000))
        else:
            power = 0.2 + 0.1 * np.log(avg_sample_size / 1000)

        return power

    def _bootstrap_confidence_interval(
        self, data: pd.DataFrame, price_columns: List[str], environment_columns: List[str]
    ) -> Tuple[float, float]:
        """Calculate bootstrap confidence interval for the test statistic"""

        bootstrap_stats = []

        for _ in range(self.config.n_bootstrap):
            # Bootstrap sample
            bootstrap_data = data.sample(n=len(data), replace=True)

            # Re-run analysis on bootstrap sample
            try:
                env_data = self._partition_by_environments(bootstrap_data, environment_columns)
                if len(env_data) >= 2:
                    test_result = self._test_invariance(env_data, price_columns)
                    bootstrap_stats.append(test_result["test_statistic"])
            except (ValueError, KeyError):
                # Skip if bootstrap sample doesn't meet requirements
                continue

        if not bootstrap_stats:
            return (0.0, 1.0)

        # Calculate confidence interval
        alpha = 1 - self.config.bootstrap_confidence
        lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
        upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

        return (lower, upper)

    def _calculate_confidence_interval(
        self, test_statistic: float, n_environments: int
    ) -> Tuple[float, float]:
        """Calculate confidence interval for the test statistic"""

        # Simplified confidence interval calculation
        # In practice, this would use more sophisticated methods
        margin_of_error = 1.96 * np.sqrt(test_statistic * (1 - test_statistic) / n_environments)

        lower = max(0, test_statistic - margin_of_error)
        upper = min(1, test_statistic + margin_of_error)

        return (lower, upper)

    def _calculate_diagnostics(
        self, environment_data: Dict[str, pd.DataFrame], price_columns: List[str]
    ) -> Dict[str, float]:
        """Calculate model diagnostics"""

        # Calculate R-squared across all environments
        total_ss = 0
        residual_ss = 0

        for env_data in environment_data.values():
            target_col = price_columns[0]
            feature_cols = price_columns[1:]

            X = env_data[feature_cols].values
            y = env_data[target_col].values

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)

            total_ss += np.sum((y - np.mean(y)) ** 2)
            residual_ss += np.sum((y - y_pred) ** 2)

        r_squared = 1 - (residual_ss / total_ss) if total_ss > 0 else 0

        # Test residual normality (simplified)
        all_residuals = []
        for env_data in environment_data.values():
            target_col = price_columns[0]
            feature_cols = price_columns[1:]

            X = env_data[feature_cols].values
            y = env_data[target_col].values

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            residuals = y - y_pred

            all_residuals.extend(residuals)

        # Normality test
        if len(all_residuals) > 3:
            _, normality_p = stats.normaltest(all_residuals)
        else:
            normality_p = 1.0

        # Heteroscedasticity test (simplified)
        heteroscedasticity_p = 0.5  # Placeholder

        return {
            "r_squared": r_squared,
            "residual_normality": normality_p,
            "heteroscedasticity": heteroscedasticity_p,
        }


def run_icp_analysis(
    data: pd.DataFrame, price_columns: List[str], config: Optional[ICPConfig] = None
) -> ICPResult:
    """
    Convenience function to run ICP analysis

    Args:
        data: DataFrame with price and environment data
        price_columns: List of price column names
        config: Optional ICP configuration

    Returns:
        ICPResult with analysis results
    """
    if config is None:
        config = ICPConfig()

    engine = ICPEngine(config)
    return engine.analyze_invariance(data, price_columns)


if __name__ == "__main__":
    # Example usage
    from ..data.synthetic_crypto import generate_validation_datasets

    # Generate test data
    competitive_data, coordinated_data = generate_validation_datasets()

    # Run ICP analysis on competitive data
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

    print("ICP Analysis on Competitive Data:")
    result_competitive = run_icp_analysis(competitive_data, price_cols)
    print(f"Reject H0 (invariant): {result_competitive.reject_h0}")
    print(f"P-value: {result_competitive.p_value:.4f}")
    print(f"Effect size: {result_competitive.effect_size:.4f}")
    print(f"Power: {result_competitive.power:.4f}")

    print("\nICP Analysis on Coordinated Data:")
    result_coordinated = run_icp_analysis(coordinated_data, price_cols)
    print(f"Reject H0 (invariant): {result_coordinated.reject_h0}")
    print(f"P-value: {result_coordinated.p_value:.4f}")
    print(f"Effect size: {result_coordinated.effect_size:.4f}")
    print(f"Power: {result_coordinated.power:.4f}")
