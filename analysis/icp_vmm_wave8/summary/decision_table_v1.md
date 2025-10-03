# Wave 8 Final Decision Table

**Generated**: 2025-10-04T01:21:59.964064
**Total edges**: 50
**Confirmed**: 32
**Fragile**: 2
**Rejected**: 16

## Summary Statistics

- **Confirmed edges**: 32 (64.0%)
- **Fragile edges**: 2 (4.0%)
- **Rejected edges**: 16 (32.0%)

## Decision Table

| Source | Target | Lag | Original Coef | Pass Rate | Decision | Reason |
|--------|--------|-----|----------------|-----------|----------|--------|
| BINANCE | COINBASE | 1s | 0.2455 | 18.2% | REJECTED | Not robust (18.2% pass rate) |
| BINANCE | COINBASE | 2s | 0.1240 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BINANCE | COINBASE | 3s | 0.0760 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BINANCE | COINBASE | 5s | 1.2994 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BINANCE | COINBASE | 10s | 1.5698 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BINANCE | BITGET | 2s | 0.1122 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| BINANCE | BITGET | 3s | 0.0516 | 9.1% | REJECTED | Not robust (9.1% pass rate) |
| BINANCE | BITGET | 5s | 1.5812 | 63.6% | FRAGILE | Partially robust (63.6% pass rate) |
| BINANCE | BITGET | 10s | 1.3551 | 72.7% | FRAGILE | Partially robust (72.7% pass rate) |
| BINANCE | BYBITSPOT | 1s | 0.2055 | 9.1% | REJECTED | Not robust (9.1% pass rate) |
| BINANCE | BYBITSPOT | 2s | 0.1038 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BINANCE | BYBITSPOT | 3s | 0.0504 | 81.8% | CONFIRMED | Robust across scales and subsamples (81.8% pass rate) |
| BINANCE | BYBITSPOT | 5s | 1.1352 | 90.9% | CONFIRMED | Robust across scales and subsamples (90.9% pass rate) |
| BINANCE | BYBITSPOT | 10s | -0.1524 | 90.9% | CONFIRMED | Robust across scales and subsamples (90.9% pass rate) |
| COINBASE | BINANCE | 1s | 0.1946 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| COINBASE | BINANCE | 2s | 0.1076 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| COINBASE | BINANCE | 3s | 0.0618 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| COINBASE | BINANCE | 5s | 1.1952 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| COINBASE | BINANCE | 10s | 1.6211 | 81.8% | CONFIRMED | Robust across scales and subsamples (81.8% pass rate) |
| COINBASE | BITGET | 3s | 0.0875 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| COINBASE | BITGET | 10s | 1.9313 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| COINBASE | BYBITSPOT | 10s | 2.3100 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| BITGET | BINANCE | 1s | 0.1946 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BINANCE | 2s | 0.0953 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BINANCE | 3s | 0.0361 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BINANCE | 5s | 0.2331 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BINANCE | 10s | 0.0583 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | COINBASE | 1s | 0.2539 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | COINBASE | 2s | 0.1117 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | COINBASE | 3s | 0.0599 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | COINBASE | 5s | 1.1471 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | COINBASE | 10s | 1.5879 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BYBITSPOT | 1s | 0.2106 | 90.9% | CONFIRMED | Robust across scales and subsamples (90.9% pass rate) |
| BITGET | BYBITSPOT | 2s | 0.1093 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BYBITSPOT | 3s | 0.0620 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BYBITSPOT | 5s | 1.0359 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BITGET | BYBITSPOT | 10s | -0.3065 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BYBITSPOT | BINANCE | 2s | 0.1067 | 81.8% | CONFIRMED | Robust across scales and subsamples (81.8% pass rate) |
| BYBITSPOT | BINANCE | 3s | 0.0471 | 90.9% | CONFIRMED | Robust across scales and subsamples (90.9% pass rate) |
| BYBITSPOT | BINANCE | 5s | 1.1475 | 90.9% | CONFIRMED | Robust across scales and subsamples (90.9% pass rate) |
| BYBITSPOT | BINANCE | 10s | -0.1158 | 90.9% | CONFIRMED | Robust across scales and subsamples (90.9% pass rate) |
| BYBITSPOT | COINBASE | 1s | 0.2660 | 18.2% | REJECTED | Not robust (18.2% pass rate) |
| BYBITSPOT | COINBASE | 2s | 0.1341 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BYBITSPOT | COINBASE | 3s | 0.0711 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BYBITSPOT | COINBASE | 5s | 1.6137 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BYBITSPOT | COINBASE | 10s | 0.4591 | 100.0% | CONFIRMED | Robust across scales and subsamples (100.0% pass rate) |
| BYBITSPOT | BITGET | 2s | 0.1306 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| BYBITSPOT | BITGET | 3s | 0.0594 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| BYBITSPOT | BITGET | 5s | 0.9221 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
| BYBITSPOT | BITGET | 10s | -0.1164 | 0.0% | REJECTED | Not robust (0.0% pass rate) |
