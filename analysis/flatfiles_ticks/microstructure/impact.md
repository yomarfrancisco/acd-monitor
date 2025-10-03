# Price Impact & Spillover Analysis

## Venue-Level Price Impact

| Venue | Impact 1-tick | Impact 3-tick | Impact 5-tick | Vol-Impact Corr | Observations |
|-------|---------------|----------------|---------------|-----------------|-------------|
| BINANCE | 2.605488 | 2.301078 | 2.065646 | 0.4525 | 205,525 |
| BITGET | 2.888075 | 2.481223 | 2.183517 | 0.4021 | 205,525 |
| BYBITSPOT | 3.645598 | 3.044790 | 2.642124 | 0.5555 | 167,164 |
| COINBASE | 3.903009 | 2.898613 | 2.429893 | 0.4267 | 205,525 |

## Cross-Venue Spillover

| Pair | Spillover Fraction | Avg Spillover Impact | Large Trade Threshold |
|------|-------------------|---------------------|----------------------|
| BINANCE_BITGET | 0.298 | 0.001111 | 0.61 |
| BINANCE_BYBITSPOT | 0.212 | 0.001481 | 0.61 |
| BINANCE_COINBASE | 0.284 | 0.001679 | 0.61 |
| BITGET_BYBITSPOT | 0.359 | 0.002028 | 0.12 |
| BITGET_COINBASE | 0.207 | 0.001191 | 0.12 |
| BYBITSPOT_COINBASE | 0.316 | 0.001612 | 0.77 |
