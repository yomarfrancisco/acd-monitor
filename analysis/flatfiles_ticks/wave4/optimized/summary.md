# Wave 4 — Optimized Tick-Level Coordination Diagnostics

**Analysis Date**: 2025-10-03 18:20:51
**Data Source**: Raw tick data (GUID-deduped, 100k trades per venue)
**Venues**: BINANCE, COINBASE, BYBITSPOT, BITGET
**Method**: Vectorized, chunked analysis with bootstrap validation

## H1: Large Trade Synchronization

| Pair | Status | Correlation | P-value | Significant |
|------|--------|-------------|---------|------------|
| BINANCE_COINBASE | SUCCESS | 0.007 | 0.085 | ✗ |
| BINANCE_BYBITSPOT | SUCCESS | 0.011 | 0.015 | ✓ |
| BINANCE_BITGET | SUCCESS | 0.015 | 0.005 | ✓ |
| COINBASE_BYBITSPOT | SUCCESS | 0.006 | 0.000 | ✓ |
| COINBASE_BITGET | SUCCESS | 0.178 | 0.000 | ✓ |
| BYBITSPOT_BITGET | SUCCESS | 0.006 | 0.020 | ✓ |

## H2: OFI Spike Co-occurrence

| Pair | Status | Correlation | P-value | Significant |
|------|--------|-------------|---------|------------|
| BINANCE_COINBASE | SUCCESS | 0.020 | 0.005 | ✓ |
| BINANCE_BYBITSPOT | SUCCESS | 0.106 | 0.000 | ✓ |
| BINANCE_BITGET | SUCCESS | 0.027 | 0.005 | ✓ |
| COINBASE_BYBITSPOT | SUCCESS | 0.012 | 0.005 | ✓ |
| COINBASE_BITGET | SUCCESS | 0.111 | 0.000 | ✓ |
| BYBITSPOT_BITGET | SUCCESS | 0.008 | 0.085 | ✗ |

## H3: Price Impact Spillovers

| Pair | Status | Max Impact | P-value | Significant |
|------|--------|------------|---------|------------|
| BINANCE_COINBASE | SUCCESS | 0.000048 | 1.000 | ✗ |
| BINANCE_BYBITSPOT | SUCCESS | 0.000045 | 1.000 | ✗ |
| BINANCE_BITGET | SUCCESS | 0.000037 | 1.000 | ✗ |
| COINBASE_BINANCE | SUCCESS | 0.000038 | 1.000 | ✗ |
| COINBASE_BYBITSPOT | SUCCESS | 0.000030 | 1.000 | ✗ |
| COINBASE_BITGET | SUCCESS | 0.000046 | 1.000 | ✗ |
| BYBITSPOT_BINANCE | SUCCESS | 0.000040 | 1.000 | ✗ |
| BYBITSPOT_COINBASE | SUCCESS | 0.000042 | 1.000 | ✗ |
| BYBITSPOT_BITGET | SUCCESS | 0.000036 | 1.000 | ✗ |
| BITGET_BINANCE | SUCCESS | 0.000041 | 1.000 | ✗ |
| BITGET_COINBASE | SUCCESS | 0.000070 | 1.000 | ✗ |
| BITGET_BYBITSPOT | SUCCESS | 0.000049 | 1.000 | ✗ |

## Summary Statistics

- **Significant Sync Pairs**: 5/6
- **Significant OFI Pairs**: 5/6
- **Significant Impact Pairs**: 0/12

## Key Findings

✅ **Coordination Signal**: 5 venue pairs show significant large trade synchronization
✅ **OFI Coordination**: 5 venue pairs show significant OFI spike co-occurrence
❌ **No Impact Spillovers**: No significant price impact spillovers detected
