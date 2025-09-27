# Sub-Minute Research Analysis Evidence Bundle

## OVERLAP
BEGIN
{"start": "2025-09-27T09:40:00.380000+00:00", "end": "2025-09-27T09:49:48.383000+00:00", "duration_minutes": 9.80005, "venues": ["binance", "bybit"], "policy": "RESEARCH_g=30s", "coverage": 1.0, "granularity_sec": 30, "min_duration_min": 3}
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
  "status": "completed",
  "resample": "1s",
  "standardize": "none",
  "venues": {
    "binance": 0.39803145118335936,
    "bybit": 0.6019685488166406
  },
  "coverage": {
    "binance": 0.9865996970905703,
    "bybit": 0.9799329242098518
  },
  "total_venues": 2
}
END

## SPREAD SUMMARY
BEGIN
{
  "status": "completed",
  "native": "1s",
  "episodes": 4,
  "avg_lift": 0.13119890406724052,
  "p_value": 0.012323344486727979,
  "permutations": 2000
}
END

## LEADLAG SUMMARY
BEGIN
{
  "status": "completed",
  "horizons": [
    1,
    2,
    5
  ],
  "coordination": 0.8598528437324806,
  "top_leader": "bybit",
  "edges": []
}
END

## STATS
BEGIN
{
  "granularity_sec": 30,
  "policy": "RESEARCH_g=30s",
  "analysis_type": "subminute_research",
  "timestamp": "2025-09-27T11:53:18.870807"
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
  "created_at": "2025-09-27T11:53:18.870820",
  "granularity_sec": 30,
  "policy": "RESEARCH_g=30s",
  "window": {
    "start": "2025-09-27T09:40:00.380000+00:00",
    "end": "2025-09-27T09:49:48.383000+00:00",
    "duration_minutes": 9.80005,
    "venues": [
      "binance",
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
  "timestamp": "2025-09-27T11:53:18.870833"
}
END
