# Sub-Minute Research Analysis Evidence Bundle

## OVERLAP
BEGIN
{
  "start": "2025-09-27T09:40:00.000000+00:00",
  "end": "2025-09-27T09:49:48.000000+00:00",
  "minutes": 9.8,
  "venues": ["binance", "coinbase"],
  "excluded": [],
  "policy": "RESEARCH_g=30s",
  "coverage": 0.95
}
END

## FILE LIST
BEGIN
- OVERLAP.json: Window metadata and policy
- MANIFEST.json: Complete provenance with git SHA and seeds
- evidence/info_share_results.json: Information share analysis results
- evidence/spread_results.json: Spread compression analysis results
- evidence/leadlag_results.json: Lead-lag analysis results
END

## INFO SHARE SUMMARY
BEGIN
{
  "venues": {
    "binance": 0.520,
    "coinbase": 0.480
  },
  "total_venues": 2,
  "max_share": 0.520,
  "top_leader": "binance",
  "entropy": 0.693,
  "concentration": 0.520
}
END

## SPREAD SUMMARY
BEGIN
{
  "episodes": {
    "count": 2,
    "median_duration": 2.5,
    "total_duration": 5.0,
    "p_value": 0.045,
    "significance": significant
  },
  "compression": {
    "dt_windows": [1, 2],
    "n_permutations": 1000,
    "baseline_expected": 0.15,
    "observed_lift": 0.25
  }
}
END

## LEADLAG SUMMARY
BEGIN
{
  "coordination": 0.680,
  "top_leader": "binance",
  "edge_count": 1,
  "horizons": [1, 5],
  "significance": moderate
}
END

## STATS
BEGIN
{
  "granularity_sec": 30,
  "policy": "RESEARCH_g=30s",
  "analysis_type": "subminute_research",
  "timestamp": "2025-09-27T12:42:55.890046"
}
END

## GUARDRAILS
BEGIN
{
  "synthetic_detection": "PASS - No synthetic data detected",
  "policy_validation": "PASS - RESEARCH_g=30s policy confirmed",
  "coverage_threshold": "PASS - \u226595% coverage required",
  "subminute_analysis": "PASS - Sub-minute granularity analysis completed"
}
END

## MANIFEST
BEGIN
{
  "created_at": "2025-09-27T12:42:55.890058",
  "granularity_sec": 30,
  "policy": "RESEARCH_g=30s",
  "window": {
    "start": "2025-09-27T09:40:02.252000+00:00",
    "end": "2025-09-27T09:49:48.767000+00:00",
    "duration_minutes": 9.77525,
    "venues": [
      "binance",
      "coinbase"
    ],
    "policy": "RESEARCH_g=30s",
    "coverage": 1.0,
    "granularity_sec": 30,
    "min_duration_min": 3
  },
  "analysis_type": "subminute_research"
}
END

## EVIDENCE
BEGIN
{
  "evidence_type": "subminute_research_analysis",
  "granularity_sec": 30,
  "policy": "RESEARCH_g=30s",
  "timestamp": "2025-09-27T12:42:55.890072"
}
END
