# InfoShare v2 — ETH-USD 2025-09-28 11:00-11:30 UTC

**Snapshot**: snapshots/btc_1200_1230/OVERLAP.json  
**Cadence**: 1s  
**N_venues**: 5

**Parameters**: max_lags=5, det_order=0, FDR q=0.05

## Stationarity Tests
- **binance**: Non-stationary (ADF p=0.1829)
- **coinbase**: Non-stationary (ADF p=0.7563)
- **kraken**: Non-stationary (ADF p=0.6042)
- **okx**: Non-stationary (ADF p=0.1755)
- **bybit**: Non-stationary (ADF p=0.6273)

## Johansen Cointegration Test
**Rank**: 0  
**Trace Statistics**: [35.63038459141668, 24.388770115833903, 13.961449165593015]  
**Trace P-values**: [[65.8202, 69.8189, 77.8202], [44.4929, 47.8545, 54.6815], [27.0669, 29.7961, 35.4628]]  
**Eigen Statistics**: [11.241614475582777, 10.427320950240889, 7.7880637793361505]  
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
- **Max lags**: 5
- **Deterministic order**: 0
- **Code version**: InfoShare v2
- **Created at**: 2025-09-29T11:21:41.263867Z
