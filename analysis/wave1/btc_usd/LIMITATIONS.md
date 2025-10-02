# Wave-1 Test Limitations - BTC-USD

## Test-Specific Limitations

### 1. Variance Ratio Test
- **Limitation**: Sensitive to volatility clustering
- **Impact**: May flag normal market stress as coordination
- **Mitigation**: Consider market regime context

### 2. Autocorrelation & AR(1) Decay  
- **Limitation**: Confounds with microstructure noise
- **Impact**: May misattribute venue-specific effects as coordination
- **Mitigation**: Control for venue-specific factors

### 3. Cross-Correlation of Prices/Spreads
- **Limitation**: Common shocks may confound results
- **Impact**: Macro events may appear as coordination
- **Mitigation**: Include macro controls in analysis

### 4. PCA Loadings / Common Factor Analysis
- **Limitation**: Factors may reflect macro shocks, not collusion
- **Impact**: May identify common risk factors as coordination
- **Mitigation**: Interpret in context of market conditions

### 5. Rolling Volatility & Spread Convergence
- **Limitation**: Could reflect liquidity improvements, not coordination
- **Impact**: Market efficiency gains may appear as collusion
- **Mitigation**: Consider liquidity and market structure changes

## General Limitations

- **Sample Size**: Limited to recent capture data
- **Time Period**: May not capture full market cycles
- **Venue Coverage**: Results depend on venue data quality
- **Market Regime**: Tests assume normal market conditions

## Interpretation Guidelines

- **Wave-1 tests are screening tools, not conclusive evidence**
- **Results should be interpreted in context of market conditions**
- **Multiple tests showing similar patterns increase confidence**
- **Consider alternative explanations before concluding coordination**

## Next Steps

- **Wave-2**: Deeper econometric analysis with controls
- **Wave-3**: Advanced ML methods for pattern detection
- **Validation**: Cross-check with independent data sources
