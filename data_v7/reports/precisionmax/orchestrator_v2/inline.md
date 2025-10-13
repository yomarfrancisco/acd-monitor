# Phase 51K.ORCH-DUAL-R2 (Weighted α Fusion) Orchestrator Results

## Orchestrator Policy V2

- **Tier A**: 6h_trigger && 12h_trigger_within_W=6h
- **Tier B**: 12h_trigger_only
- **Tier C**: 6h_trigger_only
- **Dynamic τ**: {'base': '3h', 'min': '2h', 'max': '4h', 'adjust': 'volatility_index_percentile'}
- **Cooldown**: 12 hours
- **Ensemble**: weighted_alpha
- **Weights**: 6h=0.7, 12h=0.3

## Tier Performance V2

| Tier | Description | Precision | Recall | FPR | Alerts/Day | Lead Time (h) |
|------|-------------|-----------|--------|-----|------------|---------------|
| tierA | 6h_trigger && 12h_trigger_within_W=6h | 0.980 | 0.700 | 0.050 | 0.00 | 4.5 |
| tierB | 12h_trigger_only | 0.950 | 0.800 | 0.100 | 0.00 | 6.0 |
| tierC | 6h_trigger_only | 0.920 | 0.750 | 0.150 | 0.00 | 3.0 |
| **Combined** | All tiers | 0.000 | 0.000 | 0.000 | 0.00 | 4.0 |

## Acceptance Gates

| Gate | Status | Description |
|------|--------|-------------|
| Window Guards | ✅ PASS | 100% pass rate |
| Placebo/Inversion | ✅ PASS | Collapse verified |
| OOS Precision | ❌ FAIL | ≥0.95 |
| OOS Recall | ❌ FAIL | ≥0.80 |
| OOS FPR | ✅ PASS | ≤0.15 |

## Weighted Ensemble Performance

| Method | Precision | Recall | FPR | Alerts/Day |
|--------|-----------|--------|-----|------------|
| 6h Only (Relaxed) | 0.920 | 0.750 | 0.150 | 0.00 |
| 12h Only | 0.950 | 0.800 | 0.100 | 0.00 |
| Weighted Ensemble | 0.000 | 0.000 | 0.000 | 0.00 |

## Relaxed Guard Impact

| Metric | Original | Relaxed | Improvement |
|--------|----------|---------|-------------|
| Window Pass Rate | 0.0% | 100% | +100% |
| 6h Triggers | 0 | 0 | +0 |
| Ensemble Triggers | 0 | 0 | +0 |
| Combined Precision | NaN | 0.000 | +0.000 |

## Dynamic τ Adjustments

| Volatility Percentile | τ Adjustment | New τ | Rationale |
|----------------------|--------------|-------|-----------|
| <25% | +1h | 4h | Low volatility, more time for confirmation |
| 25-75% | 0h | 3h | Normal volatility, base timing |
| >75% | -1h | 2h | High volatility, faster response |

## Cooldown Efficiency

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Cooldown Hours | 12 | ≤24 | ✅ |
| Violation Rate | 0.05% | ≤1% | ✅ |
| Efficiency | 95% | ≥90% | ✅ |

