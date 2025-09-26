# Research Baseline 2s Evidence

## BEGIN OVERLAP
{
  "startUTC": "2025-09-26T21:30:00.000000+00:00",
  "endUTC": "2025-09-26T21:32:00.000000+00:00",
  "minutes": 2.0,
  "venues": [
    "binance",
    "coinbase",
    "kraken",
    "okx",
    "bybit"
  ],
  "policy": "RESEARCH_g=2s",
  "coverage": 0.99,
  "granularity_sec": 2,
  "min_duration_min": 1,
  "baseline": true
}
## END OVERLAP

## BEGIN FILE LIST
- OVERLAP.json
- MANIFEST.json
- GAP_REPORT.json
- EVIDENCE.md
- info_share_results.json
- spread_results.json
- leadlag_results.json
- research_bundle_2s.zip
## END FILE LIST

## BEGIN INFO SHARE SUMMARY
InfoShare analysis completed on 2s research baseline with:
- Standardization: none
- GG blend alpha: 0.7
- Venues: binance, coinbase, kraken, okx, bybit
- Duration: 2.0 minutes
- Coverage: 0.990
## END INFO SHARE SUMMARY

## BEGIN SPREAD SUMMARY
Spread compression analysis completed on 2s research baseline with:
- Permutations: 2000
- Analysis window: 2025-09-26T21:30:00.000000+00:00 to 2025-09-26T21:32:00.000000+00:00
- Venues: binance, coinbase, kraken, okx, bybit
## END SPREAD SUMMARY

## BEGIN LEADLAG SUMMARY
Lead-Lag analysis completed on 2s research baseline with:
- Horizons: 1s, 2s, 5s
- Analysis window: 2025-09-26T21:30:00.000000+00:00 to 2025-09-26T21:32:00.000000+00:00
- Venues: binance, coinbase, kraken, okx, bybit
## END LEADLAG SUMMARY

## BEGIN STATS
- Baseline type: 2s research
- Policy: RESEARCH_g=2s
- Duration: 2.0 minutes
- Coverage: 0.990
- Venues: 5
- Analysis timestamp: 2025-09-27T01:09:09.888994
## END STATS

## BEGIN GUARDRAILS
- InfoShare bounds: [0,1]
- Venue sum: ≈1.0
- Permutations: ≥2000
- No NaNs after inner join
- Research baseline: 2s
## END GUARDRAILS

## BEGIN MANIFEST
{
  "baseline_type": "2s_research",
  "policy": "RESEARCH_g=2s",
  "research_baseline": "2s",
  "timestamp": "2025-09-27T01:09:09.889009"
}
## END MANIFEST

## BEGIN EVIDENCE
Research baseline 2s evidence bundle created successfully.
All analyses completed with proper guardrails and validation.
Baseline ready for court-mode comparison.
## END EVIDENCE
