# 1s Retry Failure Report

## Rule Applied
enforce_inner_join_coverage

## Diagnostics Results
{
  "timestamp": "2025-09-27T01:12:04.775562",
  "analyses": {
    "infoshare": {
      "success": false,
      "ordering_stable": false,
      "ranks_stable": false,
      "js_distance": 0.1
    },
    "spread": {
      "success": false,
      "pval_stable": false,
      "permutations": 5000
    },
    "leadlag": {
      "success": false,
      "coordination_stable": false,
      "top_leader_consistent": false,
      "horizons": [
        1,
        2,
        5
      ]
    }
  },
  "settings": {
    "min_duration_sec": 180,
    "permutes": 5000,
    "leadlag_horizons": [
      1,
      2,
      5
    ],
    "prev_tick_align": true,
    "refresh_time": true,
    "hac_bandwidth": "auto"
  }
}

## Recommendation
Stay at 2s baseline until court-mode 1s windows appear.

## Timestamp
2025-09-27T01:12:07.248054
