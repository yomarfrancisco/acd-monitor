# Wave-3 Variables Summary

**Generated**: 2025-09-30T19:37:18.549524
**Purpose**: Variables-only preparation for Wave-3 methods (ICP, VMM, copulas, clustering, composite index)

## File Summary

### icp_design.parquet
- **Rows**: 21,853
- **Columns**: 51
- **Non-missing %**: 95.6%
- **Sample columns**: ['ts', 'Y', 'binance_return_0', 'binance_return_1', 'binance_return_5']...

### vmm_moments.parquet
- **Rows**: 79
- **Columns**: 67
- **Non-missing %**: 96.3%
- **Sample columns**: ['window_start', 'window_end', 'n_obs', 'spread_eq_mean', 'spread_eq_var']...

### copula_marginals.parquet
- **Rows**: 0
- **Columns**: 2
- **Non-missing %**: nan%
- **Sample columns**: ['ts', 'session_label']...

### clustering_features.parquet
- **Rows**: 74
- **Columns**: 77
- **Non-missing %**: 96.4%
- **Sample columns**: ['window_start', 'window_end', 'session_label', 'coinbase_return_mean', 'coinbase_return_std']...

### composite_inputs.parquet
- **Rows**: 74
- **Columns**: 16
- **Non-missing %**: 100.0%
- **Sample columns**: ['window_start', 'window_end', 'dispersion_mean', 'dispersion_95th', 'spread_mean']...

## Usage Notes

- **ICP Design**: Ready for ICP model fitting with environment partitions
- **VMM Moments**: Ready for VMM model fitting with instruments
- **Copula Marginals**: Ready for copula fitting with uniform marginals
- **Clustering Features**: Ready for clustering analysis with standardized features
- **Composite Inputs**: Ready for composite index construction

## Next Steps

1. **ICP Model**: Fit ICP models on design matrix
2. **VMM Model**: Fit VMM models on moment set
3. **Copula Analysis**: Fit copulas on marginals
4. **Clustering**: Run clustering algorithms on features
5. **Composite Index**: Construct coordination index from inputs
