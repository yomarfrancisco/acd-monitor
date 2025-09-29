# Environment Taxonomy (Detection vs Validation)

**Purpose**: Clarify that we use two distinct environment layers so we don't confuse surveillance signals with causal tests.

## Layer A — Detection Environments (Endogenous, market-driven)

**What**: Market structure & trader-anchored signals that may themselves be influenced by coordination:
- Market structure breaks (CHoCH/BOS, trend reversals)
- Volume profile pivots (POC/value areas, VWAP deviations)
- Order-flow zones (institutional "order blocks", depth/imbalance extremes)
- Liquidity/volatility patterns (ICT-style raids/"power of 3", spread tightening episodes)

**Why**: High-frequency episode discovery (surveillance). These carve out candidate windows for deeper investigation.

**How**: Implemented on tick/1s data from S3 snapshots; produces flagged windows + structured logs.

**Caveat**: Not ICP evidence. Endogenous by nature → useful for where to look, not proof.

## Layer B — Validation Environments (Exogenous, policy/structural)

**What**: External shocks not caused by venue behavior:
- Trading sessions (Asia/Europe/US/overlaps; UTC clock-time)
- Regulatory/policy events (SEC/FCA actions, ETF approvals, executive orders)
- Infrastructure shocks (exchange/API outages, fee changes, venue launches)
- Global liquidity regimes (exogenous monetary/credit proxies; rising/falling/stable)

**Why**: ICP/causal testing: do detected relationships persist across exogenous changes?

**How**: Apply ICP/invariance tests (chi-square, bootstrap CI, stability indices) to detector outputs/windows conditioned on these exogenous bins.

**Court stance**: Only results invariant across exogenous environments enter court-ready evidence bundles.

## Integration Principle — Surveillance ≠ Causation

1. **Detect**: Use Layer A to flag episodes/windows from tick data (endogenous signals).
2. **Validate**: Re-test those windows across Layer B bins (exogenous shocks).
3. **Promote**: Only promote to "coordination-consistent" if invariant across Layer B.

## Implementation Status

- **Layer A signals** are supported by current S3 snapshots (tick, depth, imbalance, spreads) and existing detector scaffolding.
- **Layer B bins** are partially implemented (sessions) and planned/underway (policy events, infra shocks, global liquidity index).
- **Evidence routing** unchanged: detection → candidate windows; validation → ICP tests → EVIDENCE.md bundles with MANIFEST provenance.

## Reviewer Alignment

- Addresses the exogeneity critique directly: we're not testing stability over variables that could be outcomes of coordination.
- Keeps trader-centric signals where they shine (surveillance), while reserving causal claims for true exogenous variation.
