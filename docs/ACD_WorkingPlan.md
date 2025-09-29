# Algorithmic Coordination Diagnostic (ACD) – Crypto Application Working Document

⸻

## 1. Problem

Crypto markets are global, fragmented, and highly automated. Exchanges (Binance, Coinbase, OKX, Kraken, Bybit) dominate order flow and price discovery.

Central Question:
👉 Do we see evidence of algorithmic coordination (collusion) in these markets, or are price dynamics consistent with competitive adaptation?

Courts, regulators, and economists need court-ready evidence: outputs that are reproducible, robust, and interpretable. The challenge is to move beyond anecdotes ("Binance leads") toward systematic invariance tests of leadership and coordination across environments.

⸻

## 2. Solution

We apply the ACD framework (causal inference + invariance testing) to live tick-level BTC-USD data from multiple venues.

Hypotheses:
- If venues are competing → leadership shifts across environments (volatility, funding, liquidity, regulation).
- If venues are colluding → leadership remains invariant across environments, despite shocks.

The ACD produces outputs that can be interpreted both:
- Econometrically (lead-lag, information leadership, consensus proximity).
- Legally (evidence of coordination consistent with collusion).

⸻

## 3. What's Required
- Data Access: Continuous tick-level snapshots across 5+ exchanges (✅ implemented).
- Event Definition (E): Define environments (volatility terciles, funding shifts, liquidity regimes, policy events).
- Leadership Metrics: Consensus proximity, lead-lag tests, robustness checks.
- Invariance Tests: Leadership stability across E.
- Logging & Interpretation: Structured logs + LLM summarization to translate econometrics → plain English.

⸻

## 4. Current Position
- ✅ Continuous 30-minute tick-level snapshots (50% overlap) stored in S3.
- ✅ Coverage ≥95% per venue, ≥3 venues per window (enforced).
- ✅ Enriched schema: spreads, depth, imbalance, volatility, momentum, trades, fees, provenance.
- ✅ Automated GitHub Actions for continuous capture and nightly sweeps.
- ✅ Verification tools (coverage reports, clock skew, snapshot integrity).

This enables invariance testing with court-ready outputs.

⸻

## 5. Data Sufficiency Note

Position (Sept 2025)
- Now: We capture tick-level top-of-book + trades across 5 venues with full coverage monitoring.
- Implication:
- Sufficient for first-pass invariance analysis (volatility, funding, liquidity environments).
- Stronger than OHLCV: intraday stress, spreads, depth, and imbalance can all be tested.
- Still pending: policy/regulatory events and harm module sequencing.

Audience-Specific
- Economists / Regulators / Courts
- Care about: who leads, under what environments, whether leadership is competitive or collusive.
- Tick-level data + structured invariance outputs = sufficient to make case.
- Exchanges (Binance, Coinbase, etc.)
- Already run microstructure surveillance.
- Expect tick-level rigor: spreads, cross-venue lags, slippage, adverse selection.
- Our capture pipeline is now aligned with these standards.

Sufficiency Gaps
- Still missing: policy event overlays and harm quantification (venue revenue + trader cost uplift).
- Next: Connect LLM interpretation layer for regulator-ready phrasing.

⸻

## 6. Next Steps (High-Level Plan)
1. Implement policy/regulatory events: ETF approvals, lawsuits, exchange outages, rulings.
2. Anchor leadership metrics with consensus proximity + full ranking.
3. Run invariance tests across environments (volatility, funding, liquidity, policy).
4. Add harm module (post-ICP/VMM) using fee revenue + execution cost uplift.
5. Add interpretation layer: LLM generates court-ready phrasing from JSON/CSV results.

⸻

## 7. Environments (E)

Definition: Conditions under which price competition plays out.

Good environments:
- Exogenous, economically meaningful, enough sample size.

Bad environments:
- Endogenous (caused by the variable we measure), too short/noisy, or non-economic.

Crypto timescales:
- Volatility/funding: daily.
- Liquidity: intraday/daily.
- Policy/regulatory: 1–3 day windows.

⸻

## 8. Initial Environment Definitions for BTC-USD
- Volatility regimes: σ terciles (low / mid / high volatility).
- Funding regimes: Positive vs negative, with shock flags (Δ > p90).
- Liquidity regimes: Tight vs thin spreads, volume- and depth-adjusted.
- Policy/regulatory events: ETF approvals, lawsuits, outages, rulings.

These form the first battery of environments. Collusion should not be invariant across all.

⸻

## 9. Why These Are Good
- Volatility: Natural stress vs calm → exogenous to leadership.
- Funding: Captures sentiment/order-flow shifts.
- Liquidity: Thin books easier to manipulate.
- Policy: Shocks test information incorporation speed.

⸻

## 10. Working Plan (Updated – Sept 2025)

Short-Term (Q4 2025)
- Integrate policy/regulatory event library.
- Add interpretation layer for regulator-facing outputs.

Medium-Term (2026)
- Extend to order book depth + slippage validation.
- Deliver regulator-facing briefs with court-ready invariance evidence.

⸻

## 11. Implementation Status

✅ Completed

1. Volatility Regimes
- Module: src/acd/analytics/volatility_regimes.py
- Script: scripts/run_volatility_regime_analysis.py
- Features:
- 20d rolling σ from OHLCV
- Tercile partitioning (low/med/high)
- Daily regime labeling
- Leadership distribution analysis by regime
- Structured logging + JSON/CSV exports

2. Funding Regimes
- Module: src/acd/analytics/funding_regimes.py
- Script: scripts/run_funding_regime_analysis.py
- Features:
- 8h funding rates → daily mean
- Positive vs negative partitions
- Funding shock flags (|Δ| > p90)
- Leadership analysis per regime
- Structured logging + JSON/CSV exports

3. Liquidity Regimes
- Module: src/acd/analytics/liquidity_regimes.py
- Script: scripts/run_liquidity_regime_analysis.py
- Features:
- Composite liquidity metric (volume, range/close, return/σ20)
- Tercile partitioning
- Consensus leadership with ≥3 venues
- Structured logging + JSON/CSV exports

4. Invariance Matrix
- Module: src/acd/analytics/invariance_matrix.py
- Script: scripts/run_invariance_matrix_analysis.py
- Features:
- Leadership invariance across 9 bins (3 env × 3 regimes)
- Stability Index (SI), Range, MinShare
- Chi-square + bootstrap tests
- Exports: invariance_matrix.csv, invariance_report.json, invariance_summary.md

Result: Venues show stability (SI ≈ 0.8–0.87). Leadership appears invariant across environments → possible coordination.

⸻

## 12. Pending
1. Policy / Regulatory Events
- Add exogenous shocks.
- Deliver structured logs + exports.
2. Interpretation Layer
- Translate results into court/economist phrasing.
- Example:
- Econometric: "Binance led 43% of days in high-vol vs 28% in low-vol regimes."
- Legal: "Leadership invariance across regimes is consistent with coordination."
3. Robustness Guardrails
- Tick-level order-book validation.
- Sample size ≥30 days per regime.
- Tie/outlier handling logged.

⸻

## 13. Key Takeaway

As of Sept 29, 2025, the ACD framework covers:
- Environments: volatility, funding, liquidity.
- Tests: invariance matrix with Stability Index.
- Infrastructure: live 30m tick-level capture, ≥95% coverage, 5 venues.

Next milestones: add policy/regulatory events and the interpretation layer, then scale to harm quantification (venue revenue + trader cost uplift).

⸻

End of document

⸻