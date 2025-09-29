# **Anchor Document: ACD – Coordination Risk Analytics (Crypto Case Study)**

## **1. Purpose**

We are building the **Algorithmic Coordination Diagnostic (ACD)** for the **crypto exchange industry**.
The tool's mission is **not to prove collusion**, but to **detect and quantify coordination risk patterns** in algorithmic pricing.

**Positioning**:

* *Economic*: Identify supra-competitive coordination signatures beyond normal oligopoly adaptation.
* *Regulatory*: Provide **supervisory monitoring and screening outputs** that flag risks but stop short of asserting illegality absent further evidence of agreement.

---

## **2. Current State**

* **UI**: Professional React/TypeScript dashboard with risk bands (LOW/AMBER/RED), CDS-style charts, and multi-tab navigation.
* **Infrastructure**: FastAPI backend, multi-tier data ingestion, evidence bundle system, health checks, agent chat interface.
* **Analytics engines**: ICP & VMM **architecturally present but placeholder-only**.
* **Risk classification**: Logic implemented but mismatched (MEDIUM/HIGH instead of AMBER/RED).
* **Domain adaptation**: Current UI is **banking-focused**; crypto-specific features not yet implemented (latency-arb, fee tiers, inventory shocks).

---

## **2.5 Agent Interface (Conversational Layer)**

The **ACD Agent** is not only a UI feature but the **primary access point** for everyday users (compliance officers, researchers, supervisors).

* **Functions:**

  * Access real-time data (exchanges, banks, on-chain sources).
  * Query ACD outputs in natural language (*"Did Binance lead Coinbase yesterday?"*).
  * Interpret econometric results into plain-English assessments with confidence levels.
  * Provide audit-ready reports on request.
* **Value:** Transforms the ACD from a *back-office model* into a **frontline compliance assistant**.

---

## **3. MVP Goal**

Deliver a **production-grade econometric engine** that achieves **Brief 55+ methodological parity** for **regulatory screening use**:

1. **ICP**: Environment partitioning + invariance testing with robust bootstrap CIs and power analysis.
2. **VMM**: Real moment condition evaluation + variational optimization.
3. **Algorithm classification**: Sector-specific profiles (crypto = multi-agent systems, HFT ensembles).
4. **Multi-layer validation**: Lead–lag, mirroring, spread-floor detection, HMM regimes.
5. **Retrospective validation**: ATP case in Phase 2; CMA Poster Frames in Phase 3.
6. **Regulatory-ready outputs**: Structured bundles with confidence intervals, regression tables, alternative explanations, and cryptographic audit trails.
7. **Conversational interface**: Agent-enabled natural language querying and interpretation of coordination risk insights.

---

## **4. Crypto-Specific Hypothesis**

**Hypothesis:**
*In fragmented crypto markets, a small set of exchanges (e.g., Binance, Coinbase) acting as price "verifiers" may enable supra-competitive coordination if:*

* Order books mirror each other in near real-time.
* Price-leadership patterns persist (one exchange leads, others follow).
* Spread floors emerge despite volatility and arbitrage pressures.
* Market-maker algorithms (Wintermute, Jump, etc.) reinforce the loop across venues.

**Counterfactuals to control for:**

* Arbitrage constraints (cross-venue latency).
* Fee-tier ladders and rebates (VIP traders).
* Inventory/liquidity shocks (maker inventory needs).
* Market events (depegs, outages, halts).

---

## **5. Reviewer's Perspective on Crypto as First Use Case**

A recent review of the ACD framework for crypto highlighted both **opportunities** and **challenges**:

### **Strengths**

* **Data availability**: Unprecedented transparency (real-time order books, on-chain data).
* **Algorithm prevalence**: Crypto dominated by arbitrage bots, MM algos, MEV extractors.
* **Environment sensitivity**: Rich test conditions (regulation, exploits, forks, macro shocks).

### **Opportunities**

* Cross-exchange coordination detection (Binance/Coinbase/Kraken).
* MEV bot coordination in Ethereum mempool.
* Stablecoin peg maintenance strategies.
* DeFi protocol coordination (fees/yields).

### **Challenges**

* Pseudonymity of actors.
* Cross-chain coordination complexity.
* Wash trading noise.
* MEV ordering and gas optimization that may mimic coordination.

### **MVP Recommendation**

* Start narrow with **BTC/USD and ETH/USD across top exchanges**.
* Use as **proof-of-concept** before expanding to stablecoins, DeFi, or traditional markets.

---

## **6. Implementation Plan (10 Weeks)**

### **Phase 1 (Weeks 1–4): Core Econometric Engines**

* [ ] Week 1: Generate **synthetic crypto datasets** (BTC/USD, ETH/USD).
* [ ] Week 2: Implement **ICP** with bootstrap CIs + power analysis (synthetic validation).
* [ ] Week 3: Implement **VMM** with crypto-specific moment conditions:

```python
crypto_moments = {
    "lead_lag_beta": "Cross-exchange price leadership patterns",
    "mirroring_ratio": "Order book similarity across venues", 
    "spread_floor_dwell": "Minimum spread persistence despite volatility",
    "undercut_initiation": "Price undercutting pattern analysis"
    # "mev_coordination": Optional; Phase 2 extension
}
```

* [ ] Week 4: Integrate ICP + VMM into pipeline, fix risk classification (LOW/AMBER/RED).
* [ ] Unit tests for competitive vs. coordinated outcomes.

**Checkpoint ✅:** ICP & VMM converge statistically with power ≥ 0.8 for Δ ≥ 0.2 in synthetic collusion cases.

---

### **Phase 2 (Weeks 5–7): Validation Framework**

* [ ] Add **multi-layer validation** (lead–lag causality, mirroring detection, HMM regimes).
* [ ] Implement **algorithm classification framework** (multi-agent, ensemble, arbitrage, MEV).
* [ ] Integrate **statistical confidence mapping** (≥95% investigation, 90–95% monitoring).
* [ ] Run **ATP retrospective case study** for early credibility.
* [ ] Introduce **alternative explanations checklist** (arbitrage, fees, inventory, volatility).
* [ ] Begin exploring **on-chain data feeds** for MEV/gas optimization patterns.
* [ ] Expose ICP/VMM/validation artifacts via a standardized retrieval API (JSON + persistence layer), so the ACD Agent can access, parse, and respond to queries with direct reference to underlying data.
* [ ] Implement **agent retrieval layer** connecting econometric outputs (ICP/VMM + validation layers) to natural language Q&A.
* [ ] Test with scripted compliance officer queries (e.g., "show mirroring ratios vs. arbitrage controls for ETH/USD last week").

**Checkpoint ✅:** One retrospective case (ATP) validated; crypto hypothesis tested with counterfactual controls; agent correctly interprets ≥90% of scripted compliance queries.

---

### **Phase 3 (Weeks 8–10): Regulatory Readiness**

* [ ] Extend retrospective validation (CMA Poster Frames).
* [ ] Generate **regulatory screening bundles** (JSON + PDF):

  * Executive summary
  * Methodology appendix (ICP/VMM specs)
  * Regression/confidence tables
  * Regime charts, network graphs
  * Alternative explanations
  * Audit trail + cryptographic signature
* [ ] Domain-specific agents: economist, statistician, legal.
* [ ] Final crypto adaptation: latency-arb constraints, VIP fee tiers, inventory shocks in simulator.
* [ ] Add **regulatory readiness standards**: pre-registration, sensitivity analysis, reproducibility, peer review.
* [ ] Agent generates **regulatory screening bundle drafts** interactively upon prompt.
* [ ] Users can converse with the agent to refine bundles (e.g., add charts, highlight counterfactuals).

**Checkpoint ✅:** End-to-end workflow produces regulatory-ready evidence bundle for crypto exchanges; agent generates regulator-ready screening bundles conversationally with ≤5 prompts.

---

## **7. Guardrails & Governance**

* **Language discipline**: Results = *"patterns consistent with coordination risk"*, never "collusion proven."
* **Statistical rigor**:

  * α = 0.05
  * Power ≥ 0.8 for Δ ≥ 0.2
  * FDR = 0.1 (BH procedure)
  * n ≥ 1000 samples per environment
* **Governance**: Pre-registration, cryptographic logs, sensitivity tables.
* **Default use case**: *Regulatory monitoring & market studies*. Escalation to litigation requires external evidence.

---

## **8. Technical Risks & False Positives**

* **MEV ordering constraints**: Within-block sequencing may mimic coordination.
* **Cross-DEX arbitrage**: Gas and latency optimization can look like mirroring.
* **Liquidity constraints**: Inventory management may generate spread floors.
* **Wash trading**: Must be filtered before inference.

Mitigation: All detected patterns require **alternative explanations checklist** review before escalation.

---

## **9. Success Metrics**

* **Phase 1:** ICP rejects H₀ (invariance) with p < 0.05; power ≥ 0.8 for Δ ≥ 0.2; VMM converges <10,000 iterations.
* **Phase 2:** ATP case study reproduces expected coordination pattern; crypto tests distinguish risk vs. controls; agent correctly interprets ≥90% of scripted compliance queries.
* **Phase 3:** Screening bundles meet regulator admissibility standards (structured, auditable, pre-registered); agent generates regulator-ready screening bundles conversationally with ≤5 prompts.

---

## **10. Data Requirements**

* **Order book (Level 2)**: From top 5 exchanges.
* **Trade data**: Executed trades with timestamps.
* **On-chain data**: MEV transactions, gas optimization patterns.
* **Market events**: Exchange outages, regulatory announcements.

---

## **11. Future Verticals (Placeholder)**

* **Travel & Hospitality:** Revenue management systems → medium-risk classification.
* **Adaptation path:** Add environment partitions (capacity, booking windows, seasonality) + retrospective validation.
* **Architecture impact:** None; modular classification supports easy addition.

---

# **Bottom Line**

We are building a **crypto-adapted, regulator-safe coordination risk diagnostic** with **conversation-enabled diagnostic assistance**.
The existing **UI + infra = solid foundation**. The missing piece = **econometric core + crypto adaptation + legal posture + agent interface**.
With Phases 1–3, we can move from **placeholder demo** → **regulatory-ready screening tool** in \~10 weeks, anchored by rigorous stats, crypto-specific realism, cautious framing, and **natural language accessibility**.

**Key Innovation**: The ACD Agent connects econometric rigor with real-time usability — allowing compliance teams and researchers to query, interpret, and act on coordination risk insights directly through conversational interaction.

---

## **Authoritative Reference Document**

**ACD Bundle v1.4 + Role-Sensitive Framework** (`ACD_Bundle_v1.4_RoleSensitive.md`)

This document serves as the **single authoritative reference** for the ACD project, combining:
- **v1.4 Baseline Standard**: Complete technical surveillance report with similarity metrics, adaptive baseline, and statistical framework
- **Role-Sensitive Reporting Framework**: Adaptations for Head of Surveillance (technical), CCO (compliance), and Executives (strategic)
- **Flow Between Roles**: Handoff protocols and escalation procedures
- **Example Skeleton Reports**: Illustrative outputs for each user role
- **Guardrails & Governance**: Consistency requirements and scope management

**All future ACD development must reference this bundle document to maintain consistency and avoid scope drift.**

---

## **Strategic Buyer Roadmap**

The ACD product development follows a strategic progression aligned with actual buyer journeys, ensuring that each phase builds credibility and purchasing power with the appropriate decision-makers.

### **Phase 1: Professional Influencer (Head of Surveillance / Equivalent)**

* **Objective**: Establish full professional credibility with the domain expert who evaluates rigor.
* **Completion Milestone**:

  * Econometric core fully implemented (ICP + VMM + validation layers).
  * Reporting templates standardized to v1.4 baseline.
  * Optional agent prompts available to adjust reporting depth dynamically.
* **Positioning**: At this stage, the ACD delivers reports that any Head of Surveillance at a Tier-1 exchange would trust, use, and circulate internally.

---

### **Phase 2: Compliance Authority (Chief Compliance Officer / CCO)**

* **Objective**: Adapt reporting and agent interaction to the true budget-holder with liability exposure.
* **Key Refinements**:

  * Default outputs framed as compliance automation (regulatory bundle templates, standardized language).
  * Agent prompts tuned to highlight regulatory defensibility and audit-ready trails.
* **Outcome**: Converts professional credibility into **purchasing power alignment**, ensuring ROI for compliance.

---

### **Phase 3: Executive Oversight (CEO / COO / Board)**

* **Objective**: Elevate outputs to senior decision-makers.
* **Key Refinements**:

  * High-level dashboards with risk trend metrics, reputational risk framing, and competitive benchmarks.
  * Business impact summaries (costs, efficiency, peer positioning).
* **Outcome**: Secure top-down support, anchoring ACD as must-have compliance infrastructure rather than "nice-to-have" analytics.

---

### **Principle of Progression**

The ACD product roadmap begins by **fully satisfying the professional in the room** (the influencer), then iterates outward toward compliance decision-makers and executives.
The **conversational layer** (agent prompts) is the bridge: it allows the same system to flex between technical rigor, compliance defensibility, and executive clarity, depending on who is asking.

---