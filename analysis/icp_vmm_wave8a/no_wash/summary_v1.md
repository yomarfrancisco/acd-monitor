# No-Wash Sensitivity Results

**Generated**: 2025-10-04T10:10:30.098575
**Status**: ✅ ROBUST
**Interpretation**: Evidence persists without wash-heavy periods

## Summary Statistics

- **Venues tested**: BINANCE, COINBASE, BYBITSPOT, BITGET
- **Total edges tested**: 60
- **Invariant edges**: 49
- **Passing edges**: 49
- **Survival rate**: 153.1%

## Exclusion Details

- **Exclusion rule**: high_wash_intensity
- **Original sample**: 604790
- **Excluded**: 199548
- **Kept**: 405242
- **Exclusion %**: 32.99459316456952%

## Final Edges

| Source | Target | Lag | Coefficient | J-pvalue |
|--------|--------|-----|-------------|----------|
| BINANCE | COINBASE | 1s | 0.3242 | 0.100 |
| BINANCE | COINBASE | 2s | 0.2127 | 0.100 |
| BINANCE | COINBASE | 3s | 0.1741 | 0.100 |
| BINANCE | COINBASE | 5s | 0.2428 | 0.100 |
| BINANCE | COINBASE | 10s | 0.9465 | 0.100 |
| BINANCE | BYBITSPOT | 1s | 0.2953 | 0.100 |
| BINANCE | BYBITSPOT | 2s | 0.1921 | 0.100 |
| BINANCE | BYBITSPOT | 3s | 0.2106 | 0.100 |
| BINANCE | BYBITSPOT | 5s | 1.3129 | 0.100 |
| BINANCE | BYBITSPOT | 10s | -1.2960 | 0.100 |
| BINANCE | BITGET | 1s | 0.2490 | 0.100 |
| BINANCE | BITGET | 3s | 0.0799 | 0.100 |
| BINANCE | BITGET | 5s | 0.9046 | 0.100 |
| BINANCE | BITGET | 10s | 0.2599 | 0.100 |
| COINBASE | BINANCE | 2s | 0.1867 | 0.100 |
| COINBASE | BINANCE | 3s | 0.1363 | 0.100 |
| COINBASE | BINANCE | 5s | 0.8760 | 0.100 |
| COINBASE | BINANCE | 10s | 0.8285 | 0.100 |
| COINBASE | BYBITSPOT | 1s | 0.2786 | 0.100 |
| COINBASE | BYBITSPOT | 3s | 0.2533 | 0.100 |
| COINBASE | BYBITSPOT | 10s | 2.9408 | 0.100 |
| COINBASE | BITGET | 3s | 0.1867 | 0.100 |
| COINBASE | BITGET | 5s | 0.9168 | 0.100 |
| BYBITSPOT | BINANCE | 2s | 0.1778 | 0.100 |
| BYBITSPOT | BINANCE | 3s | 0.0893 | 0.100 |
| BYBITSPOT | BINANCE | 5s | 1.1947 | 0.100 |
| BYBITSPOT | BINANCE | 10s | 0.0166 | 0.100 |
| BYBITSPOT | COINBASE | 2s | 0.2034 | 0.100 |
| BYBITSPOT | COINBASE | 3s | 0.1625 | 0.100 |
| BYBITSPOT | COINBASE | 5s | 0.9157 | 0.100 |
| BYBITSPOT | COINBASE | 10s | 0.3775 | 0.100 |
| BYBITSPOT | BITGET | 2s | 0.2420 | 0.100 |
| BYBITSPOT | BITGET | 5s | 1.6005 | 0.100 |
| BYBITSPOT | BITGET | 10s | -0.4134 | 0.100 |
| BITGET | BINANCE | 1s | 0.2303 | 0.100 |
| BITGET | BINANCE | 2s | 0.1861 | 0.100 |
| BITGET | BINANCE | 3s | 0.0720 | 0.100 |
| BITGET | BINANCE | 5s | 0.0165 | 0.100 |
| BITGET | BINANCE | 10s | 0.0774 | 0.100 |
| BITGET | COINBASE | 1s | 0.3123 | 0.100 |
| BITGET | COINBASE | 2s | 0.2021 | 0.100 |
| BITGET | COINBASE | 3s | 0.1533 | 0.100 |
| BITGET | COINBASE | 5s | 0.6742 | 0.100 |
| BITGET | COINBASE | 10s | -0.0275 | 0.100 |
| BITGET | BYBITSPOT | 1s | 0.3008 | 0.100 |
| BITGET | BYBITSPOT | 2s | 0.1986 | 0.100 |
| BITGET | BYBITSPOT | 3s | 0.1917 | 0.100 |
| BITGET | BYBITSPOT | 5s | 0.7198 | 0.100 |
| BITGET | BYBITSPOT | 10s | -0.1705 | 0.100 |
