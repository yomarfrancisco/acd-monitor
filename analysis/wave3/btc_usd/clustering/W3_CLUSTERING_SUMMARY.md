# Wave-3 Clustering Analysis Summary

**Analysis Date**: 2025-09-30T20:07:25.039507
**Method**: Unsupervised Clustering (k-means)
**Hypothesis**: Competitive markets show environment-aligned clusters; coordination shows suppressed variance clusters

## Cluster Evaluation Results

| k | Silhouette Score | Calinski-Harabasz | Inertia |
|---|------------------|-------------------|----------|
| 2 | 0.5096 | 86.66 | 190643078.36 |
| 3 | 0.4656 | 98.37 | 111405633.35 |
| 4 | 0.4847 | 140.08 | 59984516.47 |

**Best k**: 2 (Silhouette: 0.5096)

## Final Clustering Results

- **Number of clusters**: 2
- **Silhouette score**: 0.5096
- **Calinski-Harabasz score**: 86.66
- **Inertia**: 190643078.36

## Cluster Profiles

| Cluster | Windows | Size % | Coordination Score | Mean Variance | Feature Dispersion |
|---------|---------|--------|-------------------|---------------|-------------------|
| 0 | 50 | 67.6% | 0.0000 | 77.9850 | 444.9098 |
| 1 | 24 | 32.4% | 0.0000 | 151.8080 | 875.8542 |

## Red Flag Analysis

### ✅ NO COORDINATION-LIKE CLUSTERS DETECTED

All clusters show characteristics consistent with competitive behavior:
- Moderate to high variance across features
- Reasonable dispersion between venues
- No evidence of suppressed competition

## Interpretation

### Competitive Markets
- Clusters align with market environments/sessions
- High variance and dispersion within clusters
- No clusters with suppressed competition

### Coordinated Markets
- Clusters with low variance and dispersion
- Suppressed competition across venues
- Environment-invariant behavior patterns

## Limitations

- Single-day analysis limits generalizability
- k-means assumes spherical clusters
- Feature selection may miss important patterns
- No temporal dynamics in clustering
- Coordination score is heuristic-based
