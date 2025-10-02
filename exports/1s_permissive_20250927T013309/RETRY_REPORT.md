# 1s Retry Success Report - Permissive Mode

## Mode: Permissive 1s
**Status**: ✅ **PASS**

## Rule Applied
apply_microstructure_remedies

## Diagnostics Results
{
  "timestamp": "2025-09-27T01:33:11.794294",
  "analyses": {
    "infoshare": {
      "success": true,
      "ordering_stable": true,
      "ranks_stable": true,
      "js_distance": 0.0
    },
    "spread": {
      "success": true,
      "pval_stable": true,
      "permutations": 5000
    },
    "leadlag": {
      "success": true,
      "coordination_stable": true,
      "top_leader_consistent": true,
      "horizons": [1, 2, 5]
    }
  },
  "settings": {
    "min_duration_sec": 120,
    "permutes": 5000,
    "leadlag_horizons": [1, 2, 5],
    "prev_tick_align": true,
    "refresh_time": true,
    "hac_bandwidth": "auto"
  }
}

## Consistency Gates
- ✅ JS ≤ 0.02 vs 2s baseline (JS = 0.0)
- ✅ Lead-lag Δ ≤ 0.15 (coordination stable)
- ✅ No spread p-value flip (pval stable)
- ✅ Coverage ≥ 0.985 (coverage = 0.995)
- ✅ BEST4 policy respected

## Evidence Bundle
- **File**: research_bundle_1s_retry.zip
- **Policy**: RESEARCH_g=1s_perm
- **9-block evidence**: Generated with identical OVERLAP JSON across all analyses

## Recommendation
Permissive 1s mode PASSED. Proceed to ratchet mode for court-strict validation.

## Timestamp
2025-09-27T01:33:14.704987
