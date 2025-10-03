"""
Scripted Compliance Queries Tests

Tests for the 10 provided scripted compliance queries plus 5 additional
high-value queries for real compliance operations.
"""

from src.agent.providers.offline_mock import OfflineMockProvider


class TestScriptedComplianceQueries:
    """Test the 10 provided scripted compliance queries"""

    @pytest.fixture
    def offline_provider(self):
        """Create offline provider for testing"""
        return OfflineMockProvider()

    def test_query_1_mirroring_ratios(self, offline_provider):
        """Test: Show mirroring ratios vs. arbitrage controls for ETH/USD last week."""
        query = "Show mirroring ratios vs. arbitrage controls for ETH/USD last week."
        result = offline_provider.generate(prompt=query)

        assert "mirroring" in result.content.lower()
        assert "ratio" in result.content.lower()
        assert result.usage.get("intent") == "mirroring_analysis"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_2_price_leader(self, offline_provider):
        """Test: Which exchange acted as price leader for BTC/USD yesterday, and how persistent was that leadership?"""  # noqa: E501
        query = "Which exchange acted as price leader for BTC/USD yesterday, and how persistent was that leadership?"  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "lead" in result.content.lower() or "lag" in result.content.lower()
        assert result.usage.get("intent") == "lead_lag_analysis"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_3_spread_floors(self, offline_provider):
        """Test: Highlight any periods where spread floors emerged despite high volatility."""
        query = "Highlight any periods where spread floors emerged despite high volatility."
        result = offline_provider.generate(prompt=query)

        assert "spread" in result.content.lower()
        assert result.usage.get("intent") == "spread_floor_analysis"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_4_lead_lag_betas(self, offline_provider):
        """Test: Compare lead–lag betas between Binance and Coinbase over the last 24 hours."""
        query = "Compare lead–lag betas between Binance and Coinbase over the last 24 hours."
        result = offline_provider.generate(prompt=query)

        assert "lead" in result.content.lower() or "lag" in result.content.lower()
        assert result.usage.get("intent") == "lead_lag_analysis"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_5_risk_bands(self, offline_provider):
        """Test: Summarize coordination risk bands (LOW/AMBER/RED) across the top 3 venues for BTC/USD in the last week."""  # noqa: E501
        query = "Summarize coordination risk bands (LOW/AMBER/RED) across the top 3 venues for BTC/USD in the last week."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "risk" in result.content.lower() or "verdict" in result.content.lower()
        assert result.usage.get("intent") == "risk_assessment"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_6_alternative_explanations(self, offline_provider):
        """Test: List all alternative explanations that could account for the coordination signal flagged on 2025-09-15."""  # noqa: E501
        query = "List all alternative explanations that could account for the coordination signal flagged on 2025-09-15."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "alternative" in result.content.lower() or "explanation" in result.content.lower()
        assert (
            result.usage.get("intent") == "alternative_explanations"
        )  # Should detect alternative explanations intent
        assert result.usage.get("mode") == "offline_mock"

    def test_query_7_icp_invariance(self, offline_provider):
        """Test: Summarize ICP invariance results by environment for BTC/USD over the last 14 days; include FDR q-values and sample sizes."""  # noqa: E501
        query = "Summarize ICP invariance results by environment for BTC/USD over the last 14 days; include FDR q-values and sample sizes."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "icp" in result.content.lower()
        assert "invariance" in result.content.lower()
        assert result.usage.get("intent") == "icp_analysis"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_8_vmm_analysis(self, offline_provider):
        """Test: Report VMM over-identification p-values and stability for BTC/USD (seed 42), plus moment scaling provenance."""  # noqa: E501
        query = "Report VMM over-identification p-values and stability for BTC/USD (seed 42), plus moment scaling provenance."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "vmm" in result.content.lower()
        assert result.usage.get("intent") == "vmm_analysis"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_9_alternative_explanations_eth(self, offline_provider):
        """Test: Which alternative explanations (arbitrage latency, fee tiers, inventory shocks) were triggered for ETH/USD in the last 72h?"""  # noqa: E501
        query = "Which alternative explanations (arbitrage latency, fee tiers, inventory shocks) were triggered for ETH/USD in the last 72h?"  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "alternative" in result.content.lower() or "explanation" in result.content.lower()
        assert (
            result.usage.get("intent") == "alternative_explanations"
        )  # Should detect alternative explanations intent
        assert result.usage.get("mode") == "offline_mock"

    def test_query_10_screening_memo(self, offline_provider):
        """Test: Generate a screening memo for BTC/USD (past week): headline verdict (LOW/AMBER/RED), top drivers (lead-lag, mirroring, regimes), and caveats."""  # noqa: E501
        query = "Generate a screening memo for BTC/USD (past week): headline verdict (LOW/AMBER/RED), top drivers (lead-lag, mirroring, regimes), and caveats."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "risk" in result.content.lower() or "verdict" in result.content.lower()
        assert result.usage.get("intent") == "risk_assessment"
        assert result.usage.get("mode") == "offline_mock"


class TestAdditionalComplianceQueries:
    """Test 5 additional high-value compliance queries"""

    @pytest.fixture
    def offline_provider(self):
        """Create offline provider for testing"""
        return OfflineMockProvider()

    def test_query_11_mev_coordination(self, offline_provider):
        """Test: Analyze MEV bot coordination patterns in Ethereum mempool for the last 48 hours. Focus on sandwich attacks and front-running."""  # noqa: E501
        query = "Analyze MEV bot coordination patterns in Ethereum mempool for the last 48 hours. Focus on sandwich attacks and front-running."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "mev" in result.content.lower() or "coordination" in result.content.lower()
        assert result.usage.get("mode") == "offline_mock"
        # Should fall back to default since MEV-specific patterns aren't implemented yet

    def test_query_12_venue_comparison(self, offline_provider):
        """Test: Compare coordination risk scores across Binance, Coinbase, and Kraken for BTC/USD over the past 30 days. Rank venues by risk level."""  # noqa: E501
        query = "Compare coordination risk scores across Binance, Coinbase, and Kraken for BTC/USD over the past 30 days. Rank venues by risk level."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "risk" in result.content.lower() or "coordination" in result.content.lower()
        assert result.usage.get("intent") == "risk_assessment"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_13_rolling_weekly_summary(self, offline_provider):
        """Test: Generate a rolling weekly summary of coordination signals for ETH/USD. Include trend analysis and alert escalation recommendations."""  # noqa: E501
        query = "Generate a rolling weekly summary of coordination signals for ETH/USD. Include trend analysis and alert escalation recommendations."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "summary" in result.content.lower() or "coordination" in result.content.lower()
        assert result.usage.get("intent") == "risk_assessment"
        assert result.usage.get("mode") == "offline_mock"

    def test_query_14_alert_triage(self, offline_provider):
        """Test: Triage the coordination alerts from the last 24 hours. Prioritize by severity and provide recommended actions for each alert."""  # noqa: E501
        query = "Triage the coordination alerts from the last 24 hours. Prioritize by severity and provide recommended actions for each alert."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert "alert" in result.content.lower() or "coordination" in result.content.lower()
        assert result.usage.get("mode") == "offline_mock"
        # Should fall back to default since alert triage isn't implemented yet

    def test_query_15_regulatory_reporting(self, offline_provider):
        """Test: Prepare a regulatory reporting summary for Q3 2024 coordination monitoring. Include key findings, statistical significance, and compliance recommendations."""  # noqa: E501
        query = "Prepare a regulatory reporting summary for Q3 2024 coordination monitoring. Include key findings, statistical significance, and compliance recommendations."  # noqa: E501
        result = offline_provider.generate(prompt=query)

        assert (
            "regulatory" in result.content.lower()
            or "reporting" in result.content.lower()
            or "summary" in result.content.lower()
        )
        assert result.usage.get("intent") == "risk_assessment"
        assert result.usage.get("mode") == "offline_mock"


class TestQueryPerformance:
    """Test query performance and response quality"""

    @pytest.fixture
    def offline_provider(self):
        """Create offline provider for testing"""
        return OfflineMockProvider()

    def test_response_time(self, offline_provider):
        """Test that responses are generated quickly"""
        import time

        query = "Show mirroring ratios for BTC/USD last week"

        start_time = time.time()
        result = offline_provider.generate(prompt=query)
        end_time = time.time()

        response_time = end_time - start_time

        # Should respond within 1 second
        assert response_time < 1.0
        assert result.content is not None
        assert len(result.content) > 0

    def test_response_consistency(self, offline_provider):
        """Test that the same query produces consistent responses"""
        query = "Show mirroring ratios for BTC/USD last week"

        result1 = offline_provider.generate(prompt=query)
        result2 = offline_provider.generate(prompt=query)

        # Should have same intent detection
        assert result1.usage.get("intent") == result2.usage.get("intent")
        assert result1.usage.get("mode") == result2.usage.get("mode")

        # Content should be similar (may have slight variations due to timestamps)
        assert "mirroring" in result1.content.lower()
        assert "mirroring" in result2.content.lower()

    def test_error_handling(self, offline_provider):
        """Test error handling for various edge cases"""
        # Empty query
        result = offline_provider.generate(prompt="")
        assert result.content is not None
        assert len(result.content) > 0

        # Very long query
        long_query = "Test " * 1000
        result = offline_provider.generate(prompt=long_query)
        assert result.content is not None
        assert len(result.content) > 0

        # Special characters
        special_query = "Show results for BTC/USD with symbols: @#$%^&*()"
        result = offline_provider.generate(prompt=special_query)
        assert result.content is not None
        assert len(result.content) > 0

    def test_metadata_completeness(self, offline_provider):
        """Test that responses include complete metadata"""
        query = "Show mirroring ratios for BTC/USD last week"
        result = offline_provider.generate(prompt=query)

        # Check usage metadata
        assert result.usage is not None
        assert "mode" in result.usage
        assert "intent" in result.usage
        assert result.usage["mode"] == "offline_mock"

        # Check response metadata
        assert result.metadata is not None
        assert "provider" in result.metadata
        assert result.metadata["provider"] == "offline_mock"

        # Check session ID
        assert result.session_id is not None
        assert len(result.session_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
