# Court Evidence Bundle

## BEGIN OVERLAP
{
  "startUTC": "2025-09-27T01:00:00.000000+00:00",
  "endUTC": "2025-09-27T01:02:00.000000+00:00",
  "minutes": 2.0,
  "venues": [
    "binance",
    "coinbase",
    "kraken",
    "okx",
    "bybit"
  ],
  "policy": "COURT_1s",
  "coverage": 0.999,
  "granularity_sec": 1,
  "min_duration_min": 2,
  "all_venues": true,
  "stitch": false,
  "mode": "COURT",
  "granularity": "1s"
}
## END OVERLAP

## BEGIN FILE LIST
- OVERLAP.json: court/1s/OVERLAP.json
- InfoShare Results: court/1s/evidence/info_share_results.json
- Spread Results: court/1s/evidence/spread_results.json
- Lead-Lag Results: court/1s/evidence/leadlag_results.json
- MANIFEST.json: court/1s/evidence/MANIFEST.json
## END FILE LIST

## BEGIN INFO SHARE SUMMARY
InfoShare Analysis Results:
- Top Venue: N/A
- Venue Shares: {}
- Window: 2.0 minutes
- Policy: COURT_1s
## END INFO SHARE SUMMARY

## BEGIN SPREAD SUMMARY
Spread Analysis Results:
- Episodes: 2
- P-Value: N/A
- Permutations: N/A
- Policy: COURT_1s
## END SPREAD SUMMARY

## BEGIN LEADLAG SUMMARY
Lead-Lag Analysis Results:
- Top Leader: N/A
- Edges: 20
- Horizons: 1s, 5s
- Policy: COURT_1s
## END LEADLAG SUMMARY

## BEGIN STATS
Court Mode Analysis Statistics:
- Analysis Type: Court Diagnostics
- Gap Policy: ≤1s (strict)
- Stitching: Disabled
- Venue Policy: ALL5
- Coverage: ≥0.999
## END STATS

## BEGIN GUARDRAILS
Court Mode Guardrails:
- Real Data Only: Enforced
- No Synthetic: Enforced
- Coverage Threshold: ≥0.999
- Gap Tolerance: ≤1s
- All 5 Venues: Required
## END GUARDRAILS

## BEGIN MANIFEST
{
  "mode": "COURT",
  "granularity": "1s",
  "policy": "COURT_1s",
  "overlap_window": {
    "startUTC": "2025-09-27T01:00:00.000000+00:00",
    "endUTC": "2025-09-27T01:02:00.000000+00:00",
    "minutes": 2.0,
    "venues": [
      "binance",
      "coinbase",
      "kraken",
      "okx",
      "bybit"
    ],
    "policy": "COURT_1s",
    "coverage": 0.999,
    "granularity_sec": 1,
    "min_duration_min": 2,
    "all_venues": true,
    "stitch": false,
    "mode": "COURT",
    "granularity": "1s"
  },
  "analysis_settings": {
    "permutes": 5000,
    "alpha": 0.05,
    "no_stitch": true,
    "all5": true
  },
  "evidence_files": [
    "info_share_results.json",
    "spread_results.json",
    "leadlag_results.json",
    "EVIDENCE.md"
  ]
}
## END MANIFEST

## BEGIN EVIDENCE
Court Evidence Bundle Generated: 2025-09-27T20:42:02.649463
Overlap Window: 2025-09-27T01:00:00.000000+00:00 to 2025-09-27T01:02:00.000000+00:00
Venues: binance, coinbase, kraken, okx, bybit
Policy: COURT_1s
## END EVIDENCE