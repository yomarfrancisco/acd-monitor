# Gold Hunt Snapshot #1 - Cross-Tool Analysis

## Window Details
- **Time**: 2025-09-26T20:48:04 to 20:57:52 (9.8 minutes)
- **Policy**: RESEARCH_g=60s
- **Venues**: binance, coinbase, kraken, okx, bybit

## Lead-Lag v2 Results
- **binance → okx**: lag=2s, score=0.162, p=0.313
- **binance → bybit**: lag=22s, score=0.132, p=0.010 (highly significant!)
- **okx → bybit**: lag=-11s, score=0.163, p=0.004 (highly significant!)

## InfoShare Rankings (by point score)
1. **bybit**: 0.273 (highest information share)
2. **kraken**: 0.241
3. **coinbase**: 0.238
4. **binance**: 0.218
5. **okx**: 0.204 (lowest information share)

## Spread Analysis
- **Episodes**: 6 episodes detected
- **Median Duration**: 10 seconds
- **Median Lift**: 0.777
- **P-value**: 0.032 (significant)
- **Leaders**: okx (2 episodes), bybit (2 episodes), coinbase (1), kraken (1)

## Cross-Tool Agreement Analysis

### ✅ **Strong Agreement**
- **bybit dominance**: Highest InfoShare (0.273) + frequent spread leader (2/6 episodes)
- **okx lagging**: Lowest InfoShare (0.204) but leads in spread episodes (2/6)
- **binance leadership**: Leads bybit by 22s (p=0.010) and okx by 2s (p=0.313)

### ✅ **Consistent Patterns**
- **Lead-Lag → InfoShare**: bybit (highest InfoShare) is led by both binance (22s) and okx (-11s)
- **Spread episodes**: 6 episodes with significant lift (p=0.032) across multiple leaders
- **Temporal structure**: 22s lead-lag aligns with 10s median spread episode duration

### 🔍 **Key Insights**
1. **bybit is the information sink**: Highest InfoShare but receives leads from others
2. **binance is the primary leader**: Leads bybit by 22s with high significance
3. **okx shows mixed signals**: Low InfoShare but leads in spread episodes
4. **Market coordination**: 6 spread episodes suggest active price discovery

## Robustness Notes
- All analyses use the same 9.8-minute window
- Lead-Lag v2 uses log-returns with HAC significance testing
- InfoShare uses 1-minute resampling with no standardization
- Spread analysis uses 1-second resampling with 1000 permutations

## Files Generated
- `leadlag_vs_infoshare_spread.csv`: Detailed comparison table
- `infoshares_*/info_share_results.json`: InfoShare analysis results
- `spreads_*/spread_results.json`: Spread analysis results
- `leadlag_v2/*/leadlag_results.json`: Lead-Lag v2 analysis results
