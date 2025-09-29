"""
Integrated ACD Analytics Engine

Combines ICP and VMM engines with crypto-specific moment conditions
to provide comprehensive coordination risk analysis.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..icp.engine import ICPConfig, ICPEngine, ICPResult
from ..vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig, CryptoMoments
from ..vmm.engine import VMMConfig, VMMEngine, VMMOutput

logger = logging.getLogger(__name__)


@dataclass
class IntegratedConfig:
    """Configuration for integrated ACD analysis"""

    # ICP configuration
    icp_config: ICPConfig

    # VMM configuration
    vmm_config: VMMConfig

    # Crypto moments configuration
    crypto_moments_config: CryptoMomentConfig

    # Risk classification thresholds
    low_threshold: float = 33.0
    amber_threshold: float = 66.0

    # Composite scoring weights (adjusted for Phase 1 - ICP is working, VMM is placeholder)
    icp_weight: float = 0.4  # Restored to target weights
    vmm_weight: float = 0.4  # Restored to target weights
    crypto_moments_weight: float = 0.2


@dataclass
class IntegratedResult:
    """Results from integrated ACD analysis"""

    # Individual engine results
    icp_result: ICPResult
    vmm_result: VMMOutput
    crypto_moments: CryptoMoments

    # Composite risk assessment
    composite_risk_score: float
    risk_classification: str  # LOW, AMBER, RED
    confidence_level: float

    # Diagnostic information
    coordination_indicators: Dict[str, float]
    alternative_explanations: List[str]

    # Metadata
    analysis_timestamp: pd.Timestamp
    data_quality_score: float


class IntegratedACDEngine:
    """
    Integrated ACD Analytics Engine

    Combines ICP, VMM, and crypto-specific moment analysis to provide
    comprehensive coordination risk assessment for crypto markets.
    """

    def __init__(self, config: IntegratedConfig):
        self.config = config

        # Initialize engines
        self.icp_engine = ICPEngine(config.icp_config)
        self.vmm_engine = VMMEngine(config.vmm_config)
        self.crypto_calculator = CryptoMomentCalculator(config.crypto_moments_config)

    def analyze_coordination_risk(
        self,
        data: pd.DataFrame,
        price_columns: List[str],
        environment_columns: Optional[List[str]] = None,
    ) -> IntegratedResult:
        """
        Main analysis method for coordination risk assessment

        Args:
            data: DataFrame with price and environment data
            price_columns: List of price column names
            environment_columns: Optional list of environment column names

        Returns:
            IntegratedResult with comprehensive risk assessment
        """
        logger.info("Starting integrated ACD coordination risk analysis")

        # Validate input
        self._validate_input(data, price_columns)

        # Run ICP analysis
        logger.info("Running ICP analysis")
        icp_result = self.icp_engine.analyze_invariance(data, price_columns, environment_columns)

        # Run VMM analysis
        logger.info("Running VMM analysis")
        vmm_result = self.vmm_engine.run_vmm(data, price_columns)

        # Calculate crypto moments
        logger.info("Calculating crypto moments")
        crypto_moments = self.crypto_calculator.calculate_moments(data, price_columns)

        # Calculate composite risk score
        composite_score = self._calculate_composite_risk_score(
            icp_result, vmm_result, crypto_moments
        )

        # Determine risk classification
        risk_classification = self._classify_risk(composite_score)

        # Calculate confidence level
        confidence_level = self._calculate_confidence_level(icp_result, vmm_result, crypto_moments)

        # Identify coordination indicators
        coordination_indicators = self._identify_coordination_indicators(
            icp_result, vmm_result, crypto_moments
        )

        # Generate alternative explanations
        alternative_explanations = self._generate_alternative_explanations(
            coordination_indicators, data, price_columns
        )

        # Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(data, price_columns)

        return IntegratedResult(
            icp_result=icp_result,
            vmm_result=vmm_result,
            crypto_moments=crypto_moments,
            composite_risk_score=composite_score,
            risk_classification=risk_classification,
            confidence_level=confidence_level,
            coordination_indicators=coordination_indicators,
            alternative_explanations=alternative_explanations,
            analysis_timestamp=pd.Timestamp.now(),
            data_quality_score=data_quality_score,
        )

    def _validate_input(self, data: pd.DataFrame, price_columns: List[str]) -> None:
        """Validate input data"""
        if len(price_columns) < 2:
            raise ValueError("Need at least 2 price columns for analysis")

        missing_cols = [col for col in price_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing price columns: {missing_cols}")

        if len(data) < 100:
            raise ValueError("Insufficient data for analysis")

    def _calculate_composite_risk_score(
        self, icp_result: ICPResult, vmm_result: VMMOutput, crypto_moments: CryptoMoments
    ) -> float:
        """Calculate composite risk score from all engines"""

        # ICP contribution (invariance rejection = higher risk)
        icp_contribution = 100.0 if icp_result.reject_h0 else 0.0

        # VMM contribution (structural stability = higher risk)
        # Cap VMM contribution to prevent overflow from placeholder values
        vmm_contribution = min(100.0, vmm_result.structural_stability * 100.0)

        # Crypto moments contribution
        crypto_summary = self.crypto_calculator.get_moment_summary(crypto_moments)
        crypto_contribution = (
            crypto_summary.get("max_lead_lag_beta", 0.0) * 30.0
            + crypto_summary.get("max_mirroring_ratio", 0.0) * 30.0
            + crypto_summary.get("avg_spread_frequency", 0.0) * 20.0
            + crypto_summary.get("avg_undercut_rate", 0.0) * 20.0
        )

        # Weighted composite score
        composite_score = (
            self.config.icp_weight * icp_contribution
            + self.config.vmm_weight * vmm_contribution
            + self.config.crypto_moments_weight * crypto_contribution
        )

        return min(100.0, max(0.0, composite_score))

    def _classify_risk(self, composite_score: float) -> str:
        """Classify risk level based on composite score"""
        if composite_score <= self.config.low_threshold:
            return "LOW"
        elif composite_score <= self.config.amber_threshold:
            return "AMBER"
        else:
            return "RED"

    def _calculate_confidence_level(
        self, icp_result: ICPResult, vmm_result: VMMOutput, crypto_moments: CryptoMoments
    ) -> float:
        """Calculate overall confidence level"""

        # ICP confidence (based on power and sample size)
        icp_confidence = min(1.0, icp_result.power)

        # VMM confidence (based on convergence)
        vmm_confidence = 1.0 if vmm_result.convergence_status == "converged" else 0.5

        # Crypto moments confidence (based on data quality)
        crypto_confidence = 0.8  # Placeholder

        # Weighted average
        confidence = (
            self.config.icp_weight * icp_confidence
            + self.config.vmm_weight * vmm_confidence
            + self.config.crypto_moments_weight * crypto_confidence
        )

        return confidence

    def _identify_coordination_indicators(
        self, icp_result: ICPResult, vmm_result: VMMOutput, crypto_moments: CryptoMoments
    ) -> Dict[str, float]:
        """Identify specific coordination indicators"""

        indicators = {}

        # ICP indicators
        indicators["environment_invariance"] = 1.0 if icp_result.reject_h0 else 0.0
        indicators["invariance_strength"] = icp_result.effect_size

        # VMM indicators
        indicators["structural_stability"] = vmm_result.structural_stability
        indicators["regime_confidence"] = vmm_result.regime_confidence

        # Crypto moments indicators
        crypto_summary = self.crypto_calculator.get_moment_summary(crypto_moments)
        indicators["lead_lag_strength"] = crypto_summary.get("max_lead_lag_beta", 0.0)
        indicators["mirroring_strength"] = crypto_summary.get("max_mirroring_ratio", 0.0)
        indicators["spread_floor_persistence"] = crypto_summary.get("avg_spread_dwell_time", 0.0)
        indicators["undercut_coordination"] = crypto_summary.get("avg_undercut_rate", 0.0)

        return indicators

    def _generate_alternative_explanations(
        self,
        coordination_indicators: Dict[str, float],
        data: pd.DataFrame,
        price_columns: List[str],
    ) -> List[str]:
        """Generate alternative explanations for observed patterns"""

        explanations = []

        # Check for arbitrage constraints
        if coordination_indicators.get("mirroring_strength", 0.0) > 0.7:
            explanations.append(
                "High mirroring may reflect arbitrage constraints rather than coordination"
            )

        # Check for market structure effects
        if coordination_indicators.get("lead_lag_strength", 0.0) > 0.5:
            explanations.append(
                "Lead-lag patterns may reflect natural market structure and information flow"
            )

        # Check for liquidity effects
        if coordination_indicators.get("spread_floor_persistence", 0.0) > 5.0:
            explanations.append(
                "Spread floors may reflect liquidity constraints and inventory management"
            )

        # Check for volatility effects
        price_volatility = np.std([data[col].pct_change().std() for col in price_columns])
        if price_volatility > 0.05:
            explanations.append("High volatility may create spurious coordination patterns")

        # Check for data quality issues
        if coordination_indicators.get("environment_invariance", 0.0) > 0.8:
            explanations.append(
                "Environment invariance may reflect insufficient environmental variation in data"
            )

        return explanations

    def _calculate_data_quality_score(self, data: pd.DataFrame, price_columns: List[str]) -> float:
        """Calculate data quality score"""

        quality_factors = []

        # Completeness
        completeness = 1.0 - (
            data[price_columns].isnull().sum().sum() / (len(data) * len(price_columns))
        )
        quality_factors.append(completeness)

        # Consistency (no extreme outliers)
        for col in price_columns:
            prices = data[col].dropna()
            if len(prices) > 0:
                q99 = prices.quantile(0.99)
                q01 = prices.quantile(0.01)
                outlier_rate = ((prices > q99) | (prices < q01)).sum() / len(prices)
                consistency = 1.0 - outlier_rate
                quality_factors.append(consistency)

        # Temporal consistency
        temporal_consistency = 1.0  # Placeholder
        quality_factors.append(temporal_consistency)

        return np.mean(quality_factors) if quality_factors else 0.0

    def generate_diagnostic_report(self, result: IntegratedResult) -> Dict[str, any]:
        """Generate comprehensive diagnostic report"""

        report = {
            "summary": {
                "risk_classification": result.risk_classification,
                "composite_score": result.composite_risk_score,
                "confidence_level": result.confidence_level,
                "analysis_timestamp": result.analysis_timestamp.isoformat(),
                "data_quality_score": result.data_quality_score,
            },
            "icp_analysis": {
                "reject_invariance": result.icp_result.reject_h0,
                "p_value": result.icp_result.p_value,
                "effect_size": result.icp_result.effect_size,
                "power": result.icp_result.power,
                "n_environments": result.icp_result.n_environments,
            },
            "vmm_analysis": {
                "structural_stability": result.vmm_result.structural_stability,
                "regime_confidence": result.vmm_result.regime_confidence,
                "convergence_status": result.vmm_result.convergence_status,
                "iterations": result.vmm_result.iterations,
            },
            "crypto_moments": result.coordination_indicators,
            "alternative_explanations": result.alternative_explanations,
            "recommendations": self._generate_recommendations(result),
        }

        return report

    def _generate_recommendations(self, result: IntegratedResult) -> List[str]:
        """Generate recommendations based on analysis results"""

        recommendations = []

        if result.risk_classification == "RED":
            recommendations.append(
                "Investigation warranted: Multiple coordination indicators detected"
            )
            recommendations.append("Consider regulatory notification and detailed market study")
        elif result.risk_classification == "AMBER":
            recommendations.append(
                "Enhanced monitoring recommended: Borderline coordination patterns detected"
            )
            recommendations.append("Continue surveillance and consider additional data sources")
        else:
            recommendations.append(
                "Routine monitoring sufficient: No significant coordination indicators"
            )
            recommendations.append("Continue standard surveillance protocols")

        if result.confidence_level < 0.7:
            recommendations.append(
                "Low confidence in results: Consider additional data or longer observation period"
            )

        if result.data_quality_score < 0.8:
            recommendations.append(
                "Data quality concerns: Review data sources and validation procedures"
            )

        return recommendations


def run_integrated_analysis(
    data: pd.DataFrame, price_columns: List[str], config: Optional[IntegratedConfig] = None
) -> IntegratedResult:
    """
    Convenience function to run integrated ACD analysis

    Args:
        data: DataFrame with price and environment data
        price_columns: List of price column names
        config: Optional configuration

    Returns:
        IntegratedResult with comprehensive analysis
    """
    if config is None:
        config = IntegratedConfig(
            icp_config=ICPConfig(),
            vmm_config=VMMConfig(),
            crypto_moments_config=CryptoMomentConfig(),
        )

    engine = IntegratedACDEngine(config)
    return engine.analyze_coordination_risk(data, price_columns)


if __name__ == "__main__":
    # Example usage
    from ..data.synthetic_crypto import generate_validation_datasets

    # Generate test data
    competitive_data, coordinated_data = generate_validation_datasets()

    # Run integrated analysis on competitive data
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

    print("Integrated ACD Analysis - Competitive Data:")
    result_competitive = run_integrated_analysis(competitive_data, price_cols)
    print(f"Risk Classification: {result_competitive.risk_classification}")
    print(f"Composite Score: {result_competitive.composite_risk_score:.2f}")
    print(f"Confidence Level: {result_competitive.confidence_level:.2f}")

    print("\nIntegrated ACD Analysis - Coordinated Data:")
    result_coordinated = run_integrated_analysis(coordinated_data, price_cols)
    print(f"Risk Classification: {result_coordinated.risk_classification}")
    print(f"Composite Score: {result_coordinated.composite_risk_score:.2f}")
    print(f"Confidence Level: {result_coordinated.confidence_level:.2f}")
