# ACD Overlap Orchestrator

## Overview

The ACD Overlap Orchestrator is a robust real-time capture system that continuously monitors cryptocurrency exchanges for strict temporal overlap windows and automatically runs microstructure analyses when sufficient data is available.

## Key Features

### 🔄 **Real-Time Capture**
- Concurrent WebSocket connections to all 5 major exchanges
- Dual timestamp recording (exchange + local)
- Normalized tick data with bid/ask/mid prices
- Parquet partitioning for efficient storage

### 🎯 **Strict Overlap Detection**
- Rolling window monitoring every 30 seconds
- Policy hierarchy: BEST4≥30m → BEST4≥20m → BEST4≥10m → ALL5≥10m
- Continuous coverage validation (no gaps >1s)
- Hard abort on synthetic data

### ⚡ **Auto-Analysis**
- Automatic trigger when overlap found
- Spread compression analysis
- Information share analysis  
- Invariance matrix analysis
- Court-ready evidence generation

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Orchestrator  │───▶│  Overlap Monitor │───▶│ Auto-Analysis   │
│                 │    │                  │    │                 │
│ • WebSocket     │    │ • Rolling Check  │    │ • Spread        │
│ • REST APIs     │    │ • Policy Engine  │    │ • InfoShare     │
│ • Heartbeats    │    │ • Gap Detection  │    │ • Invariance    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Tick Storage   │    │  Overlap JSON    │    │ Evidence Files  │
│                 │    │                  │    │                 │
│ data/ticks/     │    │ exports/overlap  │    │ MANIFEST.json   │
│ <venue>/        │    │ .json            │    │ EVIDENCE.md     │
│ <pair>/1s/      │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Usage

### 1. Start the Orchestrator

```bash
python src/acd/capture/overlap_orchestrator.py \
  --pair BTC-USD \
  --export-dir exports \
  --verbose
```

### 2. Monitor Progress

The orchestrator emits several log types:

```bash
# Clock state (startup)
[CLOCK:ntp] {"source":"system","offset_ms":null}

# Heartbeats (every 5s per venue)
[CAPTURE:hb] {"venue":"binance","ts_local":"2025-09-26T20:30:00","lag_ms":15,"msgs":1250}

# Overlap status (every 30s)
[OVERLAP:PENDING] {"minutes_max":0,"venues_ready":["binance","coinbase"],"venues_missing":["kraken","okx","bybit"]}

# Success (when overlap found)
[OVERLAP] {"startUTC":"2025-09-26T20:30:00","endUTC":"2025-09-26T21:00:00","minutes":30.0,"venues":["binance","coinbase","kraken","okx"],"excluded":["bybit"],"policy":"BEST4_30m"}
```

### 3. Auto-Analysis Execution

When overlap is found, the system automatically:

1. **Stops capture** and writes `exports/overlap.json`
2. **Runs spread compression** with exact window bounds
3. **Runs information share** with no standardization
4. **Runs invariance matrix** on the same window
5. **Generates evidence** with nine BEGIN/END blocks
6. **Commits results** with provenance

## Data Schema

### Tick Data Format

Each captured tick includes:

```json
{
  "exchange": "binance",
  "pair": "BTC-USD", 
  "ts_exchange": 1695758400000,
  "ts_local": 1695758400015,
  "best_bid": 43250.50,
  "best_ask": 43251.00,
  "mid": 43250.75,
  "last_trade_px": 43250.80,
  "last_trade_qty": 0.001,
  "event_type": "ticker"
}
```

### Storage Structure

```
data/ticks/
├── binance/
│   └── BTC-USD/
│       └── 1s/
│           └── 2025-09-26/
│               └── 20/
│                   ├── ticks_00.parquet
│                   ├── ticks_01.parquet
│                   └── ...
├── coinbase/
│   └── BTC-USD/
│       └── 1s/
│           └── 2025-09-26/
│               └── 20/
│                   ├── ticks_00.parquet
│                   └── ...
└── ...
```

## Overlap Policies

The system enforces strict overlap policies in order of preference:

1. **BEST4≥30m**: 4+ venues with 30+ minutes continuous overlap
2. **BEST4≥20m**: 4+ venues with 20+ minutes continuous overlap  
3. **BEST4≥10m**: 4+ venues with 10+ minutes continuous overlap
4. **ALL5≥10m**: All 5 venues with 10+ minutes continuous overlap

### Gap Detection

- Maximum allowed gap: 1 second
- Continuous coverage required within overlap window
- Venues with gaps >1s are excluded from analysis

## Hard Abort Rules

The system maintains strict integrity with these abort conditions:

### ❌ **Synthetic Data Detection**
```bash
[ABORT:synthetic] {"policy":"SYNTHETIC_DEMO","reason":"synthetic data not allowed in court-ready evidence"}
```

### ❌ **Missing Overlap**
```bash
[ABORT:overlap_missing] {"file":"exports/overlap.json","reason":"overlap.json required for analysis"}
```

### ❌ **Window Mismatch**
```bash
[ABORT:window_mismatch] {"requested":["binance","coinbase"],"got":["binance"]}
```

### ❌ **Insufficient Data**
```bash
[OVERLAP:INSUFFICIENT] {"quorum":4,"minutes_max":5,"venues_ready":["binance","coinbase"],"venues_missing":["kraken","okx","bybit"]}
```

## Evidence Generation

### MANIFEST.json

```json
{
  "commit": "c4a48f3",
  "tz": "UTC",
  "sampleWindow": {
    "start": "2025-09-26T20:30:00",
    "end": "2025-09-26T21:00:00"
  },
  "runs": {
    "spread": "completed",
    "infoShare": "completed", 
    "invariance": "completed"
  },
  "seeds": {"numpy": 42, "random": 42},
  "overlap_policy": "BEST4_30m",
  "venues_used": ["binance", "coinbase", "kraken", "okx"],
  "excluded": ["bybit"],
  "venue_stats": {
    "binance": {"messages": 1800, "first_timestamp": 1695758400000, "last_timestamp": 1695760200000}
  },
  "strict_window": true,
  "no_synthetic": true
}
```

### EVIDENCE.md

Contains nine BEGIN/END blocks:
- **OVERLAP**: Exact window JSON
- **FILE LIST**: Generated files
- **SPREAD SUMMARY**: Episodes and leaders
- **INFO SHARE SUMMARY**: Bounds and methods
- **INVARIANCE MATRIX**: Top venues by stability
- **STATS**: Chi-square and permutation results
- **GUARDRAILS**: Warning/abort logs
- **MANIFEST**: Full provenance JSON
- **EVIDENCE**: Human-readable summary

## Operational Notes

### Capture Duration
- **Target**: 3 hours maximum
- **Early termination**: When BEST4≥30m overlap found
- **Timeout**: If no overlap after 3 hours, exit with status 2

### Performance
- **Heartbeat frequency**: Every 5 seconds per venue
- **Overlap check**: Every 30 seconds
- **Storage**: Parquet files partitioned by minute
- **Memory**: Streaming processing, no full dataset loading

### Error Handling
- **WebSocket reconnection**: Automatic retry with exponential backoff
- **API rate limits**: Built-in delays and retry logic
- **Data validation**: Schema enforcement and gap detection
- **Graceful shutdown**: Clean exit on overlap found or timeout

## Court-Ready Features

### 🔒 **Integrity Guarantees**
- No synthetic data contamination
- Strict window enforcement
- Complete audit trail
- Reproducible results

### 📊 **Transparent Limitations**
- Real data constraints documented
- Venue exclusion reasons logged
- Gap statistics provided
- Policy decisions explained

### ⚖️ **Legal Compliance**
- Fixed random seeds for reproducibility
- Complete provenance tracking
- Immutable evidence generation
- Git commit verification

## Troubleshooting

### No Overlap Found
```bash
[OVERLAP:INSUFFICIENT] {"quorum":4,"minutes_max":0,"venues_ready":[],"venues_missing":["binance","coinbase","kraken","okx","bybit"]}
```
**Solution**: Check network connectivity and exchange API status

### WebSocket Connection Failed
```bash
Failed to connect to binance: Connection refused
```
**Solution**: Verify exchange WebSocket endpoints and firewall settings

### Analysis Script Errors
```bash
[ABORT:spread_missing] {"log":"[SPREAD:episodes]","reason":"required log line missing"}
```
**Solution**: Check analysis script logs for underlying errors

## Future Enhancements

- **Multi-pair support**: Extend to ETH-USD, etc.
- **Custom policies**: User-defined overlap criteria
- **Real-time alerts**: Webhook notifications on overlap found
- **Historical analysis**: Backtest on stored tick data
- **Performance metrics**: Latency and throughput monitoring
