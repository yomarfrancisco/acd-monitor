"""
ATP Golden File Tests

This module contains golden file tests to ensure the ATP analysis
reproduces expected coordination patterns and maintains consistency
across runs.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import json
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from cases.atp.prepare_data import prepare_atp_data, ATPConfig
from cases.atp.run_analysis import run_atp_analysis


class TestATPGoldenFiles:
    """Test suite for ATP golden file validation"""

    @pytest.fixture
    def atp_data(self):
        """Generate ATP data for testing"""
        config = ATPConfig(seed=42)
        return prepare_atp_data(config)

    @pytest.fixture
    def atp_results(self, atp_data):
        """Run ATP analysis and return results"""
        # Save data temporarily
        temp_data_path = "temp_atp_data.csv"
        atp_data.to_csv(temp_data_path, index=False)

        try:
            results = run_atp_analysis(temp_data_path, seed=42)
            return results
        finally:
            # Clean up temp file
            Path(temp_data_path).unlink(missing_ok=True)

    def test_atp_data_structure(self, atp_data):
        """Test that ATP data has expected structure"""
        # Check required columns
        required_columns = ["date", "volatility_regime", "market_condition", "coordination_period"]
        airline_columns = [col for col in atp_data.columns if col.startswith("Airline_")]

        assert len(airline_columns) == 4, f"Expected 4 airlines, got {len(airline_columns)}"

        for col in required_columns:
            assert col in atp_data.columns, f"Missing required column: {col}"

        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(
            atp_data["date"]
        ), "Date column should be datetime"
        assert (
            atp_data["volatility_regime"].isin(["low", "high"]).all()
        ), "Invalid volatility regime values"
        assert (
            atp_data["market_condition"].isin(["bullish", "bearish"]).all()
        ), "Invalid market condition values"
        assert (
            atp_data["coordination_period"].dtype == bool
        ), "Coordination period should be boolean"

        # Check coordination periods exist
        assert atp_data["coordination_period"].sum() > 0, "Should have coordination periods"

        # Check price data
        for airline in airline_columns:
            assert atp_data[airline].dtype in [
                np.float64,
                np.int64,
            ], f"Price data should be numeric for {airline}"
            assert (atp_data[airline] > 0).all(), f"All prices should be positive for {airline}"

    def test_atp_coordination_patterns(self, atp_data):
        """Test that ATP data shows expected coordination patterns"""
        airline_columns = [col for col in atp_data.columns if col.startswith("Airline_")]

        # Check that coordination periods have higher prices
        coordination_prices = atp_data[atp_data["coordination_period"]][airline_columns].mean()
        non_coordination_prices = atp_data[~atp_data["coordination_period"]][airline_columns].mean()

        # Coordination periods should have higher average prices
        for airline in airline_columns:
            assert (
                coordination_prices[airline] > non_coordination_prices[airline]
            ), f"Coordination periods should have higher prices for {airline}"

        # Check lead-lag pattern (Airline_0 should lead others)
        lead_airline = "Airline_0"
        follower_airlines = [col for col in airline_columns if col != lead_airline]

        # Calculate correlation between lead and followers during coordination
        coordination_data = atp_data[atp_data["coordination_period"]]

        for follower in follower_airlines:
            correlation = coordination_data[lead_airline].corr(coordination_data[follower])
            assert (
                correlation > 0.5
            ), f"Lead-follower correlation should be high during coordination: {correlation:.3f}"

    def test_atp_analysis_reproducibility(self, atp_results):
        """Test that ATP analysis is reproducible"""
        # Check that results are not None
        assert atp_results is not None, "Analysis should return results"

        # Check that all major components are present
        required_components = ["icp", "vmm", "validation", "integrated", "report"]
        for component in required_components:
            assert component in atp_results, f"Missing analysis component: {component}"

        # Check ICP results
        icp_result = atp_results["icp"]
        assert (
            icp_result["status"] == "success"
        ), f"ICP analysis failed: {icp_result.get('error', 'Unknown error')}"
        assert "invariance_p_value" in icp_result, "ICP should have invariance p-value"
        assert "power" in icp_result, "ICP should have power calculation"

        # Check VMM results
        vmm_result = atp_results["vmm"]
        assert (
            vmm_result["status"] == "success"
        ), f"VMM analysis failed: {vmm_result.get('error', 'Unknown error')}"
        assert (
            "over_identification_p_value" in vmm_result
        ), "VMM should have over-identification p-value"
        assert "structural_stability" in vmm_result, "VMM should have structural stability"

        # Check validation layers
        validation = atp_results["validation"]
        required_layers = ["lead_lag", "mirroring", "hmm", "infoflow"]
        for layer in required_layers:
            assert layer in validation, f"Missing validation layer: {layer}"
            assert validation[layer]["status"] == "success", f"{layer} analysis failed"

    def test_atp_coordination_detection(self, atp_results):
        """Test that ATP analysis detects coordination patterns"""
        summary = atp_results.get("report", {}).get("summary", {})

        # Should detect coordination (since we generated coordinated data)
        assert summary.get("coordination_detected", False), "Should detect coordination in ATP data"

        # Should have key findings
        key_findings = summary.get("key_findings", [])
        assert len(key_findings) > 0, "Should have key findings"

        # Check specific coordination indicators
        indicators = atp_results.get("report", {}).get("coordination_indicators", {})

        # Lead-lag should show low switching entropy (persistent leadership)
        lead_lag = indicators.get("lead_lag_persistence")
        if lead_lag:
            assert lead_lag["switching_entropy"] < 1.0, "Should show some leadership persistence"

        # Mirroring should show coordination
        mirroring = indicators.get("mirroring_coordination")
        if mirroring:
            assert mirroring["coordination_score"] > 0, "Should show some coordination score"
            assert mirroring["mirroring_ratio"] >= 0, "Should have mirroring ratio"

        # HMM should show regime stability
        hmm = indicators.get("regime_stability")
        if hmm:
            assert hmm["regime_stability"] >= 0, "Should have regime stability score"

    def test_atp_statistical_significance(self, atp_results):
        """Test statistical significance of ATP results"""
        significance = atp_results.get("report", {}).get("statistical_significance", {})

        # ICP should show some significance
        icp_p = significance.get("icp_p_value")
        if icp_p is not None:
            assert 0 <= icp_p <= 1, f"ICP p-value should be between 0 and 1: {icp_p}"

        # VMM should show some significance
        vmm_p = significance.get("vmm_p_value")
        if vmm_p is not None:
            assert 0 <= vmm_p <= 1, f"VMM p-value should be between 0 and 1: {vmm_p}"

        # Granger tests should show some significance
        granger_p = significance.get("granger_p_values")
        if granger_p is not None:
            assert 0 <= granger_p <= 1, f"Granger p-value should be between 0 and 1: {granger_p}"

    def test_atp_environment_analysis(self, atp_results):
        """Test environment-specific analysis"""
        env_analysis = atp_results.get("report", {}).get("environment_analysis", {})

        # Should have volatility regimes
        assert "volatility_regimes" in env_analysis, "Should analyze volatility regimes"
        assert "low" in env_analysis["volatility_regimes"], "Should have low volatility regime"
        assert "high" in env_analysis["volatility_regimes"], "Should have high volatility regime"

        # Should have market conditions
        assert "market_conditions" in env_analysis, "Should analyze market conditions"
        assert (
            "bullish" in env_analysis["market_conditions"]
        ), "Should have bullish market condition"
        assert (
            "bearish" in env_analysis["market_conditions"]
        ), "Should have bearish market condition"

        # Should detect coordination periods
        assert env_analysis.get("coordination_periods", False), "Should detect coordination periods"

    def test_atp_recommendations(self, atp_results):
        """Test that ATP analysis generates appropriate recommendations"""
        recommendations = atp_results.get("report", {}).get("recommendations", [])

        assert len(recommendations) > 0, "Should generate recommendations"

        # Should include monitoring recommendation
        monitoring_recs = [rec for rec in recommendations if "monitor" in rec.lower()]
        assert len(monitoring_recs) > 0, "Should recommend monitoring"

        # Should include validation recommendation
        validation_recs = [rec for rec in recommendations if "validat" in rec.lower()]
        assert len(validation_recs) > 0, "Should recommend validation"

    def test_atp_artifacts_saved(self, atp_results):
        """Test that analysis artifacts are saved correctly"""
        artifacts_dir = Path("cases/atp/artifacts")

        # Check that artifacts directory exists
        assert artifacts_dir.exists(), "Artifacts directory should exist"

        # Check for results JSON file
        results_files = list(artifacts_dir.glob("atp_analysis_results_seed_*.json"))
        assert len(results_files) > 0, "Should save results JSON file"

        # Check for report markdown file
        report_files = list(artifacts_dir.glob("atp_analysis_report_seed_*.md"))
        assert len(report_files) > 0, "Should save report markdown file"

        # Verify JSON file is valid
        if results_files:
            with open(results_files[0], "r") as f:
                saved_results = json.load(f)
            assert "report" in saved_results, "Saved results should include report"
            assert "icp" in saved_results, "Saved results should include ICP analysis"

    def test_atp_seed_reproducibility(self):
        """Test that ATP analysis is reproducible with same seed"""
        # Generate data with same seed
        config1 = ATPConfig(seed=42)
        data1 = prepare_atp_data(config1)

        config2 = ATPConfig(seed=42)
        data2 = prepare_atp_data(config2)

        # Data should be identical
        pd.testing.assert_frame_equal(data1, data2, "Data should be identical with same seed")

        # Run analysis with same seed
        temp_data_path1 = "temp_atp_data1.csv"
        temp_data_path2 = "temp_atp_data2.csv"

        try:
            data1.to_csv(temp_data_path1, index=False)
            data2.to_csv(temp_data_path2, index=False)

            results1 = run_atp_analysis(temp_data_path1, seed=42)
            results2 = run_atp_analysis(temp_data_path2, seed=42)

            # Results should be identical
            assert (
                results1["icp"]["invariance_p_value"] == results2["icp"]["invariance_p_value"]
            ), "ICP results should be identical with same seed"
            assert (
                results1["vmm"]["over_identification_p_value"]
                == results2["vmm"]["over_identification_p_value"]
            ), "VMM results should be identical with same seed"

        finally:
            # Clean up temp files
            for path in [temp_data_path1, temp_data_path2]:
                Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
