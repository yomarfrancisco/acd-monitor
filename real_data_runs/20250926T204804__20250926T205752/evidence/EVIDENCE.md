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
- evidence/leadlag_results.json: Lead-lag analysis results
- evidence/leadlag_summary.json: Lead-lag summary statistics
END

## SPREAD SUMMARY
BEGIN
{
  "status": "not_available",
  "reason": "Data cache miss - tick data not found in expected location",
  "note": "Analysis would require actual tick data from orchestrator capture"
}
END

## INFO SHARE SUMMARY
BEGIN
{
  "status": "not_available", 
  "reason": "Data cache miss - tick data not found in expected location",
  "note": "Analysis would require actual tick data from orchestrator capture"
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
  "analysis_type": "research"
}
END

## GUARDRAILS
BEGIN
{
  "synthetic_detection": "PASS - No synthetic data detected",
  "policy_validation": "PASS - RESEARCH_g=60s policy confirmed",
  "venue_coverage": "PASS - All 5 venues present",
  "data_integrity": "PASS - Overlap window validated",
  "analysis_bounds": "PASS - Analysis bounded to exact window"
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
  "analysis_completeness": "partial",
  "notes": [
    "Lead-lag analysis completed successfully",
    "Info share and spread analyses require actual tick data",
    "Window represents 9.8 minutes of continuous 5-venue overlap",
    "Research policy allows 60-second gap tolerance"
  ]
}
END
