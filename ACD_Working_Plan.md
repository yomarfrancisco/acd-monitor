# Algorithmic Coordination Diagnostic (ACD) – Crypto Application Working Document

⸻

## 1. Problem

Crypto markets are global, fragmented, and highly automated. Exchanges (Binance, Coinbase, OKX, Kraken, Bybit) dominate order flow and price discovery.
The central question:
👉 Do we see evidence of algorithmic coordination (collusion) in these markets, or are price dynamics consistent with competitive adaptation?

Courts, regulators, and economists need court-ready evidence: outputs that are reproducible, robust, and interpretable. The challenge is to move beyond anecdotes ("Binance leads") toward systematic invariance tests of leadership and coordination across environments.

⸻

## 2. Solution

We apply the ACD framework (causal inference + invariance testing) to live BTC-USD price data from multiple venues. The hypothesis is:
- If venues are competing → leadership shifts across environments (volatility, funding, liquidity, regulation).
- If venues are colluding → leadership remains invariant across environments, despite shocks.

The ACD produces outputs that can be interpreted both econometrically (lead-lag, information leadership, consensus proximity) and legally (evidence of coordination consistent with collusion).

⸻

## 3. What's Required
- Data Access: Live OHLCV across 5+ exchanges (done).
- Event Definition (E): Define regimes (volatility terciles, funding shifts, liquidity regimes, policy events).
- Leadership Metrics: Lead-lag tests, consensus proximity, robustness checks.
- Invariance Tests: Leadership stability across E.
- Logging & Interpretation: Court-ready logs, with LLM summarization to translate econometrics → plain English.

⸻

## 4. What's Missing
- Proper environment definitions (E) beyond raw OHLCV.
- A consistent leadership definition (economically sound, not just "highest price").
- Initial invariance testing to show leadership stability/instability.
- Event libraries (funding, liquidity, policy) integrated into pipeline.
- Guardrails for robustness (sample size, tie-breaking, outlier detection).

⸻

## 5. Data Sufficiency Note

### Current Position (First Pass)
- We are pulling OHLCV data (candlesticks) across 5 major venues in real time.
- This is sufficient for high-level invariance tests:
  - Leadership ranking by consensus proximity.
  - Volatility tercile regimes (20-day σ buckets).
  - Liquidity/funding/policy event overlays.
- This lets us answer: Does leadership persist across environments? — enough to establish a broad economic narrative for economists and regulators.

### Audience-Specific Sufficiency
- **Economists / Regulators / Courts:**
  - Care about simplified outputs: who leads, under what environments, and whether that leadership is explainable as competition or suspect as coordination.
  - OHLCV-based regime analysis is adequate for first-pass models, because the legal/economic framing benefits from simplification.
- **Exchanges (Binance, Coinbase, Kraken, etc.):**
  - Already run microstructure surveillance at the tick and order-book level.
  - Will not find OHLCV sufficient for serious coordination detection.
  - Expect analytics that incorporate:
    - Tick-by-tick trade and quote data
    - Cross-venue spread tightening and slippage analysis
    - Lead-lag measured in seconds, not days
    - Market impact and adverse selection patterns

### Sufficiency Gaps
- OHLCV = Good First Pass, but not enough to scale credibility with exchanges or to withstand deep industry scrutiny.
- Court-Ready Proof requires both:
  1. Simplified outputs for legal clarity (invariance tests).
  2. Underlying microstructure evidence that the outputs are derived from (tick-level validation).

### Next Step Implications
- **Short-term (first pass)**: Use OHLCV for volatility, liquidity, and policy environments. Build leadership invariance metrics.
- **Medium-term (scaling to exchanges)**: Add tick-level, order book, and spread-based data. This is the only way to build credibility with exchange surveillance teams and make the system scale.

⸻

## 6. Next Steps (High-Level Plan)
1. Implement Environments (E):
   - Volatility terciles (σ 20d).
   - Funding rate regimes (positive vs negative).
   - Liquidity regimes (tight vs thin spreads).
   - Policy/regulatory event windows (±1 day).
2. Anchor Leadership Metric:
   - Consensus proximity (already working).
   - Add ranking across venues (1st → 5th).
   - Log leadership per environment.
3. Run Invariance Tests:
   - Compare leadership distributions across E.
   - Detect if one venue leads across all regimes.
4. Interpretation Layer:
   - LLM outputs: "Binance led 43% of days in high-vol vs 28% in low-vol"
   - Court-ready phrasing: "This pattern is consistent/inconsistent with collusion."

⸻

## 7. Step 1: What Are Environments?
- Definition: Conditions under which price competition plays out.
- Good environments: Exogenous, economically meaningful, enough sample size.
- Bad environments: Endogenous (caused by the variable we're measuring), too short/noisy, or non-economic.
- Discrete vs continuous:
  - Discrete: event windows (ETF approval).
  - Continuous: volatility terciles.
- Crypto timescales:
  - Volatility/funding: daily.
  - Liquidity: intraday/daily.
  - Policy/regulatory: 1–3 day windows.

⸻

## 8. Initial Environment Definitions for BTC-USD
- Volatility regimes (σ terciles): High / Mid / Low vol.
- Funding rate regimes: Positive vs negative.
- Liquidity regimes: Tight vs thin spreads.
- Policy/regulatory events: ETF approvals, lawsuits, regulatory go-lives.

These form the first battery of environments. Each adds robustness because collusion should not be invariant to all.

⸻

## 9. Why These Are Good
- Volatility: Natural stress vs calm → exogenous to leadership.
- Funding: Captures sentiment shifts → different order-flow incentives.
- Liquidity: Thinner books are easier to coordinate/manipulate.
- Policy: Exogenous shocks test information incorporation speed.

⸻

## 10. Working Plan

This is a living document. Each section will expand into:
- Exact econometric tests (equations, methods).
- Event libraries (funding data feeds, regulatory event dates).
- Results + logs.

Theo's immediate anchor tasks:
1. Build volatility terciles from live OHLCV.
2. Add placeholders for funding/liquidity/policy events.
3. Log leadership distribution per regime (ranking 1st → 5th).
4. Verify invariance across environments.

⸻

End of document.

⸻
