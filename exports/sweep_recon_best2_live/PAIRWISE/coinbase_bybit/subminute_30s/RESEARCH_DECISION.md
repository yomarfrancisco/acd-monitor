# Research Diagnostics Decision

## Decision: [RESEARCH:FLAGGED]

**Granularity**: 30s  
**Timestamp**: 2025-09-27T12:47:35.053785  
**Status**: FLAGGED

## Flags (1)

- Missing analysis sections

## Reasons

- InfoShare patterns: 0 flags
- Spread patterns: 0 flags
- Lead-Lag patterns: 0 flags
- Coherence issues: 1 flags

## Detailed Metrics

### InfoShare Analysis
- Leader Persistence: False
- Dominance Threshold: 0.000
- Venue Concentration: 0.000

### Spread Analysis  
- Episode Count: 0
- Clustering Detected: False
- Compression Ratio: 0.000

### Lead-Lag Analysis
- Coordination Score: 0.000
- Edge Count: 0
- Top Leader: N/A

### Coherence Analysis
- Overall Coherence: False
- InfoShare-Spread Alignment: False
- Spread-LeadLag Alignment: False

## JSON Decision

```json
{
  "status": "FLAGGED",
  "granularity": "30s",
  "timestamp": "2025-09-27T12:47:35.053785",
  "flags": [
    "Missing analysis sections"
  ],
  "metrics": {
    "infoshare": {
      "leader_persistence": false,
      "dominance_threshold": 0.0,
      "venue_concentration": 0.0,
      "flags": []
    },
    "spread": {
      "episode_count": 0,
      "clustering_detected": false,
      "compression_ratio": 0.0,
      "flags": []
    },
    "leadlag": {
      "coordination_score": 0.0,
      "edge_count": 0,
      "top_leader": null,
      "flags": []
    },
    "coherence": {
      "infoshare_spread_alignment": false,
      "spread_leadlag_alignment": false,
      "overall_coherence": false,
      "flags": [
        "Missing analysis sections"
      ]
    }
  },
  "reasons": [
    "InfoShare patterns: 0 flags",
    "Spread patterns: 0 flags",
    "Lead-Lag patterns: 0 flags",
    "Coherence issues: 1 flags"
  ]
}
```
