# InfoShare v2 — ETH-USD 2025-09-28 11:00-11:30 UTC

**Snapshot**: snapshots/btc_1200_1230  
**Cadence**: 1s  
**N_venues**: 5

**Parameters**: max_lags=5, det_order=1, FDR q=0.05

## Stationarity Tests
- **binance**: Non-stationary (ADF p=0.1829)
- **coinbase**: Non-stationary (ADF p=0.7563)
- **kraken**: Non-stationary (ADF p=0.6042)
- **okx**: Non-stationary (ADF p=0.1755)
- **bybit**: Non-stationary (ADF p=0.6273)

## Johansen Cointegration Test
**Rank**: 0  
**Trace Statistics**: [58.27166663801107, 29.72095573764352, 18.48514584284404]  
**Trace P-values**: [[75.1027, 79.3422, 87.7748], [51.6492, 55.2459, 62.5202], [32.0645, 35.0116, 41.0815]]  
**Eigen Statistics**: [28.55071090036755, 11.235809894799479, 7.657143307119086]  
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
- **Deterministic order**: 1
- **Code version**: InfoShare v2
- **Created at**: 2025-09-29T09:23:21.241319Z
