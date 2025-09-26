# NO OVERLAP REPORT

**Generated**: 2025-09-26T21:42:31  
**Status**: [OVERLAP:INSUFFICIENT]  
**Reason**: No continuous overlap window found within capture period

## OVERLAP STATUS

```json
{
  "status": "INSUFFICIENT",
  "venues_ready": ["binance", "coinbase", "kraken", "okx", "bybit"],
  "venues_missing": [],
  "minutes_max": 0,
  "reason": "Data gaps exceed 1-second threshold",
  "policy_attempted": ["BEST4_30m", "BEST4_20m", "BEST4_10m", "ALL5_10m"]
}
```

## HEARTBEAT SUMMARY

| Venue | Messages | Last Tick | Lag (ms) | Gaps (30s) |
|-------|----------|-----------|----------|------------|
| binance | 19 | 1758915513024 | 0 | 0 |
| coinbase | 108 | - | - | 0 |
| kraken | 6 | - | - | 0 |
| okx | 118 | - | - | 0 |
| bybit | 84 | - | - | 0 |

## DATA GAP ANALYSIS

- **binance**: 219 gaps > 1.0s in overlap window
- **coinbase**: 127 gaps > 1.0s in overlap window  
- **kraken**: 124 gaps > 1.0s in overlap window
- **okx**: 5 gaps > 1.0s in overlap window
- **bybit**: 118 gaps > 1.0s in overlap window

## RECOMMENDATION

**Extend capture window and/or relax to BEST3_20m (not for court), or schedule synchronized capture across venues.**

### Options:
1. **Extend capture window**: Run for 6+ hours to accumulate sufficient continuous data
2. **Relax gap threshold**: Allow 2-3 second gaps (not recommended for court evidence)
3. **Synchronized capture**: Coordinate with exchanges for simultaneous data collection
4. **Alternative venues**: Consider additional exchanges with more stable feeds

## CAPTURE METRICS

- **Duration**: 3 minutes (target: 180 minutes)
- **Venues active**: 5/5 (100%)
- **Data files created**: 260 parquet files
- **Gap threshold**: 1.0 seconds (strict)
- **Policy hierarchy**: BEST4_30m → BEST4_20m → BEST4_10m → ALL5_10m

## TECHNICAL NOTES

- All venues are actively capturing data
- Data gaps are common in real-time cryptocurrency feeds
- 1-second gap threshold is appropriate for court evidence
- System correctly detected insufficient overlap and aborted gracefully
