# Algorithmic Coordination Diagnostic (ACD) Product Specification
## Version 1.8 - Brief 55+ Aligned & RBB-Native Edition

**Date:** January 2025  
**Owner:** RBB Economics  
**Classification:** Public Product Specification  

---

## Executive Summary

The Algorithmic Coordination Diagnostic (ACD) is a continuous monitoring platform that distinguishes legitimate algorithmic competition from anticompetitive coordination using empirically grounded econometric methods. Built on the methodological foundation of RBB Brief 55+, the ACD applies Invariant Causal Prediction (ICP) and Variational Method of Moments (VMM) to detect structural stability in pricing relationships across changing market environments.

**Core Value Proposition:** Continuous compliance monitoring for algorithm-intensive firms, providing defensible evidence of competitive behavior while enabling early detection of coordination risks.

---

## 1. Product Overview

### 1.1 Problem Statement
Enforcement agencies face an acute challenge in distinguishing legitimate algorithmic competition from anticompetitive coordination. Current approaches rely on theoretical speculation without systematic methodology, creating regulatory uncertainty that chills innovation while potentially missing genuine coordination.

### 1.2 Solution
The ACD provides objective, empirically grounded tools for this distinction by testing whether pricing relationships remain invariant across market environments — a key signature of coordination — or adapt dynamically as competitive conditions change.

### 1.3 Target Markets (Reordered by Revenue Potential)

**Primary Market: Financial Institutions & Defendants**
- **Problem:** Continuous threat of algorithmic pricing investigations and litigation
- **Solution:** Continuous monitoring and compliance auditing to prevent coordination allegations
- **Value:** Proactive risk management and defensible evidence generation for defense
- **Revenue Model:** Enterprise subscriptions — predictable ARR anchored on compliance-as-a-service
- **Example:** Google, Meta, major banks, and airlines paying $500K–$2M/year

**Secondary Market: Legal & Compliance Teams**
- **Problem:** Need defensible evidence and expert testimony for ongoing cases
- **Solution:** Quantified coordination risk assessments with documented methodology and confidence intervals
- **Value:** Strengthened defense arguments and expert economic testimony
- **Revenue Model:** Case-based consulting + recurring compliance retainers

**Tertiary Market: Competition Authorities**
- **Problem:** Limited capacity for algorithmic coordination detection
- **Solution:** Automated detection using validated econometric methods (ICP + VMM)
- **Value:** Evidence quality designed for regulatory and judicial proceedings
- **Revenue Model:** Pilot programs + licensing fees (valuable but not the primary driver)

---

## 2. Core Analytics Engine

### 2.1 Dual Pillar Methodology

**Pillar 1: Invariant Causal Prediction (ICP)**
- Tests whether price relationships between competitors remain structurally stable across different market environments
- Provides formal statistical tests for "invariance" (suggesting coordination) vs. "environment-sensitivity" (consistent with competition)
- Handles multiple environmental dimensions simultaneously (cost shocks, demand shifts, competitive entry, regulatory changes)

**Pillar 2: Variational Method of Moments (VMM)**
- Continuous monitoring engine adapted from financial risk management
- Detects structural deterioration in pricing relationships in real-time
- Eliminates need for ex-ante environment specification
- Provides dynamic confidence scoring with evolving intervals

### 2.2 Multi-Layer Validation

**Information Flow Analysis**
- Identifies consistent price leadership patterns across environments
- Distinguishes systematic leadership (coordination focal points) from dynamic competitive responses

**Network Analysis**
- Maps pricing influence propagation through competitive networks
- Assesses structural stability required for genuine coordination

**Regime-Switching Detection**
- Identifies distinct periods of pricing behavior
- Correlates high-correlation periods with specific events (algorithm adoption, market changes)

**Statistical Confidence Mapping**
- 95%+ confidence: Investigation warranted
- 90-95% confidence: Monitoring recommended
- <90% confidence: Competitive behavior indicated

---

## 3. Technical Architecture

### 3.1 Backend Framework
- **Language:** Python 3.11+
- **Framework:** FastAPI (async, OpenAPI 3.1.0)
- **Database:** PostgreSQL 15+ (partitioned tables for time-series)
- **Caching:** Redis (real-time processing, session management)
- **Queue:** Celery + Redis (background analytics, batch processing)

### 3.2 Core Libraries
- **Econometrics:** Custom ICP implementation, VMM adaptation
- **Data Processing:** Pandas, NumPy, SciPy
- **Machine Learning:** Scikit-learn, PyTorch (for advanced VMM)
- **Time Series:** Statsmodels, Prophet
- **Network Analysis:** NetworkX, igraph

### 3.3 Data Pipeline
- **Ingestion:** API-first (REST, GraphQL, WebSockets)
- **Storage:** Time-series optimized PostgreSQL with partitioning
- **Processing:** Real-time streaming + batch analytics
- **Caching:** Multi-tier Redis (L1: hot data, L2: warm data, L3: cold data)

### 3.4 Frontend Framework
- **Framework:** React 18+ with TypeScript
- **UI Library:** Material-UI (MUI) v5
- **Charts:** D3.js (network graphs), Chart.js (time series)
- **State Management:** React Query + Zustand
- **Real-time:** WebSocket connections for live updates

---

## 4. Data Strategy & Independence

### 4.1 Multi-Tier Data Acquisition

**Tier 1: Direct Client Feeds**
- Primary ingestion of client CDS curves, internal pricing, transaction data
- Real-time API connections with fallback mechanisms

**Tier 2: Global Independent Feeds**
- S&P Global / IHS Markit (~$250k+/yr enterprise)
- ICE Data Services (~$150k+/yr enterprise)
- Refinitiv CDS/bond pricing (~$100k+/yr enterprise)

**Tier 3: South African Market Proxies**
- JSE-listed bank bond spreads
- SARB sovereign yield curves
- National Treasury auction results

**Tier 4: Derived Signals**
- Bond-CDS basis modeling
- ZAR FX volatility
- Cross-currency basis spreads
- Rating agency announcements

### 4.2 Data Quality & Fallback Management

**Cross-Validation**
- Compare client vs. independent feeds, flag discrepancies > ±5bps
- Discrepancy thresholds vary by market liquidity (liquid: 3-5bps, semi-liquid: 5-10bps, illiquid: 10-20bps)

**Confidence Scoring**
- Each datapoint tagged 0-100 based on source reliability, recency, and variance vs. peers
- Weighted composite fine-tuned via historical manipulation cases

**Fallback Triggers**
- Auto-switch if client feed silent >10 minutes
- Manual override (requires compliance/legal authorization)
- Hysteresis: 2 consecutive healthy checks before reverting

**Mixed-Frequency Handling**
- Interpolation for gaps <10 minutes
- 1-minute rollups for CDS, bond, FX, macro data
- Source-change alerts visible in dashboard

---

## 5. Risk Scoring & Outputs

### 5.1 Composite Risk Score (0-100)

**Risk Levels**
- **LOW (0-33):** Competitive behavior indicated
- **AMBER (34-66):** Monitoring recommended
- **RED (67-100):** Investigation warranted

**Component Scores**
- **Invariance (0-1):** Structural stability across environments
- **Network (0-1):** Centrality and influence patterns
- **Regime (0-1):** VMM regime confidence
- **Synchrony (0-1):** Temporal coordination patterns

### 5.2 Confidence Assessment
- **Statistical Confidence:** P-values, standard errors, confidence intervals
- **Data Quality Confidence:** Source reliability, coverage, freshness
- **Methodological Confidence:** Model fit, assumption validity

### 5.3 Evidence Bundle
- **Raw Data:** Source-tagged, cryptographically timestamped
- **Analysis Results:** Statistical outputs, confidence measures
- **Audit Trail:** All processing steps, source switches, overrides
- **RFC 3161 Timestamp:** Cryptographic proof of analysis timing

---

## 6. Implementation Roadmap

### 6.1 Phase 1: Pilot Validation (Months 1-6)
- Retrospective analysis of known coordination cases
- Methodology refinement based on data quality and availability
- Statistical threshold calibration for different industry contexts
- FNB CDS market pilot implementation

### 6.2 Phase 2: Regulatory Sandbox (Months 7-12)
- Pilot applications with willing competition authorities
- Court testimony and expert witness protocols
- Training programs for regulatory staff
- Methodological validation and peer review

### 6.3 Phase 3: Industry Compliance Programs (Year 2)
- Proactive compliance auditing for algorithm-intensive firms
- Integration with existing competition compliance systems
- Continuous monitoring deployment
- Enterprise subscription model launch

### 6.4 Phase 4: Full Deployment (Year 3)
- Standard investigative tool for competition authorities
- Integration with merger control processes
- International harmonization across jurisdictions
- Full commercial rollout

---

## 7. Legal & Compliance Framework

### 7.1 Regulatory Credibility
- **Data Transparency:** Dashboard visibly indicates current data source
- **Audit Logs:** All source switches timestamped and archived
- **Court Admissibility:** Confidence scores and source-change logs included in evidence packs
- **Methodological Transparency:** Full disclosure of analytical approach

### 7.2 Evidence Standards
- **Cryptographic Signing:** RFC 3161 timestamping for all outputs
- **Immutable Audit Trail:** Complete chain of custody for all data and analysis
- **Source Independence:** Multiple independent data sources with cross-validation
- **Expert Testimony:** Qualified economists available for court proceedings

### 7.3 Compliance Integration
- **Regulatory Reporting:** Automated compliance dashboards
- **Risk Alerts:** Early warning systems for potential coordination patterns
- **Documentation:** Continuous compliance record generation
- **Training:** Staff education on algorithmic pricing compliance

---

## 8. Success Metrics & KPIs

### 8.1 Technical Performance
- **Availability:** 99.0% monthly uptime (30-day rolling)
- **Latency:** P50 <5s, P95 <8s for standard queries
- **Data Freshness:** 95% of data <10 minutes old
- **Evidence Export:** 95% of exports complete in <2 minutes

### 8.2 Analytical Accuracy
- **False Positive Rate:** <5% on golden competitive datasets
- **True Positive Rate:** >90% on golden coordinated datasets
- **Determinism:** Max 0.5 risk score delta across 10 identical runs
- **VMM Stability:** <5% spurious regime changes, <3% drift reproducibility delta

### 8.3 Commercial Success
- **Enterprise Subscriptions:** Target 10 major clients by Year 2
- **ARR Growth:** 100% year-over-year growth target
- **Client Retention:** 95% annual retention rate
- **Regulatory Adoption:** 5+ competition authorities using ACD by Year 3

---

## 9. Technical Specifications

### 9.1 VMM Implementation Details

**Moment Conditions**
- Orthogonality: E[g(θ, X)] = 0
- Conditional variance stability: Var(g|Z) remains bounded
- Temporal smoothness: θ changes gradually over time
- Optional lead-lag checks: E[g(θ, X_t, X_{t-k})] = 0

**Variational Update**
- Mean-field Gaussian approximation: q(θ) = N(μ, Σ)
- Online ELBO ascent with natural-gradient updates
- Learning rate decay: η_t = η_0 / (1 + λt)
- Gradient clipping: ||∇_θ||₂ ≤ γ
- Mini-batching with exponential kernel weighting

**Update Cadence**
- Every 5 minutes for real-time monitoring
- Warm-up: minimum 2,000 data points
- Decay: λ = 0.98 per day (exponential forgetting)
- Convergence: ELBO relative change < 1e-4 or ||Δθ||₂ < 1e-3 over 5 consecutive inner iterations, max 50 inner iterations

### 9.2 API Contracts

**REST Endpoints**
- `POST /api/v1/cases` - Create new monitoring case
- `GET /api/v1/risk/current` - Current risk assessment
- `GET /api/v1/risk/history` - Historical risk evolution
- `POST /api/v1/evidence/export` - Generate evidence bundle

**WebSocket Events**
- `risk_update` - Real-time risk score changes
- `regime_change` - VMM regime transitions
- `data_source_switch` - Fallback data source changes

**Data Schemas**
- `Case`: Monitoring case definition and metadata
- `Observation`: Individual data point with source tagging
- `RiskSummary`: Comprehensive risk assessment output
- `EvidenceBundle`: Complete evidence package for legal proceedings

---

## 10. Development & Deployment

### 10.1 Development Methodology
- **Contract-First:** OpenAPI specs, JSON schemas, acceptance criteria
- **Walking Skeleton:** Vertical slice implementation with full CI/CD
- **Deterministic Testing:** Golden datasets, seeded randomness, reproducible builds
- **Continuous Validation:** Automated testing of all contracts and schemas

### 10.2 Infrastructure
- **Containerization:** Docker with multi-stage builds
- **Orchestration:** Kubernetes (EKS/GKE) with auto-scaling
- **Monitoring:** Prometheus + Grafana, OpenTelemetry tracing
- **CI/CD:** GitHub Actions with automated testing and deployment

### 10.3 Security & Compliance
- **Authentication:** OAuth2/JWT with RBAC
- **Encryption:** AES-256 at rest, TLS 1.3 in transit
- **Data Protection:** GDPR/POPIA/CCPA compliance
- **Audit:** Immutable audit trails, cryptographic signing

---

## 11. Limitations & Considerations

### 11.1 Technical Limitations
- **Data Requirements:** High-frequency data over extended periods required
- **Market Complexity:** Works best in price-focused competitive environments
- **Statistical Interpretation:** Requires expert economic analysis
- **Gaming Resistance:** Multi-layer validation reduces manipulation potential

### 11.2 Sector-Specific Challenges
- **Optimal Application:** Data-intensive sectors (finance, airlines, e-commerce)
- **Limited Application:** Traditional industries with infrequent pricing
- **Mixed Effectiveness:** Highly differentiated markets may require additional analysis

### 11.3 Legal & Regulatory Adaptation
- **Jurisdictional Variation:** Adapts to different legal standards
- **Complementary Analysis:** Supplements traditional competition analysis
- **International Coordination:** Facilitates cross-border harmonization

---

## 12. Conclusion

The ACD represents a fundamental shift from theoretical speculation to empirical evidence in algorithmic pricing enforcement. By providing objective, scientifically rigorous tools for distinguishing competition from coordination, it addresses the current enforcement vacuum while enabling proactive compliance.

The platform's dual-pillar methodology (ICP + VMM), multi-tier data strategy, and comprehensive validation framework create a robust foundation for regulatory credibility and court admissibility. The commercial model prioritizes ongoing enterprise subscriptions, positioning RBB as the trusted authority on algorithmic pricing compliance.

Success depends on maintaining methodological rigor while delivering practical value to clients. The roadmap balances rapid deployment with thorough validation, ensuring the ACD becomes the standard tool for algorithmic coordination detection across global markets.

---

**Document Version:** 1.8  
**Last Updated:** January 2025  
**Next Review:** March 2025  
**Classification:** Public Product Specification
