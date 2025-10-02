# BTC-USD Pipeline Validation Report
*Preliminary Technical Validation – 2025-09-29*

## 1. Purpose
This report documents successful execution of the ACD pipeline on BTC-USD data. The goal is technical validation:
- Confirm capture, coverage, schema integrity,
- Verify detectors run end-to-end without error,
- Produce structured outputs (CSV/JSON/S3),
- Establish a **baseline "competitive-behavior reference point"** for future comparisons.

It does **not** assess whether coordination occurred.

## 2. Hypotheses Tested
We tested for **signals consistent with price coordination** using:
- Lead-Lag v2 (ρ ≥ 0.12 threshold),
- InfoShare v2 (≥70% dominance threshold).

Thresholds are provisional, drawn from literature starting points, pending crypto-specific calibration.

## 3. Methods and Data
- Windows: 4 consecutive 30-min BTC-USD windows (12:00–14:00 UTC),
- Coverage: ≥95% across 5 venues,
- Validation: Placebo shuffles + 300 bootstrap resamples,
- Outputs: JSON/CSV artifacts stored at `s3://acd-monitor-snapshots/analysis/BTC/20250929/`.

## 4. Results
- Lead-Lag: No significant edges (ρ < 0.12),
- InfoShare: No venue exceeded 70% dominance,
- Bootstrap: Stable at 300 iterations,
- Placebo: No false positives,
- Replication: Null results consistent across windows.

## 5. Interpretation
No coordination signatures detected in this period. Possible explanations:
1. Competitive behavior,
2. Coordination below thresholds,
3. Mechanisms not captured,
4. Insufficient statistical power.

This establishes pipeline functionality, not a substantive conduct assessment.

## 6. Limitations
- 2-hour, single-regime dataset,
- Incomplete detector suite (Spread v2, Leadership Rotation missing),
- Bootstrap size <1000 (per spec §2.1),
- Thresholds provisional, not crypto-calibrated,
- Economic context: Sunday, low volatility, BTC $XX–$XXk range, volumes ~X% of daily average.

## 7. Technical Validation Checklist
- Data: ✓ ≥95% coverage, ✓ no skew, ✓ schema OK, TODO tick density.
- Pipeline: ✓ detectors ran, ✓ outputs structured, ✓ S3 integration, TODO reproducibility check.
- Stats: ✓ stable bootstrap, ✓ placebo behaved, TODO power analysis + null distribution check.

## 8. Next Steps
1. Analyze contrasting high-volatility period (e.g. Sept 22–23 liquidation cascade),
2. Inject synthetic positive controls,
3. Validate against known competitive baselines,
4. Deploy full detector suite,
5. Increase bootstrap to 1000, perform power analysis.

## 9. Conclusion
The ACD pipeline is **validated technically** on BTC-USD for 12:00–14:00 UTC. This is a baseline, not a conduct assessment. More environments and detectors are required for substantive claims.