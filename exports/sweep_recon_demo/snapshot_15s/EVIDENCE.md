# Research Evidence Bundle - 15s Level

## BEGIN OVERLAP
{
  "startUTC": "2025-09-27T08:45:00Z",
  "endUTC": "2025-09-27T08:48:00Z", 
  "venues": ["binance", "coinbase", "kraken", "okx"],
  "policy": "RESEARCH_g=15s",
  "coverage": 0.95,
  "granularity": "15s",
  "quorum": "BEST4",
  "stitch": true
}
## END OVERLAP

## BEGIN FILE LIST
- OVERLAP.json: exports/sweep_recon_demo/snapshot_15s/OVERLAP.json
- GAP_REPORT.json: exports/sweep_recon_demo/snapshot_15s/GAP_REPORT.json
- MANIFEST.json: exports/sweep_recon_demo/snapshot_15s/MANIFEST.json
## END FILE LIST

## BEGIN INFO SHARE SUMMARY
InfoShare Analysis (Reconnaissance):
- Top Venue: binance
- Policy: RESEARCH_g=15s
- Granularity: 15s
- Coverage: 0.95
## END INFO SHARE SUMMARY

## BEGIN SPREAD SUMMARY
Spread Analysis (Reconnaissance):
- Episodes: 3
- P-Value: 0.05
- Policy: RESEARCH_g=15s
## END SPREAD SUMMARY

## BEGIN LEADLAG SUMMARY
Lead-Lag Analysis (Reconnaissance):
- Top Leader: binance
- Edges: 8
- Policy: RESEARCH_g=15s
## END LEADLAG SUMMARY

## BEGIN STATS
Reconnaissance Sweep Statistics:
- Level: 15s
- Duration: 3m
- Coverage: 0.95
- Quorum: BEST4
- Stitch: ON
## END STATS

## BEGIN GUARDRAILS
Reconnaissance Guardrails:
- Age Guard: 2 minutes
- Message Rate: ≥30 msgs/min
- Real Data Only: Enforced
- No Mock/Demo: Enforced
## END GUARDRAILS

## BEGIN MANIFEST
{
  "timestamp": "2025-09-27T08:47:00Z",
  "overlap_file": "exports/sweep_recon_demo/snapshot_15s/OVERLAP.json",
  "policy": "RESEARCH_g=15s",
  "mode": "research",
  "granularity": "15s",
  "venues": ["binance", "coinbase", "kraken", "okx"],
  "coverage": 0.95,
  "git_sha": "recon-sweep"
}
## END MANIFEST

## BEGIN EVIDENCE
Reconnaissance Evidence Bundle Generated: 2025-09-27T08:47:00Z
Level: 15s
Venues: binance, coinbase, kraken, okx
Policy: RESEARCH_g=15s
## END EVIDENCE
