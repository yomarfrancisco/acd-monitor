"""
Offline Provider End-to-End Tests

Tests the offline provider with scripted compliance queries to ensure
it can generate appropriate responses with metrics and provenance.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agent.providers.offline_mock import OfflineMockProvider
from src.agent.retrieval.loader import ACDArtifactLoader
from src.agent.retrieval.select import ACDArtifactSelector
from src.agent.compose.answer import ACDAnswerComposer


class TestOfflineE2E:
    """End-to-end tests for offline provider"""

    @pytest.fixture
    def temp_artifacts_dir(self):
        """Create temporary artifacts directory with test data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_path = Path(temp_dir) / "artifacts"
            artifacts_path.mkdir()

            # Create test validation data
            validation_data = {
                "mirroring": {
                    "coordination_score": 0.75,
                    "mirroring_ratio": 0.85,
                    "avg_cosine_similarity": 0.92,
                    "high_mirroring_pairs": 3,
                },
                "lead_lag": {
                    "switching_entropy": 0.45,
                    "significant_relationships": 4,
                    "avg_granger_p": 0.02,
                },
                "hmm": {
                    "regime_stability": 0.68,
                    "coordination_regime_score": 0.55,
                    "log_likelihood": -1250.5,
                },
                "infoflow": {
                    "coordination_network_score": 2.1,
                    "avg_transfer_entropy": 0.15,
                    "out_degree_concentration": 0.8,
                },
            }

            validation_file = artifacts_path / "validation_results.json"
            with open(validation_file, "w") as f:
                json.dump(validation_data, f)

            # Create test ICP data
            icp_data = {
                "invariance_p_value": 0.03,
                "power": 0.85,
                "n_environments": 2,
                "environment_sizes": [150, 200],
            }

            icp_file = artifacts_path / "icp_results.json"
            with open(icp_file, "w") as f:
                json.dump(icp_data, f)

            # Create test VMM data
            vmm_data = {
                "over_identification_p_value": 0.01,
                "structural_stability": 0.72,
                "n_moments": 17,
                "convergence_achieved": True,
            }

            vmm_file = artifacts_path / "vmm_results.json"
            with open(vmm_file, "w") as f:
                json.dump(vmm_data, f)

            # Create test integrated data
            integrated_data = {
                "composite_score": 65.5,
                "risk_band": "AMBER",
                "icp_contribution": 0.4,
                "vmm_contribution": 0.4,
                "crypto_contribution": 0.2,
            }

            integrated_file = artifacts_path / "integrated_results.json"
            with open(integrated_file, "w") as f:
                json.dump(integrated_data, f)

            yield str(artifacts_path)

    @pytest.fixture
    def offline_provider(self, temp_artifacts_dir):
        """Create offline provider with test artifacts"""
        return OfflineMockProvider(artifacts_dir=temp_artifacts_dir)

    def test_mirroring_analysis_query(self, offline_provider):
        """Test mirroring analysis query"""
        query = "Show mirroring ratios vs. arbitrage controls for ETH/USD last week."

        result = offline_provider.generate(prompt=query, session_id="test_session_1")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "mirroring" in result.content.lower()
        assert "ratio" in result.content.lower()

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "mirroring_analysis"

        # Verify session ID
        assert result.session_id == "test_session_1"

    def test_lead_lag_analysis_query(self, offline_provider):
        """Test lead-lag analysis query"""
        query = "Which exchange acted as price leader for BTC/USD yesterday, and how persistent was that leadership?"

        result = offline_provider.generate(prompt=query, session_id="test_session_2")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "lead" in result.content.lower() or "lag" in result.content.lower()
        assert "entropy" in result.content.lower() or "persistence" in result.content.lower()

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "lead_lag_analysis"

    def test_spread_floor_analysis_query(self, offline_provider):
        """Test spread floor analysis query"""
        query = "Highlight any periods where spread floors emerged despite high volatility."

        result = offline_provider.generate(prompt=query, session_id="test_session_3")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "spread" in result.content.lower()
        assert "regime" in result.content.lower() or "volatility" in result.content.lower()

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "spread_floor_analysis"

    def test_icp_analysis_query(self, offline_provider):
        """Test ICP analysis query"""
        query = "Summarize ICP invariance results by environment for BTC/USD over the last 14 days; include FDR q-values and sample sizes."

        result = offline_provider.generate(prompt=query, session_id="test_session_4")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "icp" in result.content.lower()
        assert "invariance" in result.content.lower()
        assert "environment" in result.content.lower()

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "icp_analysis"

    def test_vmm_analysis_query(self, offline_provider):
        """Test VMM analysis query"""
        query = "Report VMM over-identification p-values and stability for BTC/USD (seed 42), plus moment scaling provenance."

        result = offline_provider.generate(prompt=query, session_id="test_session_5")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "vmm" in result.content.lower()
        assert (
            "over-identification" in result.content.lower() or "stability" in result.content.lower()
        )

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "vmm_analysis"

    def test_risk_summary_query(self, offline_provider):
        """Test risk summary query"""
        query = "Generate a screening memo for BTC/USD (past week): headline verdict (LOW/AMBER/RED), top drivers (lead-lag, mirroring, regimes), and caveats."

        result = offline_provider.generate(prompt=query, session_id="test_session_6")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "risk" in result.content.lower() or "verdict" in result.content.lower()
        assert any(level in result.content.upper() for level in ["LOW", "AMBER", "RED"])

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "risk_summary"

    def test_artifacts_list_query(self, offline_provider):
        """Test artifacts list query"""
        query = "Show all artifacts and seeds used in the last run for BTC/USD; include file paths for audit."

        result = offline_provider.generate(prompt=query, session_id="test_session_7")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "artifacts" in result.content.lower()

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "artifacts_list"

    def test_general_query(self, offline_provider):
        """Test general query that doesn't match specific patterns"""
        query = "What can you tell me about the analysis results?"

        result = offline_provider.generate(prompt=query, session_id="test_session_8")

        # Verify response structure
        assert result.content is not None
        assert len(result.content) > 0
        assert "analysis" in result.content.lower()

        # Verify metadata
        assert result.usage is not None
        assert result.usage.get("mode") == "offline_mock"
        assert result.usage.get("intent") == "default"

    def test_health_check(self, offline_provider):
        """Test provider health check"""
        health = offline_provider.healthcheck()

        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert health.details is not None
        assert "provider" in health.details
        assert health.details["provider"] == "offline_mock"
        assert health.last_check is not None

    def test_error_handling(self, offline_provider):
        """Test error handling in provider"""
        # Test with empty prompt
        result = offline_provider.generate(prompt="")

        assert result.content is not None
        assert len(result.content) > 0

        # Test with very long prompt
        long_prompt = "Test " * 1000
        result = offline_provider.generate(prompt=long_prompt)

        assert result.content is not None
        assert len(result.content) > 0

    def test_artifact_loading_integration(self, temp_artifacts_dir):
        """Test integration with artifact loading"""
        loader = ACDArtifactLoader(temp_artifacts_dir)
        selector = ACDArtifactSelector(temp_artifacts_dir)
        composer = ACDAnswerComposer()

        # Test artifact loading
        available_artifacts = loader.list_available_artifacts()
        assert len(available_artifacts) > 0

        # Test artifact selection
        query = "Show mirroring analysis results"
        selection_result = selector.select_artifacts(query)

        assert "selected_artifacts" in selection_result
        assert "intent" in selection_result

        # Test answer composition
        if selection_result["selected_artifacts"]:
            answer = composer.compose_answer(
                query=query,
                selected_artifacts=selection_result["selected_artifacts"],
                intent=selection_result["intent"],
            )

            assert answer.content is not None
            assert len(answer.content) > 0
            assert answer.confidence >= 0.0
            assert answer.confidence <= 1.0


class TestScriptedComplianceQueries:
    """Test the specific scripted compliance queries"""

    @pytest.fixture
    def offline_provider(self):
        """Create offline provider for compliance query tests"""
        return OfflineMockProvider()

    def test_scripted_query_1(self, offline_provider):
        """Test: Show mirroring ratios vs. arbitrage controls for ETH/USD last week."""
        query = "Show mirroring ratios vs. arbitrage controls for ETH/USD last week."
        result = offline_provider.generate(prompt=query)

        assert "mirroring" in result.content.lower()
        assert "ratio" in result.content.lower()
        assert result.usage.get("intent") == "mirroring_analysis"

    def test_scripted_query_2(self, offline_provider):
        """Test: Which exchange acted as price leader for BTC/USD yesterday, and how persistent was that leadership?"""
        query = "Which exchange acted as price leader for BTC/USD yesterday, and how persistent was that leadership?"
        result = offline_provider.generate(prompt=query)

        assert "lead" in result.content.lower() or "lag" in result.content.lower()
        assert result.usage.get("intent") == "lead_lag_analysis"

    def test_scripted_query_3(self, offline_provider):
        """Test: Highlight any periods where spread floors emerged despite high volatility."""
        query = "Highlight any periods where spread floors emerged despite high volatility."
        result = offline_provider.generate(prompt=query)

        assert "spread" in result.content.lower()
        assert result.usage.get("intent") == "spread_floor_analysis"

    def test_scripted_query_4(self, offline_provider):
        """Test: Compare lead–lag betas between Binance and Coinbase over the last 24 hours."""
        query = "Compare lead–lag betas between Binance and Coinbase over the last 24 hours."
        result = offline_provider.generate(prompt=query)

        assert "lead" in result.content.lower() or "lag" in result.content.lower()
        assert result.usage.get("intent") == "lead_lag_analysis"

    def test_scripted_query_5(self, offline_provider):
        """Test: Summarize coordination risk bands (LOW/AMBER/RED) across the top 3 venues for BTC/USD in the last week."""
        query = "Summarize coordination risk bands (LOW/AMBER/RED) across the top 3 venues for BTC/USD in the last week."
        result = offline_provider.generate(prompt=query)

        assert "risk" in result.content.lower() or "verdict" in result.content.lower()
        assert result.usage.get("intent") == "risk_summary"

    def test_scripted_query_6(self, offline_provider):
        """Test: List all alternative explanations that could account for the coordination signal flagged on 2025-09-15."""
        query = "List all alternative explanations that could account for the coordination signal flagged on 2025-09-15."
        result = offline_provider.generate(prompt=query)

        assert "alternative" in result.content.lower() or "explanation" in result.content.lower()
        assert result.usage.get("intent") == "default"  # Should fall back to default

    def test_scripted_query_7(self, offline_provider):
        """Test: Summarize ICP invariance results by environment for BTC/USD over the last 14 days; include FDR q-values and sample sizes."""
        query = "Summarize ICP invariance results by environment for BTC/USD over the last 14 days; include FDR q-values and sample sizes."
        result = offline_provider.generate(prompt=query)

        assert "icp" in result.content.lower()
        assert "invariance" in result.content.lower()
        assert result.usage.get("intent") == "icp_analysis"

    def test_scripted_query_8(self, offline_provider):
        """Test: Report VMM over-identification p-values and stability for BTC/USD (seed 42), plus moment scaling provenance."""
        query = "Report VMM over-identification p-values and stability for BTC/USD (seed 42), plus moment scaling provenance."
        result = offline_provider.generate(prompt=query)

        assert "vmm" in result.content.lower()
        assert result.usage.get("intent") == "vmm_analysis"

    def test_scripted_query_9(self, offline_provider):
        """Test: Which alternative explanations (arbitrage latency, fee tiers, inventory shocks) were triggered for ETH/USD in the last 72h?"""
        query = "Which alternative explanations (arbitrage latency, fee tiers, inventory shocks) were triggered for ETH/USD in the last 72h?"
        result = offline_provider.generate(prompt=query)

        assert "alternative" in result.content.lower() or "explanation" in result.content.lower()
        assert result.usage.get("intent") == "default"  # Should fall back to default

    def test_scripted_query_10(self, offline_provider):
        """Test: Generate a screening memo for BTC/USD (past week): headline verdict (LOW/AMBER/RED), top drivers (lead-lag, mirroring, regimes), and caveats."""
        query = "Generate a screening memo for BTC/USD (past week): headline verdict (LOW/AMBER/RED), top drivers (lead-lag, mirroring, regimes), and caveats."
        result = offline_provider.generate(prompt=query)

        assert "risk" in result.content.lower() or "verdict" in result.content.lower()
        assert result.usage.get("intent") == "risk_summary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
