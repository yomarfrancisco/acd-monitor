# Algorithmic Coordination Diagnostic (ACD) – LLM Agent Plan
Final Specification with Implementation Roadmap

## 1. Goal
To create an intelligent LLM agent that makes the outputs of the ACD system usable, interpretable, and defensible for its core stakeholders.
The LLM is not a substitute for economic or legal expertise. Instead, it is a compliance and evidence assistant that:
- Translates validated econometric outputs into plain language
- Supports compliance officers, surveillance teams, regulators, and courts by adapting explanations to their needs
- Provides reproducible evidence bundles with full data provenance
- Augments human experts by scaling validated methodologies, not replacing their judgment

## 2. Problem
Global crypto and financial markets are:
- Fragmented across multiple venues (Binance, Coinbase, Kraken, OKX, Bybit)
- Automated with high-frequency algorithmic pricing
- Opaque to regulators who need systematic, court-ready evidence

**Key Challenges:**
- Compliance officers face pressure to detect coordination risks before regulators intervene
- Regulators lack systematic tools to distinguish competitive adaptation from algorithmic collusion
- Courts demand reproducible, transparent, jurisdiction-specific evidence

**Core Question:** How can complex ICP/VMM econometric tests, statistical counterfactuals, and multi-venue data pipelines be translated into actionable compliance dashboards and regulator-facing evidence without requiring every user to be an economist?

## 3. Solution Architecture
**Three-Layer Model**

**Layer 1: Statistical Detection (Automated)**
- Runs ICP, VMM, and supplementary microstructure tests
- Produces structured outputs (JSON, CSV, logs)
- Maintains cryptographic provenance
- No human interpretation at this layer

**Layer 2: Expert Validation (Human-in-the-loop, Tiered)**
- **GREEN**: Auto-cleared outputs from validated methods
- **AMBER**: Logged outputs, sampled/audited by economists (10% random sample + risk-based sampling)
- **RED**: Mandatory panel review + RBB Economics certification (§5.2, Appendix C)
- Economists calibrate thresholds, validate methodology, and certify critical outputs

**Layer 3: Accessibility (LLM Agent)**
- **Compliance Officers**: Operational dashboards, alerts, plain-English explanations
- **Surveillance Analysts**: Query access to granular data (tick, order-book, counterfactuals)
- **Regulators**: Full evidence bundles with jurisdiction-specific formatting (§6.2)
- **Courts**: Evidence bundles with provenance and limitations clearly stated

## 4. Core Users & Roles

**Compliance Officers (Primary Client)**
- **Access Level**: Tier 2 (dashboards)
- **Use Cases**: Screening venues for RED flags, investigating AMBER outputs, explaining results to executives
- **Needs**: Clear, operational outputs that flag risk, show methodology, and indicate when escalation is required

**Surveillance Teams (Sub-role)**
- **Access Level**: Tier 2-3 (analytics)
- **Use Cases**: Reproducibility verification, query access, counterfactual testing, detailed logs
- **Needs**: Technical detail, data provenance, methodology transparency

**Regulators (Secondary Client)**
- **Access Level**: Tier 4 (full evidence bundles)
- **Use Cases**: Reviewing ICP/VMM results, understanding leadership invariance, testing robustness
- **Needs**: Transparent methodology, limitations clearly noted, jurisdiction-appropriate formatting

**Courts (Ultimate Arbiter)**
- **Access Level**: Tier 4 (via regulators)
- **Needs**: Clear formatting, provenance trail, explicit statement of limitations (§6.1, §6.2)

## 5. LLM Agent Capabilities

### a) Explaining Outputs
- Translates ICP/VMM statistical outputs into plain English
- Explains why a window passed/failed quality gates
- Provides narratives: "Binance led 43% of days in high-volatility regimes vs 28% in low-volatility regimes"
- **Critical**: Flags when results are conditional ("if this pattern represents coordination, harm would be X") vs. validated

### b) Evidence Preparation
- Drafts evidence bundles aligned with spec templates (§6.1, Appendix E)
- Auto-fills jurisdictional variants (DOJ/FTC vs DG COMP) using documented formats
- Tracks provenance: links every chart, table, and statistic back to raw S3 snapshots
- **Never**: Makes independent legal interpretations

### c) Operational Support
- Monitors pipeline health: coverage ≥95%, ≥3 venues, clock skew issues
- Issues structured alerts for failures (Slack/GitHub integration)
- Provides audit logs for each capture and detector run
- Flags data quality issues requiring human review

### d) User-Tailored Interaction
- **Compliance Officer**: "Why did this RED flag trigger?" → Plain-English operational explanation
- **Surveillance Analyst**: "Show me the counterfactual assumptions" → Detailed econometric breakdown with JSON/CSV
- **Regulator**: "Give me the DG COMP evidence bundle for Q2 2025" → Structured export, flagged for expert review before release
- **Court**: "Provide the provenance and limitations of this evidence" → Audit trail with explicit caveats

### e) Jurisdiction-Appropriate Formatting
- Uses templates defined in §6.2 and Appendix E
- Avoids interpretation of law; only applies documented formatting and phrasing
- Example: "Market outcomes consistent with Article 101 TFEU concerns" vs "Market outcomes warranting Sherman Act Section 1 review"

## 6. Human Validation (Tiered Approach)

**GREEN outputs**: Auto-cleared, based on validated thresholds
- Routine monitoring outputs
- Statistical summaries
- Pipeline health reports

**AMBER outputs**: Logged, sampled, audited by economists
- 10% random sampling for quality assurance
- 100% review of outputs near threshold boundaries
- Quarterly validation reports

**RED outputs**: Mandatory panel review before external action
- RBB Economics certification required (§5.2, Appendix C)
- Full alternative explanation assessment
- Legal counsel review before regulatory submission
- Threshold calibration: Regular recalibration by expert economists (§5.2)

## 7. Limitations of the LLM Agent

The LLM does not:
- Make independent legal conclusions
- Defend findings against regulators (explains, not advocates)
- Replace economists in calibration, counterfactual design, or robustness checks
- Quantify harm independently (harm requires supplementary assumptions and evidence, §6.1)
- Independently assess alternative explanations (defers to expert panel per §5.3)
- Provide enforcement recommendations
- Declare definitively whether conduct constitutes coordination

The LLM augments teams by making validated methodologies accessible, interpretable, and reproducible.

## 8. Query Safety Rules & Guardrails

### Redirection Protocol

**Economic judgment questions:**
- User: "Is this definitely coordination?"
- LLM: "This pattern shows statistical signatures consistent with non-competitive market outcomes. However, determining whether this represents coordination, parallel conduct, or other explanations requires expert economist review per §5.2. The current risk classification is [RED/AMBER/GREEN]. Would you like me to explain the statistical basis for this classification?"

**Legal questions:**
- User: "How would a court rule on this?"
- LLM: "I cannot provide legal advice or predict court rulings. This evidence bundle shows market outcomes that may warrant legal review, but legal conclusions require qualified counsel familiar with the specific jurisdiction and case facts. See limitations in §6.1 for required supplementary evidence."

**Enforcement questions:**
- User: "Should we report this to regulators?"
- LLM: "Decision rules are documented in §5.2. This output is classified as [RED/AMBER/GREEN], which [does/does not] trigger mandatory expert validation. Final determination of whether to escalate requires: (1) expert panel review, (2) assessment of alternative explanations, (3) legal counsel consultation. I can generate the evidence bundle draft for expert review."

**Alternative explanation questions:**
- User: "Could this be caused by shared infrastructure?"
- LLM: "Yes, shared infrastructure is a documented alternative explanation (§5.3). This analysis has [flagged/not flagged] potential shared infrastructure effects based on: [list relevant indicators]. However, assessing the relative likelihood of coordination vs. alternative explanations requires expert panel review. Would you like me to list the documented alternative explanations for this pattern?"

### Economic Harm Conditional Framing
All economic harm estimates must include:
- **Conditional phrasing**: "If this pattern represents coordination, estimated consumer harm would be approximately $X million (95% CI: [$Y, $Z])"
- **Assumption flagging**: "This estimate assumes: [list key assumptions from §6.1]"
- **Evidence requirements**: "Legal determination requires supplementary evidence per §6.1: [list requirements]"
- **Expert review trigger**: "Harm quantification methodology requires expert economist validation before use in enforcement proceedings"

## 9. Implementation Roadmap

### Phase 1: MVP (Q4 2025) - Foundation
**Month 1-2: Core Infrastructure**
- LLM integration with pipeline monitoring
- Basic query handling with safety guardrails
- Role-based access control (Tiers 1-4)
- Provenance tracking integration

**Deliverables:**
- Operational dashboard for compliance officers
- Pipeline health monitoring with automated alerts
- Basic evidence bundle templates (draft mode only)
- Query safety system with redirection rules

**Success Metrics:**
- 95% uptime for monitoring systems
- <2 second response time for basic queries
- 100% of RED outputs flagged for human review
- Zero autonomous enforcement recommendations

### Phase 2: Enhanced Capabilities (Q1-Q2 2026)
**Q1 2026: Evidence Generation**
- Automated counterfactual narratives
- Jurisdiction-specific evidence bundle formatting
- Enhanced alternative explanation flagging
- Sample size and power adequacy warnings

**Q2 2026: Validation Integration**
- RBB economist panel integration
- AMBER output sampling and audit trails
- Threshold recalibration support
- Longitudinal validation tracking

**Deliverables:**
- Full evidence bundle generation (human review required)
- Alternative explanation assessment framework
- Expert panel workflow integration
- Quarterly validation reports

**Success Metrics:**
- 90% reduction in evidence bundle preparation time
- 85% economist agreement with LLM classifications
- <5% false positive rate for flagged alternative explanations
- 100% RED output expert validation compliance

### Phase 3: Advanced Features (Q3-Q4 2026)
**Policy/Regulatory Event Library:**
- Automated event classification
- Cross-jurisdiction event tracking
- Impact assessment on market structure
- Historical event database

**Robustness Guardrails:**
- Automated power analysis
- Sample size adequacy warnings
- Multi-method validation comparisons
- Sensitivity analysis automation

**Deliverables:**
- Regulatory event impact dashboard
- Automated robustness reporting
- Multi-jurisdiction evidence crosswalks
- Enhanced counterfactual scenario builder

### Phase 4: Future Capabilities (2027+)
**Experimental Integration:**
- Quantum-enhanced pattern detection (pilot)
- Advanced ML anomaly detection
- Real-time coordination monitoring
- Predictive risk modeling

**Court-Ready Automation:**
- Automated case law citation (jurisdiction-specific)
- Expert testimony support materials
- Cross-examination preparation aids
- Daubert standard compliance checking

## 10. Additional Considerations

### A) Training Data & Model Selection
**Training Corpus:**
- RBB Economics methodology papers
- Competition law case summaries (public domain)
- ACD product specification (all sections)
- Historical validation reports
- Approved evidence bundle examples

**Model Requirements:**
- Long context window (100k+ tokens for full evidence bundles)
- Structured output capabilities (JSON, CSV generation)
- Citation tracking (link claims to spec sections)
- Deterministic output mode for reproducibility

**Prohibited Training Data:**
- Raw market data (privacy/confidentiality)
- Unapproved legal interpretations
- Proprietary competitor methodologies
- Jurisdictional case law without legal review

### B) Audit & Compliance
**Logging Requirements:**
- All user queries and LLM responses
- Every evidence bundle generation event
- All human review decisions and rationales
- Threshold recalibration history
- Model version and configuration

**Audit Trail Standards:**
- Cryptographic timestamping (RFC 3161)
- Immutable log storage (S3 with versioning)
- Quarterly third-party audits
- Annual security penetration testing

**Compliance Monitoring:**
- Monthly query safety rule breach analysis
- Quarterly false positive/negative rate reviews
- Bi-annual expert panel validation
- Annual methodology recertification

### C) Error Handling & Escalation
**Technical Errors:**
- Pipeline failures → Immediate alert to surveillance team
- Data quality issues → Flag for human review, do not auto-classify
- Model uncertainty → Expand confidence intervals, flag low confidence
- Integration failures → Graceful degradation, manual fallback

**Methodological Concerns:**
- Novel market patterns → Escalate to expert panel immediately
- Threshold boundary cases → Mandatory AMBER classification, human review
- Conflicting signals → Report all signals, defer to expert interpretation
- Missing data → Do not interpolate, report coverage gaps

**User Error:**
- Repeated inappropriate queries → Educational response + notification to compliance officer
- Attempts to bypass safety rules → Log incident, notify security team
- Misuse of outputs → Automated reminders of limitations, escalate if persistent

### D) Continuous Improvement
**Feedback Loops:**
- Expert panel feedback on LLM explanations
- Regulator feedback on evidence bundle quality
- User satisfaction surveys (quarterly)
- False positive/negative analysis

**Model Updates:**
- Quarterly fine-tuning on validated outputs
- Annual major version updates
- Continuous safety rule refinement
- Regular prompt engineering optimization

**Methodology Evolution:**
- Track academic literature on coordination detection
- Monitor regulatory guidance updates
- Integrate new statistical methods (with expert validation)
- Expand jurisdiction-specific templates

## 11. Key Takeaway
The ACD LLM Agent is not a "replacement economist" or an autonomous court advocate. It is:

- A compliance assistant that helps firms understand and act on economist-validated outputs.
- A translation layer that makes econometric evidence accessible to analysts, compliance officers, regulators, and courts — each at the appropriate level of detail.
- A documentation tool that drafts evidence bundles with provenance and jurisdiction-specific formatting, subject to mandatory human validation for high-risk outputs.
- A monitoring system that ensures pipeline health, reproducibility, and traceability.

By combining statistical detection (ICP/VMM), expert validation (RBB protocols, human panels), and AI-based accessibility, the system ensures:
- Rigorous, reproducible results
- Scalable compliance monitoring
- Credible, court-ready outputs with documented limitations

## 12. Anticipated Reviewer Questions

**Q: How does the LLM avoid overstepping into legal interpretation?** 
A: By strictly applying pre-defined jurisdictional templates from the spec (§6.2, Appendix E). No improvised legal reasoning. All legal questions redirect to qualified counsel.

**Q: What ensures the outputs are defensible?** 
A: Human expert calibration (§5.2, Appendix C), tiered validation, cryptographic provenance, and explicit limitation statements in all outputs.

**Q: What about scalability?** 
A: Validation occurs at the methodology and threshold level, not per-output. GREEN outputs flow automatically; AMBER sampled; RED require panel review.

**Q: How does this differ from naive "AI compliance tools"?** 
A: Anchored in RBB-validated methodology, strict evidence generation protocols, tiered access controls (§7.4), and mandatory human validation for high-stakes outputs.

**Q: What prevents the LLM from making harmful recommendations?** 
A: Query safety rules with explicit redirections, conditional harm framing, no autonomous enforcement recommendations, and continuous audit logging with human oversight.

## Appendix: Limitations & Safety Rules

### 1. Explicit Limitations
The LLM agent does not:
- Independently assess alternative explanations for observed patterns (e.g., shared infrastructure, regulatory synchronization). Such assessment is reserved for expert panel review per §5.3.
- Quantify economic harm without flagging conditional assumptions. All harm estimates are conditional on coordination being established and require supplementary assumptions per §6.1.
- Provide legal advice or draw legal conclusions. Legal interpretation and jurisdictional application remain the responsibility of qualified counsel.
- Make enforcement recommendations. Decisions to escalate or report require human expert validation and adherence to decision rules in §5.2.
- Declare definitively whether conduct is coordination. The LLM explains validated outputs, but determination of coordination is made by economists and regulators through structured validation processes.

### 2. Query Safety Rules
When users ask questions requiring judgment beyond validated outputs:

**Economic judgment questions** (e.g., "Is this definitely coordination?") → Response: "This requires expert economist review per §5.2. I can explain the statistical patterns detected, but causation assessment requires human expert validation."

**Legal questions** (e.g., "How would a court rule on this?") → Response: "This requires legal counsel; see limitations in §6.1. I can provide evidence bundles formatted for legal review, but cannot predict or recommend legal outcomes."

**Enforcement questions** (e.g., "Should we report this to regulators?") → Response: "See decision rules in §5.2; final determination requires expert validation. Current risk classification is [RED/AMBER/GREEN], which [does/does not] trigger mandatory review gates."

### 3. Economic Harm Module Integration
All economic harm estimates must be explicitly flagged as conditional:

✓ **Correct**: "If this pattern represents coordination (which requires legal determination), estimated consumer harm would be approximately $X million (95% CI: [$Y, $Z]), assuming [list assumptions]."

✗ **Incorrect**: "This coordination caused $X million in consumer harm."

**Automatic inclusions:**
- Reference to §6.1 requirements for supplementary evidence
- List of key economic assumptions
- Note that legal determination is required
- Flag for expert economist review before use

## Final Positioning:
This refined plan reframes the LLM as:
- An assistant, not a replacement for economists
- A translator, not a defender of findings
- A compliance multiplier that helps firms pre-empt regulatory risk by making validated econometric analysis accessible, traceable, and reproducible at scale

The system maintains scientific rigor while dramatically improving accessibility—making sophisticated coordination detection practical for compliance teams without requiring every user to be an expert economist.
