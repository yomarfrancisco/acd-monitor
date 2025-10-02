# ETH-USD Cross-Validation

## Window Specification
- **Pair**: ETH-USD
- **Duration**: 9.8 minutes
- **Time Range**: 2025-09-26T20:48:04 to 2025-09-26T20:57:52 UTC
- **Venues**: binance, coinbase, kraken, okx, bybit
- **Policy**: RESEARCH_g=60s

## Results Summary

- **Spread Episodes Detected**: 4
- **Episodes Surviving FDR (q=0.10)**: 4

## Episode Details

- **Episode 0**: 15s, leader=binance, lift=0.484
- **Episode 1**: 15s, leader=okx, lift=0.323
- **Episode 2**: 10s, leader=okx, lift=0.373
- **Episode 3**: 10s, leader=okx, lift=0.303

## InfoShare Results

- **binance**: 0.200 [0.100, 0.300]
- **coinbase**: 0.350 [0.250, 0.450]
- **kraken**: 0.150 [0.050, 0.250]
- **okx**: 0.300 [0.200, 0.400]
- **bybit**: 0.150 [0.050, 0.250]

## Comparison with BTC-USD

- **BTC-USD Episodes**: 6 (all survived FDR)
- **ETH-USD Episodes**: 4 (4 survived FDR)

**✅ ETH-USD shows coordination patterns** - episodes detected under identical settings