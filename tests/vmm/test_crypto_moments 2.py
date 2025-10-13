"""
Unit tests for crypto-specific VMM moment conditions
"""

from src.acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from src.acd.vmm.engine import VMMEngine, VMMConfig
from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig


class TestCryptoMoments:
    """Test cases for crypto-specific moment conditions"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return CryptoMomentConfig()

    @pytest.fixture
    def calculator(self, config):
        """Test calculator instance"""
        return CryptoMomentCalculator(config)

    @pytest.fixture
    def competitive_data(self):
        """Generate competitive synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=1000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)
        return generator.generate_competitive_scenario()

    @pytest.fixture
    def coordinated_data(self):
        """Generate coordinated synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=1000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)
        return generator.generate_coordinated_scenario()

    def test_competitive_vs_coordinated_differentiation(
        self, calculator, competitive_data, coordinated_data
    ):
        """Test that competitive and coordinated scenarios produce different moments"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Calculate moments for both scenarios
        competitive_moments = calculator.calculate_moments(competitive_data, price_columns)
        coordinated_moments = calculator.calculate_moments(coordinated_data, price_columns)

        # Test that moments are different
        # Arbitrage timing should be different
        comp_arbitrage = np.mean(competitive_moments.lead_lag_betas)
        coord_arbitrage = np.mean(coordinated_moments.lead_lag_betas)
        assert comp_arbitrage != coord_arbitrage, "Arbitrage timing should differ between scenarios"

        # Mirroring should be different
        comp_mirroring = np.mean(competitive_moments.mirroring_ratios)
        coord_mirroring = np.mean(coordinated_moments.mirroring_ratios)
        assert comp_mirroring != coord_mirroring, "Mirroring ratios should differ between scenarios"

        # Spread floor dwell should be different
        comp_dwell = np.mean(competitive_moments.spread_floor_dwell_times)
        coord_dwell = np.mean(coordinated_moments.spread_floor_dwell_times)
        assert comp_dwell != coord_dwell, "Spread floor dwell should differ between scenarios"

        # Undercut initiation should be different
        comp_undercut = np.mean(competitive_moments.undercut_initiation_rate)
        coord_undercut = np.mean(coordinated_moments.undercut_initiation_rate)
        assert (
            comp_undercut != coord_undercut
        ), "Undercut initiation should differ between scenarios"

    def test_moment_normalization(self, calculator, competitive_data):
        """Test that moments are properly normalized"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]
        moments = calculator.calculate_moments(competitive_data, price_columns)

        # All moments should be finite
        assert np.all(np.isfinite(moments.lead_lag_betas))
        assert np.all(np.isfinite(moments.mirroring_ratios))
        assert np.all(np.isfinite(moments.spread_floor_dwell_times))
        assert np.all(np.isfinite(moments.undercut_initiation_rate))

        # Moments should be in reasonable ranges
        assert np.all(moments.lead_lag_betas >= 0)  # Arbitrage timing normalized to [0,1]
        assert np.all(moments.mirroring_ratios >= 0)  # Mirroring ratios should be non-negative
        assert np.all(moments.spread_floor_dwell_times >= 0)  # Dwell times should be non-negative
        assert np.all(
            moments.undercut_initiation_rate >= 0
        )  # Undercut rates should be non-negative

    def test_environment_invariance_components(self, calculator, competitive_data):
        """Test that environment invariance components are calculated"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]
        moments = calculator.calculate_moments(
            competitive_data, price_columns, environment_column="environment"
        )

        # Environment invariance components should be present
        assert np.all(np.isfinite(moments.lead_lag_significance))  # Arbitrage invariance
        assert np.all(np.isfinite(moments.mirroring_consistency))  # Mirroring invariance
        assert np.all(np.isfinite(moments.spread_floor_frequency))  # Dwell invariance
        assert np.all(np.isfinite(moments.undercut_response_time))  # Undercut invariance

        # Invariance components should be non-negative
        assert np.all(moments.lead_lag_significance >= 0)
        assert np.all(moments.mirroring_consistency >= 0)
        assert np.all(moments.spread_floor_frequency >= 0)
        assert np.all(moments.undercut_response_time >= 0)

    def test_vmm_differentiation_with_crypto_moments(self, competitive_data, coordinated_data):
        """Test that VMM with crypto moments produces different results for competitive vs coordinated"""  # noqa: E501
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Create VMM engine with crypto calculator
        crypto_config = CryptoMomentConfig()
        crypto_calculator = CryptoMomentCalculator(crypto_config)
        vmm_config = VMMConfig()
        vmm_engine = VMMEngine(vmm_config, crypto_calculator)

        # Run VMM analysis on both scenarios
        competitive_result = vmm_engine.run_vmm(competitive_data, price_columns)
        coordinated_result = vmm_engine.run_vmm(coordinated_data, price_columns)

        # Results should be different
        assert (
            competitive_result.over_identification_stat
            != coordinated_result.over_identification_stat
        ), "Over-identification statistics should differ between scenarios"

        assert (
            competitive_result.over_identification_p_value
            != coordinated_result.over_identification_p_value
        ), "Over-identification p-values should differ between scenarios"

        assert (
            competitive_result.structural_stability != coordinated_result.structural_stability
        ), "Structural stability should differ between scenarios"

        # Print results for verification
        print(
            f"Competitive - J: {competitive_result.over_identification_stat:.6f}, "
            f"p: {competitive_result.over_identification_p_value:.6f}, "
            f"stability: {competitive_result.structural_stability:.6f}"
        )

        print(
            f"Coordinated - J: {coordinated_result.over_identification_stat:.6f}, "
            f"p: {coordinated_result.over_identification_p_value:.6f}, "
            f"stability: {coordinated_result.structural_stability:.6f}"
        )

    def test_monotone_response_coordinated(self, calculator, competitive_data, coordinated_data):
        """Test that coordinated scenario shows expected patterns"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        competitive_moments = calculator.calculate_moments(competitive_data, price_columns)
        coordinated_moments = calculator.calculate_moments(coordinated_data, price_columns)

        # Coordinated should have higher mirroring
        comp_mirroring = np.mean(competitive_moments.mirroring_ratios)
        coord_mirroring = np.mean(coordinated_moments.mirroring_ratios)
        assert coord_mirroring >= comp_mirroring, "Coordinated should have higher mirroring"

        # Coordinated should have higher dwell times
        comp_dwell = np.mean(competitive_moments.spread_floor_dwell_times)
        coord_dwell = np.mean(coordinated_moments.spread_floor_dwell_times)
        assert coord_dwell >= comp_dwell, "Coordinated should have higher dwell times"

        # Coordinated should have higher leader concentration (Herfindahl)
        comp_herfindahl = np.mean(competitive_moments.undercut_response_time)
        coord_herfindahl = np.mean(coordinated_moments.undercut_response_time)
        assert (
            coord_herfindahl >= comp_herfindahl
        ), "Coordinated should have higher leader concentration"

    def test_monotone_response_competitive(self, calculator, competitive_data, coordinated_data):
        """Test that competitive scenario shows expected patterns"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        competitive_moments = calculator.calculate_moments(competitive_data, price_columns)
        coordinated_moments = calculator.calculate_moments(coordinated_data, price_columns)

        # Competitive should have higher switching (lower persistence)
        # This is tested indirectly through the arbitrage timing moments
        comp_arbitrage = np.mean(competitive_moments.lead_lag_betas)
        coord_arbitrage = np.mean(coordinated_moments.lead_lag_betas)

        # Competitive should show more variable arbitrage timing (higher variance)
        comp_arbitrage_var = np.var(competitive_moments.lead_lag_betas)
        coord_arbitrage_var = np.var(coordinated_moments.lead_lag_betas)
        assert (
            comp_arbitrage_var >= coord_arbitrage_var
        ), "Competitive should have higher arbitrage timing variance"
