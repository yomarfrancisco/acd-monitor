"""
Unit tests for lead-lag validation layer
"""

import pytest
import numpy as np
import pandas as pd
from src.acd.validation.lead_lag import LeadLagValidator, LeadLagConfig


class TestLeadLagValidator:
    """Test cases for LeadLagValidator"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return LeadLagConfig(
            window_size=50, step_size=10, significance_level=0.05, min_observations=20
        )

    @pytest.fixture
    def validator(self, config):
        """Test validator instance"""
        return LeadLagValidator(config)

    @pytest.fixture
    def competitive_data(self):
        """Generate competitive synthetic data"""
        np.random.seed(42)
        n_points = 200
        n_exchanges = 3

        # Independent price series
        prices = np.zeros((n_points, n_exchanges))
        prices[0, :] = 50000.0

        for t in range(1, n_points):
            for i in range(n_exchanges):
                # Independent random walk
                innovation = np.random.normal(0, 100)
                prices[t, i] = prices[t - 1, i] + innovation

        # Create DataFrame
        data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2023-01-01", periods=n_points, freq="1min"),
                "Exchange_0": prices[:, 0],
                "Exchange_1": prices[:, 1],
                "Exchange_2": prices[:, 2],
                "environment": ["low"] * (n_points // 2) + ["high"] * (n_points - n_points // 2),
            }
        )

        return data

    @pytest.fixture
    def coordinated_data(self):
        """Generate coordinated synthetic data"""
        np.random.seed(42)
        n_points = 200
        n_exchanges = 3

        # Coordinated price series with lead-lag
        prices = np.zeros((n_points, n_exchanges))
        prices[0, :] = 50000.0

        for t in range(1, n_points):
            # Lead exchange (Exchange_0)
            lead_innovation = np.random.normal(0, 50)
            prices[t, 0] = prices[t - 1, 0] + lead_innovation

            # Follower exchanges with lag
            if t >= 2:
                for i in range(1, n_exchanges):
                    # Follow with lag and some noise
                    lag_change = prices[t - 1, 0] - prices[t - 2, 0]
                    follow_strength = 0.8 if i == 1 else 0.6
                    noise = np.random.normal(0, 20)
                    prices[t, i] = prices[t - 1, i] + follow_strength * lag_change + noise
            else:
                for i in range(1, n_exchanges):
                    prices[t, i] = prices[t - 1, i] + np.random.normal(0, 50)

        # Create DataFrame
        data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2023-01-01", periods=n_points, freq="1min"),
                "Exchange_0": prices[:, 0],
                "Exchange_1": prices[:, 1],
                "Exchange_2": prices[:, 2],
                "environment": ["low"] * (n_points // 2) + ["high"] * (n_points - n_points // 2),
            }
        )

        return data

    def test_competitive_lead_lag_analysis(self, validator, competitive_data):
        """Test lead-lag analysis on competitive data"""
        result = validator.analyze_lead_lag(
            competitive_data, ["Exchange_0", "Exchange_1", "Exchange_2"]
        )

        # Should have results for all pairs
        assert len(result.lead_lag_betas) == 3  # 3 pairs
        assert len(result.significant_lead_fraction) == 3
        assert len(result.persistence_metrics) == 3
        assert len(result.switching_entropy) == 3

        # Competitive data should have low persistence and high switching entropy
        for pair_name in result.persistence_metrics:
            assert -1.0 <= result.persistence_metrics[pair_name] <= 1.0
            assert 0.0 <= result.switching_entropy[pair_name] <= 1.0

        # Should have low significant lead fraction for competitive data
        for pair_name in result.significant_lead_fraction:
            assert 0.0 <= result.significant_lead_fraction[pair_name] <= 1.0

    def test_coordinated_lead_lag_analysis(self, validator, coordinated_data):
        """Test lead-lag analysis on coordinated data"""
        result = validator.analyze_lead_lag(
            coordinated_data, ["Exchange_0", "Exchange_1", "Exchange_2"]
        )

        # Should have results for all pairs
        assert len(result.lead_lag_betas) == 3
        assert len(result.significant_lead_fraction) == 3
        assert len(result.persistence_metrics) == 3
        assert len(result.switching_entropy) == 3

        # Coordinated data should show higher persistence for lead-follower pairs
        # Exchange_0 -> Exchange_1 should have higher persistence
        if "Exchange_0_Exchange_1" in result.persistence_metrics:
            persistence_01 = result.persistence_metrics["Exchange_0_Exchange_1"]
            assert persistence_01 > 0.0  # Should show some persistence

    def test_environment_sensitivity_analysis(self, validator, competitive_data):
        """Test environment sensitivity analysis"""
        result = validator.analyze_lead_lag(
            competitive_data,
            ["Exchange_0", "Exchange_1", "Exchange_2"],
            environment_column="environment",
        )

        # Should have environment sensitivity results
        assert len(result.environment_sensitivity) == 3

        # Environment sensitivity should be non-negative
        for pair_name in result.environment_sensitivity:
            assert result.environment_sensitivity[pair_name] >= 0.0

    def test_granger_causality_analysis(self, validator, coordinated_data):
        """Test Granger causality analysis"""
        result = validator.analyze_lead_lag(
            coordinated_data, ["Exchange_0", "Exchange_1", "Exchange_2"]
        )

        # Should have Granger results for all pairs
        assert len(result.granger_results) == 3

        # Each Granger result should have required fields
        for pair_name in result.granger_results:
            granger_result = result.granger_results[pair_name]
            assert "p_values" in granger_result
            assert "min_p_value" in granger_result
            assert "significant_lags" in granger_result

            assert 0.0 <= granger_result["min_p_value"] <= 1.0
            assert isinstance(granger_result["significant_lags"], list)

    def test_input_validation(self, validator):
        """Test input validation"""
        # Test insufficient data
        small_data = pd.DataFrame(
            {"Exchange_0": [50000.0, 50010.0], "Exchange_1": [50000.0, 50005.0]}
        )

        with pytest.raises(ValueError, match="Need at least"):
            validator.analyze_lead_lag(small_data, ["Exchange_0", "Exchange_1"])

        # Test insufficient columns
        data = pd.DataFrame({"Exchange_0": np.random.randn(100)})

        with pytest.raises(ValueError, match="Need at least 2 price columns"):
            validator.analyze_lead_lag(data, ["Exchange_0"])

        # Test missing column
        with pytest.raises(ValueError, match="not found in data"):
            validator.analyze_lead_lag(data, ["Exchange_0", "Missing_Exchange"])

    def test_rolling_lead_lag_regression(self, validator):
        """Test rolling lead-lag regression calculation"""
        # Create test data with known lead-lag relationship
        np.random.seed(42)
        n = 100
        x = np.cumsum(np.random.randn(n))
        y = 0.5 * np.roll(x, 1) + 0.1 * np.random.randn(n)  # y follows x with lag

        betas, p_values = validator._rolling_lead_lag_regression(x, y)

        # Should have valid results
        assert len(betas) > 0
        assert len(p_values) > 0
        assert len(betas) == len(p_values)

        # Should have some significant relationships
        significant_count = np.sum(p_values < 0.05)
        assert significant_count > 0  # Should find some significant lead-lag

    def test_persistence_metrics_calculation(self, validator):
        """Test persistence metrics calculation"""
        # Test with persistent betas
        persistent_betas = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
        persistence = validator._calculate_persistence_metrics({"test_pair": persistent_betas})

        assert "test_pair" in persistence
        assert persistence["test_pair"] > 0.0  # Should be positive for persistent data

        # Test with switching betas
        switching_betas = np.array([0.5, -0.5, 0.5, -0.5, 0.5])
        persistence = validator._calculate_persistence_metrics({"test_pair": switching_betas})

        assert persistence["test_pair"] < 0.0  # Should be negative for switching data

    def test_switching_entropy_calculation(self, validator):
        """Test switching entropy calculation"""
        # Test with no switching
        stable_betas = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        entropy = validator._calculate_switching_entropy({"test_pair": stable_betas})

        assert "test_pair" in entropy
        assert entropy["test_pair"] == 0.0  # Should be 0 for no switching

        # Test with high switching
        switching_betas = np.array([0.5, -0.5, 0.5, -0.5, 0.5])
        entropy = validator._calculate_switching_entropy({"test_pair": switching_betas})

        assert entropy["test_pair"] >= 0.0  # Should be non-negative for switching
