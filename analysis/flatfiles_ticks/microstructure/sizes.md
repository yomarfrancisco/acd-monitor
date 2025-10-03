# Trade Size & Volume Distribution Analysis

## Venue-Level Size Distributions

| Venue | Mean | Median | Std | P95 | Gini | Observations |
|-------|------|--------|-----|-----|------|-------------|
| BINANCE | 0.3077 | 0.0163 | 1.5111 | 1.2799 | 0.878 | 205,526 |
| BITGET | 0.0612 | 0.0088 | 0.3005 | 0.2513 | 0.847 | 205,526 |
| BYBITSPOT | 0.2762 | 0.0111 | 0.8434 | 1.1972 | 0.817 | 167,165 |
| COINBASE | 0.1326 | 0.0041 | 0.5980 | 0.6141 | 0.884 | 205,526 |

## Size Distribution Percentiles

| Venue | P10 | P25 | P50 | P75 | P90 | P95 |
|-------|----|----|----|----|----|----|
| BINANCE | 0.0005 | 0.0024 | 0.0163 | 0.1258 | 0.6094 | 1.2799 |
| BITGET | 0.0007 | 0.0025 | 0.0088 | 0.0244 | 0.1181 | 0.2513 |
| BYBITSPOT | 0.0001 | 0.0010 | 0.0111 | 0.2866 | 0.7718 | 1.1972 |
| COINBASE | 0.0001 | 0.0007 | 0.0041 | 0.0500 | 0.2973 | 0.6141 |

## Cross-Venue Simultaneous Large Trades

| Pair | Simultaneous Fraction | Threshold 1 | Threshold 2 |
|------|----------------------|-------------|-------------|
| BINANCE_BITGET | 0.238 | 0.6094 | 0.1181 |
| BINANCE_BYBITSPOT | 0.243 | 0.6094 | 0.7718 |
| BINANCE_COINBASE | 0.267 | 0.6094 | 0.2973 |
| BITGET_BYBITSPOT | 0.135 | 0.1181 | 0.7718 |
| BITGET_COINBASE | 0.136 | 0.1181 | 0.2973 |
| BYBITSPOT_COINBASE | 0.112 | 0.7718 | 0.2973 |
