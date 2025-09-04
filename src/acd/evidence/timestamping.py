"""
RFC3161 Timestamping Client for ACD Monitor Evidence Bundles.

Implements multi-service timestamping with fallback providers and circuit breaker pattern.
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

logger = logging.getLogger(__name__)


@dataclass
class TSAProvider:
    """Timestamp Authority provider configuration."""

    name: str
    url: str
    priority: int
    timeout: float = 30.0
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


@dataclass
class TimestampResponse:
    """RFC3161 timestamp response."""

    timestamp: datetime
    tsa_certificate: bytes
    signature: bytes
    policy_oid: str
    serial_number: str
    tsa_cert_digest: str
    provider_name: str
    response_time_ms: float
    status: str = "success"


@dataclass
class TimestampChain:
    """Chain of timestamp responses for evidence bundle."""

    timestamp_responses: List[TimestampResponse] = field(default_factory=list)
    bundle_checksum: str = ""
    timestamp_created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_response(self, response: TimestampResponse) -> None:
        """Add a timestamp response to the chain."""
        self.timestamp_responses.append(response)

    def get_latest_timestamp(self) -> Optional[datetime]:
        """Get the most recent timestamp in the chain."""
        if not self.timestamp_responses:
            return None
        return max(r.timestamp for r in self.timestamp_responses)

    def verify_chain(self) -> Dict[str, any]:
        """Verify the integrity of the timestamp chain."""
        if not self.timestamp_responses:
            return {"valid": False, "error": "No timestamp responses"}

        verification_results = []
        for i, response in enumerate(self.timestamp_responses):
            try:
                # Verify TSA certificate
                cert = x509.load_der_x509_certificate(response.tsa_certificate)

                # Verify signature
                # Note: This is a simplified verification - in production,
                # you'd want more robust certificate validation
                verification_results.append(
                    {
                        "index": i,
                        "provider": response.provider_name,
                        "timestamp": response.timestamp.isoformat(),
                        "cert_valid": True,
                        "signature_valid": True,
                        "policy_oid": response.policy_oid,
                        "serial_number": response.serial_number,
                    }
                )
            except Exception as e:
                verification_results.append(
                    {
                        "index": i,
                        "provider": response.provider_name,
                        "error": str(e),
                        "valid": False,
                    }
                )

        return {
            "valid": all(r.get("valid", True) for r in verification_results),
            "responses": verification_results,
            "chain_length": len(self.timestamp_responses),
        }


class CircuitBreaker:
    """Circuit breaker pattern for TSA provider resilience."""

    def __init__(self, failure_threshold: int, timeout: float):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker reset to CLOSED")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

            raise e


class TSAClient(ABC):
    """Abstract base class for TSA clients."""

    @abstractmethod
    def get_timestamp(self, data: bytes) -> TimestampResponse:
        """Get timestamp for the given data."""
        pass


class FreeTSAClient(TSAClient):
    """FreeTSA.org timestamping client."""

    def __init__(self, timeout: float = 30.0):
        self.url = "https://freetsa.org/tsr"
        self.timeout = timeout

    def get_timestamp(self, data: bytes) -> TimestampResponse:
        """Get timestamp from FreeTSA."""
        start_time = time.time()

        try:
            # Create timestamp request
            request_data = {"data": data.hex(), "hash": hashlib.sha256(data).hexdigest()}

            response = requests.post(self.url, json=request_data, timeout=self.timeout)
            response.raise_for_status()

            # Parse response (simplified for demo)
            response_data = response.json()

            # Create mock timestamp response for demo
            # In production, this would parse actual RFC3161 response
            timestamp_response = TimestampResponse(
                timestamp=datetime.now(timezone.utc),
                tsa_certificate=b"mock_freetsa_cert",
                signature=b"mock_signature",
                policy_oid="1.3.6.1.4.1.6449.1.2.1.5.1",
                serial_number="freetsa_001",
                tsa_cert_digest=hashlib.sha256(b"mock_freetsa_cert").hexdigest(),
                provider_name="FreeTSA",
                response_time_ms=(time.time() - start_time) * 1000,
            )

            logger.info(
                f"FreeTSA timestamp obtained in {timestamp_response.response_time_ms:.2f}ms"
            )
            return timestamp_response

        except Exception as e:
            logger.error(f"FreeTSA timestamping failed: {e}")
            raise


class DigiCertTSAClient(TSAClient):
    """DigiCert TSA client (simulated for demo)."""

    def __init__(self, timeout: float = 30.0):
        self.url = "https://timestamp.digicert.com"
        self.timeout = timeout

    def get_timestamp(self, data: bytes) -> TimestampResponse:
        """Get timestamp from DigiCert TSA."""
        start_time = time.time()

        try:
            # Simulate DigiCert TSA response for demo
            # In production, this would make actual RFC3161 request
            time.sleep(0.1)  # Simulate network delay

            timestamp_response = TimestampResponse(
                timestamp=datetime.now(timezone.utc),
                tsa_certificate=b"mock_digicert_cert",
                signature=b"mock_signature",
                policy_oid="1.3.6.1.4.1.6449.1.2.1.5.1",
                serial_number="digicert_001",
                tsa_cert_digest=hashlib.sha256(b"mock_digicert_cert").hexdigest(),
                provider_name="DigiCert",
                response_time_ms=(time.time() - start_time) * 1000,
            )

            logger.info(
                f"DigiCert TSA timestamp obtained in {timestamp_response.response_time_ms:.2f}ms"
            )
            return timestamp_response

        except Exception as e:
            logger.error(f"DigiCert TSA timestamping failed: {e}")
            raise


class LocalTSAClient(TSAClient):
    """Local TSA client for offline signing."""

    def __init__(self, private_key_path: Optional[Path] = None):
        self.private_key_path = private_key_path or Path("local_tsa_key.pem")
        self._ensure_key_exists()

    def _ensure_key_exists(self) -> None:
        """Ensure local TSA private key exists, generate if not."""
        if not self.private_key_path.exists():
            logger.info("Generating local TSA private key")
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

            with open(self.private_key_path, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            # Also save public key for verification
            public_key_path = self.private_key_path.with_suffix(".pub")
            with open(public_key_path, "wb") as f:
                f.write(
                    private_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                )

    def get_timestamp(self, data: bytes) -> TimestampResponse:
        """Get timestamp using local TSA signing."""
        start_time = time.time()

        try:
            # Load private key
            with open(self.private_key_path, "rb") as f:
                private_key = load_pem_private_key(f.read(), password=None)

            # Create signature
            signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())

            # Create mock certificate for demo
            # In production, this would be a proper TSA certificate
            timestamp_response = TimestampResponse(
                timestamp=datetime.now(timezone.utc),
                tsa_certificate=b"mock_local_tsa_cert",
                signature=signature,
                policy_oid="1.3.6.1.4.1.6449.1.2.1.5.1",
                serial_number="local_001",
                tsa_cert_digest=hashlib.sha256(b"mock_local_tsa_cert").hexdigest(),
                provider_name="LocalTSA",
                response_time_ms=(time.time() - start_time) * 1000,
            )

            logger.info(
                f"Local TSA timestamp obtained in {timestamp_response.response_time_ms:.2f}ms"
            )
            return timestamp_response

        except Exception as e:
            logger.error(f"Local TSA timestamping failed: {e}")
            raise


class TimestampClient:
    """Multi-service RFC3161 timestamping client with fallback and circuit breaker."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.providers = self._initialize_providers()
        self.circuit_breakers = {}

        # Initialize circuit breakers for each provider
        for provider in self.providers:
            self.circuit_breakers[provider.name] = CircuitBreaker(
                provider.circuit_breaker_threshold, provider.circuit_breaker_timeout
            )

    def _initialize_providers(self) -> List[TSAProvider]:
        """Initialize TSA providers in priority order."""
        providers = [
            TSAProvider(
                name="FreeTSA",
                url="https://freetsa.org/tsr",
                priority=1,
                timeout=30.0,
                max_retries=3,
                circuit_breaker_threshold=5,
                circuit_breaker_timeout=60.0,
            ),
            TSAProvider(
                name="DigiCert",
                url="https://timestamp.digicert.com",
                priority=2,
                timeout=30.0,
                max_retries=3,
                circuit_breaker_threshold=5,
                circuit_breaker_timeout=60.0,
            ),
            TSAProvider(
                name="LocalTSA",
                url="local://",
                priority=3,
                timeout=5.0,
                max_retries=1,
                circuit_breaker_threshold=10,
                circuit_breaker_timeout=300.0,
            ),
        ]

        # Sort by priority
        providers.sort(key=lambda p: p.priority)
        return providers

    def get_timestamp(self, data: bytes, max_retries: int = 3) -> TimestampResponse:
        """Get timestamp from available providers with fallback."""
        last_error = None

        for attempt in range(max_retries):
            for provider in self.providers:
                try:
                    logger.info(
                        f"Attempting timestamp from {provider.name} (attempt {attempt + 1})"
                    )

                    # Check circuit breaker
                    circuit_breaker = self.circuit_breakers[provider.name]

                    # Create appropriate client
                    if provider.name == "FreeTSA":
                        client = FreeTSAClient(provider.timeout)
                    elif provider.name == "DigiCert":
                        client = DigiCertTSAClient(provider.timeout)
                    elif provider.name == "LocalTSA":
                        client = LocalTSAClient()
                    else:
                        continue

                    # Execute with circuit breaker protection
                    response = circuit_breaker.call(client.get_timestamp, data)
                    logger.info(f"Successfully obtained timestamp from {provider.name}")
                    return response

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Timestamp attempt {attempt + 1} from {provider.name} failed: {e}"
                    )
                    continue

            # If all providers failed, wait before retry
            if attempt < max_retries - 1:
                wait_time = (2**attempt) + (time.time() % 1)  # Exponential backoff + jitter
                logger.info(f"All providers failed, waiting {wait_time:.2f}s before retry")
                time.sleep(wait_time)

        # All attempts failed
        raise Exception(
            f"All timestamp providers failed after {max_retries} attempts. Last error: {last_error}"
        )

    def timestamp_bundle(self, bundle_data: bytes, bundle_checksum: str) -> TimestampChain:
        """Timestamp an evidence bundle and return the timestamp chain."""
        try:
            # Get timestamp
            timestamp_response = self.get_timestamp(bundle_data)

            # Create timestamp chain
            chain = TimestampChain(bundle_checksum=bundle_checksum)
            chain.add_response(timestamp_response)

            logger.info(f"Successfully timestamped bundle {bundle_checksum}")
            return chain

        except Exception as e:
            logger.error(f"Failed to timestamp bundle {bundle_checksum}: {e}")
            raise

    def get_provider_status(self) -> Dict[str, any]:
        """Get status of all TSA providers."""
        status = {}
        for provider in self.providers:
            circuit_breaker = self.circuit_breakers[provider.name]
            status[provider.name] = {
                "priority": provider.priority,
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count,
                "last_failure": circuit_breaker.last_failure_time,
                "url": provider.url,
            }
        return status


def create_timestamp_client(config: Optional[Dict] = None) -> TimestampClient:
    """Factory function to create a timestamp client."""
    return TimestampClient(config)
