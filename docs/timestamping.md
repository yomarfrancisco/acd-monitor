# RFC3161 Timestamping System

## Overview

The ACD Monitor implements a robust RFC3161 timestamping system to provide cryptographic proof of when evidence bundles were created. This system ensures regulatory compliance and provides non-repudiation for all analysis results.

## Architecture

### Multi-Service Provider Design

The timestamping system uses a fallback architecture with multiple TSA (Timestamp Authority) providers:

1. **FreeTSA.org** (Primary) - Free, public timestamping service
2. **DigiCert TSA** (Secondary) - Commercial timestamping service
3. **Local TSA** (Fallback) - Offline signing capability for high-availability scenarios

### Circuit Breaker Pattern

Each TSA provider is protected by a circuit breaker that:
- Monitors failure rates
- Opens circuit after threshold failures
- Automatically recovers after timeout period
- Prevents cascading failures

## Components

### TimestampClient

The main client class that orchestrates timestamping operations:

```python
from acd.evidence.timestamping import create_timestamp_client

# Create client with default configuration
client = create_timestamp_client()

# Get timestamp for data
response = client.get_timestamp(data_bytes)
```

### TSA Providers

#### FreeTSA Client

```python
from acd.evidence.timestamping import FreeTSAClient

client = FreeTSAClient(timeout=30.0)
response = client.get_timestamp(data)
```

**Features:**
- Free public service
- 30-second timeout
- JSON-based API
- Suitable for development and testing

#### DigiCert TSA Client

```python
from acd.evidence.timestamping import DigiCertTSAClient

client = DigiCertTSAClient(timeout=30.0)
response = client.get_timestamp(data)
```

**Features:**
- Commercial timestamping service
- RFC3161 compliant
- High reliability
- Suitable for production use

#### Local TSA Client

```python
from acd.evidence.timestamping import LocalTSAClient

client = LocalTSAClient(private_key_path="local_tsa_key.pem")
response = client.get_timestamp(data)
```

**Features:**
- Offline signing capability
- RSA-2048 key generation
- Self-signed certificates
- Emergency fallback option

### TimestampResponse

Represents a timestamp response from a TSA:

```python
@dataclass
class TimestampResponse:
    timestamp: datetime
    tsa_certificate: bytes
    signature: bytes
    policy_oid: str
    serial_number: str
    tsa_cert_digest: str
    provider_name: str
    response_time_ms: float
    status: str = "success"
```

### TimestampChain

Represents a chain of timestamp responses for an evidence bundle:

```python
@dataclass
class TimestampChain:
    timestamp_responses: List[TimestampResponse]
    bundle_checksum: str
    timestamp_created: datetime
    
    def get_latest_timestamp(self) -> Optional[datetime]
    def verify_chain(self) -> Dict[str, Any]
```

## Usage

### Basic Timestamping

```python
from acd.evidence.timestamping import create_timestamp_client

# Create client
client = create_timestamp_client()

# Timestamp data
data = b"evidence bundle content"
checksum = "sha256_hash_of_data"

timestamp_chain = client.timestamp_bundle(data, checksum)
```

### Provider Status Monitoring

```python
# Get status of all providers
status = client.get_provider_status()

for provider_name, provider_status in status.items():
    print(f"{provider_name}: {provider_status['state']}")
    print(f"  Failures: {provider_status['failure_count']}")
```

### Timestamp Verification

```python
# Verify timestamp chain
verification_result = timestamp_chain.verify_chain()

if verification_result["valid"]:
    print("✅ Timestamp chain verified successfully")
else:
    print("❌ Timestamp chain verification failed")
```

## CLI Usage

### Timestamp a Bundle

```bash
python scripts/timestamp_bundle.py --bundle demo/outputs/demo_bundle.json
```

### Verify Timestamps

```bash
python scripts/timestamp_bundle.py --bundle demo_bundle.json --verify
```

### Check Provider Status

```bash
python scripts/timestamp_bundle.py --providers
```

### Show Bundle Status

```bash
python scripts/timestamp_bundle.py --bundle demo_bundle.json --status
```

## Configuration

### Provider Configuration

```python
config = {
    "providers": [
        {
            "name": "FreeTSA",
            "url": "https://freetsa.org/tsr",
            "priority": 1,
            "timeout": 30.0,
            "max_retries": 3,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 60.0
        }
    ]
}

client = create_timestamp_client(config)
```

### Circuit Breaker Settings

- **Failure Threshold**: Number of failures before opening circuit
- **Timeout**: Time to wait before attempting recovery
- **State Transitions**: CLOSED → OPEN → HALF_OPEN → CLOSED

## Integration with Evidence Bundles

### Adding Timestamps to Bundles

```python
from acd.evidence.bundle import EvidenceBundle
from acd.evidence.timestamping import create_timestamp_client

# Create bundle
bundle = EvidenceBundle.create_demo_bundle(...)

# Timestamp bundle
client = create_timestamp_client()
timestamp_chain = client.timestamp_bundle(bundle_data, bundle.checksum)

# Add timestamp to bundle
bundle.timestamp_chain = timestamp_chain
```

### Bundle Fields

The `EvidenceBundle` now includes:

```python
@dataclass
class EvidenceBundle:
    # ... existing fields ...
    
    # Timestamping information
    timestamp_chain: Optional[TimestampChain] = None
```

## Error Handling

### Provider Failures

The system automatically handles provider failures:

1. **Primary failure**: Switch to secondary provider
2. **Secondary failure**: Use local TSA fallback
3. **All failures**: Raise exception with detailed error information

### Circuit Breaker States

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Circuit open, requests blocked
- **HALF_OPEN**: Testing recovery, limited requests allowed

### Retry Logic

- Exponential backoff with jitter
- Configurable retry counts per provider
- Graceful degradation to fallback providers

## Security Considerations

### Certificate Validation

- TSA certificate verification
- Policy OID validation
- Serial number tracking
- Certificate digest storage

### Signature Verification

- Cryptographic signature validation
- Hash algorithm verification
- Timestamp integrity checks

### Privacy

- No data content sent to external TSAs
- Only hash values transmitted
- Local fallback for sensitive data

## Performance

### Response Times

- **FreeTSA**: ~100-500ms (network dependent)
- **DigiCert**: ~200-800ms (network dependent)
- **Local TSA**: ~10-50ms (local processing)

### Throughput

- **Concurrent requests**: Limited by provider capacity
- **Batch processing**: Supported for multiple bundles
- **Caching**: TSA responses cached for verification

## Monitoring and Metrics

### Key Metrics

- Timestamp success rate
- Provider response times
- Circuit breaker state changes
- Failure rates by provider

### Logging

```python
import logging

logger = logging.getLogger("acd.evidence.timestamping")
logger.info("Timestamping bundle %s", bundle_id)
logger.warning("Provider %s failed, switching to fallback", provider_name)
```

## Troubleshooting

### Common Issues

1. **Network timeouts**: Check provider URLs and network connectivity
2. **Certificate errors**: Verify TSA certificate validity
3. **Circuit breaker open**: Wait for recovery timeout or reset manually

### Debug Mode

```python
import logging
logging.getLogger("acd.evidence.timestamping").setLevel(logging.DEBUG)
```

### Manual Recovery

```python
# Reset circuit breaker for specific provider
client.circuit_breakers["FreeTSA"].state = "CLOSED"
client.circuit_breakers["FreeTSA"].failure_count = 0
```

## Future Enhancements

### Planned Features

- **Multiple timestamp chains**: Support for multiple TSA providers per bundle
- **Timestamp renewal**: Automatic timestamp refresh before expiration
- **Audit logging**: Comprehensive audit trail for compliance
- **Performance optimization**: Connection pooling and request batching

### Integration Opportunities

- **Blockchain timestamps**: Integration with blockchain-based timestamping
- **Distributed TSA**: Peer-to-peer timestamping network
- **Custom policies**: Configurable timestamping policies per organization

## Compliance

### RFC3161 Compliance

- Full RFC3161 timestamp request/response support
- Policy OID and serial number tracking
- Certificate chain validation
- Signature verification

### Regulatory Requirements

- **GDPR**: Data integrity and non-repudiation
- **SOX**: Audit trail and timestamp verification
- **Basel III**: Risk assessment evidence preservation
- **MiFID II**: Transaction timestamping requirements

## References

- [RFC3161 - Internet X.509 Public Key Infrastructure Time-Stamp Protocol](https://tools.ietf.org/html/rfc3161)
- [FreeTSA.org Documentation](https://freetsa.org/)
- [DigiCert TSA Services](https://www.digicert.com/timestamping)
- [Cryptography Python Package](https://cryptography.io/)
