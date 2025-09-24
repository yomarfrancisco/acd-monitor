# Phase-3 Implementation Checklist: Regulatory Readiness

## **🎯 PHASE-3 OBJECTIVES**

Transform ACD from a validated diagnostic into a **regulatory-ready tool** with structured reporting and retrospective validation.

**Main Goals:**
1. **CMA Poster Frames retrospective case study**
2. **Reporting v2** — attribution tables, structured outputs, JSON + PDF bundles
3. **Agent-driven bundle generation** — conversational drafting and refinement
4. **Tight governance & reproducibility** — provenance, pre-registration, peer-review readiness

---

## **📋 IMPLEMENTATION CHECKLIST**

### **1. Retrospective Validation**

#### **1.1 CMA Poster Frames Case Study**
- [ ] **Data Collection & Preparation**
  - [ ] Identify CMA Poster Frames data sources (public filings, academic papers, regulatory documents)
  - [ ] Create `cases/cma_poster_frames/prepare_data.py` for data reconstruction
  - [ ] Map CMA case to ACD framework (venues → airlines, prices → fares, coordination periods)
  - [ ] Generate synthetic CMA data if real data unavailable
  - [ ] Validate data quality and completeness

- [ ] **Analysis Pipeline**
  - [ ] Create `cases/cma_poster_frames/run_analysis.py` for ACD analysis
  - [ ] Apply ICP, VMM, and validation layers to CMA data
  - [ ] Generate coordination signatures and risk assessments
  - [ ] Compare results to documented CMA findings
  - [ ] Create reproducibility report with provenance

- [ ] **Validation & Testing**
  - [ ] Create `cases/cma_poster_frames/test_cma_golden_files.py`
  - [ ] Implement golden-file tests for key metrics
  - [ ] Validate coordination patterns match expected signatures
  - [ ] Test reproducibility across multiple runs
  - [ ] Document any discrepancies and alternative explanations

#### **1.2 Golden File Validation**
- [ ] **ATP Case Validation**
  - [ ] Verify ATP case study still passes all golden-file tests
  - [ ] Update golden files if methodology changes
  - [ ] Ensure reproducibility across different seeds

- [ ] **Synthetic Data Validation**
  - [ ] Verify synthetic competitive/coordinated scenarios still differentiate
  - [ ] Update golden files for any VMM or validation layer changes
  - [ ] Test power analysis and statistical rigor

### **2. Reporting v2 Implementation**

#### **2.1 Attribution Tables**
- [ ] **Core Attribution System**
  - [ ] Create `src/acd/analytics/attribution.py` for driver breakdown
  - [ ] Implement per-layer contribution calculation (ICP, VMM, validation layers)
  - [ ] Add confidence intervals and statistical significance
  - [ ] Include alternative explanations and counterfactuals
  - [ ] Add sensitivity analysis and robustness checks

- [ ] **Attribution Table Generation**
  - [ ] Create structured attribution tables with:
    - [ ] Lead-lag contribution to composite score
    - [ ] Mirroring ratio impact and confidence
    - [ ] HMM regime detection contribution
    - [ ] Information flow network analysis
    - [ ] Alternative explanations (arbitrage, fees, inventory, volatility)
  - [ ] Add statistical significance indicators (p-values, confidence intervals)
  - [ ] Include provenance and methodology references

#### **2.2 Bundle Export System**
- [ ] **JSON Bundle Generation**
  - [ ] Create `src/acd/reporting/bundle_generator.py`
  - [ ] Implement structured JSON export with:
    - [ ] Executive summary and key findings
    - [ ] Methodology appendix (ICP/VMM/validation specs)
    - [ ] Attribution tables with driver breakdowns
    - [ ] Statistical significance and confidence intervals
    - [ ] Alternative explanations and counterfactuals
    - [ ] Audit trail with cryptographic signature
    - [ ] Provenance and reproducibility metadata

- [ ] **PDF Bundle Generation**
  - [ ] Create `src/acd/reporting/pdf_generator.py`
  - [ ] Implement PDF export with:
    - [ ] Executive summary (1-2 pages)
    - [ ] Methodology appendix (technical details)
    - [ ] Regression/confidence tables
    - [ ] Charts/graphs (regimes, networks, time series)
    - [ ] Alternative explanations checklist
    - [ ] Audit trail and cryptographic signature
    - [ ] Regulatory-ready formatting and styling

#### **2.3 Bundle Quality Assurance**
- [ ] **Content Validation**
  - [ ] Ensure all required sections are present
  - [ ] Validate statistical rigor and methodology
  - [ ] Check for completeness and consistency
  - [ ] Verify regulatory language and terminology

- [ ] **Format Validation**
  - [ ] Test JSON schema compliance
  - [ ] Validate PDF formatting and readability
  - [ ] Ensure proper page breaks and styling
  - [ ] Test file size and performance

### **3. Agent Bundle Generation**

#### **3.1 Conversational Bundle Drafting**
- [ ] **Bundle Generation Queries**
  - [ ] Extend agent to handle bundle generation requests
  - [ ] Implement query patterns for:
    - [ ] "Generate a full screening bundle for [asset] [timeframe]"
    - [ ] "Draft a regulatory memo for [asset] covering [period]"
    - [ ] "Create a compliance report for [venue] [timeframe]"
  - [ ] Add bundle-specific intent detection and routing

- [ ] **Bundle Content Generation**
  - [ ] Create `src/agent/compose/bundle_generator.py`
  - [ ] Implement bundle content generation with:
    - [ ] Executive summary generation
    - [ ] Methodology section compilation
    - [ ] Attribution table integration
    - [ ] Chart and graph generation
    - [ ] Alternative explanations inclusion
    - [ ] Audit trail and provenance

#### **3.2 Bundle Refinement System**
- [ ] **Refinement Query Handling**
  - [ ] Implement refinement patterns for:
    - [ ] "Add [specific section] to the bundle"
    - [ ] "Highlight [specific patterns] in the report"
    - [ ] "Include [counterfactuals/alternative explanations]"
    - [ ] "Refine the [section] to emphasize [aspect]"
  - [ ] Add refinement intent detection and routing

- [ ] **Iterative Bundle Improvement**
  - [ ] Create `src/agent/compose/bundle_refiner.py`
  - [ ] Implement iterative bundle improvement with:
    - [ ] Section-specific refinement
    - [ ] Content addition and modification
    - [ ] Emphasis and highlighting
    - [ ] Counterfactual inclusion
    - [ ] Quality validation after each refinement

#### **3.3 Bundle Quality Control**
- [ ] **Refinement Limits**
  - [ ] Implement ≤5 prompt refinement limit
  - [ ] Add quality gates after each refinement
  - [ ] Prevent infinite refinement loops
  - [ ] Ensure bundle coherence and completeness

- [ ] **Bundle Validation**
  - [ ] Validate bundle completeness after generation
  - [ ] Check for required sections and content
  - [ ] Ensure statistical rigor and methodology
  - [ ] Verify regulatory compliance and language

### **4. Compliance Officer Query Testing**

#### **4.1 Core Bundle Queries**
- [ ] **Primary Bundle Generation Queries**
  - [ ] "Generate a full screening bundle for BTC/USD last week with attribution tables"
  - [ ] "Draft a regulatory memo for ETH/USD covering Q3 2024, include alternative explanations"
  - [ ] "Create a compliance report for Binance BTC/USD last month"
  - [ ] "Generate a screening bundle for top 3 venues ETH/USD past 30 days"
  - [ ] "Draft a regulatory summary for all major venues BTC/USD Q3 2024"

#### **4.2 Bundle Refinement Queries**
- [ ] **Content Addition Queries**
  - [ ] "Add regime charts and lead-lag drivers to the BTC/USD screening bundle"
  - [ ] "Include mirroring vs arbitrage counterfactuals in the ETH/USD report"
  - [ ] "Add sensitivity analysis to the Binance compliance report"
  - [ ] "Include power analysis and statistical rigor in the regulatory memo"
  - [ ] "Add network analysis and information flow to the screening bundle"

- [ ] **Emphasis and Highlighting Queries**
  - [ ] "Refine the ETH/USD report to highlight mirroring patterns"
  - [ ] "Emphasize coordination risk drivers in the BTC/USD bundle"
  - [ ] "Highlight alternative explanations in the regulatory memo"
  - [ ] "Focus on statistical significance in the compliance report"
  - [ ] "Emphasize regulatory implications in the screening bundle"

#### **4.3 Edge Case and Complex Queries**
- [ ] **Complex Multi-Asset Queries**
  - [ ] "Generate comparative bundles for BTC/USD vs ETH/USD across all venues"
  - [ ] "Create a cross-venue coordination analysis bundle for top 5 exchanges"
  - [ ] "Draft a regulatory memo comparing coordination patterns across asset pairs"

- [ ] **Temporal and Regime Queries**
  - [ ] "Generate bundles for different volatility regimes in BTC/USD"
  - [ ] "Create time-series analysis bundles showing coordination evolution"
  - [ ] "Draft regulatory memos for specific market events and their coordination impact"

- [ ] **Methodology and Validation Queries**
  - [ ] "Generate bundles with detailed methodology validation and robustness checks"
  - [ ] "Create regulatory memos with alternative methodology comparisons"
  - [ ] "Draft compliance reports with pre-registration and peer-review readiness"

### **5. Quality Assurance & Testing**

#### **5.1 Bundle Generation Testing**
- [ ] **Functional Testing**
  - [ ] Test all bundle generation queries
  - [ ] Validate bundle content completeness
  - [ ] Check JSON and PDF export functionality
  - [ ] Verify attribution table accuracy

- [ ] **Refinement Testing**
  - [ ] Test all refinement query patterns
  - [ ] Validate iterative improvement functionality
  - [ ] Check refinement limit enforcement
  - [ ] Verify bundle coherence after refinements

#### **5.2 Integration Testing**
- [ ] **End-to-End Testing**
  - [ ] Test complete bundle generation workflow
  - [ ] Validate agent integration with reporting system
  - [ ] Check provenance tracking and audit trails
  - [ ] Verify regulatory compliance and language

- [ ] **Performance Testing**
  - [ ] Test bundle generation performance
  - [ ] Validate PDF generation speed and quality
  - [ ] Check memory usage and resource consumption
  - [ ] Verify scalability with large datasets

#### **5.3 Regulatory Compliance Testing**
- [ ] **Content Validation**
  - [ ] Ensure regulatory language and terminology
  - [ ] Validate statistical rigor and methodology
  - [ ] Check for completeness and consistency
  - [ ] Verify alternative explanations inclusion

- [ ] **Format Validation**
  - [ ] Test regulatory-ready formatting
  - [ ] Validate PDF styling and readability
  - [ ] Check for proper citations and references
  - [ ] Verify audit trail and cryptographic signatures

### **6. Documentation & Handoff**

#### **6.1 Technical Documentation**
- [ ] **API Documentation**
  - [ ] Document bundle generation API endpoints
  - [ ] Create agent query pattern documentation
  - [ ] Document refinement system usage
  - [ ] Create troubleshooting and FAQ guides

- [ ] **User Documentation**
  - [ ] Create compliance officer user guide
  - [ ] Document bundle generation workflows
  - [ ] Create refinement best practices guide
  - [ ] Document regulatory compliance requirements

#### **6.2 Regulatory Documentation**
- [ ] **Methodology Documentation**
  - [ ] Document attribution methodology
  - [ ] Create statistical rigor guidelines
  - [ ] Document alternative explanations framework
  - [ ] Create sensitivity analysis procedures

- [ ] **Compliance Documentation**
  - [ ] Document regulatory language standards
  - [ ] Create audit trail requirements
  - [ ] Document provenance and reproducibility standards
  - [ ] Create peer-review readiness checklist

---

## **🚩 RESIDUAL RISKS & MITIGATION**

### **High Priority Risks**
1. **CMA Poster Frames Data Availability**
   - **Risk**: Real CMA data may not be publicly available
   - **Mitigation**: Create synthetic CMA data based on documented patterns
   - **Status**: [ ] Data source identified, [ ] Synthetic data created

2. **Bundle Generation Performance**
   - **Risk**: PDF generation may be slow or resource-intensive
   - **Mitigation**: Implement caching and optimization
   - **Status**: [ ] Performance testing completed, [ ] Optimization implemented

3. **Agent Refinement Complexity**
   - **Risk**: Bundle refinement may become too complex
   - **Mitigation**: Implement strict refinement limits and quality gates
   - **Status**: [ ] Refinement limits implemented, [ ] Quality gates tested

### **Medium Priority Risks**
4. **Regulatory Language Compliance**
   - **Risk**: Generated content may not meet regulatory standards
   - **Mitigation**: Implement regulatory language templates and validation
   - **Status**: [ ] Language templates created, [ ] Validation implemented

5. **Attribution Table Accuracy**
   - **Risk**: Attribution calculations may be incorrect
   - **Mitigation**: Implement comprehensive testing and validation
   - **Status**: [ ] Attribution testing completed, [ ] Validation implemented

### **Low Priority Risks**
6. **Bundle Export Format Issues**
   - **Risk**: JSON/PDF export may have formatting issues
   - **Mitigation**: Implement comprehensive format testing
   - **Status**: [ ] Format testing completed, [ ] Issues resolved

---

## **📊 SUCCESS METRICS**

### **Functional Metrics**
- [ ] **Bundle Generation**: 100% success rate for all query patterns
- [ ] **Refinement System**: ≤5 prompt refinement limit enforced
- [ ] **Export Functionality**: JSON and PDF generation working
- [ ] **Attribution Tables**: Accurate driver breakdowns

### **Quality Metrics**
- [ ] **Content Completeness**: All required sections present
- [ ] **Statistical Rigor**: Proper methodology and significance testing
- [ ] **Regulatory Compliance**: Appropriate language and terminology
- [ ] **Provenance Tracking**: Complete audit trails and reproducibility

### **Performance Metrics**
- [ ] **Generation Speed**: Bundle generation <30 seconds
- [ ] **Refinement Speed**: Each refinement <10 seconds
- [ ] **Export Speed**: PDF generation <15 seconds
- [ ] **Memory Usage**: <2GB peak memory usage

---

## **🎯 PHASE-3 ACCEPTANCE CRITERIA**

### **Must Have**
- [ ] CMA Poster Frames case reproduces expected coordination patterns
- [ ] Reporting v2 outputs JSON + PDF bundles with attribution tables
- [ ] Agent can generate draft regulatory bundles conversationally
- [ ] Bundle refinement works within ≤5 prompts
- [ ] All outputs provenance-tracked and stored correctly

### **Should Have**
- [ ] All 15+ compliance officer queries working
- [ ] Bundle generation performance <30 seconds
- [ ] Regulatory language compliance validated
- [ ] Alternative explanations included in all bundles
- [ ] Audit trails and cryptographic signatures working

### **Nice to Have**
- [ ] Cross-venue comparative bundles
- [ ] Temporal analysis bundles
- [ ] Methodology validation bundles
- [ ] Pre-registration and peer-review readiness
- [ ] Advanced visualization and charting

---

## **📅 TIMELINE & MILESTONES**

### **Week 1-2: CMA Poster Frames & Attribution**
- [ ] Complete CMA Poster Frames case study
- [ ] Implement attribution table system
- [ ] Create bundle export infrastructure

### **Week 3-4: Agent Bundle Generation**
- [ ] Implement conversational bundle drafting
- [ ] Create bundle refinement system
- [ ] Test core compliance officer queries

### **Week 5-6: Testing & Validation**
- [ ] Complete end-to-end testing
- [ ] Validate regulatory compliance
- [ ] Performance optimization and tuning

### **Week 7-8: Documentation & Handoff**
- [ ] Complete technical documentation
- [ ] Create user guides and best practices
- [ ] Final validation and acceptance testing

---

**Status**: 🚀 **PHASE-3 KICKOFF READY**
**Last Updated**: 2025-09-21
**Estimated Completion**: 8 weeks
**Dependencies**: Phase-2 completion ✅



