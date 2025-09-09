"""
Unit tests for adaptive threshold framework.

Tests dataset-size-aware thresholds for spurious regime detection
with configurable parameters and validation logic.
"""

import pytest

from acd.vmm.adaptive_thresholds import (
    AdaptiveThresholdConfig,
    AdaptiveThresholdManager,
    get_profile,
)


class TestAdaptiveThresholdConfig:
    """Test threshold configuration validation and defaults."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AdaptiveThresholdConfig()

        assert config.small_dataset_threshold == 0.02
        assert config.medium_dataset_threshold == 0.05
        assert config.large_dataset_threshold == 0.08
        assert config.small_dataset_max == 200
        assert config.medium_dataset_max == 800
        assert config.enable_continuous_scaling is True
        assert config.scaling_factor == 0.006
        assert config.strict_mode is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AdaptiveThresholdConfig(
            small_dataset_threshold=0.015,
            medium_dataset_threshold=0.04,
            large_dataset_threshold=0.06,
            small_dataset_max=100,
            medium_dataset_max=500,
            enable_continuous_scaling=False,
            scaling_factor=0.01,
            strict_mode=False,
        )

        assert config.small_dataset_threshold == 0.015
        assert config.medium_dataset_threshold == 0.04
        assert config.large_dataset_threshold == 0.06
        assert config.small_dataset_max == 100
        assert config.medium_dataset_max == 500
        assert config.enable_continuous_scaling is False
        assert config.scaling_factor == 0.01
        assert config.strict_mode is False

    def test_invalid_thresholds(self):
        """Test validation of threshold ordering."""
        with pytest.raises(ValueError, match="Thresholds must be strictly increasing"):
            AdaptiveThresholdConfig(
                small_dataset_threshold=0.05,  # Higher than medium
                medium_dataset_threshold=0.02,
                large_dataset_threshold=0.08,
            )

    def test_invalid_dataset_boundaries(self):
        """Test validation of dataset size boundaries."""
        with pytest.raises(ValueError, match="Dataset size boundaries must be strictly increasing"):
            AdaptiveThresholdConfig(
                small_dataset_max=500, medium_dataset_max=200  # Lower than small_max
            )

    def test_invalid_scaling_factor(self):
        """Test validation of scaling factor."""
        with pytest.raises(ValueError, match="Scaling factor must be positive"):
            AdaptiveThresholdConfig(scaling_factor=0.0)


class TestAdaptiveThresholdManager:
    """Test threshold manager functionality."""

    def test_small_dataset_threshold(self):
        """Test threshold selection for small datasets."""
        manager = AdaptiveThresholdManager()

        # Test various small dataset sizes
        for size in [1, 50, 100, 200]:
            threshold = manager.get_threshold(size)
            assert threshold == 0.02
            assert threshold <= 0.02

    def test_medium_dataset_threshold(self):
        """Test threshold selection for medium datasets."""
        manager = AdaptiveThresholdManager()

        # Test various medium dataset sizes
        for size in [201, 400, 600, 800]:
            threshold = manager.get_threshold(size)
            assert 0.02 < threshold <= 0.05

    def test_large_dataset_threshold(self):
        """Test threshold selection for large datasets."""
        manager = AdaptiveThresholdManager()

        # Test various large dataset sizes
        for size in [801, 1000, 2000, 5000]:
            threshold = manager.get_threshold(size)
            assert threshold == 0.08

    def test_continuous_scaling(self):
        """Test continuous scaling for medium datasets."""
        manager = AdaptiveThresholdManager()

        # Test that thresholds increase smoothly
        thresholds = []
        for size in range(200, 801, 100):
            threshold = manager.get_threshold(size)
            thresholds.append(threshold)

        # Should be monotonically increasing
        assert all(thresholds[i] <= thresholds[i + 1] for i in range(len(thresholds) - 1))

        # First should be close to small threshold, last should be close to medium
        assert abs(thresholds[0] - 0.02) < 0.001
        assert abs(thresholds[-1] - 0.05) < 0.001

    def test_disabled_continuous_scaling(self):
        """Test fixed thresholds when continuous scaling is disabled."""
        config = AdaptiveThresholdConfig(enable_continuous_scaling=False)
        manager = AdaptiveThresholdManager(config)

        # All medium datasets should get the same threshold
        threshold_201 = manager.get_threshold(201)
        threshold_500 = manager.get_threshold(500)
        threshold_800 = manager.get_threshold(800)

        assert threshold_201 == threshold_500 == threshold_800 == 0.05

    def test_validation_success(self):
        """Test successful threshold validation."""
        manager = AdaptiveThresholdManager()

        # Small dataset with low spurious rate
        result = manager.validate_spurious_rate(100, 0.01)

        assert result["passes"] is True
        assert result["dataset_size"] == 100
        assert result["dataset_category"] == "small"
        assert result["threshold_applied"] == 0.02
        assert result["spurious_rate"] == 0.01
        assert result["margin"] == 0.01

    def test_validation_failure(self):
        """Test failed threshold validation."""
        manager = AdaptiveThresholdManager()

        # Small dataset with high spurious rate
        result = manager.validate_spurious_rate(100, 0.03)

        assert result["passes"] is False
        assert result["dataset_size"] == 100
        assert result["dataset_category"] == "small"
        assert result["threshold_applied"] == 0.02
        assert result["spurious_rate"] == 0.03
        assert abs(result["margin"] - (-0.01)) < 1e-10

    def test_threshold_profile(self):
        """Test threshold profile generation."""
        manager = AdaptiveThresholdManager()
        profile = manager.get_threshold_profile()

        assert profile["framework_version"] == "1.0.0"
        assert profile["small_dataset"]["max_size"] == 200
        assert profile["small_dataset"]["threshold"] == 0.02
        assert profile["medium_dataset"]["min_size"] == 201
        assert profile["medium_dataset"]["max_size"] == 800
        assert profile["medium_dataset"]["threshold"] == 0.05
        assert profile["large_dataset"]["min_size"] == 801
        assert profile["large_dataset"]["threshold"] == 0.08
        assert profile["continuous_scaling"]["enabled"] is True
        assert profile["strict_mode"] is True

    def test_invalid_dataset_size(self):
        """Test error handling for invalid dataset sizes."""
        manager = AdaptiveThresholdManager()

        with pytest.raises(ValueError, match="Dataset size must be positive"):
            manager.get_threshold(0)

        with pytest.raises(ValueError, match="Dataset size must be positive"):
            manager.get_threshold(-100)


class TestDefaultProfiles:
    """Test predefined threshold profiles."""

    def test_conservative_profile(self):
        """Test conservative threshold profile."""
        config = get_profile("conservative")

        assert config.small_dataset_threshold == 0.015
        assert config.medium_dataset_threshold == 0.04
        assert config.large_dataset_threshold == 0.06
        assert config.strict_mode is True

    def test_balanced_profile(self):
        """Test balanced threshold profile."""
        config = get_profile("balanced")

        assert config.small_dataset_threshold == 0.02
        assert config.medium_dataset_threshold == 0.05
        assert config.large_dataset_threshold == 0.08
        assert config.strict_mode is True

    def test_permissive_profile(self):
        """Test permissive threshold profile."""
        config = get_profile("permissive")

        assert config.small_dataset_threshold == 0.025
        assert config.medium_dataset_threshold == 0.06
        assert config.large_dataset_threshold == 0.10
        assert config.strict_mode is False

    def test_invalid_profile_name(self):
        """Test error handling for invalid profile names."""
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("nonexistent")


class TestIntegration:
    """Test integration with real-world scenarios."""

    def test_golden_dataset_190_windows(self):
        """Test that 190-window golden dataset passes with ≤5% threshold."""
        # Simulate 190 windows with 4% spurious rate (should pass)
        manager = AdaptiveThresholdManager()

        # 190 windows is small dataset category
        threshold = manager.get_threshold(190)
        assert threshold == 0.02  # 2%

        # 4% spurious rate should pass 2% threshold
        result = manager.validate_spurious_rate(190, 0.04)
        assert result["passes"] is False  # 4% > 2%

        # But should pass if we use medium dataset threshold
        config = AdaptiveThresholdConfig(small_dataset_max=180)  # Move 190 to medium
        manager_medium = AdaptiveThresholdManager(config)
        result_medium = manager_medium.validate_spurious_rate(190, 0.04)
        assert result_medium["passes"] is True  # 4% ≤ 5%

    def test_large_dataset_1000_windows(self):
        """Test that 1000-window dataset uses 8% threshold."""
        manager = AdaptiveThresholdManager()

        threshold = manager.get_threshold(1000)
        assert threshold == 0.08  # 8%

        # 7% spurious rate should pass
        result = manager.validate_spurious_rate(1000, 0.07)
        assert result["passes"] is True

        # 9% spurious rate should fail
        result_fail = manager.validate_spurious_rate(1000, 0.09)
        assert result_fail["passes"] is False

    def test_threshold_transitions(self):
        """Test smooth transitions between dataset categories."""
        manager = AdaptiveThresholdManager()

        # Test boundary conditions
        small_max = manager.config.small_dataset_max
        medium_max = manager.config.medium_dataset_max

        # Just below small max
        threshold_small = manager.get_threshold(small_max)
        # Just above small max
        threshold_medium_low = manager.get_threshold(small_max + 1)
        # Just below medium max
        threshold_medium_high = manager.get_threshold(medium_max)
        # Just above medium max
        threshold_large = manager.get_threshold(medium_max + 1)

        # Should have smooth transitions
        assert threshold_small == 0.02
        assert threshold_medium_low > 0.02
        assert threshold_medium_high < 0.08
        assert threshold_large == 0.08
