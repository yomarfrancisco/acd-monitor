# Model Card Addendum - Dual Horizon Orchestrator v2.0.0

## Model Overview
The Dual Horizon Orchestrator combines 12h precision-first and 6h staggered policies using a 2-tier OR fusion strategy.

## Architecture
- **Tier-1**: 12h precision-first policy (always emits when triggered)
- **Tier-2**: 6h staggered policy (emits when Tier-1 silent and conditions met)
- **Fusion**: 2-tier OR with guard-based escalation

## Performance Metrics
- **Precision**: 0.965 (target: ≥0.95) ✅
- **Recall**: 0.647 (target: ≥0.60) ✅
- **FPR**: 0.123 (target: ≤0.15) ✅
- **Lead Time**: 193 minutes (target: ≥180) ✅
- **Window Pass**: 100% (target: 100%) ✅

## Verification Status
- **Metrics Exact-Match**: ✅ (tolerance ≤ 1e-6)
- **Window Guards**: ✅ (100% pass rate)
- **Placebo/Inversion Collapse**: ✅ (verified)
- **OOS Reproduced**: ✅ (consistent across folds)

## Production Readiness
- **Status**: PRODUCTION_READY
- **Version**: v2.0.0
- **Verification**: COMPLETE
- **Bundle**: prod_bundle_orch_v2/

## Usage
1. Load policy.json for orchestrator configuration
2. Use thresholds.json for operational parameters
3. Apply conformal.json for uncertainty quantification
4. Monitor metrics.json for performance tracking

## Guardrails
- READ_ONLY_CANON=true
- NETWORK=FROZEN
- NO_SYNTHETIC_DATA=true
- DETERMINISTIC_SEED=42
