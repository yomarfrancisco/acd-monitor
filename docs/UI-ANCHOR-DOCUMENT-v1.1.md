# UI Anchor Document v1.1
## ACD Monitor – Financial Compliance Dashboard

**Date:** September 2025  
**Status:** Frontend Implementation Complete (UI ~85% aligned with Brief 55+)  
**Next Phase:** Backend Integration  

---

## 1. Purpose of This Anchor
This document anchors the current UI implementation as a fixed reference point for the ACD Monitor project. It ensures all stakeholders are aligned on **what the UI does today**, how it maps to **Brief 55+ methodology**, and what backend dependencies must be delivered to close remaining gaps.

---

## 2. Site Map & Core Questions

### **Agents Tab (Default Landing)**
**Core Question:** *"How do I interact with AI economists to get analysis and insights?"*  
- **Jobs-to-be-Done:**
  - Chat with AI economists (Jnr Economist, Statistician, etc.)
  - Log market events via conversation
  - Generate compliance reports
  - Assess statistical confidence
  - Upload external data for analysis
- **Key Features:**
  - Chat interface with agent selector
  - Data upload (CSV/JSON/Parquet)
  - Pre-populated conversation starters
  - Event logging integration

---

### **Dashboard → Overview Page**
**Core Question:** *"Are these companies colluding? What's my current risk level?"*  
- **Jobs-to-be-Done:**
  - Monitor algorithmic cartel risk in real-time
  - View price leadership dynamics (FANS – avatar flow)
  - Track significant market events on price charts
  - Assess risk scores & compliance confidence
- **Key Features:**
  - Live risk score (14/100, pulsing "LIVE" indicator)
  - Interactive CDS spread charts with event markers
  - Dynamic avatar flow showing price leadership
  - Timeframe selection (30d, 6m, 1y, YTD)
  - Event visualization with background bands

---

### **Dashboard → Health Checks Page**
**Core Question:** *"Is my monitoring system working properly and reliably?"*  
- **Jobs-to-be-Done:**
  - Track convergence rate, data integrity, evidence chain, runtime stability
  - Assess compliance readiness
  - Validate information flow & regime detection accuracy
- **Key Features:**
  - System integrity score (84/100)
  - Compliance readiness (67%)
  - Multi-line performance charts (clay/pastel scheme)
  - Validation metrics dashboard
  - Data source indicators

---

### **Dashboard → Events Log Page**
**Core Question:** *"What significant market events happened and how did they impact pricing?"*  
- **Jobs-to-be-Done:**
  - Review system- and user-generated events
  - Export event data for evidence
  - Assess event impact on pricing
- **Key Features:**
  - Event timeline with risk indicators
  - Market events (ZAR depreciation, SARB guidance)
  - Coordination & regime switch detections
  - "Log Event" button (sends to Agents tab)
  - Download/export capabilities

---

### **Dashboard → Data Sources Page**
**Core Question:** *"Is my data connected, secure, and properly integrated?"*  
- **Jobs-to-be-Done:**
  - Connect files, APIs, databases, cloud storage
  - Manage API keys & security
  - Monitor feed status
- **Key Features:**
  - File upload, REST/GraphQL APIs, PostgreSQL/MongoDB
  - Cloud (S3, Azure Blob)
  - API key management
  - Connection status indicators

---

### **Dashboard → AI Agents Page**
**Core Question:** *"What analysis can I get from AI economists and how do I access it?"*  
- **Jobs-to-be-Done:**
  - Request quick analyses (pricing, compliance, statistical confidence)
  - Generate reports & evidence packages
  - Log market events through agents
- **Key Features:**
  - Quick analysis buttons
  - Evidence package generator
  - Specialized agent types (Lawyer, Economist, Data Scientist)

---

### **Dashboard → Configuration Page**
**Core Question:** *"How do I configure my monitoring system?"*  
- **Jobs-to-be-Done:**
  - Adjust analysis settings (price thresholds, sensitivity)
  - Configure monitoring frequency
  - Manage alerts & notifications
- **Key Features:**
  - Price analysis & monitoring configuration
  - Auto-detect market changes
  - Data quality controls

---

## 3. UI Enhancements Delivered
- Dynamic Avatar Flow (FANS – price leadership)  
- Event Visualization (colored bands on charts)  
- Live Risk Indicators (pulsing dot, "LIVE" tag)  
- Improved Event Logging (button integrated with Agents tab)  
- Expanded Quick Analysis Tools  
- Validation Metrics (system confidence & integrity checks)  
- Unified Tile Styling (consistent dark theme)  
- Data Source Indicators  

---

## 4. Alignment with Brief 55+ and Anchors
- **ICP / VMM Pillars:** Represented through price stability, synchronization, and environmental sensitivity metrics.  
- **Evidence & Compliance:** Events log and health checks prepare audit trails.  
- **Enterprise Client Focus:** Clear, intuitive UX for compliance teams.  
- **Delegation to LLM Agents:** Deep econometrics (significance testing, cross-environment analysis, testimony prep) are offloaded to AI agents.  

**Alignment Score:** ~85%  
Remaining 15% requires backend (real data feeds, evidence export, live confidence updates).  

---

## 5. Backend Dependencies
- Evidence export (PDF with cryptographic timestamps)  
- Data source transparency (Tier indicators, schema validation)  
- Statistical confidence display (confidence intervals, %s)  
- Audit trail visibility (source switches, logs)  
- Real-time data feeds (WebSocket integration)  

---

## 6. Conclusion
The UI is **enterprise-ready and decision-focused**. It avoids overload by delegating heavy analysis to AI agents while providing compliance teams with clear, actionable monitoring tools.  

With backend integration (data feeds, evidence export, audit trail), the dashboard will fully align with Brief 55+ and Mission Control.  

---
