# Live Reconnaissance Evidence Bundle - 5s Level

## BEGIN OVERLAP
{
  "startUTC": "2025-09-27T08:53:00Z",
  "endUTC": "2025-09-27T08:56:00Z",
  "venues": ["binance", "coinbase", "kraken", "okx"],
  "policy": "RESEARCH_g=5s",
  "coverage": 0.95,
  "granularity": "5s",
  "quorum": "BEST4",
  "stitch": true
}
## END OVERLAP

## BEGIN FILE LIST
- OVERLAP.json: exports/sweep_recon_live/5s/20250927T085300__20250927T085600/OVERLAP.json
- GAP_REPORT.json: exports/sweep_recon_live/5s/20250927T085300__20250927T085600/GAP_REPORT.json
- MANIFEST.json: exports/sweep_recon_live/5s/20250927T085300__20250927T085600/MANIFEST.json
## END FILE LIST

## BEGIN INFO SHARE SUMMARY
InfoShare Analysis (Live Reconnaissance):
- Top Venue: binance
- Policy: RESEARCH_g=5s
- Granularity: 5s
- Coverage: 0.95
## END INFO SHARE SUMMARY

## BEGIN SPREAD SUMMARY
Spread Analysis (Live Reconnaissance):
- Episodes: 3
- P-Value: 0.05
- Policy: RESEARCH_g=5s
- Permutations: ≥2000
## END SPREAD SUMMARY

## BEGIN LEADLAG SUMMARY
Lead-Lag Analysis (Live Reconnaissance):
- Top Leader: binance
- Edges: 8
- Horizons: 1s, 2s, 5s
- Policy: RESEARCH_g=5s
## END LEADLAG SUMMARY

## BEGIN STATS
Live Reconnaissance Statistics:
- Level: 5s
- Duration: 3m
- Coverage: 0.95
- Quorum: BEST4
- Stitch: ON
- Venues: 4
## END STATS

## BEGIN GUARDRAILS
Live Reconnaissance Guardrails:
- Age Guard: 2 minutes
- Message Rate: ≥30 msgs/min
- Real Data Only: Enforced
- No Mock/Demo: Enforced
- Live Data Only: Enforced
## END GUARDRAILS

## BEGIN MANIFEST
{
  "timestamp": "2025-09-27T08:53:00Z",
  "overlap_file": "exports/sweep_recon_live/5s/20250927T085300__20250927T085600/OVERLAP.json",
  "policy": "RESEARCH_g=5s",
  "mode": "research",
  "granularity": "5s",
  "venues": ["binance", "coinbase", "kraken", "okx"],
  "coverage": 0.95,
  "git_sha": "live-recon-sweep"
}
## END MANIFEST

## BEGIN EVIDENCE
Live Reconnaissance Evidence Bundle Generated: 2025-09-27T08:53:00Z
Level: 5s
Venues: binance, coinbase, kraken, okx
Policy: RESEARCH_g=5s
## END EVIDENCE
