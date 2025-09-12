# Mission Control — ACD Platform (Brief 55+ Continuation)

**Owner:** Theo (Senior Econometrician, RBB Economics)  
**Version:** 1.1  
**Date:** January 2025  
**Classification:** Internal Build Plan  

---

## 1. Mission Context

Theo has full mandate to operationalize Brief 55+ into the ACD Platform. No need to pitch; the partners are aligned. Priority is speed and quality: build a robust, regulator-ready tool without compromise on methodological integrity.

The platform extends Brief 55+'s dual pillars:
- **Pillar 1:** Environment partitioning + invariance testing (ICP).
- **Pillar 2:** Continuous monitoring & dynamic validation (VMM).

The mission is to translate these into operational code, acceptance gates, and a working monitoring platform.

---

## 2. Strategic Priorities

1. **Anchor Everything to Brief 55+**
   - ICP for environment testing.
   - VMM as continuous monitoring engine.
   - Avoid dilution with unaligned methods unless used as secondary validation.

2. **Robustness First**
   - Determinism contracts, reproducibility packs, CI-enforced acceptance gates.
   - Every output defensible in court/regulator context.

3. **Speed without Drift**
   - Deliver incrementally (monthly milestones).
   - Avoid speculative features (e.g. order book, trader-level attribution).

4. **Empirical Rigor**
   - All thresholds, weights, and acceptance gates justified with empirical backtests or literature references.

---

## 3. Current Build Targets (v1.8 → v1.9)

### a) Immediate Development (v1.8 hardening)
- ✅ Core ICP implementation (Chow/Wald tests).
- ✅ VMM engine (moment conditions + variational updates).
- ✅ Network and synchrony modules.
- ✅ Composite risk scoring (weighted).
- ✅ Acceptance criteria (acceptance/criteria.yaml).
- ✅ Schema contracts (schemas/*.json).
- ✅ Evidence bundle & reproducibility framework.

### b) Next Increment (v1.9)
- Front-end Enhancements: Dashboard v2 (risk dial, trend lines, event tagging).
- Scaling Tests: Stress tests with 20+ participants, 24-month datasets.
- Data Quality Engine: Full cross-source validation and discrepancy handling.
- Empirical Library: Golden datasets (competitive & coordinated cases) as unit test suite.
- CI Integration: Automated regression tests for AUROC, FPR, reproducibility drift.

---

## 4. Technical North Stars

- **VMM Acceptance Gates:**
  - Spurious regime ≤ 5% on competitive dataset.
  - Drift reproducibility |Δstructural_stability| ≤ 0.03.

- **ICP Invariance:**
  - Stable relationships identified at 95% confidence.

- **Composite Risk Score:**
  - Bayesian-optimized weights with quarterly re-fit.
  - Default: [0.35 INV, 0.25 NET, 0.25 REG, 0.15 SYNC].

- **Evidence Reproducibility:**
  - ±0.5 risk score reproducibility tolerance.
  - P-values stable to ±0.01.

- **Data Independence:**
  - Tiered feeds with automatic failover and hysteresis.
  - Cross-source discrepancy clamped to market-specific bps ranges.

---

## 5. Development Phases

**Phase 1 — Core Hardening (Jan–Mar 2025)**
- Lock down ICP + VMM implementations.
- Validate against golden datasets.
- Finalize acceptance gates in CI.
- Build out schema library.

**Phase 2 — Market Validation (Apr–Jun 2025)**
- Deploy pilot with financial institution (FNB).
- Build compliance dashboard (v2).
- Benchmark live data performance.
- Expand acceptance tests to cover stress events (e.g. SARB MPC shocks).

**Phase 3 — Enterprise Grade (Jul–Dec 2025)**
- Scale infra to 50+ participants.
- Optimize latency (<5s p95 standard query).
- Harden evidence pipeline for production (SOC2-ready).
- Publish methodology note + tool demo internally & externally.

---

## 6. Immediate Tasks (Theo's Queue)

1. **Golden Dataset Library**
   - Synthetic (competitive vs coordinated).
   - Public SA bank CDS sample.
   - Scripts + metadata in datasets/golden/.

2. **VMM Monitoring Package**
   - Finalize moment condition implementation.
   - Add acceptance gates in CI.
   - Document equations + code alignment in docs/vmm.md.

3. **Risk Scoring Validation**
   - Run backtests with AUROC/F1 benchmarks.
   - Store artifacts under calibration/{market}/{yyyymm}/.

4. **Evidence Bundle Exporter**
   - Ensure schema validation 100% pass.
   - RFC3161 timestamps implemented in Python module.
   - Add replay.py to regenerate exports.

---

## 7. Governance & Quality

- **Mission Control Principle:** No feature merged without acceptance test pass.
- **Specs & Docs:** All refinements added to spec/ and docs/.
- **CI/CD Enforcement:** GitHub Actions enforce acceptance gates, regression drift, schema validation.
- **Reproducibility Pack:** Every evidence export must regenerate risk scores within tolerance.

---

## 8. Partner Alignment (Already Secured)

- Partners have approved scope + resources.
- No need for business case reiteration.
- Deliverables are technical and methodological only.
- RBB positioning as thought leader & innovator follows naturally from execution.

---

## 9. Closing Note for Theo

Theo, you're not building "just a product," you're operationalizing Brief 55+ into RBB's first proprietary monitoring platform. Your task is to keep fidelity to the methodology while making it run at scale — fast, rigorous, and court-defensible.

Every design choice should answer:
- Does it align with Brief 55+?
- Is it reproducible and regulator-ready?
- Can it run in production without collapse?

Ship v1.9 with these priorities locked.

---

## 10. Deployment Protocols (Anchor for Theo)

### 10.1 Source of Truth
- All deploys must flow through GitHub → Vercel integration.
- Repo: yomarfrancisco/acd-monitor.
- Production branch: main.
- Root directory: ui/cursor-dashboard.
- CLI deploys are strictly prohibited.

### 10.2 Workflow
1. Create branch for changes.
2. Commit + push to GitHub.
3. Open PR → main.
4. Vercel auto-builds preview from GitHub PR.
5. Verify preview scope (only intended changes).
6. Merge PR → auto production deploy.

### 10.3 Guardrails
- ❌ Do not use vercel deploy from CLI.
- ❌ Do not re-link project to cursor-dashboard.
- ✅ Always verify .vercel/project.json points to acd-monitor with root ui/cursor-dashboard.

### 10.4 Verification Checklist

Theo must confirm on each deploy:
- ✅ PR link + commit hash.
- ✅ Preview URL (GitHub-sourced).
- ✅ Scope confirmation (only intended changes).
- ✅ Production URL after merge.
