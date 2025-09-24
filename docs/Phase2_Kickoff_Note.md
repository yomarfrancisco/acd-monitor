# **Phase-2 Kickoff Note – ACD Continuation**

## **1. Context**

Phase-1 successfully delivered a working econometric core:

* **ICP**: invariance test operational on synthetic data.
* **VMM**: hardened, stabilized, provenance-tracked, reproducible, and differentiating competitive vs coordinated scenarios.
* **Composite weights restored**: ICP 0.4, VMM 0.4, Crypto 0.2.

This gives us a **production-grade mathematical engine**. Regulators can now see a proof-of-concept that tells "no coordination risk" apart from "coordination risk."

---

## **2. Phase-2 Objectives**

Phase-2 is about **moving from math engine → diagnostic framework**:

1. **Validation Layers (multi-lens detection)**

   * Lead–lag causality (who moves first, who follows).
   * Mirroring detection (depth-weighted order book similarity).
   * HMM regimes (detect stable spread-floor states vs volatility states).
   * Information flow (transfer entropy / directed correlation).

   ✅ Output: Risk pattern attribution across multiple dimensions.

2. **ATP Retrospective Case**

   * Reconstruct data from airline price-leadership case.
   * Run the ACD through it.
   * Show the tool reproduces known coordination patterns.

   ✅ Output: Credibility anchor ("this matches what regulators already know").

3. **Agent Integration**

   * Expose ACD results to the **agent interface**.
   * Compliance officers and researchers can query:

     * "Which exchange led BTC moves yesterday?"
     * "Show me mirroring ratios across Binance & Coinbase last week."
     * "Generate a monitoring bundle for ETH/USD."
   * The agent must **read artifacts, interpret them, and respond conversationally**.

   ✅ Output: Everyday usability — a **compliance co-pilot**, not just a batch econometrics script.

---

## **3. Deliverables**

* `src/acd/validation/lead_lag.py`, `mirroring.py`, `hmm.py`, `infoflow.py` (+ unit tests).
* `cases/atp/` pipeline with golden-file tests.
* `src/acd/analytics/report_v2.py`: risk attribution tables, layer-by-layer.
* `scripts/run_synthetic_phase2.py`: full one-button reproducible pipeline.
* **Agent adapter**: endpoint/API or local reader so the agent can answer prompts about results.

---

## **4. Acceptance Criteria**

1. **Validation layers**: Coordinated scenarios show higher persistence, lower entropy, higher mirroring, stable HMM states. Competitive scenarios do not.
2. **ATP case study**: Matches documented coordination signatures in historical data.
3. **Agent integration**:

   * Agent can access VMM/ICP/validation artifacts.
   * Agent can answer queries in natural language with references to the data.
   * Example: *"Show me coordination risk between Binance and Coinbase on BTC last week"* → returns structured response with p-values, risk bands, and layer attribution.

---

## **5. Timeline (4 Weeks)**

* **Week 1–2**: Implement + unit-test validation layers.
* **Week 3**: ATP retrospective pipeline.
* **Week 4**: Agent integration + reporting v2.

---

**Bottom Line:**
Phase-1 = **engine proves the math**.
Phase-2 = **framework proves the use-case** — multi-lens detection, case validation, and a conversational agent interface that makes this tool usable daily by compliance officers and regulators.

---



