# Order Flow Imbalance (OFI) Analysis

## Venue-Level OFI Statistics

| Venue | OFI 1s Mean | OFI 1s Std | OFI 5s Mean | OFI 5s Std | Total Seconds |
|-------|-------------|------------|-------------|------------|---------------|
| BINANCE | -0.02 | 1.51 | -0.11 | 3.62 | 205,526 |
| BITGET | -0.00 | 0.30 | -0.02 | 0.71 | 205,526 |
| BYBITSPOT | -0.01 | 0.88 | -0.06 | 2.07 | 167,165 |
| COINBASE | -0.01 | 0.61 | -0.03 | 1.41 | 205,526 |

## Cross-Venue OFI Correlations

| Pair | OFI Correlation | Aligned Seconds |
|------|-----------------|-----------------|
| BINANCE_BITGET | 0.4194 | 205,526 |
| BINANCE_BYBITSPOT | 0.4389 | 167,165 |
| BINANCE_COINBASE | 0.3679 | 205,526 |
| BITGET_BYBITSPOT | 0.4505 | 167,165 |
| BITGET_COINBASE | 0.3779 | 205,526 |
| BYBITSPOT_COINBASE | 0.4236 | 167,165 |
