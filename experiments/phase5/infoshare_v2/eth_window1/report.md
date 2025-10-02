# InfoShare v2 — ETH-USD 2025-09-28 11:00-11:30 UTC

**Snapshot**: snapshots/eth_window1/OVERLAP.json  
**Cadence**: 1s  
**N_venues**: 5

**Parameters**: max_lags=4, det_order=0, FDR q=0.05

## Stationarity Tests
- **binance**: Non-stationary (ADF p=0.9870)
- **coinbase**: Non-stationary (ADF p=0.6849)
- **kraken**: Non-stationary (ADF p=0.5068)
- **okx**: Non-stationary (ADF p=0.1229)
- **bybit**: Non-stationary (ADF p=0.5167)

## Johansen Cointegration Test
**Rank**: 0  
**Trace Statistics**: [40.46185065192961, 22.384174728839067, 10.1173493028632]  
**Trace P-values**: [[65.8202, 69.8189, 77.8202], [44.4929, 47.8545, 54.6815], [27.0669, 29.7961, 35.4628]]  
**Eigen Statistics**: [18.07767592309054, 12.26682542597587, 5.73649732892779]  
**Eigen P-values**: [1.0, 1.0, 1.0]

## VECM Results
**No VECM estimated** (no cointegration or estimation failed)

## Placebo Tests (±60s)
**Collapse**: Yes  
**Placebo Ranks**: [0, 0]

## Verdict (InfoShare Gate)
**Status**: FAIL  
**Rationale**: No cointegration or placebo test failed

## Provenance
- **Max lags**: 4
- **Deterministic order**: 0
- **Code version**: InfoShare v2
- **Created at**: 2025-09-28T21:27:13.059836Z
