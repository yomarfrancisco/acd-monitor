"""
Tests for ACD Data Features Module

Tests feature engineering and windowing functionality:
- Deterministic windowing with seed control
- Fixed windows for VMM
- Rolling windows for ICP
- Feature extraction
"""

from src.acd.data.features import (
    DataWindowing,
    FeatureEngineering,
    WindowConfig,
    WindowedData,
    create_window_config,
    create_windows,
)


class TestDataWindowing:
    """Test data windowing functionality"""

    @pytest.fixture
    def sample_data(self):
        """Sample market data for testing"""
        dates = pd.date_range("2024-01-01", periods=200, freq="H")

        data = pd.DataFrame(
            {
                "firm_0_price": np.random.normal(100, 10, 200),
                "firm_1_price": np.random.normal(100, 10, 200),
                "firm_2_price": np.random.normal(100, 10, 200),
            },
            index=dates,
        )

        return data

    @pytest.fixture
    def fixed_window_config(self):
        """Fixed window configuration for VMM"""
        return create_window_config(window_size=100, step_size=50, window_type="fixed", seed=42)

    @pytest.fixture
    def rolling_window_config(self):
        """Rolling window configuration for ICP"""
        return create_window_config(window_size=100, step_size=50, window_type="rolling", seed=42)

    def test_fixed_window_creation(self, fixed_window_config, sample_data):
        """Test fixed window creation for VMM"""
        windower = DataWindowing(fixed_window_config)
        windowed_data = windower.create_windows(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Check window creation
        assert len(windowed_data) > 0
        assert len(windowed_data.windows) > 0

        # Check window sizes
        for window in windowed_data.windows:
            assert len(window) == 100  # Fixed size
            assert "window_index" in window.columns

        # Check metadata
        assert windowed_data.metadata["total_windows"] > 0
        assert windowed_data.metadata["window_size"] == 100
        assert windowed_data.metadata["window_type"] == "fixed"

    def test_rolling_window_creation(self, rolling_window_config, sample_data):
        """Test rolling window creation for ICP"""
        windower = DataWindowing(rolling_window_config)
        windowed_data = windower.create_windows(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Check window creation
        assert len(windowed_data) > 0
        assert len(windowed_data.windows) > 0

        # Check window sizes
        for window in windowed_data.windows:
            assert len(window) == 100  # Fixed size
            assert "window_index" in window.columns
            assert "rolling_start" in window.columns
            assert "rolling_end" in window.columns

        # Check rolling features
        first_window = windowed_data.windows[0]
        rolling_features = [col for col in first_window.columns if "rolling" in col]
        assert len(rolling_features) > 0

        # Check metadata
        assert windowed_data.metadata["total_windows"] > 0
        assert windowed_data.metadata["window_type"] == "rolling"

    def test_deterministic_windowing(self, fixed_window_config, sample_data):
        """Test deterministic windowing with seed control"""
        # Create two windowers with same seed
        windower1 = DataWindowing(fixed_window_config)
        windower2 = DataWindowing(fixed_window_config)

        # Create windows
        windowed_data1 = windower1.create_windows(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )
        windowed_data2 = windower2.create_windows(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Should produce identical results
        assert len(windowed_data1) == len(windowed_data2)
        assert len(windowed_data1.windows) == len(windowed_data2.windows)

        # Check window contents are identical
        for i in range(len(windowed_data1.windows)):
            window1 = windowed_data1.windows[i]
            window2 = windowed_data2.windows[i]

            pd.testing.assert_frame_equal(window1, window2)

    def test_window_validation(self, fixed_window_config, sample_data):
        """Test window validation"""
        windower = DataWindowing(fixed_window_config)
        windowed_data = windower.create_windows(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Validate windows
        is_valid = windower.validate_windows(windowed_data)
        assert is_valid

        # Check window statistics
        stats = windower.get_window_statistics(windowed_data)
        assert stats["total_windows"] > 0
        assert stats["window_size_consistency"]  # All windows should be same size
        assert stats["data_coverage"] > 0

    def test_insufficient_data_handling(self, fixed_window_config):
        """Test handling of insufficient data"""
        windower = DataWindowing(fixed_window_config)

        # Create data with insufficient points
        insufficient_data = pd.DataFrame(
            {"firm_0_price": np.random.normal(100, 10, 30)}  # Less than min_data_points
        )

        with pytest.raises(ValueError):
            windower.create_windows(insufficient_data, ["firm_0_price"])

    def test_empty_data_handling(self, fixed_window_config):
        """Test handling of empty data"""
        windower = DataWindowing(fixed_window_config)
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError):
            windower.create_windows(empty_data, [])

    def test_window_access_methods(self, fixed_window_config, sample_data):
        """Test window access methods"""
        windower = DataWindowing(fixed_window_config)
        windowed_data = windower.create_windows(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Test get_window method
        first_window = windowed_data.get_window(0)
        assert len(first_window) == 100

        # Test get_window_metadata method
        first_meta = windowed_data.get_window_metadata(0)
        assert "window_index" in first_meta
        assert first_meta["window_index"] == 0

        # Test error handling
        with pytest.raises(IndexError):
            windowed_data.get_window(999)

        with pytest.raises(IndexError):
            windowed_data.get_window_metadata(999)


class TestFeatureEngineering:
    """Test feature engineering functionality"""

    @pytest.fixture
    def sample_data(self):
        """Sample market data for feature engineering"""
        dates = pd.date_range("2024-01-01", periods=100, freq="H")

        data = pd.DataFrame(
            {
                "firm_0_price": np.random.normal(100, 10, 100),
                "firm_1_price": np.random.normal(100, 10, 100),
                "firm_2_price": np.random.normal(100, 10, 100),
            },
            index=dates,
        )

        return data

    def test_price_feature_extraction(self, sample_data):
        """Test price feature extraction"""
        engineer = FeatureEngineering(seed=42)
        features = engineer.extract_price_features(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Check price change features
        assert "firm_0_price_price_change" in features.columns
        assert "firm_0_price_price_change_pct" in features.columns

        # Check volatility features
        assert "firm_0_price_volatility" in features.columns
        assert "firm_0_price_volatility_pct" in features.columns

        # Check momentum features
        assert "firm_0_price_momentum_5" in features.columns
        assert "firm_0_price_momentum_10" in features.columns

        # Check feature calculations
        assert not features["firm_0_price_price_change"].isna().all()
        assert not features["firm_0_price_volatility"].isna().all()

    def test_temporal_feature_extraction(self, sample_data):
        """Test temporal feature extraction"""
        engineer = FeatureEngineering(seed=42)
        features = engineer.extract_temporal_features(sample_data)

        # Check time-based features
        assert "hour" in features.columns
        assert "day_of_week" in features.columns
        assert "day_of_month" in features.columns
        assert "month" in features.columns

        # Check cyclical encoding
        assert "hour_sin" in features.columns
        assert "hour_cos" in features.columns
        assert "day_sin" in features.columns
        assert "day_cos" in features.columns

        # Check feature values
        assert features["hour"].min() >= 0
        assert features["hour"].max() <= 23
        assert features["day_of_week"].min() >= 0
        assert features["day_of_week"].max() <= 6

    def test_statistical_feature_extraction(self, sample_data):
        """Test statistical feature extraction"""
        engineer = FeatureEngineering(seed=42)
        features = engineer.extract_statistical_features(
            sample_data, ["firm_0_price", "firm_1_price", "firm_2_price"]
        )

        # Check rolling statistics
        assert "firm_0_price_rolling_mean" in features.columns
        assert "firm_0_price_rolling_std" in features.columns
        assert "firm_0_price_rolling_median" in features.columns

        # Check percentile features
        assert "firm_0_price_rolling_p25" in features.columns
        assert "firm_0_price_rolling_p75" in features.columns

        # Check distribution features
        assert "firm_0_price_rolling_skew" in features.columns
        assert "firm_0_price_rolling_kurt" in features.columns

        # Check feature calculations
        assert not features["firm_0_price_rolling_mean"].isna().all()
        assert not features["firm_0_price_rolling_std"].isna().all()

    def test_deterministic_feature_engineering(self, sample_data):
        """Test deterministic feature engineering with seed control"""
        # Create two engineers with same seed
        engineer1 = FeatureEngineering(seed=42)
        engineer2 = FeatureEngineering(seed=42)

        # Extract features
        features1 = engineer1.extract_price_features(sample_data, ["firm_0_price"])
        features2 = engineer2.extract_price_features(sample_data, ["firm_0_price"])

        # Should produce identical results
        pd.testing.assert_frame_equal(features1, features2)

    def test_feature_engineering_without_seed(self, sample_data):
        """Test feature engineering without seed (should still work)"""
        engineer = FeatureEngineering()  # No seed
        features = engineer.extract_price_features(sample_data, ["firm_0_price"])

        # Should still extract features
        assert "firm_0_price_price_change" in features.columns
        assert "firm_0_price_volatility" in features.columns


class TestWindowConfig:
    """Test window configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = WindowConfig(
            window_size=100, step_size=50, min_data_points=50, window_type="fixed"
        )

        assert config.window_size == 100
        assert config.step_size == 50
        assert config.min_data_points == 50
        assert config.window_type == "fixed"
        assert config.seed is None

    def test_config_with_seed(self):
        """Test configuration with seed"""
        config = WindowConfig(
            window_size=100, step_size=50, min_data_points=50, window_type="fixed", seed=42
        )

        assert config.seed == 42

    def test_invalid_window_type(self):
        """Test invalid window type handling"""
        # This should not raise an error at config level
        config = WindowConfig(
            window_size=100, step_size=50, min_data_points=50, window_type="invalid_type"
        )

        assert config.window_type == "invalid_type"


class TestConvenienceFunctions:
    """Test convenience functions"""

    def test_create_window_config(self):
        """Test window config creation function"""
        config = create_window_config(
            window_size=150, step_size=75, window_type="rolling", seed=123
        )

        assert config.window_size == 150
        assert config.step_size == 75
        assert config.window_type == "rolling"
        assert config.seed == 123
        assert config.min_data_points == 50  # Default value

    def test_create_windows(self):
        """Test convenience window creation function"""
        # Create sample data
        data = pd.DataFrame(
            {
                "firm_0_price": np.random.normal(100, 10, 200),
                "firm_1_price": np.random.normal(100, 10, 200),
            }
        )

        # Create windows with default config
        windowed_data = create_windows(data, ["firm_0_price", "firm_1_price"])

        assert isinstance(windowed_data, WindowedData)
        assert len(windowed_data) > 0
        assert len(windowed_data.windows) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
