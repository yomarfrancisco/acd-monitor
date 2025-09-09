"""Unit tests for demo pipeline feature engineering module."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from acd.demo.features import DemoFeatureEngineering


class TestDemoFeatureEngineering:
    """Test cases for DemoFeatureEngineering class."""

    def test_initialization(self):
        """Test DemoFeatureEngineering initialization."""
        feature_eng = DemoFeatureEngineering()

        assert feature_eng.feature_engine is None  # We don't need it for demo
        assert feature_eng.vmm_config is not None
        assert feature_eng.vmm_config.max_iters == 100
        assert feature_eng.vmm_config.tol == 1e-4
        assert feature_eng.vmm_config.step_initial == 0.01

    def test_prepare_vmm_windows(self):
        """Test VMM window preparation."""
        feature_eng = DemoFeatureEngineering()

        # Create test data
        test_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=150, freq="1min"),
                "firm_id": [f"firm_{i%5}" for i in range(150)],
                "price": [100 + i * 0.1 for i in range(150)],
                "volume": [1000 + i * 10 for i in range(150)],
            }
        )

        windows = feature_eng.prepare_vmm_windows(test_data, window_size=50)

        assert len(windows) == 3  # 150 / 50 = 3 windows
        for i, window in enumerate(windows):
            assert len(window) >= 25  # minimum window size
            assert "window_id" in window.columns
            assert "window_start" in window.columns
            assert "window_end" in window.columns
            assert window["window_id"].iloc[0] == f"window_{i:03d}"

    def test_prepare_vmm_windows_with_timestamp_sorting(self):
        """Test VMM window preparation with timestamp sorting."""
        feature_eng = DemoFeatureEngineering()

        # Create unsorted test data
        test_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=100, freq="1min")[
                    ::-1
                ],  # Reverse order
                "firm_id": [f"firm_{i%5}" for i in range(100)],
                "price": [100 + i * 0.1 for i in range(100)],
                "volume": [1000 + i * 10 for i in range(100)],
            }
        )

        windows = feature_eng.prepare_vmm_windows(test_data, window_size=50)

        # Check that timestamps are now sorted
        for window in windows:
            timestamps = pd.to_datetime(window["timestamp"])
            assert timestamps.is_monotonic_increasing

    def test_extract_vmm_features_price_based(self):
        """Test price-based feature extraction."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame(
            {"price": [100, 101, 102, 103, 104], "volume": [1000, 1010, 1020, 1030, 1040]}
        )

        features = feature_eng.extract_vmm_features(test_data)

        assert "price" in features
        assert "price_changes" in features
        assert "price_mean" in features
        assert "price_std" in features

        # Check price changes
        assert len(features["price_changes"]) == 4  # 5 prices -> 4 changes
        assert all(features["price_changes"] == 1)  # Each change is +1

        # Check rolling statistics
        assert len(features["price_mean"]) == 5
        assert features["price_mean"][0] == 100.0  # First element
        assert abs(features["price_mean"][-1] - 102.0) < 0.01  # Last element

    def test_extract_vmm_features_volume_based(self):
        """Test volume-based feature extraction."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame({"volume": [1000, 1010, 1020, 1030, 1040]})

        features = feature_eng.extract_vmm_features(test_data)

        assert "volume" in features
        assert "volume_changes" in features

        # Check volume changes
        assert len(features["volume_changes"]) == 4
        assert all(features["volume_changes"] == 10)  # Each change is +10

    def test_extract_vmm_features_bid_ask(self):
        """Test bid-ask spread feature extraction."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame(
            {"bid": [99.5, 100.5, 101.5, 102.5, 103.5], "ask": [100.5, 101.5, 102.5, 103.5, 104.5]}
        )

        features = feature_eng.extract_vmm_features(test_data)

        assert "spreads" in features
        assert "spread_changes" in features

        # Check spreads
        assert len(features["spreads"]) == 5
        assert all(features["spreads"] == 1.0)  # All spreads are 1.0

        # Check spread changes
        assert len(features["spread_changes"]) == 4
        assert all(features["spread_changes"] == 0.0)  # No changes in spreads

    def test_extract_vmm_features_firm_concentration(self):
        """Test firm concentration feature extraction."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame(
            {"firm_id": ["firm_1", "firm_2", "firm_1", "firm_3", "firm_2", "firm_1"]}
        )

        features = feature_eng.extract_vmm_features(test_data)

        assert "firm_concentration" in features

        # Check firm concentration (Herfindahl index)
        # 3 firms: firm_1 (3 obs), firm_2 (2 obs), firm_3 (1 obs)
        # Total: 6 obs
        # Concentration = (3/6)² + (2/6)² + (1/6)² = 0.25 + 0.11 + 0.03 = 0.39
        expected_concentration = (3 / 6) ** 2 + (2 / 6) ** 2 + (1 / 6) ** 2
        assert abs(features["firm_concentration"][0] - expected_concentration) < 0.01

    def test_reshape_for_vmm(self):
        """Test data reshaping for VMM analysis."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame(
            {
                "firm_id": ["firm_1", "firm_2", "firm_1", "firm_2", "firm_1"],
                "price": [100, 101, 102, 103, 104],
            }
        )

        features = {"price": np.array([100, 101, 102, 103, 104])}

        firm_matrix = feature_eng._reshape_for_vmm(test_data, features)

        # Should be 2 firms x 5 time points
        assert firm_matrix.shape == (2, 5)

        # Check firm_1 data (row 0) - firm_1 appears at positions 0, 2, 4
        assert firm_matrix[0, 0] == 100  # firm_1, time 0
        assert firm_matrix[0, 2] == 102  # firm_1, time 2
        assert firm_matrix[0, 4] == 104  # firm_1, time 4

        # Check firm_2 data (row 1) - firm_2 appears at positions 1, 3
        assert firm_matrix[1, 1] == 101  # firm_2, time 1
        assert firm_matrix[1, 3] == 103  # firm_2, time 3

        # Check that positions where firms don't appear are 0
        assert firm_matrix[0, 1] == 0  # firm_1 doesn't appear at time 1
        assert firm_matrix[0, 3] == 0  # firm_1 doesn't appear at time 3
        assert firm_matrix[1, 0] == 0  # firm_2 doesn't appear at time 0
        assert firm_matrix[1, 2] == 0  # firm_2 doesn't appear at time 2
        assert firm_matrix[1, 4] == 0  # firm_2 doesn't appear at time 4

    def test_reshape_for_vmm_missing_columns(self):
        """Test error handling for missing columns."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame({"price": [100, 101, 102]})  # Missing firm_id

        features = {"price": np.array([100, 101, 102])}

        with pytest.raises(ValueError, match="Missing required columns for VMM analysis"):
            feature_eng._reshape_for_vmm(test_data, features)

    def test_run_vmm_analysis_success(self):
        """Test successful VMM analysis."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame(
            {"firm_id": ["firm_1", "firm_2", "firm_1", "firm_2"], "price": [100, 101, 102, 103]}
        )

        # Mock successful VMM run
        with patch("acd.demo.features.run_vmm") as mock_run_vmm:
            mock_result = MagicMock()
            mock_result.metrics.regime_confidence = 0.7
            mock_result.metrics.structural_stability = 0.8
            mock_result.convergence_status = "converged"
            mock_run_vmm.return_value = mock_result

            result = feature_eng.run_vmm_analysis(test_data)

            assert result == mock_result
            mock_run_vmm.assert_called_once()

    def test_run_vmm_analysis_fallback(self):
        """Test VMM analysis fallback when analysis fails."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame({"firm_id": ["firm_1", "firm_2"], "price": [100, 101]})

        # Mock failed VMM run
        with patch("acd.demo.features.run_vmm") as mock_run_vmm:
            mock_run_vmm.side_effect = Exception("VMM failed")

            result = feature_eng.run_vmm_analysis(test_data)

            # Should return dummy result
        assert result.convergence_status == "failed"
        assert result.regime_confidence == 0.5
        assert result.structural_stability == 0.5

    def test_create_dummy_vmm_result(self):
        """Test dummy VMM result creation."""
        feature_eng = DemoFeatureEngineering()

        test_data = pd.DataFrame(
            {"window_id": "test_window", "firm_id": ["firm_1", "firm_2"], "price": [100, 101]}
        )

        result = feature_eng._create_dummy_vmm_result(test_data)

        assert result.window_size == 2  # 2 rows in test data
        assert result.regime_confidence == 0.5
        assert result.structural_stability == 0.5
        assert result.convergence_status == "failed"
        assert result.iterations == 0
        assert result.elbo_final == 0.0

    def test_prepare_evidence_data(self):
        """Test evidence data preparation."""
        feature_eng = DemoFeatureEngineering()

        # Create test window data
        test_data = pd.DataFrame(
            {
                "window_id": "test_window",
                "timestamp": pd.date_range("2024-01-01", periods=5, freq="1min"),
                "firm_id": ["firm_1"] * 5,
                "price": [100, 101, 102, 103, 104],
            }
        )

        # Create test VMM result
        vmm_result = feature_eng._create_dummy_vmm_result(test_data)

        # Create test quality metrics
        quality_metrics = {
            "completeness": 0.95,
            "accuracy": 0.90,
            "timeliness": 0.85,
            "consistency": 0.92,
            "overall": 0.91,
        }

        evidence_data = feature_eng.prepare_evidence_data(test_data, vmm_result, quality_metrics)

        # Check core identification
        assert "bundle_id" in evidence_data
        assert "creation_timestamp" in evidence_data
        assert "analysis_window_start" in evidence_data
        assert "analysis_window_end" in evidence_data
        assert evidence_data["market"] == "demo_market"

        # Check VMM outputs
        assert "vmm_outputs" in evidence_data
        assert evidence_data["vmm_outputs"]["regime_confidence"] == 0.5
        assert evidence_data["vmm_outputs"]["structural_stability"] == 0.5

        # Check data quality
        assert "data_quality" in evidence_data
        assert evidence_data["data_quality"]["overall_quality_score"] == 0.91

        # Check analysis configuration
        assert "vmm_config" in evidence_data
        assert evidence_data["vmm_config"]["max_iterations"] == 100
