# Court 1s Evidence Bundle

## OVERLAP
```json
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
```

## FILE LIST
- info_share_results.json
- spread_results.json
- leadlag_results.json

## INFO SHARE SUMMARY
InfoShare analysis completed with court-strict settings.

## SPREAD SUMMARY
Spread analysis completed with 5000 permutations.

## LEADLAG SUMMARY
Lead-Lag analysis completed with horizons 1s, 2s, 5s.

## STATS
Policy: COURT_1s
Coverage: 0.999
Venues: 5

## GUARDRAILS
- ALL5 venues: ✅
- No stitching: ✅
- Coverage ≥ 0.999: ✅
- Permutations ≥ 5000: ✅

## MANIFEST
Court 1s baseline evidence bundle.

## EVIDENCE
Court-strict 1s evidence bundle generated successfully.
