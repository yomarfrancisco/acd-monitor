"""
Power Analysis Module - v1.4 Baseline Standard Implementation

This module implements the power analysis framework required for the v1.4 baseline standard:
- Minimum detectable effect size calculation
- Statistical power analysis with 80% target
- Sample size requirements for reliable detection
- Detection sensitivity by market conditions

All methods follow the v1.4 professional standards with transparent formulas and economic interpretation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
from scipy.optimize import minimize_scalar
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PowerAnalysisResult:
    """Container for power analysis results."""

    minimum_detectable_effect: float
    statistical_power: float
    required_sample_size: int
    significance_level: float
    effect_size: float
    market_regime: str
    detection_threshold: float
    false_positive_rate: float
    analysis_date: str


@dataclass
class DetectionSensitivity:
    """Container for detection sensitivity by market conditions."""

    market_regime: str
    baseline_similarity: float
    detection_threshold: float
    false_positive_rate: float
    minimum_effect_size: float
    required_power: float


class PowerAnalysisCalculator:
    """
    Power Analysis Calculator for Coordination Detection

    Implements statistical power analysis to determine minimum detectable
    effect sizes and required sample sizes for reliable coordination detection.

    Economic Interpretation: Ensures coordination detection has sufficient
    statistical power to distinguish genuine coordination from random variation.
    """

    def __init__(
        self,
        target_power: float = 0.8,
        significance_level: float = 0.05,
        effect_size_threshold: float = 0.15,
    ):
        """
        Initialize power analysis calculator.

        Args:
            target_power: Target statistical power (default: 80%)
            significance_level: Significance level (default: 5%)
            effect_size_threshold: Minimum effect size threshold (default: 15pp)
        """
        self.target_power = target_power
        self.significance_level = significance_level
        self.effect_size_threshold = effect_size_threshold
        self.logger = logging.getLogger(__name__)

    def calculate_minimum_detectable_effect(
        self, sample_size: int, baseline_similarity: float, volatility: float
    ) -> float:
        """
        Calculate minimum detectable effect size for given sample size.

        Args:
            sample_size: Number of observations
            baseline_similarity: Baseline similarity level
            volatility: Market volatility measure

        Returns:
            Minimum detectable effect size (in percentage points)
        """
        try:
            # Calculate standard error based on sample size and volatility
            standard_error = self._calculate_standard_error(sample_size, volatility)

            # Calculate critical value for significance level
            critical_value = stats.norm.ppf(1 - self.significance_level / 2)

            # Calculate power adjustment factor
            power_factor = stats.norm.ppf(self.target_power)

            # Calculate minimum detectable effect
            mde = (critical_value + power_factor) * standard_error

            return mde

        except Exception as e:
            self.logger.error(f"Error calculating minimum detectable effect: {e}")
            return 0.0

    def calculate_required_sample_size(
        self, effect_size: float, baseline_similarity: float, volatility: float
    ) -> int:
        """
        Calculate required sample size for detecting given effect size.

        Args:
            effect_size: Effect size to detect (in percentage points)
            baseline_similarity: Baseline similarity level
            volatility: Market volatility measure

        Returns:
            Required sample size
        """
        try:
            # Calculate standardized effect size
            standardized_effect = effect_size / self._calculate_standard_error(1000, volatility)

            # Calculate required sample size using power analysis formula
            # n = (Z_α/2 + Z_β)² * σ² / δ²
            z_alpha = stats.norm.ppf(1 - self.significance_level / 2)
            z_beta = stats.norm.ppf(self.target_power)

            required_n = ((z_alpha + z_beta) ** 2) / (standardized_effect**2)

            return max(100, int(np.ceil(required_n)))  # Minimum 100 observations

        except Exception as e:
            self.logger.error(f"Error calculating required sample size: {e}")
            return 1000

    def calculate_statistical_power(
        self, effect_size: float, sample_size: int, baseline_similarity: float, volatility: float
    ) -> float:
        """
        Calculate statistical power for given parameters.

        Args:
            effect_size: Effect size to detect
            sample_size: Number of observations
            baseline_similarity: Baseline similarity level
            volatility: Market volatility measure

        Returns:
            Statistical power (0-1)
        """
        try:
            # Calculate standardized effect size
            standard_error = self._calculate_standard_error(sample_size, volatility)
            standardized_effect = effect_size / standard_error

            # Calculate critical value
            critical_value = stats.norm.ppf(1 - self.significance_level / 2)

            # Calculate power
            power = 1 - stats.norm.cdf(critical_value - standardized_effect)

            return max(0.0, min(1.0, power))

        except Exception as e:
            self.logger.error(f"Error calculating statistical power: {e}")
            return 0.0

    def _calculate_standard_error(self, sample_size: int, volatility: float) -> float:
        """Calculate standard error based on sample size and volatility."""
        try:
            # Standard error decreases with square root of sample size
            # and increases with volatility
            base_error = 0.1  # Base standard error
            volatility_adjustment = 1 + volatility
            sample_size_adjustment = 1 / np.sqrt(sample_size)

            standard_error = base_error * volatility_adjustment * sample_size_adjustment

            return standard_error

        except Exception as e:
            self.logger.error(f"Error calculating standard error: {e}")
            return 0.1

    def analyze_detection_sensitivity(
        self,
        market_regimes: List[str],
        baseline_similarities: List[float],
        volatilities: List[float],
    ) -> List[DetectionSensitivity]:
        """
        Analyze detection sensitivity across different market regimes.

        Args:
            market_regimes: List of market regime names
            baseline_similarities: List of baseline similarity levels
            volatilities: List of volatility measures

        Returns:
            List of DetectionSensitivity objects
        """
        try:
            sensitivities = []

            for regime, baseline, volatility in zip(
                market_regimes, baseline_similarities, volatilities
            ):
                # Calculate detection threshold (baseline + minimum detectable effect)
                min_effect = self.calculate_minimum_detectable_effect(1000, baseline, volatility)
                detection_threshold = baseline + min_effect

                # Calculate false positive rate
                false_positive_rate = self._calculate_false_positive_rate(baseline, volatility)

                sensitivity = DetectionSensitivity(
                    market_regime=regime,
                    baseline_similarity=baseline,
                    detection_threshold=detection_threshold,
                    false_positive_rate=false_positive_rate,
                    minimum_effect_size=min_effect,
                    required_power=self.target_power,
                )

                sensitivities.append(sensitivity)

            return sensitivities

        except Exception as e:
            self.logger.error(f"Error analyzing detection sensitivity: {e}")
            return []

    def _calculate_false_positive_rate(self, baseline: float, volatility: float) -> float:
        """Calculate false positive rate for given baseline and volatility."""
        try:
            # False positive rate increases with volatility
            base_fpr = 0.05  # 5% base false positive rate
            volatility_adjustment = 1 + (volatility * 2)  # Double the volatility impact

            false_positive_rate = min(0.5, base_fpr * volatility_adjustment)  # Cap at 50%

            return false_positive_rate

        except Exception as e:
            self.logger.error(f"Error calculating false positive rate: {e}")
            return 0.05


class FalsePositiveEstimator:
    """
    False Positive Estimator for Historical Backtesting

    Implements historical backtesting to estimate false positive rates
    under different market conditions and volatility regimes.

    Economic Interpretation: Provides realistic estimates of false positive
    rates to inform operational decision-making and risk management.
    """

    def __init__(self, backtest_periods: int = 12, confidence_level: float = 0.95):
        """
        Initialize false positive estimator.

        Args:
            backtest_periods: Number of historical periods for backtesting
            confidence_level: Confidence level for estimates
        """
        self.backtest_periods = backtest_periods
        self.confidence_level = confidence_level
        self.logger = logging.getLogger(__name__)

    def estimate_false_positive_rate(
        self, historical_data: pd.DataFrame, volatility_regime: str
    ) -> Dict:
        """
        Estimate false positive rate using historical backtesting.

        Args:
            historical_data: Historical similarity data with volatility measures
            volatility_regime: Current volatility regime

        Returns:
            Dictionary with false positive rate estimates
        """
        try:
            # Filter data for current volatility regime
            regime_data = historical_data[historical_data["volatility_regime"] == volatility_regime]

            if len(regime_data) < 100:
                # Use all data if regime-specific data is insufficient
                regime_data = historical_data

            # Calculate false positive rate
            false_positive_rate = self._calculate_historical_fpr(regime_data)

            # Calculate confidence interval
            confidence_interval = self._calculate_fpr_confidence_interval(
                regime_data, false_positive_rate
            )

            # Calculate volatility sensitivity
            volatility_sensitivity = self._calculate_volatility_sensitivity(regime_data)

            return {
                "false_positive_rate": false_positive_rate,
                "confidence_interval": confidence_interval,
                "volatility_sensitivity": volatility_sensitivity,
                "sample_size": len(regime_data),
                "volatility_regime": volatility_regime,
                "analysis_date": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error estimating false positive rate: {e}")
            return {"false_positive_rate": 0.18, "error": str(e)}

    def _calculate_historical_fpr(self, data: pd.DataFrame) -> float:
        """Calculate historical false positive rate."""
        try:
            # Simulate detection under null hypothesis (no coordination)
            # by analyzing periods with low similarity
            low_similarity_data = data[data["similarity"] < data["similarity"].quantile(0.3)]

            if len(low_similarity_data) < 10:
                return 0.18  # Default estimate

            # Calculate false positive rate as proportion of low-similarity
            # periods that would trigger detection
            detection_threshold = data["similarity"].quantile(0.8)
            false_positives = len(
                low_similarity_data[low_similarity_data["similarity"] > detection_threshold]
            )

            false_positive_rate = false_positives / len(low_similarity_data)

            return false_positive_rate

        except Exception as e:
            self.logger.error(f"Error calculating historical FPR: {e}")
            return 0.18

    def _calculate_fpr_confidence_interval(
        self, data: pd.DataFrame, fpr: float
    ) -> Tuple[float, float]:
        """Calculate confidence interval for false positive rate."""
        try:
            n = len(data)

            # Use binomial confidence interval
            alpha = 1 - self.confidence_level
            z_score = stats.norm.ppf(1 - alpha / 2)

            margin_of_error = z_score * np.sqrt((fpr * (1 - fpr)) / n)

            lower_bound = max(0.0, fpr - margin_of_error)
            upper_bound = min(1.0, fpr + margin_of_error)

            return (lower_bound, upper_bound)

        except Exception as e:
            self.logger.error(f"Error calculating FPR confidence interval: {e}")
            return (fpr - 0.05, fpr + 0.05)

    def _calculate_volatility_sensitivity(self, data: pd.DataFrame) -> float:
        """Calculate sensitivity of false positive rate to volatility changes."""
        try:
            # Calculate correlation between volatility and false positive rate
            volatility = data["volatility"]
            similarity = data["similarity"]

            # Calculate false positive rate for different volatility levels
            low_vol_data = data[data["volatility"] < data["volatility"].quantile(0.33)]
            high_vol_data = data[data["volatility"] > data["volatility"].quantile(0.67)]

            low_vol_fpr = self._calculate_historical_fpr(low_vol_data)
            high_vol_fpr = self._calculate_historical_fpr(high_vol_data)

            # Calculate sensitivity as change in FPR per unit change in volatility
            volatility_sensitivity = (high_vol_fpr - low_vol_fpr) / (
                high_vol_data["volatility"].mean() - low_vol_data["volatility"].mean()
            )

            return volatility_sensitivity

        except Exception as e:
            self.logger.error(f"Error calculating volatility sensitivity: {e}")
            return 0.0


class PowerAnalysisFramework:
    """
    Main framework for power analysis following v1.4 standards.

    Orchestrates all power analysis components and provides
    comprehensive power analysis for coordination detection.
    """

    def __init__(self):
        """Initialize power analysis framework."""
        self.power_calculator = PowerAnalysisCalculator()
        self.fpr_estimator = FalsePositiveEstimator()
        self.logger = logging.getLogger(__name__)

    def conduct_comprehensive_power_analysis(
        self,
        sample_size: int,
        baseline_similarity: float,
        volatility: float,
        market_regime: str,
        historical_data: Optional[pd.DataFrame] = None,
    ) -> PowerAnalysisResult:
        """
        Conduct comprehensive power analysis for coordination detection.

        Args:
            sample_size: Number of observations
            baseline_similarity: Baseline similarity level
            volatility: Market volatility measure
            market_regime: Current market regime
            historical_data: Optional historical data for FPR estimation

        Returns:
            PowerAnalysisResult with comprehensive analysis
        """
        try:
            # Calculate minimum detectable effect
            min_detectable_effect = self.power_calculator.calculate_minimum_detectable_effect(
                sample_size, baseline_similarity, volatility
            )

            # Calculate statistical power
            statistical_power = self.power_calculator.calculate_statistical_power(
                min_detectable_effect, sample_size, baseline_similarity, volatility
            )

            # Calculate required sample size
            required_sample_size = self.power_calculator.calculate_required_sample_size(
                min_detectable_effect, baseline_similarity, volatility
            )

            # Calculate detection threshold
            detection_threshold = baseline_similarity + min_detectable_effect

            # Estimate false positive rate
            if historical_data is not None:
                fpr_estimate = self.fpr_estimator.estimate_false_positive_rate(
                    historical_data, market_regime
                )
                false_positive_rate = fpr_estimate["false_positive_rate"]
            else:
                false_positive_rate = 0.18  # Default estimate

            return PowerAnalysisResult(
                minimum_detectable_effect=min_detectable_effect,
                statistical_power=statistical_power,
                required_sample_size=required_sample_size,
                significance_level=self.power_calculator.significance_level,
                effect_size=min_detectable_effect,
                market_regime=market_regime,
                detection_threshold=detection_threshold,
                false_positive_rate=false_positive_rate,
                analysis_date=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Error in comprehensive power analysis: {e}")
            raise


# Example usage and testing
if __name__ == "__main__":
    # Create sample data for testing
    np.random.seed(42)

    # Test power analysis framework
    framework = PowerAnalysisFramework()

    # Test parameters
    sample_size = 1000
    baseline_similarity = 0.44
    volatility = 0.15
    market_regime = "Normal"

    # Create sample historical data
    n_historical = 500
    historical_data = pd.DataFrame(
        {
            "similarity": np.random.beta(2, 5, n_historical),  # Beta distribution for similarity
            "volatility": np.random.gamma(
                2, 0.1, n_historical
            ),  # Gamma distribution for volatility
            "volatility_regime": np.random.choice(["Low", "Normal", "High"], n_historical),
        }
    )

    # Conduct comprehensive power analysis
    power_result = framework.conduct_comprehensive_power_analysis(
        sample_size=sample_size,
        baseline_similarity=baseline_similarity,
        volatility=volatility,
        market_regime=market_regime,
        historical_data=historical_data,
    )

    print("Power Analysis Results:")
    print(f"Minimum Detectable Effect: {power_result.minimum_detectable_effect:.3f}")
    print(f"Statistical Power: {power_result.statistical_power:.3f}")
    print(f"Required Sample Size: {power_result.required_sample_size}")
    print(f"Detection Threshold: {power_result.detection_threshold:.3f}")
    print(f"False Positive Rate: {power_result.false_positive_rate:.3f}")
    print(f"Market Regime: {power_result.market_regime}")

    # Test detection sensitivity analysis
    market_regimes = ["Low Volatility", "Normal", "High Volatility"]
    baseline_similarities = [0.38, 0.44, 0.52]
    volatilities = [0.08, 0.15, 0.25]

    sensitivities = framework.power_calculator.analyze_detection_sensitivity(
        market_regimes, baseline_similarities, volatilities
    )

    print("\nDetection Sensitivity by Market Regime:")
    for sensitivity in sensitivities:
        print(f"{sensitivity.market_regime}:")
        print(f"  Baseline Similarity: {sensitivity.baseline_similarity:.3f}")
        print(f"  Detection Threshold: {sensitivity.detection_threshold:.3f}")
        print(f"  False Positive Rate: {sensitivity.false_positive_rate:.3f}")
        print(f"  Minimum Effect Size: {sensitivity.minimum_effect_size:.3f}")

