# Algorithmic Coordination Diagnostic (ACD)

> Real-time diagnostic platform for distinguishing competitive vs coordinated conduct in financial markets.

The **Algorithmic Coordination Diagnostic (ACD)** is a compliance and risk tool designed for banks, regulators, and competition economists.  
It ingests **real-time CDS, bond, and FX market data**, runs **econometric tests (ICP, regime detection, flow analysis)**, and outputs **clear 0–100 risk scores** with legal-ready evidence packs.

---

## 🚀 Features
- **Real-time CDS monitoring** with sub-minute updates
- **Three-core indicators**: Price Stability, Synchronization, Environmental Sensitivity
- **Composite risk score** with Green/Amber/Red bands
- **Fallback data strategy**: integrates client feeds with independent market data (S&P, ICE, Refinitiv, JSE)
- **Court-ready evidence packs**: timestamped, source-tagged, and cryptographically signed
- **Mobile-first UI** for legal teams and compliance officers

---

## 📖 User Story — FNB CDS Market Example
FNB's legal team faces scrutiny over **CDS spread movements**.  
Using the ACD dashboard, they can:

1. Log into a **live monitor** that shows CDS spreads vs peers.  
2. See **"Coordination Risk: 14/100 (Low)"**, backed by **96.8% statistical confidence**.  
3. Check the **18-month time series chart**, proving independent movement vs competitors.  
4. Use the **Indicators tab** (Stability, Synchronization, Environmental Sensitivity) for deeper analysis.  
5. Export a **court-ready PDF evidence pack** with raw data, confidence scores, and source logs.

👉 See the [full user story](docs/user-story.md)

---

## 🖥️ UI Demo

Below is a simplified **live HTML prototype** of the dashboard.  

```html
<!-- Run in browser -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>ACD Monitor - FNB CDS</title>
<style>
  body { font-family: sans-serif; background:#f0f9ff; margin:0; }
  header { background:#fff; padding:1rem 2rem; border-bottom:1px solid #e2e8f0;
           display:flex; justify-content:space-between; align-items:center; }
  .live { background:#dcfce7; padding:4px 10px; border-radius:20px; color:#166534; font-weight:600 }
  .card { background:#fff; margin:2rem auto; max-width:900px; padding:2rem; border-radius:12px;
          border:1px solid #e2e8f0; box-shadow:0 2px 8px rgba(0,0,0,.06); text-align:center }
  .score { font-size:3rem; font-weight:700; color:#10b981 }
  .pill { display:inline-block; padding:6px 12px; border-radius:12px; background:#dcfce7; color:#166534; font-weight:600 }
  .chart { height:300px; background:#f8fafc; border:1px solid #e2e8f0; margin-top:1.5rem; display:flex; justify-content:center; align-items:center; color:#64748b }
</style>
</head>
<body>
<header>
  <div><strong>ACD Monitor</strong> — FNB CDS Market</div>
  <div class="live">● LIVE</div>
</header>
<div class="card">
  <div>Coordination Risk</div>
  <div class="score">14</div>
  <div class="pill">LOW RISK</div>
  <p>96.8% statistical confidence • 18-month view</p>
  <div class="chart">📈 Real-time CDS price chart (18m back → today)</div>
</div>
</body>
</html>
```

---

## 📂 Documentation
- [Full Technical Spec](docs/spec.md)
- [User Story: FNB CDS Market](docs/user-story.md)
- [UI Demo](docs/ui-demo.md)
- [Data Strategy & Independence](docs/data-strategy.md)
- [Legal & Compliance Framework](docs/legal-compliance.md)
- [Roadmap](docs/roadmap.md)

---

## ⚖️ License

MIT — open for research, compliance, and academic use.

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/acd-monitor.git
cd acd-monitor

# View the UI demo
open docs/ui-demo.html

# Read the full specification
open docs/spec.md
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and contribution process.

---

*Developed by RBB Economics in collaboration with financial sector partners.*
