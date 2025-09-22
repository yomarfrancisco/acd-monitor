"""
Provider Contract Tests

Tests that both Chatbase and Offline providers implement the same interface
and can be used interchangeably.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import providers
from src.agent.providers.chatbase_adapter import ChatbaseAdapter, AgentMessage, Health
from src.agent.providers.offline_mock import OfflineMockProvider


class TestProviderContract:
    """Test that both providers implement the same interface"""

    def test_chatbase_adapter_interface(self):
        """Test that ChatbaseAdapter implements required interface"""
        adapter = ChatbaseAdapter()

        # Test generate method signature
        assert hasattr(adapter, "generate")
        assert callable(adapter.generate)

        # Test healthcheck method signature
        assert hasattr(adapter, "healthcheck")
        assert callable(adapter.healthcheck)

        # Test generate method parameters
        import inspect

        sig = inspect.signature(adapter.generate)
        params = list(sig.parameters.keys())

        # Should have required parameters
        assert "prompt" in params
        assert "tools" in params
        assert "context" in params
        assert "stream" in params
        assert "session_id" in params
        assert "user_id" in params

    def test_offline_mock_interface(self):
        """Test that OfflineMockProvider implements required interface"""
        provider = OfflineMockProvider()

        # Test generate method signature
        assert hasattr(provider, "generate")
        assert callable(provider.generate)

        # Test healthcheck method signature
        assert hasattr(provider, "healthcheck")
        assert callable(provider.healthcheck)

        # Test generate method parameters
        import inspect

        sig = inspect.signature(provider.generate)
        params = list(sig.parameters.keys())

        # Should have required parameters
        assert "prompt" in params
        assert "tools" in params
        assert "context" in params
        assert "stream" in params
        assert "session_id" in params
        assert "user_id" in params

    def test_chatbase_generate_returns_agent_message(self):
        """Test that ChatbaseAdapter.generate returns AgentMessage"""
        adapter = ChatbaseAdapter()

        # Mock environment variables
        with patch.dict(
            os.environ, {"CHATBASE_API_KEY": "test_key", "CHATBASE_ASSISTANT_ID": "test_id"}
        ):
            result = adapter.generate(
                prompt="Test prompt",
                tools=None,
                context=None,
                stream=False,
                session_id="test_session",
                user_id="test_user",
            )

            assert isinstance(result, AgentMessage)
            assert hasattr(result, "content")
            assert hasattr(result, "session_id")
            assert hasattr(result, "usage")
            assert hasattr(result, "metadata")

    def test_offline_mock_generate_returns_agent_message(self):
        """Test that OfflineMockProvider.generate returns AgentMessage"""
        provider = OfflineMockProvider()

        result = provider.generate(
            prompt="Test prompt",
            tools=None,
            context=None,
            stream=False,
            session_id="test_session",
            user_id="test_user",
        )

        assert isinstance(result, AgentMessage)
        assert hasattr(result, "content")
        assert hasattr(result, "session_id")
        assert hasattr(result, "usage")
        assert hasattr(result, "metadata")

    def test_chatbase_healthcheck_returns_health(self):
        """Test that ChatbaseAdapter.healthcheck returns Health"""
        adapter = ChatbaseAdapter()

        result = adapter.healthcheck()

        assert isinstance(result, Health)
        assert hasattr(result, "status")
        assert hasattr(result, "details")
        assert hasattr(result, "last_check")

        # Status should be one of the expected values
        assert result.status in ["healthy", "degraded", "unhealthy"]

    def test_offline_mock_healthcheck_returns_health(self):
        """Test that OfflineMockProvider.healthcheck returns Health"""
        provider = OfflineMockProvider()

        result = provider.healthcheck()

        assert isinstance(result, Health)
        assert hasattr(result, "status")
        assert hasattr(result, "details")
        assert hasattr(result, "last_check")

        # Status should be one of the expected values
        assert result.status in ["healthy", "degraded", "unhealthy"]

    def test_provider_interchangeability(self):
        """Test that providers can be used interchangeably"""
        # Test with ChatbaseAdapter
        adapter = ChatbaseAdapter()
        adapter_result = adapter.generate(prompt="Test prompt")

        # Test with OfflineMockProvider
        provider = OfflineMockProvider()
        provider_result = provider.generate(prompt="Test prompt")

        # Both should return AgentMessage instances
        assert isinstance(adapter_result, AgentMessage)
        assert isinstance(provider_result, AgentMessage)

        # Both should have the same attributes
        assert hasattr(adapter_result, "content")
        assert hasattr(provider_result, "content")
        assert hasattr(adapter_result, "session_id")
        assert hasattr(provider_result, "session_id")
        assert hasattr(adapter_result, "usage")
        assert hasattr(provider_result, "usage")
        assert hasattr(adapter_result, "metadata")
        assert hasattr(provider_result, "metadata")

    def test_error_handling_consistency(self):
        """Test that both providers handle errors consistently"""
        # Test ChatbaseAdapter with missing credentials
        adapter = ChatbaseAdapter()
        with patch.dict(os.environ, {}, clear=True):
            result = adapter.generate(prompt="Test prompt")
            assert isinstance(result, AgentMessage)
            assert "mock" in result.usage.get("mode", "").lower()

        # Test OfflineMockProvider with invalid artifacts directory
        provider = OfflineMockProvider(artifacts_dir="/nonexistent/directory")
        result = provider.generate(prompt="Test prompt")
        assert isinstance(result, AgentMessage)
        assert len(result.content) > 0  # Should still return some content

    def test_session_id_handling(self):
        """Test that both providers handle session IDs consistently"""
        # Test with provided session ID
        adapter = ChatbaseAdapter()
        result1 = adapter.generate(prompt="Test", session_id="custom_session")
        assert result1.session_id == "custom_session"

        provider = OfflineMockProvider()
        result2 = provider.generate(prompt="Test", session_id="custom_session")
        assert result2.session_id == "custom_session"

        # Test with auto-generated session ID
        result3 = adapter.generate(prompt="Test")
        assert result3.session_id is not None
        assert len(result3.session_id) > 0

        result4 = provider.generate(prompt="Test")
        assert result4.session_id is not None
        assert len(result4.session_id) > 0

    def test_usage_metadata_consistency(self):
        """Test that both providers return consistent usage metadata"""
        adapter = ChatbaseAdapter()
        adapter_result = adapter.generate(prompt="Test prompt")

        provider = OfflineMockProvider()
        provider_result = provider.generate(prompt="Test prompt")

        # Both should have usage information
        assert adapter_result.usage is not None
        assert provider_result.usage is not None

        # Both should have metadata
        assert adapter_result.metadata is not None
        assert provider_result.metadata is not None

        # Usage should indicate the provider mode
        assert "mode" in adapter_result.usage
        assert "mode" in provider_result.usage

        # Metadata should indicate the provider
        assert "provider" in adapter_result.metadata
        assert "provider" in provider_result.metadata


class TestProviderFactory:
    """Test the provider factory function"""

    def test_create_provider_default(self):
        """Test creating provider with default settings"""
        from src.agent.providers.chatbase_adapter import create_provider

        # Test with default (should be chatbase)
        provider = create_provider()
        assert isinstance(provider, ChatbaseAdapter)

    def test_create_provider_chatbase(self):
        """Test creating Chatbase provider explicitly"""
        from src.agent.providers.chatbase_adapter import create_provider

        provider = create_provider("chatbase")
        assert isinstance(provider, ChatbaseAdapter)

    def test_create_provider_unknown_fallback(self):
        """Test creating provider with unknown type falls back to chatbase"""
        from src.agent.providers.chatbase_adapter import create_provider

        provider = create_provider("unknown_provider")
        assert isinstance(provider, ChatbaseAdapter)

    def test_health_check_function(self):
        """Test the convenience health check function"""
        from src.agent.providers.chatbase_adapter import check_provider_health

        health = check_provider_health("chatbase")
        assert isinstance(health, Health)
        assert hasattr(health, "status")
        assert hasattr(health, "details")
        assert hasattr(health, "last_check")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
