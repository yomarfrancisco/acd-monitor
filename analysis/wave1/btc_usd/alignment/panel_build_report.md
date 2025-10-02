# Panel Alignment Report - BTC-USD

## Alignment Parameters
- **Grid Frequency**: 1s
- **Join Type**: inner
- **Winsorization**: 0.5%
- **Total Observations**: 9,003

## Venue Coverage
- **binance**: 9,003 obs (100.0% coverage)
- **coinbase**: 9,003 obs (100.0% coverage)
- **kraken**: 9,003 obs (100.0% coverage)
- **okx**: 7,478 obs (83.1% coverage)
- **bybit**: 9,003 obs (100.0% coverage)

## Data Quality
- **Time Range**: 2025-09-29 10:00:00+00:00 to 2025-09-29 14:00:00+00:00
- **Duration**: 4.0 hours

## Files Generated
- `data/derived/btc_usd/panel_1s_inner.parquet`
- `data/derived/btc_usd/panel_1s_outer.parquet` (if outer join)

## Next Steps
- Use aligned panel for cross-correlation analysis
- Enable PCA factor analysis
- Re-run variance ratio tests on aligned data
