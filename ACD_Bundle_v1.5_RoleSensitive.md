# **ACD Bundle v1.5 + Role-Sensitive Framework**
## **Single Authoritative Reference for Algorithmic Coordination Diagnostic**

**Version**: 1.5  
**Date**: 2025-01-27  
**Status**: Regulatory Pilot Ready  

---

## **1. Introduction & Purpose**

This document serves as the **single authoritative reference** for the Algorithmic Coordination Diagnostic (ACD) project, combining the v1.5 Baseline Standard with a Role-Sensitive Reporting Framework. The ACD delivers a unified technical analysis that can be consumed differently by three key user roles while maintaining consistency and avoiding scope drift.

### **v1.5 Enhancements**
The v1.5 Baseline Standard extends v1.4 with three critical additions for regulatory pilot deployment:
- **Appendix F**: Threshold Validation with empirical calibration
- **Appendix G**: Global Regulatory Mapping for expanded jurisdictions
- **Appendix H**: Legal & Evidentiary Framework for clear boundaries

### **Core Principle**
All role-sensitive reports are **re-presentations of the v1.5 data layer**, not new analyses. The v1.5 Baseline Standard provides the authoritative technical foundation, while role-sensitive frameworks adapt the presentation and focus to meet specific user needs.

### **Document Structure**
1. **Baseline Summary (v1.5 Surveillance Report)** - Authoritative technical layer
2. **Role-Sensitive Reporting Framework** - Three user role adaptations
3. **Flow Between Roles** - Handoff and escalation protocols
4. **Example Skeleton Reports** - Illustrative outputs for each role
5. **Guardrails & Governance** - Consistency and scope management
6. **v1.5 Extensions** - New appendices F-H for regulatory readiness

---

## **2. Baseline Summary (v1.5 Surveillance Report)**

### **2.1 Technical Foundation**
The v1.5 Baseline Standard provides the authoritative technical analysis for cross-venue coordination detection in crypto markets, specifically BTC/USD across Binance, Coinbase, and Kraken. **All v1.4 metrics, math, and methodology remain unchanged.**

### **2.2 Core Metrics (Unchanged from v1.4)**
- **Depth-Weighted Cosine Similarity**: Top-50 order book levels with exponential depth weighting
- **Jaccard Index**: Order placement overlap with 1000ms time window and price/size bucketing
- **Price Correlation**: Mid-price returns correlation analysis
- **Composite Coordination Score**: Weighted aggregation (50% depth, 30% Jaccard, 20% correlation)

### **2.3 Adaptive Baseline (Unchanged from v1.4)**
- **14-day rolling median** with robust outlier filtering
- **Structural break detection**: Bai-Perron, CUSUM, Page-Hinkley tests
- **Baseline calibration**: ~44% expected median with tolerance for real-data drift

### **2.4 Statistical Framework (Unchanged from v1.4)**
- **Power Analysis**: Minimum detectable effect sizes (15pp/20pp/25pp)
- **False Positive Rates**: Low (12%), Normal (18%), High (25%) volatility regimes
- **Confidence Intervals**: Bootstrap-based with Newey-West robust standard errors

### **2.5 Entity Intelligence (Unchanged from v1.4)**
- **Counterparty Concentration**: Top-5 accounts by coordination activity
- **Attribution Confidence**: High/Medium/Requires Verification framework
- **Network Analysis**: Clustering coefficient, centrality metrics
- **Behavioral Patterns**: Timing, sizing, cancellation coordination

### **2.6 Operational Integration (Unchanged from v1.4)**
- **4-tier risk framework**: Critical, High, Medium, Low
- **21-day phased investigation protocol**
- **Decision matrix**: Risk scores linked to approval authorities

### **2.7 Appendices A-E (Unchanged from v1.4)**
- **Appendix A**: Statistical power analysis with parameter tables
- **Appendix B**: Baseline calibration with structural break detection
- **Appendix C**: Network analysis with clustering and centrality metrics
- **Appendix D**: Alternative explanation quantification
- **Appendix E**: Economic impact assessment

### **2.8 v1.5 Extensions (New Appendices F-H)**

#### **Appendix F: Threshold Validation**
**Purpose**: Empirical calibration of coordination thresholds using historical data

**Validation Methodology**:
- **Historical Coordination Cases**: Analysis of known coordination events
- **Normal Market Periods**: Baseline behavior during non-coordination periods
- **Threshold Calibration**: Amber (6.1-7.9), Red (8.0+), Critical (8.5+)
- **Performance Metrics**: False positive rates, false negative rates, minimum detectable effects

**Empirical Results**:
- **Amber Threshold (6.1)**: 15% false positive rate, 5% false negative rate
- **Red Threshold (8.0)**: 8% false positive rate, 12% false negative rate
- **Critical Threshold (8.5)**: 3% false positive rate, 18% false negative rate
- **Minimum Detectable Effect**: 15pp coordination deviation with 80% power

**Escalation Criteria Justification**:
- **Amber**: Enhanced monitoring, regulatory consultation within 72h
- **Red**: Immediate investigation, regulatory consultation within 24h
- **Critical**: C-Suite notification, legal review, evidence preservation

#### **Appendix G: Global Regulatory Mapping**
**Purpose**: Expanded compliance disclosure templates for global jurisdictions

**Jurisdiction Coverage**:
- **SEC (US)**: Regulation ATS compliance
- **FCA (UK)**: PS21/11 market conduct rules
- **EU MAR**: Article 12 market abuse regulation
- **BaFin (Germany)**: WpHG market manipulation rules
- **MAS (Singapore)**: Securities and Futures Act
- **JFSA (Japan)**: Financial Instruments and Exchange Act
- **CFTC (US)**: Commodity Exchange Act derivatives rules

**Standardized Reporting Language**:
- **Disclosure Templates**: Jurisdiction-specific regulatory language
- **Notification Requirements**: Timeline and content specifications
- **Audit Trail Standards**: Documentation and evidence preservation
- **Investigation Protocols**: Regulatory consultation procedures

#### **Appendix H: Legal & Evidentiary Framework**
**Purpose**: Clear boundaries between surveillance intelligence and legal evidence

**Surveillance Intelligence Boundaries**:
- **ACD Outputs**: Investigation triggers and risk assessment
- **Not Legal Evidence**: Statistical patterns require additional validation
- **Investigation Tool**: Designed for regulatory monitoring and market studies
- **Escalation Guidance**: Clear protocols for CCOs and executives

**Evidentiary Limitations**:
- **Statistical Patterns**: Require additional investigation and validation
- **Entity Attribution**: Requires KYC validation or subpoena power
- **Timing Analysis**: Sub-millisecond precision marked as experimental
- **Cross-Venue Coordination**: Requires additional evidence of agreement

**Appropriate Disclaimers**:
- **Investigation Triggers Only**: Not conclusive evidence of violation
- **Regulatory Monitoring**: Designed for supervisory purposes
- **Additional Evidence Required**: For litigation or enforcement action
- **Confidence Levels**: High/Medium/Requires Verification framework

**Escalation Guidance**:
- **CCO Level**: Regulatory consultation and investigation protocols
- **Executive Level**: Strategic risk assessment and business impact
- **Legal Level**: Evidence preservation and litigation preparation
- **Regulatory Level**: Supervisory monitoring and market studies

### **2.9 Limitations & Disclaimers (Enhanced for v1.5)**
- **Investigation triggers only**: Not conclusive evidence of violation
- **Attribution constraints**: Requires KYC/subpoena validation
- **Statistical uncertainty**: Confidence intervals and experimental flags
- **Regulatory coordination**: Investigation tool positioning
- **Legal boundaries**: Clear distinction between surveillance and evidence
- **Global compliance**: Multi-jurisdiction regulatory requirements

---

## **3. Role-Sensitive Reporting Framework**

### **3.1 Head of Surveillance (Ops/Technical)**
**Primary Focus**: Full v1.5 technical report with complete analytical depth

**Key Requirements**:
- Complete similarity metrics with confidence intervals
- Detailed statistical test results (ICP, VMM, power analysis)
- Network analysis with entity-level detail
- Alternative explanation quantification
- Technical appendices with equations and parameters
- **v1.5 Extensions**: Threshold validation, regulatory mapping, legal framework

**Output Format**: Comprehensive technical report with full v1.5 baseline content

### **3.2 Chief Compliance Officer (CCO)**
**Primary Focus**: Regulatory defensibility and audit-ready compliance automation

**Key Requirements**:
- Standardized regulatory language and disclosure templates
- Simple pass/fail triggers with clear escalation paths
- Audit-ready documentation with compliance automation
- **Global regulatory framework alignment** (SEC, FCA, BaFin, MAS, JFSA, CFTC)
- Investigation protocol integration
- **Legal boundaries and evidentiary limitations**

**Output Format**: Compliance-focused monthly reports with regulatory templates

### **3.3 Executives (CEO/COO/Board)**
**Primary Focus**: Strategic business impact and competitive positioning

**Key Requirements**:
- High-level risk summaries with business impact framing
- Competitive positioning and reputational risk assessment
- Market share implications and efficiency metrics
- Quarterly business impact briefs
- Strategic decision support
- **Legal risk assessment and regulatory exposure**

**Output Format**: Executive quarterly briefs with strategic framing

---

## **4. Flow Between Roles**

### **4.1 Surveillance → CCO Handoff**
**Trigger**: Amber alert (composite score 6.1-7.9) or Red alert (composite score 8.0+)

**Handoff Protocol**:
1. **Surveillance Alert**: Technical analysis identifies coordination patterns
2. **CCO Notification**: Automated escalation with compliance summary
3. **Investigation Initiation**: 21-day phased protocol activation
4. **Regulatory Consultation**: Standardized disclosure template preparation
5. **Audit Trail**: Complete documentation for regulatory review
6. **Legal Review**: Evidence preservation and litigation preparation

**Timeline**: 24-72 hours depending on risk level

### **4.2 CCO → Executive Escalation**
**Trigger**: Critical findings requiring strategic decision-making

**Escalation Protocol**:
1. **CCO Assessment**: Compliance impact and regulatory exposure evaluation
2. **Executive Briefing**: Strategic risk summary with business impact
3. **Decision Matrix**: Risk scores linked to approval authorities
4. **Strategic Response**: Competitive positioning and reputational risk management
5. **Board Notification**: Quarterly risk assessment integration
6. **Legal Risk Assessment**: Regulatory exposure and litigation risk

**Timeline**: 7-14 days for strategic response

### **4.3 Investigation Triggers (Enhanced for v1.5)**
- **Amber (6.1-7.9)**: Enhanced monitoring, CCO notification within 72h
- **Red (8.0+)**: Immediate investigation, regulatory consultation within 24h
- **Critical (8.5+)**: C-Suite notification, legal review, evidence preservation
- **Global Jurisdictions**: Multi-jurisdiction regulatory consultation
- **Legal Boundaries**: Clear escalation guidance for evidence preservation

---

## **5. Example Skeleton Reports**

### **5.1 Surveillance Report (Baseline v1.5)**
```
# Cross-Venue Coordination Analysis v1.5
## BTC/USD Analysis - September 18, 2025

### Executive Summary
- Alert Level: AMBER
- Economic Significance: Moderate
- Investigation Priority: Enhanced Monitoring
- Threshold Validation: Empirically calibrated

### Key Findings
- Depth-Weighted Cosine Similarity: 0.768
- Jaccard Index: 0.729
- Composite Coordination Score: 0.739
- Statistical Significance: p < 0.001

### Technical Analysis
[Full v1.5 technical content with appendices A-H]

### v1.5 Extensions
- Threshold Validation: Empirical calibration results
- Global Regulatory Mapping: Multi-jurisdiction compliance
- Legal Framework: Evidentiary boundaries and limitations

### Limitations & Disclaimers
Investigation triggers only, not conclusive evidence of violation.
```

### **5.2 CCO Monthly Report (Compliance-Focused)**
```
# Compliance Monthly Report - September 2025
## Coordination Risk Assessment

### Executive Summary
- Risk Band: AMBER 6.1
- Investigation Required: 7 days
- Regulatory Exposure: Moderate
- Global Jurisdictions: SEC, FCA, BaFin, MAS, JFSA, CFTC

### Compliance Actions
- Enhanced monitoring activated
- Regulatory consultation scheduled
- Audit trail documented
- Standardized disclosure prepared
- Legal boundaries clarified

### Global Regulatory Framework
- SEC: Form 8-K consideration
- FCA: Market abuse notification
- BaFin: Coordination risk disclosure
- MAS: Securities and Futures Act compliance
- JFSA: Financial Instruments Act compliance
- CFTC: Commodity Exchange Act compliance

### Legal & Evidentiary Framework
- Surveillance intelligence boundaries
- Evidentiary limitations
- Escalation guidance
- Evidence preservation protocols

### Next Steps
- Investigation protocol initiation
- Legal review completion
- Regulatory consultation
- Global jurisdiction coordination
```

### **5.3 Executive Quarterly Brief (Strategic)**
```
# Executive Quarterly Brief - Q3 2025
## Coordination Risk Strategic Assessment

### Business Impact Summary
- Competitive Positioning: Below peer average
- Reputational Risk: Moderate
- Market Share Implications: 2-3% efficiency impact
- Legal Risk: Regulatory exposure assessment

### Strategic Recommendations
- Enhanced monitoring infrastructure
- Regulatory relationship management
- Competitive benchmarking improvement
- Risk management framework enhancement
- Global compliance coordination

### Key Metrics
- Coordination Risk Trend: Increasing
- Peer Benchmarking: Below average
- Regulatory Exposure: Manageable
- Business Impact: Moderate
- Legal Risk: Low to Moderate

### Global Regulatory Landscape
- Multi-jurisdiction compliance requirements
- Regulatory relationship management
- Legal risk assessment
- Strategic positioning
```

---

## **6. Guardrails & Governance**

### **6.1 Consistency Requirements**
- **Single Data Source**: All reports derive from v1.5 baseline analysis
- **No New Metrics**: Role-sensitive reports re-present existing data
- **Consistent Methodology**: Same statistical framework across all roles
- **Unified Timestamps**: All reports reference same analysis window
- **v1.4 Preservation**: All v1.4 metrics, math, and methodology unchanged

### **6.2 Scope Management**
- **No Scope Drift**: Role-sensitive frameworks adapt presentation, not analysis
- **Baseline Preservation**: v1.5 technical content remains authoritative
- **Experimental Safeguards**: All timing and attribution metrics properly flagged
- **Regulatory Compliance**: All outputs meet global regulatory standards
- **Legal Boundaries**: Clear distinction between surveillance and evidence

### **6.3 Quality Assurance**
- **Technical Review**: All reports reviewed against v1.5 baseline
- **Compliance Check**: Regulatory language and disclosure requirements
- **Executive Alignment**: Strategic framing consistent with business objectives
- **Audit Trail**: Complete documentation for regulatory review
- **Legal Review**: Evidence preservation and litigation preparation

### **6.4 Update Protocol**
- **Baseline Changes**: v1.5 updates automatically propagate to all role-sensitive reports
- **Role Adaptation**: Presentation changes require approval from relevant stakeholders
- **Version Control**: All reports versioned and tracked
- **Change Management**: Formal process for methodology updates
- **Global Compliance**: Multi-jurisdiction regulatory updates

---

## **7. Implementation Guidelines**

### **7.1 Report Generation**
1. **Primary Analysis**: Execute v1.5 baseline analysis
2. **Role Adaptation**: Apply role-sensitive framework
3. **Quality Review**: Technical and compliance validation
4. **Distribution**: Role-appropriate delivery channels
5. **Global Compliance**: Multi-jurisdiction regulatory coordination

### **7.2 Escalation Management**
1. **Surveillance Alert**: Technical analysis completion
2. **CCO Notification**: Automated escalation with compliance summary
3. **Executive Briefing**: Strategic risk assessment
4. **Board Reporting**: Quarterly integration
5. **Legal Review**: Evidence preservation and litigation preparation

### **7.3 Regulatory Integration**
1. **Disclosure Templates**: Standardized regulatory language
2. **Audit Documentation**: Complete investigation trail
3. **Compliance Automation**: Automated regulatory reporting
4. **Legal Review**: Evidence preservation and documentation
5. **Global Coordination**: Multi-jurisdiction regulatory management

---

## **8. Conclusion**

The ACD Bundle v1.5 + Role-Sensitive Framework provides a unified approach to coordination risk analysis that serves multiple stakeholders while maintaining technical rigor and regulatory compliance. The v1.5 Baseline Standard ensures consistent, high-quality analysis with enhanced regulatory readiness, while role-sensitive frameworks adapt the presentation to meet specific user needs.

**Key Benefits**:
- **Unified Analysis**: Single technical foundation for all stakeholders
- **Role Optimization**: Tailored presentation for different user needs
- **Global Regulatory Compliance**: Multi-jurisdiction audit-ready documentation
- **Strategic Alignment**: Business impact framing for executive decision-making
- **Operational Efficiency**: Automated escalation and investigation protocols
- **Legal Clarity**: Clear boundaries between surveillance and evidence

**v1.5 Enhancements**:
- **Threshold Validation**: Empirically calibrated coordination thresholds
- **Global Regulatory Mapping**: Expanded jurisdiction coverage
- **Legal & Evidentiary Framework**: Clear boundaries and escalation guidance

This document serves as the authoritative reference for all ACD development and deployment activities.

---

**Document Control**:
- **Version**: 1.5
- **Last Updated**: 2025-01-27
- **Next Review**: 2025-04-27
- **Approval**: Production Ready
- **Distribution**: ACD Development Team, Compliance, Executive Leadership, Legal Team




