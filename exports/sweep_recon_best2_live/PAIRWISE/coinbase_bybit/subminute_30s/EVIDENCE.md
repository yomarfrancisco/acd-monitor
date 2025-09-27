# Sub-Minute Research Analysis Evidence Bundle

## OVERLAP
BEGIN
{
  "start": "2025-09-27T09:40:00.000000+00:00",
  "end": "2025-09-27T09:49:48.000000+00:00",
  "minutes": 9.8,
  "venues": ["coinbase", "bybit"],
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
    "coinbase": 0.450,
    "bybit": 0.550
  },
  "total_venues": 2,
  "max_share": 0.550,
  "top_leader": "bybit",
  "entropy": 0.693,
  "concentration": 0.550
}
END

## SPREAD SUMMARY
BEGIN
{
  "episodes": {
    "count": 3,
    "median_duration": 2.5,
    "total_duration": 7.5,
    "p_value": 0.025,
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
  "coordination": 0.750,
  "top_leader": "bybit",
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
  "timestamp": "2025-09-27T12:43:02.031837"
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
  "created_at": "2025-09-27T12:43:02.031849",
  "granularity_sec": 30,
  "policy": "RESEARCH_g=30s",
  "window": {
    "start": "2025-09-27T09:40:02.252000+00:00",
    "end": "2025-09-27T09:49:48.383000+00:00",
    "duration_minutes": 9.768849999999999,
    "venues": [
      "coinbase",
      "bybit"
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
  "timestamp": "2025-09-27T12:43:02.031862"
}
END
