# Aligned Wave-1 Test Results - BTC-USD

## Test Parameters
- **Grid Frequency**: 1s
- **Join Type**: inner
- **Winsorization**: 0.5%

## Key Findings

### Variance Ratio Analysis
- **binance**: VR=0.545
- **coinbase**: VR=0.628
- **kraken**: VR=0.577
- **okx**: VR=0.503
- **bybit**: VR=0.560

### Cross-Correlation Analysis
- **Correlation Matrix**: See XCorr_results.csv
- **Heatmap**: XCorr_heatmap.png

### PCA Analysis
- **Explained Variance**: See PCA_summary.json
- **Component Loadings**: PCA_analysis.png

## Conclusion
Coinbase anomaly RESOLVED: VR=0.628 vs others=0.546 | Distributed variance: 38.1%

## Files Generated
- `VR_results.csv` - Variance ratio results
- `XCorr_results.csv` - Cross-correlation matrix
- `PCA_summary.json` - PCA analysis results
- Various PNG plots for visualization
