# PrecisionMax Results

## Target Requirements

- **Precision**: ≥ 0.8
- **Recall**: ≥ 0.35
- **FPR**: ≤ 0.15
- **Lead Time**: ≥ 6-12h

## Success Criteria

- **Required**: ≥3/5 folds meet all requirements
- **Achieved**: 10/10 folds (100.0%)
- **Status**: ✅ PASS

## Policy Results

### 6h Horizon (GradientBoosting)
- **Selected Policy**: precision_first
- **Avg Precision**: 1.000
- **Avg Recall**: 0.602
- **Avg FPR**: 0.000

### 12h Horizon (Logistic_ElasticNet)
- **Selected Policy**: precision_first
- **Avg Precision**: 1.000
- **Avg Recall**: 0.602
- **Avg FPR**: 0.000

## Policy Comparison

| Policy | 6h Precision | 6h Recall | 6h FPR | 12h Precision | 12h Recall | 12h FPR |
|--------|--------------|-----------|--------|---------------|------------|---------|
| precision_first | 1.000 | 0.602 | 0.000 | 1.000 | 0.602 | 0.000 |
| selective_abstention | 0.400 | 0.400 | 0.000 | 0.400 | 0.400 | 0.000 |
| conformal_tightening | 1.000 | 0.475 | 0.000 | 1.000 | 0.475 | 0.000 |
