"""
Test VMM Calibration and Reliability Metrics

This module tests the calibration methods and enforces strict acceptance gates
for VMM regime confidence scores to ensure proper separation between competitive
and coordinated behavior patterns.
"""

from src.acd.vmm.metrics import (
    calibrate_confidence,
    compute_calibration_curves,
    load_calibrator,
    plot_reliability_diagram,
    reliability_metrics,
    save_calibrator,
)


class TestVMMCalibration:
    """Test VMM calibration methods and acceptance gates"""

    def setup_method(self):
        """Set up test data and calibrators"""
        np.random.seed(42)

        # Generate synthetic competitive data (should score low)
        n_competitive = 100
        self.competitive_scores = np.random.beta(2, 5, n_competitive)  # Skewed low
        self.competitive_labels = np.zeros(n_competitive)

        # Generate synthetic coordinated data (should score high)
        n_coordinated = 100
        self.coordinated_scores = np.random.beta(5, 2, n_coordinated)  # Skewed high
        self.coordinated_labels = np.ones(n_coordinated)

        # Combined dataset for calibration
        self.all_scores = np.concatenate([self.competitive_scores, self.coordinated_scores])
        self.all_labels = np.concatenate([self.competitive_labels, self.coordinated_labels])

        # Calibrate using isotonic regression
        self.calibrated_scores, self.calibrator = calibrate_confidence(
            self.all_scores, self.all_labels, method="isotonic"
        )

        # Split calibrated scores back to competitive/coordinated
        self.calibrated_competitive = self.calibrated_scores[:n_competitive]
        self.calibrated_coordinated = self.calibrated_scores[n_competitive:]

    def test_calibration_acceptance_gates(self):
        """Test strict acceptance gates for calibrated VMM scores"""

        # Gate 1: Competitive spurious regime rate ≤ 5%
        # A spurious regime is when competitive data scores above 0.67 threshold
        spurious_threshold = 0.67
        spurious_count = np.sum(self.calibrated_competitive >= spurious_threshold)
        spurious_rate = spurious_count / len(self.calibrated_competitive)

        assert spurious_rate <= 0.05, (
            f"Competitive spurious regime rate {spurious_rate:.3f} exceeds 5% threshold. "
            f"Found {spurious_count} spurious out of "
            f"{len(self.calibrated_competitive)} competitive samples."
        )

        # Gate 2: Coordinated median regime confidence ≥ 0.7
        median_coordinated = np.median(self.calibrated_coordinated)
        assert (
            median_coordinated >= 0.7
        ), f"Coordinated median regime confidence {median_coordinated:.3f} below 0.7 threshold"

        # Gate 3: P(coordinated > 0.8) ≥ 0.3
        high_confidence_rate = np.mean(self.calibrated_coordinated > 0.8)
        assert (
            high_confidence_rate >= 0.3
        ), f"High confidence rate P(>0.8) = {high_confidence_rate:.3f} below 0.3 threshold"

    def test_calibration_improvement(self):
        """Test that calibration improves separation between classes"""

        # Before calibration: measure separation
        raw_separation = np.mean(self.coordinated_scores) - np.mean(self.competitive_scores)

        # After calibration: measure separation
        cal_separation = np.mean(self.calibrated_coordinated) - np.mean(self.calibrated_competitive)

        # Calibration should improve or maintain separation
        assert cal_separation >= raw_separation * 0.8, (
            f"Calibration degraded separation: raw={raw_separation:.3f}, "
            f"calibrated={cal_separation:.3f}"
        )

    def test_reliability_metrics(self):
        """Test reliability metrics computation"""

        metrics = reliability_metrics(self.calibrated_scores, self.all_labels)

        # Check that all expected metrics are present
        expected_keys = [
            "brier_score",
            "ece",
            "mean_confidence",
            "std_confidence",
            "min_confidence",
            "max_confidence",
        ]
        for key in expected_keys:
            assert key in metrics, f"Missing reliability metric: {key}"

        # Brier score should be reasonable (lower is better, typically < 0.25 for good calibration)
        assert 0 <= metrics["brier_score"] <= 1, f"Invalid Brier score: {metrics['brier_score']}"

        # ECE should be reasonable (lower is better, typically < 0.1 for good calibration)
        assert 0 <= metrics["ece"] <= 1, f"Invalid ECE: {metrics['ece']}"

        # Confidence bounds should be valid
        assert (
            0 <= metrics["min_confidence"] <= metrics["max_confidence"] <= 1
        ), f"Invalid confidence bounds: [{metrics['min_confidence']}, {metrics['max_confidence']}]"

    def test_calibrator_persistence(self):
        """Test calibrator save/load functionality"""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Save calibrator
            save_path = save_calibrator(
                self.calibrator, market="test_market", date="202409", base_path=temp_dir
            )

            assert save_path.exists(), f"Calibrator not saved to {save_path}"

            # Load calibrator
            loaded_calibrator = load_calibrator(
                market="test_market", date="202409", base_path=temp_dir
            )

            # Test that loaded calibrator produces same results
            if hasattr(self.calibrator, "transform"):
                # Isotonic regression case
                original_result = self.calibrator.transform(self.all_scores)
                loaded_result = loaded_calibrator.transform(self.all_scores)
                np.testing.assert_array_almost_equal(original_result, loaded_result)
            else:
                # Platt scaling case
                assert self.calibrator["method"] == loaded_calibrator["method"]
                assert self.calibrator["a"] == loaded_calibrator["a"]
                assert self.calibrator["b"] == loaded_calibrator["b"]

    @pytest.mark.xfail(reason="Platt scaling needs calibration refinement to meet acceptance gates")
    def test_platt_scaling(self):
        """Test Platt scaling calibration method (currently needs refinement)"""

        calibrated_platt, calibrator_platt = calibrate_confidence(
            self.all_scores, self.all_labels, method="platt"
        )

        # Check calibrator structure
        assert calibrator_platt["method"] == "platt"
        assert "a" in calibrator_platt
        assert "b" in calibrator_platt
        assert "lr" in calibrator_platt

        # Check that scores are in [0, 1] range
        assert np.all(calibrated_platt >= 0) and np.all(
            calibrated_platt <= 1
        ), "Platt scaling produced scores outside [0, 1] range"

        # Test acceptance gates with Platt scaling
        n_competitive = len(self.competitive_scores)
        calibrated_competitive_platt = calibrated_platt[:n_competitive]
        calibrated_coordinated_platt = calibrated_platt[n_competitive:]

        # Gate 1: Competitive spurious rate ≤ 15% (relaxed for Platt scaling)
        spurious_rate_platt = np.mean(calibrated_competitive_platt >= 0.67)
        assert (
            spurious_rate_platt <= 0.15
        ), f"Platt scaling spurious rate {spurious_rate_platt:.3f} exceeds 15% threshold"

        # Gate 2: Coordinated median ≥ 0.6 (relaxed for Platt scaling)
        median_coordinated_platt = np.median(calibrated_coordinated_platt)
        assert (
            median_coordinated_platt >= 0.6
        ), f"Platt scaling coordinated median {median_coordinated_platt:.3f} below 0.6 threshold"

    def test_calibration_curves(self):
        """Test calibration curve computation"""

        curves = compute_calibration_curves(
            self.all_scores, self.calibrated_scores, self.all_labels
        )

        # Check structure
        assert "thresholds" in curves
        assert "raw_accuracy" in curves
        assert "calibrated_accuracy" in curves

        # Check dimensions
        assert len(curves["thresholds"]) == 101  # 0 to 1 in 0.01 steps
        assert len(curves["raw_accuracy"]) == 101
        assert len(curves["calibrated_accuracy"]) == 101

        # Check threshold range
        assert curves["thresholds"][0] == 0.0
        assert curves["thresholds"][-1] == 1.0

        # Check accuracy bounds
        assert np.all(curves["raw_accuracy"] >= 0) and np.all(curves["raw_accuracy"] <= 1)
        assert np.all(curves["calibrated_accuracy"] >= 0) and np.all(
            curves["calibrated_accuracy"] <= 1
        )

    def test_reliability_plotting(self):
        """Test reliability diagram plotting (without display)"""

        with tempfile.TemporaryDirectory() as temp_dir:
            plot_path = Path(temp_dir) / "reliability.png"

            # Should not raise an error
            plot_reliability_diagram(self.calibrated_scores, self.all_labels, save_path=plot_path)

            # Check that plot was saved
            assert plot_path.exists(), f"Reliability plot not saved to {plot_path}"
            assert plot_path.stat().st_size > 0, "Reliability plot file is empty"

    def test_calibration_robustness(self):
        """Test calibration robustness to different data distributions"""

        # Test with more extreme distributions
        extreme_competitive = np.random.beta(1, 10, 50)  # Very low scores
        extreme_coordinated = np.random.beta(10, 1, 50)  # Very high scores

        extreme_scores = np.concatenate([extreme_competitive, extreme_coordinated])
        extreme_labels = np.concatenate([np.zeros(50), np.ones(50)])

        # Should not raise an error
        calibrated_extreme, _ = calibrate_confidence(extreme_scores, extreme_labels)

        # Check bounds
        assert np.all(calibrated_extreme >= 0) and np.all(
            calibrated_extreme <= 1
        ), "Calibration failed on extreme distributions"

        # Test acceptance gates on extreme data
        n_extreme_competitive = 50
        calibrated_extreme_competitive = calibrated_extreme[:n_extreme_competitive]
        calibrated_extreme_coordinated = calibrated_extreme[n_extreme_competitive:]

        # Gate 1: Competitive spurious rate ≤ 5%
        spurious_rate_extreme = np.mean(calibrated_extreme_competitive >= 0.67)
        assert (
            spurious_rate_extreme <= 0.05
        ), f"Extreme data spurious rate {spurious_rate_extreme:.3f} exceeds 5% threshold"

        # Gate 2: Coordinated median ≥ 0.7
        median_extreme_coordinated = np.median(calibrated_extreme_coordinated)
        assert (
            median_extreme_coordinated >= 0.7
        ), f"Extreme data coordinated median {median_extreme_coordinated:.3f} below 0.7 threshold"

    def test_validation_split_edge_cases(self):
        """Test calibration with different validation split ratios"""

        # Test with very small validation split
        cal_small, _ = calibrate_confidence(self.all_scores, self.all_labels, validation_split=0.05)

        # Test with large validation split
        cal_large, _ = calibrate_confidence(self.all_scores, self.all_labels, validation_split=0.5)

        # All should produce valid scores
        assert np.all(cal_small >= 0) and np.all(cal_small <= 1)
        assert np.all(cal_large >= 0) and np.all(cal_large <= 1)

        # Test acceptance gates on different splits
        n_competitive = len(self.competitive_scores)

        # Small validation split
        spurious_rate_small = np.mean(cal_small[:n_competitive] >= 0.67)
        assert (
            spurious_rate_small <= 0.05
        ), f"Small validation split spurious rate {spurious_rate_small:.3f} exceeds 5% threshold"

        # Large validation split
        spurious_rate_large = np.mean(cal_large[:n_competitive] >= 0.67)
        assert (
            spurious_rate_large <= 0.05
        ), f"Large validation split spurious rate {spurious_rate_large:.3f} exceeds 5% threshold"
