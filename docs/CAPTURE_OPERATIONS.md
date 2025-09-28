# Continuous Capture Operations

## Overview

This document describes the continuous capture system for collecting 30-minute tick data windows with 50% overlap (new window every 15 minutes) for BTC-USD and ETH-USD across multiple venues.

## Architecture

### Capture Components

1. **`scripts/capture/capture_window.py`** - Captures a single 30-minute window
2. **`scripts/capture/roll_capture.py`** - Continuous daemon for rolling capture
3. **`.github/workflows/capture_continuous.yml`** - GitHub Actions for automated capture
4. **Make targets** - Manual capture operations

### Data Flow

```
Exchange APIs → capture_window.py → S3 Storage → Analysis Pipeline
```

## S3 Data Layout

```
s3://acd-monitor-snapshots/snapshots/{symbol}/{yyyymmdd}/{HHMM}-{HHMM}/
├── OVERLAP.json                    # Window metadata
├── ticks/{venue}/part-*.parquet    # Tick data (append-friendly)
├── micro_controls.json             # Per-second aggregates
└── meta/provenance.json           # Capture metadata
```

## Enriched Schema

### Per-Tick Fields

**Core Data:**
- `ts_exchange` - UTC nanosecond timestamp
- `best_bid`, `best_ask` - Best bid/ask prices
- `bid_sz`, `ask_sz` - Bid/ask sizes
- `last_px`, `last_sz` - Last trade price/size

**Computed Fields:**
- `mid_px` - Mid price: (bid + ask) / 2
- `spread_bps` - Spread in basis points: (ask - bid) / mid * 10000
- `depth_5bps_bid/ask` - Depth within 5 bps bands
- `depth_10bps_bid/ask` - Depth within 10 bps bands
- `imbalance` - Order book imbalance: (bid_sz - ask_sz) / (bid_sz + ask_sz)
- `rv_5s`, `rv_30s` - Rolling realized volatility
- `ret_1s`, `ret_5s`, `ret_30s` - Log returns
- `trade_sign` - Trade direction (+1/-1/0)
- `notional_traded` - Trade notional value
- `maker_fee_bps`, `taker_fee_bps` - Fee rates
- `fee_tier` - Fee tier (retail/institutional)

**Quality Assurance:**
- `venue_id` - Venue identifier
- `coverage_flag` - Per-second coverage indicator
- `clock_skew_ms` - Clock skew measurement
- `seed`, `code_version`, `commit` - Provenance

### Per-Window Aggregates

**Micro Controls (1-second aggregates):**
- `spread_bps_mean/median/p95` - Spread statistics
- `rv_5s/rv_30s` - Volatility measures
- `depth_5bps_*` - Depth statistics
- `imbalance` - Order book imbalance
- `volume_sec` - Volume per second
- `ret_1s/5s/30s` - Return statistics
- `time_of_day` - Hour/minute/session
- `volatility_regime` - Volatility tercile
- `venue_mask` - Venue availability

## Operations

### Manual Capture

**Single Window:**
```bash
make capture-once SYMBOL=BTC-USD START=2025-09-28T10:00:00Z END=2025-09-28T10:30:00Z
```

**Continuous Daemon:**
```bash
make capture-daemon SYMBOLS=BTC-USD,ETH-USD
```

### Automated Capture

**GitHub Actions:**
- Runs every 15 minutes via cron schedule
- Captures 30-minute windows with 50% overlap
- Includes sanity checks and error handling
- Uploads logs and artifacts on failure

### Quality Assurance

**Coverage Requirements:**
- ≥95% coverage for included venues
- Venue masking for partial outages
- Clock skew monitoring
- Schema validation

**Error Handling:**
- Retry logic for API failures
- Graceful degradation for venue outages
- Comprehensive logging
- Alert notifications

## Cost Management

### Storage Optimization

- **Parquet + Snappy compression** for efficient storage
- **Append-friendly partitioning** for scalability
- **Selective 500ms capture** (optional, auto-disable if costly)
- **Raw tick data only** (no heavy transforms in capture)

### Rate Limiting

**Venue Rate Limits:**
- Binance: 1200 requests/minute
- Coinbase: 10 requests/second
- Kraken: 1 request/second
- OKX: 20 requests/second
- Bybit: 120 requests/minute

**Throttling Strategy:**
- Exponential backoff on rate limits
- Venue-specific retry policies
- Graceful degradation for overloaded venues

## Monitoring

### Health Checks

**Per-Window Validation:**
- Coverage ≥95% for included venues
- UTC monotonic timestamps
- Deduplication by (venue, timestamp)
- Clock skew within thresholds
- Schema compliance

**Alert Conditions:**
- Coverage <95%
- Clock skew > threshold
- Schema mismatch
- Upload failure
- API rate limit exceeded

### Observability

**Logs:**
- Capture success/failure per window
- Venue coverage statistics
- API rate limit status
- Error details and stack traces

**Metrics:**
- Windows captured per hour
- Venue coverage percentages
- API response times
- Storage usage

## Troubleshooting

### Common Issues

**API Failures:**
- Check rate limits and throttling
- Verify API credentials
- Monitor venue status pages

**Coverage Issues:**
- Check venue availability
- Verify time window alignment
- Review clock skew measurements

**Storage Issues:**
- Verify S3 permissions
- Check bucket capacity
- Monitor upload success rates

### Recovery Procedures

**Missed Windows:**
- Manual capture for specific time ranges
- Backfill procedures for data gaps
- Quality validation for recovered data

**Venue Outages:**
- Automatic venue masking
- Coverage threshold adjustments
- Alternative data sources

## Development

### Testing

**Unit Tests:**
```bash
make test-micro
```

**Integration Tests:**
```bash
make capture-once SYMBOL=BTC-USD START=2025-09-28T10:00:00Z END=2025-09-28T10:30:00Z
```

**Dry Run:**
```bash
python scripts/capture/capture_window.py --symbol BTC-USD --start 2025-09-28T10:00:00Z --end 2025-09-28T10:30:00Z --verbose
```

### Configuration

**Environment Variables:**
- `ACD_S3_BUCKET` - S3 bucket name
- `ACD_S3_PREFIX` - S3 prefix path
- `AWS_REGION` - AWS region
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials

**Venue Configuration:**
- API endpoints and rate limits
- Symbol mapping
- Authentication methods
- Retry policies

## Future Enhancements

### Planned Improvements

1. **Real API Integration** - Replace synthetic data with real exchange APIs
2. **Enhanced Monitoring** - Prometheus metrics and Grafana dashboards
3. **Data Validation** - Automated quality checks and alerts
4. **Cost Optimization** - Intelligent compression and lifecycle policies
5. **Multi-Region** - Cross-region replication for disaster recovery

### Scalability Considerations

1. **Horizontal Scaling** - Multiple capture instances
2. **Load Balancing** - Distribute API calls across instances
3. **Data Partitioning** - Optimize S3 storage patterns
4. **Caching** - Reduce API calls with intelligent caching

## Support

For issues or questions:
1. Check logs in GitHub Actions artifacts
2. Review S3 storage for data quality
3. Monitor venue API status pages
4. Contact development team for assistance
