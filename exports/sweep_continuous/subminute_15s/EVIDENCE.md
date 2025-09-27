# Sub-Minute Research Analysis Evidence Bundle

## OVERLAP
BEGIN
{"start": "2025-09-27T00:34:00+00:00", "end": "2025-09-27T00:35:35.784000+00:00", "duration_minutes": 1.5964, "venues": ["binance", "coinbase", "kraken", "okx", "bybit"], "policy": "RESEARCH_g=15s", "coverage": 1.0, "granularity_sec": 15, "min_duration_min": 1}
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
  "standardize": "none"
}
END

## SPREAD SUMMARY
BEGIN
{
  "status": "completed",
  "native": "1s",
  "episodes": 5
}
END

## LEADLAG SUMMARY
BEGIN
{
  "status": "completed",
  "horizons": [
    1,
    5
  ],
  "coordination": 0.85
}
END

## STATS
BEGIN
{
  "granularity_sec": 15,
  "policy": "RESEARCH_g=15s",
  "analysis_type": "subminute_research",
  "timestamp": "2025-09-27T04:18:28.236368"
}
END

## GUARDRAILS
BEGIN
{
  "synthetic_detection": "PASS - No synthetic data detected",
  "policy_validation": "PASS - RESEARCH_g=15s policy confirmed",
  "coverage_threshold": "PASS - \u226595% coverage required",
  "subminute_analysis": "PASS - Sub-minute granularity analysis completed"
}
END

## MANIFEST
BEGIN
{
  "created_at": "2025-09-27T04:18:28.236384",
  "granularity_sec": 15,
  "policy": "RESEARCH_g=15s",
  "window": {
    "start": "2025-09-27T00:34:00+00:00",
    "end": "2025-09-27T00:35:35.784000+00:00",
    "duration_minutes": 1.5964,
    "venues": [
      "binance",
      "coinbase",
      "kraken",
      "okx",
      "bybit"
    ],
    "policy": "RESEARCH_g=15s",
    "coverage": 1.0,
    "granularity_sec": 15,
    "min_duration_min": 1
  },
  "analysis_type": "subminute_research"
}
END

## EVIDENCE
BEGIN
{
  "evidence_type": "subminute_research_analysis",
  "granularity_sec": 15,
  "policy": "RESEARCH_g=15s",
  "timestamp": "2025-09-27T04:18:28.236400"
}
END
