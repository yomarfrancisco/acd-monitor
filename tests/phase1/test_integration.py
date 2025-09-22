"""
Integration tests for ACD Engine

Tests end-to-end pipeline with competitive vs coordinated scenarios
for court/regulator-ready coordination risk analytics.
"""

from src.acd.analytics.integrated_engine import IntegratedACDEngine, IntegratedConfig
from src.acd.icp.engine import ICPConfig
from src.acd.vmm.engine import VMMConfig
from src.acd.vmm.crypto_moments import CryptoMomentConfig
from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig


class TestIntegration:
    """Test suite for integrated ACD analysis"""

    @pytest.fixture
    def integrated_engine(self):
        """Create integrated ACD engine for testing"""
        icp_config = ICPConfig()
        vmm_config = VMMConfig()
        crypto_config = CryptoMomentConfig()
        integrated_config = IntegratedConfig(icp_config, vmm_config, crypto_config)
        return IntegratedACDEngine(integrated_config)

    @pytest.fixture
    def competitive_data(self):
        """Generate competitive synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)
        return generator.generate_competitive_scenario()

    @pytest.fixture
    def coordinated_data(self):
        """Generate coordinated synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)
        return generator.generate_coordinated_scenario()

    def test_labels_end_to_end(self, integrated_engine, competitive_data, coordinated_data):
        """Test that competitive→LOW and coordinated→RED with seed=42"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Test competitive scenario
        competitive_result = integrated_engine.analyze_coordination_risk(
            competitive_data, price_columns
        )

        # Test coordinated scenario
        coordinated_result = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_columns
        )

        # Competitive should be LOW (≤33)
        assert (
            competitive_result.risk_classification == "LOW"
        ), f"Competitive should be LOW, got {competitive_result.risk_classification}"
        assert (
            competitive_result.composite_risk_score <= 33.0
        ), f"Competitive score should be ≤33, got {competitive_result.composite_risk_score}"

        # Coordinated should be RED (≥67)
        assert (
            coordinated_result.risk_classification == "RED"
        ), f"Coordinated should be RED, got {coordinated_result.risk_classification}"
        assert (
            coordinated_result.composite_risk_score >= 67.0
        ), f"Coordinated score should be ≥67, got {coordinated_result.composite_risk_score}"

        print(
            f"Competitive: {competitive_result.composite_risk_score:.2f} → {competitive_result.risk_classification}"  # noqa: E501
        )
        print(
            f"Coordinated: {coordinated_result.composite_risk_score:.2f} → {coordinated_result.risk_classification}"  # noqa: E501
        )

    def test_report_fields(self, integrated_engine, competitive_data):
        """Test that all required report fields are present and finite"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        result = integrated_engine.analyze_coordination_risk(competitive_data, price_columns)

        # Check ICP fields
        assert hasattr(result, "icp_result"), "Result should have ICP analysis"
        assert np.isfinite(result.icp_result.p_value), "ICP p-value should be finite"
        assert 0.0 <= result.icp_result.p_value <= 1.0, "ICP p-value should be in [0,1]"
        assert hasattr(result.icp_result, "power"), "ICP result should have power"
        assert np.isfinite(result.icp_result.power), "ICP power should be finite"

        # Check VMM fields
        assert hasattr(result, "vmm_result"), "Result should have VMM analysis"
        assert np.isfinite(
            result.vmm_result.over_identification_stat
        ), "VMM over-ID stat should be finite"
        assert np.isfinite(
            result.vmm_result.over_identification_p_value
        ), "VMM over-ID p-value should be finite"
        assert (
            0.0 <= result.vmm_result.over_identification_p_value <= 1.0
        ), "VMM over-ID p-value should be in [0,1]"
        assert np.isfinite(result.vmm_result.structural_stability), "VMM stability should be finite"
        assert (
            0.0 <= result.vmm_result.structural_stability <= 1.0
        ), "VMM stability should be in [0,1]"

        # Check crypto moments
        assert hasattr(result, "crypto_moments"), "Result should have crypto moments"

        # Check composite score
        assert np.isfinite(result.composite_risk_score), "Composite score should be finite"
        assert 0.0 <= result.composite_risk_score <= 100.0, "Composite score should be in [0,100]"

        # Check risk classification
        assert result.risk_classification in [
            "LOW",
            "AMBER",
            "RED",
        ], f"Invalid risk classification: {result.risk_classification}"

        # Check diagnostics
        assert hasattr(result, "diagnostics"), "Result should have diagnostics"
        assert isinstance(result.diagnostics, dict), "Diagnostics should be a dictionary"

        print("All report fields present and finite ✓")

    def test_icp_analysis_integration(self, integrated_engine, competitive_data, coordinated_data):
        """Test ICP analysis integration"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Test competitive scenario
        competitive_result = integrated_engine.analyze_coordination_risk(
            competitive_data, price_columns
        )

        # Test coordinated scenario
        coordinated_result = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_columns
        )

        # Competitive should not reject H0 (maintain invariance)
        assert not competitive_result.icp_result.reject_h0, "Competitive should maintain invariance"

        # Coordinated should reject H0 (reject invariance)
        assert coordinated_result.icp_result.reject_h0, "Coordinated should reject invariance"

        # P-values should be different
        assert (
            competitive_result.icp_result.p_value > coordinated_result.icp_result.p_value
        ), "Competitive p-value should be higher than coordinated"

        print("ICP Analysis:")
        print(
            f"  Competitive: p={competitive_result.icp_result.p_value:.6f}, reject_H0={competitive_result.icp_result.reject_h0}"  # noqa: E501
        )
        print(
            f"  Coordinated: p={coordinated_result.icp_result.p_value:.6f}, reject_H0={coordinated_result.icp_result.reject_h0}"  # noqa: E501
        )

    def test_vmm_analysis_integration(self, integrated_engine, competitive_data, coordinated_data):
        """Test VMM analysis integration"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Test competitive scenario
        competitive_result = integrated_engine.analyze_coordination_risk(
            competitive_data, price_columns
        )

        # Test coordinated scenario
        coordinated_result = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_columns
        )

        # Both should have finite VMM results
        assert np.isfinite(
            competitive_result.vmm_result.structural_stability
        ), "Competitive VMM stability should be finite"
        assert np.isfinite(
            coordinated_result.vmm_result.structural_stability
        ), "Coordinated VMM stability should be finite"

        # Both should have bounded stability
        assert (
            0.0 <= competitive_result.vmm_result.structural_stability <= 1.0
        ), "Competitive stability should be bounded"
        assert (
            0.0 <= coordinated_result.vmm_result.structural_stability <= 1.0
        ), "Coordinated stability should be bounded"

        print("VMM Analysis:")
        print("  Competitive: stability={competitive_result.vmm_result.structural_stability:.6f}")
        print("  Coordinated: stability={coordinated_result.vmm_result.structural_stability:.6f}")

    def test_crypto_moments_integration(self, integrated_engine, competitive_data):
        """Test crypto moments integration"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        result = integrated_engine.analyze_coordination_risk(competitive_data, price_columns)

        # Check crypto moments structure
        assert hasattr(result.crypto_moments, "lead_lag_betas"), "Should have lead-lag betas"
        assert hasattr(result.crypto_moments, "mirroring_ratios"), "Should have mirroring ratios"
        assert hasattr(
            result.crypto_moments, "spread_floor_frequency"
        ), "Should have spread floor frequency"
        assert hasattr(
            result.crypto_moments, "undercut_initiation_rate"
        ), "Should have undercut initiation rate"

        # Check that moments are finite
        assert np.all(
            np.isfinite(result.crypto_moments.lead_lag_betas)
        ), "Lead-lag betas should be finite"
        assert np.all(
            np.isfinite(result.crypto_moments.mirroring_ratios)
        ), "Mirroring ratios should be finite"
        assert np.all(
            np.isfinite(result.crypto_moments.spread_floor_frequency)
        ), "Spread floor frequency should be finite"
        assert np.all(
            np.isfinite(result.crypto_moments.undercut_initiation_rate)
        ), "Undercut initiation rate should be finite"

        print("Crypto moments integration ✓")

    def test_composite_score_calculation(
        self, integrated_engine, competitive_data, coordinated_data
    ):
        """Test composite score calculation"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Test competitive scenario
        competitive_result = integrated_engine.analyze_coordination_risk(
            competitive_data, price_columns
        )

        # Test coordinated scenario
        coordinated_result = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_columns
        )

        # Composite scores should be different
        assert (
            competitive_result.composite_risk_score != coordinated_result.composite_risk_score
        ), "Composite scores should be different"

        # Competitive should have lower score
        assert (
            competitive_result.composite_risk_score < coordinated_result.composite_risk_score
        ), "Competitive should have lower composite score"

        # Both should be bounded
        assert (
            0.0 <= competitive_result.composite_risk_score <= 100.0
        ), "Competitive score should be bounded"
        assert (
            0.0 <= coordinated_result.composite_risk_score <= 100.0
        ), "Coordinated score should be bounded"

        print("Composite Score Calculation:")
        print("  Competitive: {competitive_result.composite_risk_score:.2f}")
        print("  Coordinated: {coordinated_result.composite_risk_score:.2f}")

    def test_risk_classification_logic(self, integrated_engine, competitive_data, coordinated_data):
        """Test risk classification logic"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Test competitive scenario
        competitive_result = integrated_engine.analyze_coordination_risk(
            competitive_data, price_columns
        )

        # Test coordinated scenario
        coordinated_result = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_columns
        )

        # Risk classifications should be different
        assert (
            competitive_result.risk_classification != coordinated_result.risk_classification
        ), "Risk classifications should be different"

        # Check classification logic
        if competitive_result.composite_risk_score <= 33.0:
            assert competitive_result.risk_classification == "LOW", "Score ≤33 should be LOW"
        elif competitive_result.composite_risk_score <= 66.0:
            assert competitive_result.risk_classification == "AMBER", "Score 34-66 should be AMBER"
        else:
            assert competitive_result.risk_classification == "RED", "Score ≥67 should be RED"

        if coordinated_result.composite_risk_score <= 33.0:
            assert coordinated_result.risk_classification == "LOW", "Score ≤33 should be LOW"
        elif coordinated_result.composite_risk_score <= 66.0:
            assert coordinated_result.risk_classification == "AMBER", "Score 34-66 should be AMBER"
        else:
            assert coordinated_result.risk_classification == "RED", "Score ≥67 should be RED"

        print("Risk Classification Logic:")
        print(
            f"  Competitive: {competitive_result.composite_risk_score:.2f} → {competitive_result.risk_classification}"  # noqa: E501
        )
        print(
            f"  Coordinated: {coordinated_result.composite_risk_score:.2f} → {coordinated_result.risk_classification}"  # noqa: E501
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
