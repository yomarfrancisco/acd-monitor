"""Unit tests for demo pipeline ingestion module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from acd.demo.ingestion import MockDataIngestion


class TestMockDataIngestion:
    """Test cases for MockDataIngestion class."""

    def test_initialization(self):
        """Test MockDataIngestion initialization."""
        ingestion = MockDataIngestion()

        assert ingestion.base_path.name == "golden"
        assert ingestion.ingestion is not None
        assert ingestion.quality_config is not None
        assert "market_style" in ingestion.mock_feeds
        assert "regulatory_style" in ingestion.mock_feeds

    def test_ingest_golden_datasets_success(self):
        """Test successful golden dataset ingestion."""
        ingestion = MockDataIngestion()

        # Mock successful file reading
        with patch("pathlib.Path.glob") as mock_glob:
            mock_csv = MagicMock()
            mock_csv.stem = "test_dataset"
            mock_glob.return_value = [mock_csv]

            with patch("pandas.read_csv") as mock_read_csv:
                mock_df = pd.DataFrame({"test": [1, 2, 3]})
                mock_read_csv.return_value = mock_df

                result = ingestion.ingest_golden_datasets()

                assert "test_dataset" in result
                assert len(result["test_dataset"]) == 3

    def test_ingest_golden_datasets_fallback(self):
        """Test fallback to synthetic data when ingestion fails."""
        ingestion = MockDataIngestion()

        # Mock failed file reading
        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.side_effect = Exception("File not found")

            result = ingestion.ingest_golden_datasets()

            assert "competitive" in result
            assert "coordinated" in result
            assert len(result["competitive"]) == 100
            assert len(result["coordinated"]) == 100

    def test_generate_mock_feeds_market_style(self):
        """Test market-style mock feed generation."""
        ingestion = MockDataIngestion()

        feeds = ingestion.generate_mock_feeds("market_style", num_windows=3)

        assert len(feeds) == 3
        for feed in feeds:
            assert isinstance(feed, pd.DataFrame)
            assert "timestamp" in feed.columns
            assert "firm_id" in feed.columns
            assert "price" in feed.columns
            assert "volume" in feed.columns
            assert "bid" in feed.columns
            assert "ask" in feed.columns
            assert len(feed) == 1000  # sample_size from config

    def test_generate_mock_feeds_regulatory_style(self):
        """Test regulatory-style mock feed generation."""
        ingestion = MockDataIngestion()

        feeds = ingestion.generate_mock_feeds("regulatory_style", num_windows=2)

        assert len(feeds) == 2
        for feed in feeds:
            assert isinstance(feed, pd.DataFrame)
            assert "disclosure_id" in feed.columns
            assert "firm_id" in feed.columns
            assert "disclosure_type" in feed.columns
            assert "timestamp" in feed.columns
            assert "content" in feed.columns
            assert len(feed) == 100  # sample_size from config

    def test_generate_mock_feeds_invalid_type(self):
        """Test error handling for invalid feed type."""
        ingestion = MockDataIngestion()

        with pytest.raises(ValueError, match="Unknown feed type"):
            ingestion.generate_mock_feeds("invalid_type")

    def test_validate_mock_data_success(self):
        """Test successful mock data validation."""
        ingestion = MockDataIngestion()

        # Create test data
        test_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10, freq="1min"),
                "firm_id": ["firm_1"] * 10,
                "price": [100 + i for i in range(10)],
                "volume": [1000 + i * 10 for i in range(10)],
            }
        )

        quality = ingestion.validate_mock_data(test_data, "market_style")

        assert "completeness" in quality
        assert "accuracy" in quality
        assert "timeliness" in quality
        assert "consistency" in quality
        assert "overall" in quality
        assert all(isinstance(v, (int, float)) for v in quality.values())

    def test_validate_mock_data_fallback(self):
        """Test validation fallback when quality assessment fails."""
        ingestion = MockDataIngestion()

        # Create test data that might cause validation issues
        test_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5, freq="1min"),
                "firm_id": ["firm_1"] * 5,
                "price": [100, 101, 102, 103, 104],
                "volume": [1000, 1010, 1020, 1030, 1040],
            }
        )

        # Mock quality assessment failure
        with patch.object(ingestion, "quality_config") as mock_config:
            mock_config.side_effect = Exception("Validation failed")

            quality = ingestion.validate_mock_data(test_data, "market_style")

            # Should return fallback values
            assert quality["completeness"] == 0.95
            assert quality["accuracy"] == 0.90
            assert quality["overall"] == 0.90

    def test_market_style_window_generation(self):
        """Test market-style window data generation."""
        ingestion = MockDataIngestion()

        window_data = ingestion._generate_market_style_window(0, 100)

        assert isinstance(window_data, pd.DataFrame)
        assert len(window_data) == 100
        assert "timestamp" in window_data.columns
        assert "firm_id" in window_data.columns
        assert "price" in window_data.columns
        assert "volume" in window_data.columns
        assert "bid" in window_data.columns
        assert "ask" in window_data.columns

        # Check data types and ranges
        assert all(window_data["price"] > 0)
        assert all(window_data["volume"] > 0)
        assert all(window_data["ask"] > window_data["bid"])

    def test_regulatory_style_window_generation(self):
        """Test regulatory-style window data generation."""
        ingestion = MockDataIngestion()

        window_data = ingestion._generate_regulatory_style_window(1, 50)

        assert isinstance(window_data, pd.DataFrame)
        assert len(window_data) == 50
        assert "disclosure_id" in window_data.columns
        assert "firm_id" in window_data.columns
        assert "disclosure_type" in window_data.columns
        assert "timestamp" in window_data.columns
        assert "content" in window_data.columns

        # Check disclosure types
        expected_types = ["price_change", "volume_alert", "coordination_suspicion", "market_abuse"]
        assert all(dt in expected_types for dt in window_data["disclosure_type"].unique())

    def test_synthetic_golden_data_generation(self):
        """Test synthetic golden data generation."""
        ingestion = MockDataIngestion()

        golden_data = ingestion._generate_synthetic_golden_data()

        assert "competitive" in golden_data
        assert "coordinated" in golden_data

        # Check competitive data
        competitive = golden_data["competitive"]
        assert len(competitive) == 100
        assert "timestamp" in competitive.columns
        assert "firm_id" in competitive.columns
        assert "price" in competitive.columns
        assert "volume" in competitive.columns

        # Check coordinated data
        coordinated = golden_data["coordinated"]
        assert len(coordinated) == 100
        assert "timestamp" in coordinated.columns
        assert "firm_id" in coordinated.columns
        assert "price" in coordinated.columns
        assert "volume" in coordinated.columns
