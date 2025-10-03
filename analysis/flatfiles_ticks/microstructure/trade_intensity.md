# Trade Intensity & Clustering Analysis

## Venue-Level Statistics

| Venue | Avg Trades/sec | Median Trades/sec | Max Trades/sec | Avg Duration (ms) | Burstiness |
|-------|---------------|-------------------|----------------|-------------------|------------|
| BINANCE | 3.55 | 1.00 | 1147 | 282.0 | 1.289 |
| BITGET | 1.33 | 1.00 | 276 | 750.1 | 0.055 |
| BYBITSPOT | 3.19 | 1.00 | 626 | 313.0 | 1.325 |
| COINBASE | 1.96 | 1.00 | 609 | 511.2 | 0.253 |

## Cross-Venue Clustering (Δt ≤ 50ms)

| Pair | Clustering Fraction | Overlapping Seconds |
|------|-------------------|---------------------|
| BINANCE_BITGET | 0.344 | 205,526 |
| BINANCE_BYBITSPOT | 0.451 | 205,526 |
| BINANCE_COINBASE | 0.525 | 205,526 |
| BITGET_BYBITSPOT | 0.316 | 205,526 |
| BITGET_COINBASE | 0.354 | 205,526 |
| BYBITSPOT_COINBASE | 0.368 | 205,526 |
