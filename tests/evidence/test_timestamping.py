"""
Unit tests for ACD Monitor timestamping system.

Tests TSA providers, circuit breakers, timestamp clients, and integration.
"""

import time

# from unittest.mock import Mock  # noqa: F401, patch, MagicMock
from datetime import datetime, timezone  # noqa: F401

from acd.evidence.timestamping import (  # noqa: F401
    TSAProvider,
    TimestampResponse,
    TimestampChain,
    CircuitBreaker,
    TSAClient,
    FreeTSAClient,
    DigiCertTSAClient,
    LocalTSAClient,
    create_timestamp_client,
)


class TestTSAProvider:
    """Test TSA provider configuration."""

    def test_tsa_provider_creation(self):
        """Test TSA provider creation with default values."""
        provider = TSAProvider(name="TestTSA", url="https://test.tsa.com", priority=1)

        assert provider.name == "TestTSA"
        assert provider.url == "https://test.tsa.com"
        assert provider.priority == 1
        assert provider.timeout == 30.0
        assert provider.max_retries == 3
        assert provider.circuit_breaker_threshold == 5
        assert provider.circuit_breaker_timeout == 60.0

    def test_tsa_provider_custom_values(self):
        """Test TSA provider creation with custom values."""
        provider = TSAProvider(
            name="CustomTSA",
            url="https://custom.tsa.com",
            priority=2,
            timeout=15.0,
            max_retries=5,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=30.0,
        )

        assert provider.timeout == 15.0
        assert provider.max_retries == 5
        assert provider.circuit_breaker_threshold == 3
        assert provider.circuit_breaker_timeout == 30.0


class TestTimestampResponse:
    """Test timestamp response functionality."""

    def test_timestamp_response_creation(self):
        """Test timestamp response creation."""
        timestamp = datetime.now(timezone.utc)
        response = TimestampResponse(
            timestamp=timestamp,
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="TestTSA",
            response_time_ms=150.0,
        )

        assert response.timestamp == timestamp
        assert response.tsa_certificate == b"test_cert"
        assert response.signature == b"test_signature"
        assert response.policy_oid == "1.2.3.4.5"
        assert response.serial_number == "test_001"
        assert response.tsa_cert_digest == "abc123"
        assert response.provider_name == "TestTSA"
        assert response.response_time_ms == 150.0
        assert response.status == "success"

    def test_timestamp_response_custom_status(self):
        """Test timestamp response with custom status."""
        response = TimestampResponse(
            timestamp=datetime.now(timezone.utc),
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="TestTSA",
            response_time_ms=150.0,
            status="failed",
        )

        assert response.status == "failed"


class TestTimestampChain:
    """Test timestamp chain functionality."""

    def test_timestamp_chain_creation(self):
        """Test timestamp chain creation."""
        chain = TimestampChain(bundle_checksum="test_hash")

        assert chain.bundle_checksum == "test_hash"
        assert len(chain.timestamp_responses) == 0
        assert isinstance(chain.timestamp_created, datetime)

    def test_add_response(self):
        """Test adding timestamp response to chain."""
        chain = TimestampChain(bundle_checksum="test_hash")
        response = TimestampResponse(
            timestamp=datetime.now(timezone.utc),
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="TestTSA",
            response_time_ms=150.0,
        )

        chain.add_response(response)

        assert len(chain.timestamp_responses) == 1
        assert chain.timestamp_responses[0] == response

    def test_get_latest_timestamp_empty(self):
        """Test getting latest timestamp from empty chain."""
        chain = TimestampChain(bundle_checksum="test_hash")

        latest = chain.get_latest_timestamp()
        assert latest is None

    def test_get_latest_timestamp_single(self):
        """Test getting latest timestamp from single response chain."""
        chain = TimestampChain(bundle_checksum="test_hash")
        timestamp = datetime.now(timezone.utc)
        response = TimestampResponse(
            timestamp=timestamp,
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="TestTSA",
            response_time_ms=150.0,
        )

        chain.add_response(response)
        latest = chain.get_latest_timestamp()

        assert latest == timestamp

    def test_get_latest_timestamp_multiple(self):
        """Test getting latest timestamp from multiple response chain."""
        chain = TimestampChain(bundle_checksum="test_hash")

        # Add responses with different timestamps
        timestamp1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        timestamp2 = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        response1 = TimestampResponse(
            timestamp=timestamp1,
            tsa_certificate=b"test_cert1",
            signature=b"test_signature1",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="TestTSA1",
            response_time_ms=150.0,
        )

        response2 = TimestampResponse(
            timestamp=timestamp2,
            tsa_certificate=b"test_cert2",
            signature=b"test_signature2",
            policy_oid="1.2.3.4.5",
            serial_number="test_002",
            tsa_cert_digest="def456",
            provider_name="TestTSA2",
            response_time_ms=200.0,
        )

        chain.add_response(response1)
        chain.add_response(response2)

        latest = chain.get_latest_timestamp()
        assert latest == timestamp2

    def test_verify_chain_empty(self):
        """Test verifying empty timestamp chain."""
        chain = TimestampChain(bundle_checksum="test_hash")

        result = chain.verify_chain()

        assert result["valid"] is False
        assert "No timestamp responses" in result["error"]

    @patch("acd.evidence.timestamping.x509.load_der_x509_certificate")
    def test_verify_chain_success(self, mock_load_cert):
        """Test successful timestamp chain verification."""
        chain = TimestampChain(bundle_checksum="test_hash")

        # Mock certificate loading
        mock_cert = Mock()
        mock_load_cert.return_value = mock_cert

        response = TimestampResponse(
            timestamp=datetime.now(timezone.utc),
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="TestTSA",
            response_time_ms=150.0,
        )

        chain.add_response(response)
        result = chain.verify_chain()

        assert result["valid"] is True
        assert result["chain_length"] == 1
        assert len(result["responses"]) == 1
        assert result["responses"][0]["provider"] == "TestTSA"
        assert result["responses"][0]["cert_valid"] is True
        assert result["responses"][0]["signature_valid"] is True


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_creation(self):
        """Test circuit breaker creation."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)

        assert cb.failure_threshold == 3
        assert cb.timeout == 60.0
        assert cb.failure_count == 0
        assert cb.last_failure_time == 0
        assert cb.state == "CLOSED"

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)

        # Mock successful function
        def success_func():
            return "success"

        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    def test_circuit_breaker_failure_accumulation(self):
        """Test circuit breaker failure accumulation."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)

        # Mock failing function
        def fail_func():
            raise Exception("Test failure")

        # First two failures should not open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(fail_func)

        assert cb.state == "CLOSED"
        assert cb.failure_count == 2

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)

        # Mock failing function
        def fail_func():
            raise Exception("Test failure")

        # Third failure should open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(fail_func)

        assert cb.state == "OPEN"
        assert cb.failure_count == 3

    def test_circuit_breaker_blocks_when_open(self):
        """Test circuit breaker blocks requests when open."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60.0)
        cb.state = "OPEN"
        cb.last_failure_time = time.time()

        # Mock function
        def test_func():
            return "should not execute"

        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            cb.call(test_func)

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open recovery."""
        cb = CircuitBreaker(failure_threshold=3, timeout=0.1)  # Short timeout for testing

        # Open circuit
        cb.state = "OPEN"
        cb.last_failure_time = time.time() - 0.2  # Past timeout

        # Mock successful function
        def success_func():
            return "success"

        # Should transition to half-open and then closed
        result = cb.call(success_func)

        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0


class TestTSAClients:
    """Test individual TSA client implementations."""

    @patch("acd.evidence.timestamping.requests.post")
    def test_freetsa_client_success(self, mock_post):
        """Test successful FreeTSA timestamping."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = FreeTSAClient(timeout=30.0)
        data = b"test data"

        response = client.get_timestamp(data)

        assert response.provider_name == "FreeTSA"
        assert response.policy_oid == "1.3.6.1.4.1.6449.1.2.1.5.1"
        assert response.serial_number == "freetsa_001"
        assert response.status == "success"

    @patch("acd.evidence.timestamping.requests.post")
    def test_freetsa_client_failure(self, mock_post):
        """Test FreeTSA timestamping failure."""
        mock_post.side_effect = Exception("Network error")

        client = FreeTSAClient(timeout=30.0)
        data = b"test data"

        with pytest.raises(Exception, match="Network error"):
            client.get_timestamp(data)

    def test_digicert_client_success(self):
        """Test successful DigiCert TSA timestamping."""
        client = DigiCertTSAClient(timeout=30.0)
        data = b"test data"

        response = client.get_timestamp(data)

        assert response.provider_name == "DigiCert"
        assert response.policy_oid == "1.3.6.1.4.1.6449.1.2.1.5.1"
        assert response.serial_number == "digicert_001"
        assert response.status == "success"

    def test_local_tsa_client_success(self, tmp_path):
        """Test successful local TSA timestamping."""
        key_path = tmp_path / "test_key.pem"
        client = LocalTSAClient(private_key_path=key_path)
        data = b"test data"

        response = client.get_timestamp(data)

        assert response.provider_name == "LocalTSA"
        assert response.policy_oid == "1.3.6.1.4.1.6449.1.2.1.5.1"
        assert response.serial_number == "local_001"
        assert response.status == "success"

        # Check that key files were created
        assert key_path.exists()
        assert (key_path.with_suffix(".pub")).exists()


class TestTimestampClient:
    """Test main timestamp client functionality."""

    def test_timestamp_client_creation(self):
        """Test timestamp client creation."""
        client = create_timestamp_client()

        assert len(client.providers) == 3
        assert len(client.circuit_breakers) == 3

        # Check provider priority order
        priorities = [p.priority for p in client.providers]
        assert priorities == [1, 2, 3]  # Sorted by priority

    def test_get_provider_status(self):
        """Test getting provider status."""
        client = create_timestamp_client()
        status = client.get_provider_status()

        assert "FreeTSA" in status
        assert "DigiCert" in status
        assert "LocalTSA" in status

        for provider_status in status.values():
            assert "priority" in provider_status
            assert "state" in provider_status
            assert "failure_count" in provider_status
            assert "url" in provider_status

    @patch("acd.evidence.timestamping.FreeTSAClient.get_timestamp")
    def test_get_timestamp_success_first_provider(self, mock_get_timestamp):
        """Test successful timestamping with first provider."""
        mock_response = TimestampResponse(
            timestamp=datetime.now(timezone.utc),
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_001",
            tsa_cert_digest="abc123",
            provider_name="FreeTSA",
            response_time_ms=150.0,
        )
        mock_get_timestamp.return_value = mock_response

        client = create_timestamp_client()
        data = b"test data"

        response = client.get_timestamp(data)

        assert response.provider_name == "FreeTSA"
        mock_get_timestamp.assert_called_once()

    @patch("acd.evidence.timestamping.FreeTSAClient.get_timestamp")
    @patch("acd.evidence.timestamping.DigiCertTSAClient.get_timestamp")
    def test_get_timestamp_fallback_to_second_provider(self, mock_digicert, mock_freetsa):
        """Test fallback to second provider when first fails."""
        # First provider fails
        mock_freetsa.side_effect = Exception("FreeTSA failed")

        # Second provider succeeds
        mock_response = TimestampResponse(
            timestamp=datetime.now(timezone.utc),
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_002",
            tsa_cert_digest="def456",
            provider_name="DigiCert",
            response_time_ms=200.0,
        )
        mock_digicert.return_value = mock_response

        client = create_timestamp_client()
        data = b"test data"

        response = client.get_timestamp(data)

        assert response.provider_name == "DigiCert"
        mock_freetsa.assert_called_once()
        mock_digicert.assert_called_once()

    @patch("acd.evidence.timestamping.FreeTSAClient.get_timestamp")
    @patch("acd.evidence.timestamping.DigiCertTSAClient.get_timestamp")
    @patch("acd.evidence.timestamping.LocalTSAClient.get_timestamp")
    def test_get_timestamp_fallback_to_local(self, mock_local, mock_digicert, mock_freetsa):
        """Test fallback to local TSA when external providers fail."""
        # External providers fail
        mock_freetsa.side_effect = Exception("FreeTSA failed")
        mock_digicert.side_effect = Exception("DigiCert failed")

        # Local TSA succeeds
        mock_response = TimestampResponse(
            timestamp=datetime.now(timezone.utc),
            tsa_certificate=b"test_cert",
            signature=b"test_signature",
            policy_oid="1.2.3.4.5",
            serial_number="test_003",
            tsa_cert_digest="ghi789",
            provider_name="LocalTSA",
            response_time_ms=50.0,
        )
        mock_local.return_value = mock_response

        client = create_timestamp_client()
        data = b"test data"

        response = client.get_timestamp(data)

        assert response.provider_name == "LocalTSA"
        mock_freetsa.assert_called_once()
        mock_digicert.assert_called_once()
        mock_local.assert_called_once()

    def test_timestamp_bundle(self):
        """Test timestamping an evidence bundle."""
        client = create_timestamp_client()
        data = b"test bundle data"
        checksum = "test_checksum"

        # Mock the get_timestamp method
        with patch.object(client, "get_timestamp") as mock_get_timestamp:
            mock_response = TimestampResponse(
                timestamp=datetime.now(timezone.utc),
                tsa_certificate=b"test_cert",
                signature=b"test_signature",
                policy_oid="1.2.3.4.5",
                serial_number="test_001",
                tsa_cert_digest="abc123",
                provider_name="FreeTSA",
                response_time_ms=150.0,
            )
            mock_get_timestamp.return_value = mock_response

            timestamp_chain = client.timestamp_bundle(data, checksum)

            assert timestamp_chain.bundle_checksum == checksum
            assert len(timestamp_chain.timestamp_responses) == 1
            assert timestamp_chain.timestamp_responses[0].provider_name == "FreeTSA"

    def test_get_timestamp_all_providers_fail(self):
        """Test timestamping when all providers fail."""
        client = create_timestamp_client()
        data = b"test data"

        # Mock all providers to fail
        with patch.object(client, "providers") as mock_providers:
            mock_providers.__iter__.return_value = []

            with pytest.raises(Exception, match="All timestamp providers failed"):
                client.get_timestamp(data)


if __name__ == "__main__":
    pytest.main([__file__])
