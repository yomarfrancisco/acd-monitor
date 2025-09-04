# Regression Policy (Immutable Anchor)

> **IMMUTABLE**: This document defines the regression classification, reporting, and mitigation requirements for all ACD Monitor development. Once established, these policies cannot be modified without governance approval.

## 🎯 **Purpose**

This policy ensures systematic identification, classification, and resolution of regressions while maintaining the dual pillars of Brief 55+:
- **ICP (Independent Coordination Protocol)**: Market structure analysis integrity
- **VMM (Variational Method of Moments)**: Continuous monitoring reliability

## 🚨 **Regression Classification**

### **Critical Regressions (Immediate Flag + Rollback)**
**Definition**: Regressions that violate core acceptance gates or create system instability

**Examples**:
- VMM engine non-functional or producing invalid outputs
- Spurious regime rate > 5% (competitive datasets)
- ELBO variance > 5% across reproducibility runs
- Runtime > 10s (p95) for standard windows
- Data corruption or loss of validation
- Security vulnerabilities
- Breaking changes to public APIs without migration path

**Response Time**: **Immediate** (within 1 hour)
**Action Required**: Rollback to previous stable release

### **High Priority Regressions (24h Response)**
**Definition**: Regressions that significantly impact performance or accuracy

**Examples**:
- VMM runtime > 5s (p95) but < 10s
- Spurious regime rate 3-5% (competitive datasets)
- Test success rate < 90%
- Code coverage drop > 5%
- Performance degradation > 20%
- Documentation gaps for new features

**Response Time**: **24 hours**
**Action Required**: Mitigation plan with timeline

### **Medium Priority Regressions (7 days Response)**
**Definition**: Regressions that affect quality or user experience

**Examples**:
- VMM runtime 2-5s (p95) but within acceptable range
- Minor accuracy degradation (< 10%)
- Test coverage drop 1-5%
- Documentation formatting issues
- Minor performance impact (5-20%)

**Response Time**: **7 days**
**Action Required**: Documentation and recovery plan

### **Low Priority Regressions (Next Sprint)**
**Definition**: Minor issues that don't impact core functionality

**Examples**:
- Code style violations
- Minor documentation updates
- Non-critical dependency updates
- Performance improvements < 5%

**Response Time**: **Next sprint**
**Action Required**: Track in backlog

## 📋 **Regression Reporting Requirements**

### **Immediate Reporting (Critical/High)**
```markdown
## 🚨 Regression Report

**Severity**: [Critical/High/Medium/Low]
**Component**: [VMM/ICP/Data Pipeline/Infrastructure]
**Anchor Impact**: [Brief 55+/Mission Control/Governance]

**Description**: [Clear description of the regression]
**Impact**: [Business and technical impact assessment]
**Root Cause**: [Technical explanation of what went wrong]
**Timeline**: [When regression was introduced]

**Mitigation Plan**: [Immediate and long-term solutions]
**Acceptance Criteria**: [Clear gates for resolution]
**Owner**: [Person responsible for resolution]
**Target Resolution**: [Timeline for fix]
```

### **Weekly Regression Summary**
```markdown
## 📊 Regression Summary (Week XX)

**Active Regressions**: [Count by priority]
**Resolved This Week**: [Count and details]
**New This Week**: [Count and details]
**Trend**: [Improving/Stable/Deteriorating]

**Critical Issues**: [List with status]
**High Priority**: [List with status]
**Performance Impact**: [Summary of runtime/accuracy changes]
**Next Actions**: [Planned mitigation activities]
```

## 🔍 **Regression Detection Methods**

### **Automated Detection**
- **CI/CD Pipeline**: Test failures, coverage drops, lint errors
- **Performance Monitoring**: Runtime benchmarks, memory usage
- **Quality Gates**: flake8, black, isort compliance
- **Security Scanning**: Dependency vulnerability checks

### **Manual Detection**
- **Code Review**: Regression identification during PR review
- **Testing**: Manual validation of critical paths
- **Documentation Review**: Accuracy and completeness checks
- **User Feedback**: Reported issues and performance complaints

### **Detection Triggers**
- **Test Failure**: Any test that previously passed now fails
- **Performance Regression**: Runtime increase > 10%
- **Coverage Drop**: Test coverage decrease > 1%
- **Quality Issues**: New flake8 errors or warnings
- **Documentation Gaps**: Missing or outdated documentation

## 📝 **Regression Documentation**

### **Required Information**
- **Regression ID**: Unique identifier for tracking
- **Severity Classification**: Critical/High/Medium/Low
- **Component Affected**: Specific module or feature
- **Anchor Impact**: Which governance anchors are affected
- **Business Impact**: User experience and business value impact
- **Technical Details**: Root cause and technical explanation
- **Reproduction Steps**: How to reproduce the regression
- **Mitigation Plan**: Immediate and long-term solutions
- **Acceptance Criteria**: Clear gates for resolution
- **Timeline**: Target resolution date

### **Documentation Location**
- **Critical/High**: GitHub Issues with regression label
- **Medium/Low**: Project backlog with regression tag
- **All Regressions**: Tracked in achievements log
- **Resolution**: Documented in release notes

## 🛠️ **Regression Resolution Process**

### **Immediate Response (Critical)**
1. **Flag**: Immediately notify stakeholders (CEO, CTO, Theo)
2. **Assess**: Quick impact assessment within 30 minutes
3. **Rollback**: Revert to previous stable release if necessary
4. **Communicate**: Update team and stakeholders
5. **Document**: Create detailed regression report

### **Short-term Resolution (High/Medium)**
1. **Plan**: Develop mitigation plan within 24 hours
2. **Implement**: Quick fixes for immediate relief
3. **Test**: Validate fixes don't introduce new regressions
4. **Monitor**: Track resolution progress
5. **Update**: Regular status updates to stakeholders

### **Long-term Resolution (All)**
1. **Root Cause**: Identify underlying causes
2. **Prevention**: Implement measures to prevent recurrence
3. **Monitoring**: Enhanced detection and alerting
4. **Documentation**: Update processes and procedures
5. **Review**: Post-mortem analysis and lessons learned

## 📊 **Regression Metrics and Tracking**

### **Key Performance Indicators**
- **Regression Rate**: New regressions per release
- **Resolution Time**: Time from detection to resolution
- **Recurrence Rate**: Same regression occurring multiple times
- **Impact Severity**: Distribution of regression severities
- **Prevention Effectiveness**: Regressions prevented by new measures

### **Trend Analysis**
- **Weekly Trends**: Regression frequency and severity
- **Release Impact**: Regressions introduced per release
- **Component Analysis**: Which areas are most prone to regressions
- **Root Cause Patterns**: Common causes and prevention strategies
- **Resolution Efficiency**: Time and effort to resolve regressions

## 🔒 **Governance and Compliance**

### **Approval Requirements**
- **Critical Regressions**: CEO + CTO + Theo approval for resolution plan
- **High Priority**: CTO + Theo approval for mitigation approach
- **Medium Priority**: Theo approval for resolution timeline
- **Low Priority**: Team lead approval for backlog prioritization

### **Reporting Requirements**
- **Daily**: Critical regression status updates
- **Weekly**: Regression summary and trend analysis
- **Monthly**: Regression prevention effectiveness review
- **Quarterly**: Policy compliance and improvement recommendations

### **Compliance Checks**
- **All Regressions**: Must be documented and tracked
- **Resolution Plans**: Must include acceptance criteria
- **Post-mortem**: Required for critical and high priority regressions
- **Prevention Measures**: Must be implemented for recurring issues

---

## 📅 **Policy Version**

- **Version**: 1.0
- **Established**: 2024-01-XX
- **Next Review**: Governance committee approval required for changes
- **Owner**: Theo (Senior Econometrician Engineer)

---

> **Note**: This policy is an immutable anchor. Modifications require governance approval and must maintain alignment with Brief 55+ dual pillars.
