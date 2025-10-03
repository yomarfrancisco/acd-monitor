# Wash Trading Screens Dashboard

**Analysis Date**: 2025-10-03 20:14:39
**Method**: Multi-screen wash trading detection

## Venue Summary

| Venue | Total Ticks | Screens Run | Significant |
|-------|-------------|-------------|------------|
| BINANCE | 4,409,953 | 7 | 6 |
| COINBASE | 561,347 | 7 | 6 |
| BYBITSPOT | 832,133 | 7 | 6 |
| BITGET | 257,587 | 7 | 6 |

## BINANCE Results

### benford_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 35525090.857

### benford_notional

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 26656337.234

### round_clustering_volume

- **Status**: SUCCESS

### round_clustering_price

- **Status**: SUCCESS

### tail_fit_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 1.483

### tail_fit_price

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 342.984

### temporal_regularity

- **Status**: SUCCESS
- **P-Value**: 0.500
- **Significant**: ✗
- **Z-Score**: 0.000
- **Max Regularity Score**: 0.001


## COINBASE Results

### benford_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 23472.034

### benford_notional

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 33237.815

### round_clustering_volume

- **Status**: SUCCESS

### round_clustering_price

- **Status**: SUCCESS

### tail_fit_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 2.416

### tail_fit_price

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 278.015

### temporal_regularity

- **Status**: SUCCESS
- **P-Value**: 0.500
- **Significant**: ✗
- **Z-Score**: 0.000
- **Max Regularity Score**: 0.014


## BYBITSPOT Results

### benford_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 24156.397

### benford_notional

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 279609.441

### round_clustering_volume

- **Status**: SUCCESS

### round_clustering_price

- **Status**: SUCCESS

### tail_fit_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 2.312

### tail_fit_price

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 327.240

### temporal_regularity

- **Status**: SUCCESS
- **P-Value**: 0.500
- **Significant**: ✗
- **Z-Score**: 0.000
- **Max Regularity Score**: 0.007


## BITGET Results

### benford_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 42250.930

### benford_notional

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Chi-Square**: 55892.382

### round_clustering_volume

- **Status**: SUCCESS

### round_clustering_price

- **Status**: SUCCESS

### tail_fit_volume

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 2.056

### tail_fit_price

- **Status**: SUCCESS
- **P-Value**: 0.000
- **Significant**: ✓
- **Power-Law Alpha**: 370.370

### temporal_regularity

- **Status**: SUCCESS
- **P-Value**: 0.500
- **Significant**: ✗
- **Z-Score**: 0.000
- **Max Regularity Score**: 0.019

## Wash Trading Flags

| Venue | Flag Count | Flags |
|-------|------------|-------|
| BINANCE | 6 | benford_volume, benford_notional, round_clustering_volume, round_clustering_price, tail_fit_volume, tail_fit_price |
| COINBASE | 6 | benford_volume, benford_notional, round_clustering_volume, round_clustering_price, tail_fit_volume, tail_fit_price |
| BYBITSPOT | 6 | benford_volume, benford_notional, round_clustering_volume, round_clustering_price, tail_fit_volume, tail_fit_price |
| BITGET | 6 | benford_volume, benford_notional, round_clustering_volume, round_clustering_price, tail_fit_volume, tail_fit_price |
