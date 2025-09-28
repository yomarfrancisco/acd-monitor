# Gold Hunt v1 - Analysis Index

## Window Specification
- **Pair**: BTC-USD
- **Duration**: 9.8 minutes (588 seconds)
- **Time Range**: 2025-09-26T20:48:04 to 2025-09-26T20:57:52 UTC
- **Venues**: binance, coinbase, kraken, okx, bybit
- **Policy**: RESEARCH_g=60s
- **Coverage**: 100% (no gaps detected)

## Random Seeds
- **Primary seed**: 42 (reproducible across all phases)
- **Bootstrap samples**: 1000 (confidence intervals)
- **Shuffle iterations**: 500 (null baselines)

## Phase 1: Multiple Testing Corrections
- **Location**: `experiments/gold_hunt_v1/phase1/`
- **Files**: 
  - `infoshare_corrections.csv` - InfoShare bounds with Bonferroni/BH-FDR
  - `spread_corrections.csv` - Spread episodes with corrections
  - `leadlag_corrections.csv` - Lead-Lag v2 with corrections
  - `summary_report.md` - Multiple testing summary
- **Key Finding**: Spread episodes survive BH-FDR (q=0.10), InfoShare/Lead-Lag pruned

## Phase 2: Section B Completion
- **Location**: `experiments/gold_hunt_v1/phase2_nulls/`
- **Files**:
  - `episode_level_adjustments.csv` - Episode-level FDR corrections
  - `duration_sensitivity.csv` - Duration threshold sensitivity grid
  - `section_b_completion_report.md` - Null baseline completion report
- **Key Finding**: 1 episode survives across 5s & 10s thresholds (robust signal)

## Phase 3: Economic Controls
- **Location**: `experiments/gold_hunt_v1/phase3_controls/`
- **Files**:
  - `venue_controls.csv` - Volume, volatility, liquidity per venue
  - `infoshare_correlations.csv` - InfoShare-control associations
  - `episode_contrasts.csv` - Episode vs non-episode control differences
  - `economic_controls_report.md` - Controls analysis summary
- **Key Finding**: Controls show directionally positive association, not statistically conclusive

## Key Results Summary
- **Spread Episodes**: 6 detected, all survive BH-FDR (q=0.10)
- **Duration Robustness**: 1 episode survives 5s & 10s thresholds
- **Economic Controls**: Partial explanation via volume/liquidity
- **Sample Limitation**: 9.8 minutes insufficient for stable InfoShare/Lead-Lag

## Next Steps
- **Phase 4**: ETH-USD cross-validation (same window spec)
- **Phase 5**: 30+ minute window analysis (preregistered gates)
- **Status**: Awaiting 30+ minute window from orchestrators

## File Paths
- **Phase 1**: `experiments/gold_hunt_v1/phase1/` + `exports/gold_hunt/latest/phase1/`
- **Phase 2**: `experiments/gold_hunt_v1/phase2_nulls/` + `exports/gold_hunt/latest/phase2_nulls/`
- **Phase 3**: `experiments/gold_hunt_v1/phase3_controls/` + `exports/gold_hunt/latest/phase3_controls/`
- **Phase 4**: `experiments/gold_hunt_v1/eth_phase1/` + `exports/gold_hunt/latest/eth_phase1/`
- **Phase 5**: `experiments/gold_hunt_v1/phase4_30m/` + `exports/gold_hunt/latest/phase4_30m/`

## Single Episode Survivor (5s & 10s thresholds)
- **Episode ID**: 1 (from duration_sensitivity.csv)
- **Original Duration**: 10 seconds
- **Survives 5s**: YES
- **Survives 10s**: YES  
- **Survives 15s**: NO
- **Leader**: binance
- **Lift**: 0.8
- **Interpretation**: Robust coordination signal
