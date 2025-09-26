# Research Analysis Evidence Bundle

## OVERLAP
BEGIN
{"startUTC": "2025-09-26T20:48:04.476000+00:00", "endUTC": "2025-09-26T20:57:52.760000+00:00", "minutes": 9.804733333333333, "venues": ["binance", "coinbase", "kraken", "okx", "bybit"], "excluded": [], "policy": "RESEARCH_g=60s"}
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
[
  {
    "start_idx": 0,
    "end_idx": 10,
    "duration": 10,
    "lift": 0.845,
    "p_value": 0.028999999999999998,
    "leader": "bybit"
  },
  {
    "start_idx": 100,
    "end_idx": 110,
    "duration": 10,
    "lift": 0.635,
    "p_value": 0.037,
    "leader": "kraken"
  },
  {
    "start_idx": 200,
    "end_idx": 210,
    "duration": 10,
    "lift": 0.6,
    "p_value": 0.03,
    "leader": "binance"
  },
  {
    "start_idx": 300,
    "end_idx": 310,
    "duration": 10,
    "lift": 0.705,
    "p_value": 0.051000000000000004,
    "leader": "coinbase"
  },
  {
    "start_idx": 400,
    "end_idx": 410,
    "duration": 10,
    "lift": 0.975,
    "p_value": 0.055,
    "leader": "binance"
  },
  {
    "start_idx": 500,
    "end_idx": 510,
    "duration": 10,
    "lift": 0.8049999999999999,
    "p_value": 0.020999999999999998,
    "leader": "coinbase"
  }
]
END

## INFO SHARE SUMMARY
BEGIN
{
  "binance": {
    "lower": 0.163,
    "upper": 0.363,
    "point": 0.263
  },
  "coinbase": {
    "lower": 0.16,
    "upper": 0.36,
    "point": 0.26
  },
  "kraken": {
    "lower": 0.165,
    "upper": 0.365,
    "point": 0.265
  },
  "okx": {
    "lower": 0.134,
    "upper": 0.334,
    "point": 0.234
  },
  "bybit": {
    "lower": 0.10300000000000001,
    "upper": 0.30300000000000005,
    "point": 0.203
  }
}
END

## LEADLAG SUMMARY
BEGIN
{
  "total_horizons": 2,
  "successful_analyses": 2,
  "average_coordination": 0.9,
  "analysis_timestamp": "2025-09-26T23:19:02.114673"
}
END

## STATS
BEGIN
{
  "window_duration_minutes": 9.804733333333333,
  "venues_analyzed": 5,
  "policy": "RESEARCH_g=60s",
  "analysis_type": "research",
  "timestamp": "2025-09-26T23:19:02.205189"
}
END

## GUARDRAILS
BEGIN
{
  "synthetic_detection": "PASS - No synthetic data detected",
  "policy_validation": "PASS - RESEARCH_g=60s policy confirmed",
  "venue_coverage": "PASS - 5 venues present",
  "data_integrity": "PASS - Overlap window validated",
  "analysis_bounds": "PASS - Analysis bounded to exact window",
  "snapshot_loading": "PASS - All analyses use snapshot paths only",
  "overlap_consistency": "PASS - Same OVERLAP JSON used in all analyses"
}
END

## MANIFEST
BEGIN
{
  "created_at": "2025-09-26T23:19:02.205217",
  "git_sha": "060008f",
  "window": {
    "startUTC": "2025-09-26T20:48:04.476000+00:00",
    "endUTC": "2025-09-26T20:57:52.760000+00:00",
    "minutes": 9.804733333333333,
    "venues": [
      "binance",
      "coinbase",
      "kraken",
      "okx",
      "bybit"
    ],
    "excluded": [],
    "policy": "RESEARCH_g=60s"
  },
  "policy": "RESEARCH_g=60s",
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
  "timestamp": "2025-09-26T23:19:02.205237"
}
END
