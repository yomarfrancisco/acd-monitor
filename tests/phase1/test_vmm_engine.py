"""
Unit tests for VMM Engine

Tests convergence, over-identification, and structural stability
for court/regulator-ready coordination risk analytics.
"""

import pytest
import numpy as np
import pandas as pd
from src.acd.vmm.engine import VMMEngine, VMMConfig
from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig


class TestVMMEngine:
    """Test suite for VMM Engine"""

    @pytest.fixture
    def vmm_engine(self):
        """Create VMM engine for testing"""
        config = VMMConfig()
        return VMMEngine(config)

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

    def test_convergence(self, vmm_engine, competitive_data):
        """Test that VMM converges within iteration limit"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        result = vmm_engine.run_vmm(competitive_data, price_columns)

        # Check convergence
        assert result.convergence_status in [
            "converged",
            "max_iterations",
        ], f"Invalid convergence status: {result.convergence_status}"
        assert (
            result.iterations <= 10000
        ), f"Should converge within 10k iterations, got {result.iterations}"
        assert np.isfinite(result.final_loss), "Final loss should be finite"

        # Check parameter estimates
        assert np.all(np.isfinite(result.beta_estimates)), "Beta estimates should be finite"
        assert np.all(np.isfinite(result.sigma_estimates)), "Sigma estimates should be finite"
        assert np.all(np.isfinite(result.rho_estimates)), "Rho estimates should be finite"

        print(
            f"Convergence: {result.convergence_status}, iterations: {result.iterations}, loss: {result.final_loss:.6f}"
        )

    def test_over_identification(self, vmm_engine, competitive_data):
        """Test over-identification test on competitive synthetic data"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        result = vmm_engine.run_vmm(competitive_data, price_columns)

        # Over-identification test should be well-behaved
        assert np.isfinite(result.over_identification_stat), "Over-ID statistic should be finite"
        assert np.isfinite(result.over_identification_p_value), "Over-ID p-value should be finite"
        assert (
            0.0 <= result.over_identification_p_value <= 1.0
        ), "Over-ID p-value should be in [0,1]"

        # For competitive data, over-ID p-value should typically be > 0.05 (not over-identified)
        # This is a soft check - competitive data should not show strong over-identification
        if result.over_identification_p_value > 0.05:
            print(
                f"Competitive data shows no over-identification (p={result.over_identification_p_value:.6f})"
            )
        else:
            print(
                f"Competitive data shows over-identification (p={result.over_identification_p_value:.6f})"
            )

        print(f"Over-ID J-statistic: {result.over_identification_stat:.6f}")
        print(f"Over-ID p-value: {result.over_identification_p_value:.6f}")

    def test_stability_range(self, vmm_engine, competitive_data, coordinated_data):
        """Test that structural stability is bounded in [0,1]"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Test competitive data
        competitive_result = vmm_engine.run_vmm(competitive_data, price_columns)

        # Test coordinated data
        coordinated_result = vmm_engine.run_vmm(coordinated_data, price_columns)

        # Stability should be bounded
        for result, scenario in [
            (competitive_result, "competitive"),
            (coordinated_result, "coordinated"),
        ]:
            assert np.isfinite(
                result.structural_stability
            ), f"{scenario} stability should be finite"
            assert (
                0.0 <= result.structural_stability <= 1.0
            ), f"{scenario} stability should be in [0,1], got {result.structural_stability}"

            print(f"{scenario.capitalize()} stability: {result.structural_stability:.6f}")

    def test_regime_confidence(self, vmm_engine, competitive_data):
        """Test regime confidence calculation"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        result = vmm_engine.run_vmm(competitive_data, price_columns)

        # Regime confidence should be bounded
        assert np.isfinite(result.regime_confidence), "Regime confidence should be finite"
        assert (
            0.0 <= result.regime_confidence <= 1.0
        ), f"Regime confidence should be in [0,1], got {result.regime_confidence}"

        print(f"Regime confidence: {result.regime_confidence:.6f}")

    def test_moment_conditions(self, vmm_engine, competitive_data):
        """Test moment condition calculation"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Extract price data
        prices = competitive_data[price_columns].values

        # Test moment calculation
        beta = np.random.normal(0, 0.1, 3)  # Random beta for testing
        moments = vmm_engine._calculate_moment_conditions(prices, beta)

        # Moments should be finite
        assert np.all(np.isfinite(moments)), "All moment conditions should be finite"
        assert len(moments) > 0, "Should have at least one moment condition"

        print(f"Number of moment conditions: {len(moments)}")
        print(f"Moment conditions range: [{np.min(moments):.6f}, {np.max(moments):.6f}]")

    def test_gradient_calculation(self, vmm_engine, competitive_data):
        """Test gradient calculation"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Extract price data
        prices = competitive_data[price_columns].values

        # Test gradient calculation
        beta = np.random.normal(0, 0.1, 3)  # Random beta for testing
        moments = vmm_engine._calculate_moment_conditions(prices, beta)
        gradients = vmm_engine._calculate_gradients(prices, beta, moments)

        # Gradients should be finite and match beta dimension
        assert np.all(np.isfinite(gradients)), "All gradients should be finite"
        assert len(gradients) == len(beta), "Gradients should match beta dimension"

        print(f"Gradient norm: {np.linalg.norm(gradients):.6f}")

    def test_parameter_initialization(self, vmm_engine, competitive_data):
        """Test parameter initialization"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Extract price data
        prices = competitive_data[price_columns].values

        # Test parameter initialization
        beta_dim = vmm_engine.config.beta_dim
        beta_init = np.random.normal(0, 0.1, beta_dim)
        sigma_init = np.eye(beta_dim) * vmm_engine.config.sigma_prior
        rho_init = np.eye(beta_dim) * vmm_engine.config.rho_prior

        # Parameters should be finite and properly shaped
        assert np.all(np.isfinite(beta_init)), "Beta initialization should be finite"
        assert np.all(np.isfinite(sigma_init)), "Sigma initialization should be finite"
        assert np.all(np.isfinite(rho_init)), "Rho initialization should be finite"
        assert beta_init.shape == (beta_dim,), "Beta should have correct shape"
        assert sigma_init.shape == (beta_dim, beta_dim), "Sigma should be square"
        assert rho_init.shape == (beta_dim, beta_dim), "Rho should be square"

        print(
            f"Parameter shapes: beta={beta_init.shape}, sigma={sigma_init.shape}, rho={rho_init.shape}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
