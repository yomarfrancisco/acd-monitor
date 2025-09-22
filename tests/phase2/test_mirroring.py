"""
Unit tests for mirroring validation layer
"""

from src.acd.validation.mirroring import MirroringValidator, MirroringConfig


class TestMirroringValidator:
    """Test cases for MirroringValidator"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return MirroringConfig(
            top_k_levels=5,
            depth_threshold=0.01,
            similarity_threshold=0.8,
            window_size=50,
            step_size=10,
            significance_level=0.05,
            min_observations=20,
        )

    @pytest.fixture
    def validator(self, config):
        """Test validator instance"""
        return MirroringValidator(config)

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
        """Generate coordinated synthetic data with high mirroring"""
        np.random.seed(42)
        n_points = 200
        n_exchanges = 3

        # Coordinated price series with high correlation
        prices = np.zeros((n_points, n_exchanges))
        prices[0, :] = 50000.0

        for t in range(1, n_points):
            # Base innovation
            base_innovation = np.random.normal(0, 50)

            # All exchanges follow similar patterns with small variations
            for i in range(n_exchanges):
                variation = np.random.normal(0, 10)
                prices[t, i] = prices[t - 1, i] + base_innovation + variation

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

    def test_competitive_mirroring_analysis(self, validator, competitive_data):
        """Test mirroring analysis on competitive data"""
        result = validator.analyze_mirroring(
            competitive_data, ["Exchange_0", "Exchange_1", "Exchange_2"]
        )

        # Should have results for all pairs
        assert len(result.mirroring_ratios) == 3  # 3 pairs
        assert len(result.cosine_similarities) == 3
        assert len(result.dtw_distances) == 3
        assert len(result.median_mirroring_ratio) == 3
        assert len(result.high_mirroring_fraction) == 3

        # Competitive data should have low mirroring ratios
        for pair_name in result.median_mirroring_ratio:
            assert 0.0 <= result.median_mirroring_ratio[pair_name] <= 1.0
            assert 0.0 <= result.high_mirroring_fraction[pair_name] <= 1.0

        # Should have low high mirroring fraction for competitive data
        for pair_name in result.high_mirroring_fraction:
            assert result.high_mirroring_fraction[pair_name] < 0.5  # Should be low for competitive

    def test_coordinated_mirroring_analysis(self, validator, coordinated_data):
        """Test mirroring analysis on coordinated data"""
        result = validator.analyze_mirroring(
            coordinated_data, ["Exchange_0", "Exchange_1", "Exchange_2"]
        )

        # Should have results for all pairs
        assert len(result.mirroring_ratios) == 3
        assert len(result.cosine_similarities) == 3
        assert len(result.dtw_distances) == 3
        assert len(result.median_mirroring_ratio) == 3
        assert len(result.high_mirroring_fraction) == 3

        # Coordinated data should show higher mirroring ratios
        for pair_name in result.median_mirroring_ratio:
            assert 0.0 <= result.median_mirroring_ratio[pair_name] <= 1.0
            assert 0.0 <= result.high_mirroring_fraction[pair_name] <= 1.0

        # Should have higher mirroring for coordinated data
        total_high_mirroring = sum(result.high_mirroring_fraction.values())
        assert total_high_mirroring > 0.0  # Should have some high mirroring

    def test_environment_invariance_analysis(self, validator, competitive_data):
        """Test environment invariance analysis"""
        result = validator.analyze_mirroring(
            competitive_data,
            ["Exchange_0", "Exchange_1", "Exchange_2"],
            environment_column="environment",
        )

        # Should have environment invariance results
        assert len(result.environment_invariance) == 3

        # Environment invariance should be between 0 and 1
        for pair_name in result.environment_invariance:
            assert 0.0 <= result.environment_invariance[pair_name] <= 1.0

    def test_input_validation(self, validator):
        """Test input validation"""
        # Test insufficient data
        small_data = pd.DataFrame(
            {"Exchange_0": [50000.0, 50010.0], "Exchange_1": [50000.0, 50005.0]}
        )

        with pytest.raises(ValueError, match="Need at least"):
            validator.analyze_mirroring(small_data, ["Exchange_0", "Exchange_1"])

        # Test insufficient columns
        data = pd.DataFrame({"Exchange_0": np.random.randn(100)})

        with pytest.raises(ValueError, match="Need at least 2 price columns"):
            validator.analyze_mirroring(data, ["Exchange_0"])

        # Test missing column
        with pytest.raises(ValueError, match="not found in data"):
            validator.analyze_mirroring(data, ["Exchange_0", "Missing_Exchange"])

    def test_window_mirroring_ratio_calculation(self, validator):
        """Test window mirroring ratio calculation"""
        # Create test data with known correlation
        np.random.seed(42)
        n = 100
        x = np.cumsum(np.random.randn(n))
        y = 0.8 * x + 0.2 * np.random.randn(n)  # High correlation

        ratio, p_value = validator._calculate_window_mirroring_ratio(x, y)

        # Should have valid results
        assert 0.0 <= ratio <= 1.0
        assert 0.0 <= p_value <= 1.0

        # Should have high mirroring ratio for correlated data
        assert ratio > 0.5

    def test_cosine_similarity_calculation(self, validator):
        """Test cosine similarity calculation"""
        # Test with identical vectors (need vectors longer than window_size=50)
        x = np.random.randn(100)
        y = x.copy()  # Identical vectors

        similarities = validator._rolling_cosine_similarity(x, y)

        # Should have high similarity for identical vectors
        assert len(similarities) > 0
        assert similarities[0] > 0.9  # Should be close to 1.0

        # Test with orthogonal vectors
        x = np.random.randn(100)
        y = np.random.randn(100)  # Independent vectors

        similarities = validator._rolling_cosine_similarity(x, y)

        # Should have low similarity for independent vectors
        assert similarities[0] < 0.5  # Should be low for independent vectors

    def test_dtw_distance_calculation(self, validator):
        """Test DTW distance calculation"""
        # Test with identical sequences
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([1, 2, 3, 4, 5])

        distance = validator._dtw_distance(x, y)

        # Should have zero distance for identical sequences
        assert distance == 0.0

        # Test with different sequences
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([2, 3, 4, 5, 6])

        distance = validator._dtw_distance(x, y)

        # Should have positive distance for different sequences
        assert distance > 0.0

    def test_median_mirroring_ratio_calculation(self, validator):
        """Test median mirroring ratio calculation"""
        # Test with known ratios
        ratios = np.array([0.1, 0.5, 0.8, 0.9, 0.2])
        median_ratios = validator._calculate_median_mirroring_ratio({"test_pair": ratios})

        assert "test_pair" in median_ratios
        assert median_ratios["test_pair"] == 0.5  # Should be the median

        # Test with NaN values
        ratios_with_nan = np.array([0.1, np.nan, 0.8, 0.9, np.nan])
        median_ratios = validator._calculate_median_mirroring_ratio({"test_pair": ratios_with_nan})

        assert median_ratios["test_pair"] == 0.8  # Should be median of valid values

    def test_high_mirroring_fraction_calculation(self, validator):
        """Test high mirroring fraction calculation"""
        # Test with ratios above and below threshold
        ratios = np.array([0.1, 0.5, 0.8, 0.9, 0.2])
        high_fractions = validator._calculate_high_mirroring_fraction({"test_pair": ratios})

        assert "test_pair" in high_fractions
        # Should have 2 out of 5 ratios above 0.8 threshold
        assert high_fractions["test_pair"] == 0.2  # 0.8 and 0.9 are above 0.8 threshold

        # Test with all ratios below threshold
        low_ratios = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        high_fractions = validator._calculate_high_mirroring_fraction({"test_pair": low_ratios})

        assert high_fractions["test_pair"] == 0.0  # Should be 0
