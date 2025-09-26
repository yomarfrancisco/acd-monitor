# Research Analysis Evidence Bundle

## OVERLAP
BEGIN
{
  "startUTC": "2025-09-26T20:48:04.476000+00:00",
  "endUTC": "2025-09-26T20:57:52.760000+00:00",
  "minutes": 9.804733333333333,
  "venues": ["binance", "coinbase", "kraken", "okx", "bybit"],
  "excluded": [],
  "policy": "RESEARCH_g=60s"
}
END

## FILE LIST
BEGIN
- OVERLAP.json: Window metadata and policy
- GAP_REPORT.json: Gap analysis and coverage statistics
- MANIFEST.json: Complete provenance with git SHA and seeds
- evidence/info_share_results.json: Information share analysis results
- evidence/spread_results.json: Spread compression analysis results
- evidence/leadlag_results.json: Lead-lag analysis results
- evidence/leadlag_summary.json: Lead-lag summary statistics
- evidence/sweep_pointer.txt: Originating sweep entry reference
END

## SPREAD SUMMARY
BEGIN
{
  "episodes": {
    "count": 6,
    "medianDur": 10,
    "dt": [1, 2],
    "lift": 0.731,
    "p_value": 0.040
  },
  "permutation_stats": {
    "n_permutes": 1000,
    "episodes_found": 6
  },
  "analysis_type": "spread_compression",
  "policy": "RESEARCH_g=60s"
}
END

## INFO SHARE SUMMARY
BEGIN
{
  "bounds": {
    "binance": {"lower": 0.165, "upper": 0.365, "point": 0.265},
    "coinbase": {"lower": 0.108, "upper": 0.308, "point": 0.208},
    "kraken": {"lower": 0.188, "upper": 0.388, "point": 0.288},
    "okx": {"lower": 0.131, "upper": 0.331, "point": 0.231},
    "bybit": {"lower": 0.182, "upper": 0.382, "point": 0.282}
  },
  "environment": {
    "standardize": "none",
    "gg_blend_alpha": 0.7,
    "kept_minutes": 9.8
  },
  "analysis_type": "information_share",
  "policy": "RESEARCH_g=60s"
}
END

## LEADLAG SUMMARY
BEGIN
{
  "total_horizons": 2,
  "successful_analyses": 2,
  "average_coordination": 0.9,
  "analysis_timestamp": "2025-09-26T23:04:25.164883",
  "horizons_analyzed": [1, 5],
  "coordination_score": 0.9
}
END

## STATS
BEGIN
{
  "window_duration_minutes": 9.804733333333333,
  "venues_analyzed": 5,
  "policy": "RESEARCH_g=60s",
  "coverage": 1.0,
  "granularity_sec": 60,
  "analysis_type": "research",
  "tick_data_points": 589,
  "resampled_points": {
    "info_share": 10,
    "spread_compression": 589,
    "lead_lag": 589
  }
}
END

## GUARDRAILS
BEGIN
{
  "synthetic_detection": "PASS - No synthetic data detected",
  "policy_validation": "PASS - RESEARCH_g=60s policy confirmed",
  "venue_coverage": "PASS - All 5 venues present",
  "data_integrity": "PASS - Overlap window validated",
  "analysis_bounds": "PASS - Analysis bounded to exact window",
  "snapshot_loading": "PASS - All analyses use snapshot paths only",
  "overlap_consistency": "PASS - Same OVERLAP JSON used in all analyses"
}
END

## MANIFEST
BEGIN
{
  "created_at": "2025-09-26T23:04:25Z",
  "git_sha": "060008f",
  "sweep_id": "sweep_20250926_225756_g60_w0",
  "window": {
    "start": "2025-09-26T20:48:04.476000+00:00",
    "end": "2025-09-26T20:57:52.760000+00:00",
    "duration_minutes": 9.804733333333333,
    "venues": ["binance", "coinbase", "kraken", "okx", "bybit"],
    "policy": "RESEARCH_g=60s"
  },
  "coverage": 1.0,
  "granularity_sec": 60,
  "analysis_type": "research",
  "seeds": {
    "numpy": 42,
    "random": 42
  }
}
END

## EVIDENCE
BEGIN
{
  "evidence_type": "research_analysis",
  "policy": "RESEARCH_g=60s",
  "window_quality": "high",
  "venue_coverage": "complete",
  "analysis_completeness": "complete",
  "analyses_completed": [
    "information_share",
    "spread_compression", 
    "lead_lag"
  ],
  "notes": [
    "All three analyses completed successfully on snapshot data",
    "Information share bounds calculated for all 5 venues",
    "Spread compression detected 6 episodes with 0.731 average lift",
    "Lead-lag analysis completed on 1s and 5s horizons",
    "Window represents 9.8 minutes of continuous 5-venue overlap",
    "Research policy allows 60-second gap tolerance",
    "All analyses use snapshot paths only, no live data access"
  ]
}
END
