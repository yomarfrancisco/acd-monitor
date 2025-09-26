# ACD Output Schema (Working)

## 0. Scope
Pair: BTC-USD (spot) and BTC perps (funding).
Timezone: UTC. Day key = midnight UTC millis.

## 1. Inputs (per day unless noted)
- close: float USD (per venue)
- consensus: float USD (cross-venue consensus)
- leader: venue key closest to consensus (consensus-proximity)
- leaderGapBps: float, (|leader - consensus| / consensus) * 1e4
- volumeUsd (per venue): float
- trueRange: float (ATR input) or daily TR
- sigma20: realized volatility (annualized) from closes
- fundingRate (per venue, per 8h): resampled daily mean (funding regimes only)

## 2. Environments (labels)
- Volatility regime: terciles of sigma20 → {low, med, high}
- Funding regime: terciles of daily funding mean → {low, med, high}
- Funding shock: binary, |Δfunding| > p90(|Δfunding|)
- Liquidity regime (proxy): terciles of composite z-score over:
  {volumeUsd, trueRange/close, |return|/sigma20}

## 3. Leadership metrics
- Daily leader (consensus-proximity)
- Regime shares: % of days led by each venue within each regime
- Tie rule: equal fractional credit across tied venues on a given day
- Ranking table: [{venue, wins, pct}] per regime

## 4. Statistics (econometrics)
- Chi-square (venue×regime) → χ², dof, p; Cramér's V
- Bootstrap CI (leader share per regime): mean, 95% CI
- Leader gap behavior by regime: median gap (bps), 95% CI
- (Optional) KS test across regimes for gap distribution

## 5. Logs (console tags)
- [ENV:volatility:config|terciles|assignments]
- [LEADER:env:volatility:summary|table|ties|dropped]
- [STATS:env:volatility:chi2|bootstrap|gap]
- (Funding) [ENV:funding:*], [LEADER:env:funding:*], [STATS:env:funding:*]
- (Liquidity) [ENV:liquidity:*], [LEADER:env:liquidity:*], [STATS:env:liquidity:*]

## 6. Exports (files)
- vol_terciles_summary.json
- leadership_by_regime.json
- leadership_by_day.csv        # dayKey, regime, leader, leaderGapBps, prices...
- funding_terciles_summary.json
- leadership_by_funding.json
- leadership_by_day_funding.csv
- liquidity_terciles_summary.json
- leadership_by_liquidity.json
- leadership_by_day_liquidity.csv

## 7. Manifest (per run)
- MANIFEST.json:
  { commit, sampleWindow:{start,end}, tz:"UTC", seeds:[], specVersion, codeVersion }
