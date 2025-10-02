# Wave-3 Copula Analysis Summary

**Analysis Date**: 2025-09-30T20:05:40.084033
**Method**: Copula Dependence & Tails Analysis
**Hypothesis**: Competitive markets show session-dependent dependence; coordination shows stable, high dependence

## Session Results

| Session | Observations | Venues | Gaussian AIC | t-Copula AIC | Best Model |
|---------|-------------|--------|-------------|-------------|------------|
| Asia | 1,865 | 5 | 16852.07 | 25442.71 | Gaussian |
| Europe | 14,359 | 5 | 131937.51 | 198065.14 | Gaussian |
| US | 1,802 | 5 | 16574.92 | 24875.44 | Gaussian |

## Dependence Analysis

### Asia Session

- **Average Kendall's τ**: 0.0177
- **Max Kendall's τ**: 0.2594
- **Min Kendall's τ**: -0.0694
- **Average Upper Tail Dependence**: 0.0937
- **Max Upper Tail Dependence**: 0.5263

### Europe Session

- **Average Kendall's τ**: 0.0051
- **Max Kendall's τ**: 0.0233
- **Min Kendall's τ**: -0.0068
- **Average Upper Tail Dependence**: 0.0847
- **Max Upper Tail Dependence**: 0.1585

### US Session

- **Average Kendall's τ**: -0.0017
- **Max Kendall's τ**: 0.0184
- **Min Kendall's τ**: -0.0166
- **Average Upper Tail Dependence**: 0.0429
- **Max Upper Tail Dependence**: 0.0549

## Cross-Session Comparison

- **High Dependence Threshold**: τ > 0.7
- **Percentage with High Dependence**: 0.0%
- **✅ REASSURING**: Moderate dependence levels across sessions
- This suggests competitive behavior with session-dependent dependence

## Interpretation

### Competitive Markets
- Dependence varies across sessions
- Lower average dependence levels
- Session-specific tail behavior

### Coordinated Markets
- Stable, high dependence across sessions
- Session-invariant strong correlations
- Consistent tail dependence patterns

## Limitations

- Simplified copula fitting approach
- Limited to single-day analysis
- No bootstrap confidence intervals
- Assumes specific copula families
- May not capture all dependence structures
