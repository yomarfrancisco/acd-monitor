# ACD 42A-v6 Model Card

## Overview
ACD 42A-v6 is a dual-tier orchestrator system that combines the verified Dual Orchestrator v2 with the validated Q-Enhanced Knapsack Policy to provide robust CSS collapse detection with improved recall while maintaining high precision.

## Architecture
- **Tier-1**: Dual Orchestrator v2 (12h + 6h escalation OR)
- **Tier-2**: Q-Enhanced Knapsack (6h quantum features)
- **Integration**: Tier-1 priority with Tier-2 fallback

## Performance
- **Precision**: 0.960
- **Recall**: 0.730
- **FPR**: 0.136
- **Lead Time**: 193 minutes
- **Window Pass Rate**: 98.7%

## Key Features
1. **Dual-Tier Architecture**: Combines precision-first and recall-optimized approaches
2. **Quantum Feature Enhancement**: 12x feature space expansion with trigonometric mappings
3. **Robust Calibration**: ECE ≤ 0.02 across all components
4. **Temporal Integrity**: 100% window pass rate for Tier-1, ≥95% overall
5. **Stress Tested**: Placebo/inversion collapse verified

## Input Sources
- Dual Orchestrator v2: 51K.DUAL_ESC_V2_FREEZE
- Q-Enhanced Knapsack: 52Q_ABLATE
- Lead Time Manifest: 51K.METRIC_PATCH_LEAD

## Verification Gates
All 9 verification gates passed:
- Metrics replay match (|Δ| ≤ 1e-6)
- Precision ≥ 0.95
- Recall ≥ 0.677
- FPR ≤ 0.15
- Lead time ≥ 180 minutes
- Window pass rates met
- Placebo/inversion collapse verified
- Subgroup deltas ≤ 5pp
- ECE ≤ 0.02

## Release Information
- **Version**: 42A-v6
- **Release Date**: 2024-01-15
- **Status**: Production Ready
- **Rollback**: Available to 42A-v5
