"""
Phase 1 Integration Tests

Tests for the integrated ACD engine with ICP, VMM, and crypto moments.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig
from src.acd.icp.engine import ICPEngine, ICPConfig
from src.acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from src.acd.analytics.integrated_engine import IntegratedACDEngine, IntegratedConfig


class TestPhase1Integration:
    """Test Phase 1 integrated engine functionality"""

    @pytest.fixture
    def synthetic_data(self):
        """Generate synthetic competitive and coordinated data"""
        config = CryptoMarketConfig(n_timepoints=1000, n_exchanges=3)
        generator = SyntheticCryptoGenerator(config)

        competitive_data = generator.generate_competitive_scenario()
        coordinated_data = generator.generate_coordinated_scenario()

        return competitive_data, coordinated_data

    @pytest.fixture
    def integrated_config(self):
        """Create integrated configuration"""
        return IntegratedConfig(
            icp_config=ICPConfig(
                significance_level=0.05, power_threshold=0.8, min_samples_per_env=100
            ),
            vmm_config=VMMConfig(),  # Use default VMM config
            crypto_moments_config=CryptoMomentConfig(max_lag=5, mirroring_window=3),
        )

    def test_synthetic_data_generation(self, synthetic_data):
        """Test synthetic data generation"""
        competitive_data, coordinated_data = synthetic_data

        # Check data structure
        assert len(competitive_data) > 0
        assert len(coordinated_data) > 0

        # Check columns
        price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]
        assert len(price_cols) >= 2

        # Check environment columns
        assert "volatility_regime" in competitive_data.columns
        assert "market_condition" in competitive_data.columns

        # Check scenario types
        assert competitive_data["scenario_type"].iloc[0] == "competitive"
        assert coordinated_data["scenario_type"].iloc[0] == "coordinated"

    def test_icp_engine_functionality(self, synthetic_data):
        """Test ICP engine basic functionality"""
        competitive_data, coordinated_data = synthetic_data

        price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        # Test ICP on competitive data
        icp_config = ICPConfig(min_samples_per_env=50)
        icp_engine = ICPEngine(icp_config)

        result_competitive = icp_engine.analyze_invariance(competitive_data, price_cols)

        # Check result structure
        assert hasattr(result_competitive, "test_statistic")
        assert hasattr(result_competitive, "p_value")
        assert hasattr(result_competitive, "reject_h0")
        assert hasattr(result_competitive, "effect_size")
        assert hasattr(result_competitive, "power")

        # Check reasonable values
        assert 0 <= result_competitive.p_value <= 1
        assert result_competitive.effect_size >= 0
        assert 0 <= result_competitive.power <= 1

    def test_crypto_moments_calculation(self, synthetic_data):
        """Test crypto moments calculation"""
        competitive_data, coordinated_data = synthetic_data

        price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        # Test crypto moments on competitive data
        crypto_config = CryptoMomentConfig(max_lag=3)
        crypto_calculator = CryptoMomentCalculator(crypto_config)

        moments_competitive = crypto_calculator.calculate_moments(competitive_data, price_cols)

        # Check moment structure
        assert hasattr(moments_competitive, "lead_lag_betas")
        assert hasattr(moments_competitive, "mirroring_ratios")
        assert hasattr(moments_competitive, "spread_floor_dwell_times")
        assert hasattr(moments_competitive, "undercut_initiation_rate")

        # Check reasonable shapes
        n_exchanges = len(price_cols)
        assert moments_competitive.lead_lag_betas.shape == (
            n_exchanges,
            n_exchanges,
            crypto_config.max_lag,
        )
        assert moments_competitive.mirroring_ratios.shape == (n_exchanges, n_exchanges)
        assert moments_competitive.spread_floor_dwell_times.shape == (n_exchanges,)

    def test_integrated_engine_analysis(self, synthetic_data, integrated_config):
        """Test integrated engine analysis"""
        competitive_data, coordinated_data = synthetic_data

        price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        # Test integrated analysis
        integrated_engine = IntegratedACDEngine(integrated_config)

        result_competitive = integrated_engine.analyze_coordination_risk(
            competitive_data, price_cols
        )

        # Check result structure
        assert hasattr(result_competitive, "composite_risk_score")
        assert hasattr(result_competitive, "risk_classification")
        assert hasattr(result_competitive, "confidence_level")
        assert hasattr(result_competitive, "coordination_indicators")
        assert hasattr(result_competitive, "alternative_explanations")

        # Check risk classification
        assert result_competitive.risk_classification in ["LOW", "AMBER", "RED"]

        # Check reasonable values
        assert 0 <= result_competitive.composite_risk_score <= 100
        assert 0 <= result_competitive.confidence_level <= 1

        # Check coordination indicators
        assert isinstance(result_competitive.coordination_indicators, dict)
        assert len(result_competitive.coordination_indicators) > 0

    def test_competitive_vs_coordinated_distinction(self, synthetic_data, integrated_config):
        """Test that engine can distinguish competitive vs coordinated scenarios"""
        competitive_data, coordinated_data = synthetic_data

        price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        integrated_engine = IntegratedACDEngine(integrated_config)

        # Analyze both scenarios
        result_competitive = integrated_engine.analyze_coordination_risk(
            competitive_data, price_cols
        )

        result_coordinated = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_cols
        )

        # Coordinated scenario should show higher risk
        assert result_coordinated.composite_risk_score >= result_competitive.composite_risk_score

        # Check that we can distinguish the scenarios
        print(f"Competitive risk score: {result_competitive.composite_risk_score:.2f}")
        print(f"Coordinated risk score: {result_coordinated.composite_risk_score:.2f}")
        print(f"Competitive classification: {result_competitive.risk_classification}")
        print(f"Coordinated classification: {result_coordinated.risk_classification}")

    def test_diagnostic_report_generation(self, synthetic_data, integrated_config):
        """Test diagnostic report generation"""
        competitive_data, coordinated_data = synthetic_data

        price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        integrated_engine = IntegratedACDEngine(integrated_config)

        result = integrated_engine.analyze_coordination_risk(competitive_data, price_cols)
        report = integrated_engine.generate_diagnostic_report(result)

        # Check report structure
        assert "summary" in report
        assert "icp_analysis" in report
        assert "vmm_analysis" in report
        assert "crypto_moments" in report
        assert "alternative_explanations" in report
        assert "recommendations" in report

        # Check summary fields
        summary = report["summary"]
        assert "risk_classification" in summary
        assert "composite_score" in summary
        assert "confidence_level" in summary
        assert "analysis_timestamp" in summary

    def test_error_handling(self, integrated_config):
        """Test error handling for invalid inputs"""
        integrated_engine = IntegratedACDEngine(integrated_config)

        # Test with insufficient data
        small_data = pd.DataFrame({"Exchange_0": [100, 101, 102], "Exchange_1": [100, 101, 102]})

        with pytest.raises(ValueError):
            integrated_engine.analyze_coordination_risk(small_data, ["Exchange_0", "Exchange_1"])

        # Test with missing columns
        data = pd.DataFrame(
            {"Exchange_0": np.random.randn(1000), "Exchange_1": np.random.randn(1000)}
        )

        with pytest.raises(ValueError):
            integrated_engine.analyze_coordination_risk(data, ["Exchange_0", "Missing_Exchange"])


if __name__ == "__main__":
    # Run basic functionality test
    import sys

    sys.path.append("/Users/ygorfrancisco/Desktop/acd-monitor/src")

    # Generate test data
    config = CryptoMarketConfig(n_timepoints=1000, n_exchanges=3)
    generator = SyntheticCryptoGenerator(config)

    competitive_data = generator.generate_competitive_scenario()
    coordinated_data = generator.generate_coordinated_scenario()

    print("Generated synthetic data:")
    print(f"Competitive data shape: {competitive_data.shape}")
    print(f"Coordinated data shape: {coordinated_data.shape}")

    # Test integrated analysis
    integrated_config = IntegratedConfig(
        icp_config=ICPConfig(min_samples_per_env=50),
        vmm_config=VMMConfig(),
        crypto_moments_config=CryptoMomentConfig(max_lag=3),
    )

    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]

    integrated_engine = IntegratedACDEngine(integrated_config)

    print("\nRunning integrated analysis...")
    result_competitive = integrated_engine.analyze_coordination_risk(competitive_data, price_cols)
    result_coordinated = integrated_engine.analyze_coordination_risk(coordinated_data, price_cols)

    print(f"\nCompetitive scenario:")
    print(f"  Risk classification: {result_competitive.risk_classification}")
    print(f"  Composite score: {result_competitive.composite_risk_score:.2f}")
    print(f"  Confidence: {result_competitive.confidence_level:.2f}")

    print(f"\nCoordinated scenario:")
    print(f"  Risk classification: {result_coordinated.risk_classification}")
    print(f"  Composite score: {result_coordinated.composite_risk_score:.2f}")
    print(f"  Confidence: {result_coordinated.confidence_level:.2f}")

    print(
        f"\nDistinction achieved: {result_coordinated.composite_risk_score > result_competitive.composite_risk_score}"
    )
