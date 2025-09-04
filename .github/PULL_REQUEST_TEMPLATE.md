# Pull Request Template

> **REQUIRED**: This template must be completed for all PRs. Incomplete submissions will be rejected.

## 🎯 **PR Summary**

**Type**: [Feature/Bug Fix/Refactor/Documentation/Infrastructure]
**Component**: [VMM/ICP/Data Pipeline/Infrastructure/Documentation]
**Priority**: [Critical/High/Medium/Low]

**Description**: [Clear, concise description of changes]

## 🔒 **Anchor Alignment Check**

> **REQUIRED**: All changes must align with immutable anchors

### **Brief 55+ Compliance**
- [ ] **ICP Alignment**: Changes support Independent Coordination Protocol analysis
- [ ] **VMM Alignment**: Changes maintain Variational Method of Moments integrity
- [ ] **Dual Pillars**: No divergence from core methodological foundation

### **Mission Control Alignment**
- [ ] **Milestone Compliance**: Changes align with current sprint objectives
- [ ] **Acceptance Gates**: All relevant gates are met or documented
- [ ] **Timeline Adherence**: Changes fit within established development schedule

### **Governance Compliance**
- [ ] **Role Respect**: Changes respect CEO/CTO/Theo role definitions
- [ ] **Decision Rules**: Changes follow established governance procedures
- [ ] **Documentation**: All changes are properly documented

## 📋 **Acceptance Gates Results**

> **REQUIRED**: Document results for all relevant acceptance gates

### **Core Functionality Gates**
- [ ] **VMM Engine**: All tests pass (≥95% success rate)
- [ ] **VMM Calibration**: Spurious regime rate ≤ 5% (competitive datasets)
- [ ] **VMM Stability**: ELBO variance ≤ 5% across reproducibility runs
- [ ] **VMM Performance**: Median runtime ≤ 2s, p95 ≤ 5s for standard windows
- [ ] **Data Pipeline**: Ingestion, quality, and features modules operational
- [ ] **Schema Validation**: All JSON schemas pass validation in CI

### **Quality Assurance Gates**
- [ ] **Code Quality**: flake8 clean (0 errors)
- [ ] **Test Coverage**: ≥90% coverage maintained or improved
- [ ] **Documentation**: All new features documented
- [ ] **Type Hints**: All new code includes proper type annotations
- [ ] **Error Handling**: Comprehensive error handling for new features

### **Integration Gates**
- [ ] **CI/CD Pipeline**: All checks pass (lint, test, coverage)
- [ ] **Dependencies**: No security vulnerabilities in requirements
- [ ] **Performance**: No significant performance regressions
- [ ] **Compatibility**: Backward compatibility maintained where required

## 🚨 **Regression Assessment**

> **REQUIRED**: Document any regressions introduced by this PR

### **Regression Classification**
- [ ] **No Regressions**: All existing functionality maintained
- [ ] **Critical Regression**: Violates core acceptance gates (immediate flag required)
- [ ] **High Priority**: Significant impact on performance or accuracy (24h response)
- [ ] **Medium Priority**: Affects quality or user experience (7 days response)
- [ ] **Low Priority**: Minor issues (next sprint)

### **Regression Details** (if applicable)
```markdown
**Component Affected**: [Specific module or feature]
**Impact Assessment**: [Business and technical impact]
**Root Cause**: [Technical explanation]
**Mitigation Plan**: [Immediate and long-term solutions]
**Acceptance Criteria**: [Clear gates for resolution]
**Timeline**: [Target resolution date]
```

## 📊 **Performance Impact**

> **REQUIRED**: Document performance changes

### **VMM Performance**
- **Runtime Impact**: [Increase/decrease in seconds]
- **Memory Impact**: [Increase/decrease in MB]
- **Accuracy Impact**: [Change in spurious regime rate]
- **Convergence Impact**: [Change in convergence rate]

### **System Performance**
- **CI/CD Impact**: [Build time changes]
- **Test Impact**: [Test execution time changes]
- **Coverage Impact**: [Test coverage changes]

## 📝 **Achievements Update**

> **REQUIRED**: Document new milestones or achievements

### **New Achievements**
- [ ] **Feature Complete**: New functionality fully implemented
- [ ] **Performance Target**: New performance benchmarks achieved
- [ ] **Quality Improvement**: Code quality metrics improved
- [ ] **Documentation**: New documentation or schemas added
- [ ] **Integration**: New components integrated successfully

### **Achievement Evidence**
```markdown
**Milestone**: [Specific achievement]
**Evidence**: [Test results, benchmarks, documentation]
**Acceptance Gates**: [Which gates were met]
**Impact**: [Business value and technical improvement]
```

## 🔍 **Testing and Validation**

### **Test Coverage**
- [ ] **Unit Tests**: All new code has unit tests
- [ ] **Integration Tests**: New features tested in integrated environment
- [ ] **Performance Tests**: Performance benchmarks validated
- [ ] **Regression Tests**: Existing functionality verified

### **Validation Results**
```markdown
**Test Results**: [Pass/Fail counts]
**Coverage**: [Current coverage percentage]
**Performance**: [Benchmark results]
**Quality**: [Linting and style check results]
```

## 📚 **Documentation Updates**

### **Required Documentation**
- [ ] **Code Documentation**: Inline comments and docstrings updated
- [ ] **API Documentation**: Public interfaces documented
- [ ] **User Documentation**: User-facing changes documented
- [ ] **Schema Updates**: Data schemas updated if changed
- [ ] **Release Notes**: Changes documented for release

### **Documentation Quality**
- [ ] **Accuracy**: All documentation is current and accurate
- [ ] **Completeness**: All new features are documented
- [ ] **Clarity**: Documentation is clear and understandable
- [ ] **Examples**: Examples provided for complex features

## 🚀 **Deployment and Rollback**

### **Deployment Plan**
- [ ] **Environment**: Target deployment environment identified
- [ ] **Dependencies**: All dependencies documented and available
- [ ] **Configuration**: Required configuration changes documented
- [ ] **Monitoring**: Monitoring and alerting configured

### **Rollback Plan**
- [ ] **Rollback Trigger**: Clear criteria for rollback identified
- [ ] **Rollback Process**: Step-by-step rollback procedure documented
- [ ] **Data Safety**: Data integrity during rollback ensured
- [ ] **Communication**: Rollback communication plan prepared

## 🔒 **Security and Compliance**

### **Security Assessment**
- [ ] **Vulnerability Scan**: No new security vulnerabilities introduced
- [ ] **Access Control**: Proper access controls implemented
- [ ] **Data Protection**: Sensitive data properly protected
- [ ] **Audit Trail**: Changes are auditable and traceable

### **Compliance Check**
- [ ] **Regulatory**: All regulatory requirements met
- [ ] **Internal**: Internal policies and procedures followed
- [ ] **Documentation**: Compliance documentation updated
- [ ] **Training**: Team training updated if needed

## 📋 **Checklist Completion**

### **Pre-Submission Checklist**
- [ ] **Code Review**: Code reviewed by at least one team member
- [ ] **Testing**: All tests pass locally and in CI
- [ ] **Documentation**: All required documentation updated
- [ ] **Performance**: Performance impact assessed and documented
- [ ] **Security**: Security implications reviewed
- [ ] **Compliance**: All compliance requirements met

### **Submission Checklist**
- [ ] **Template Complete**: All sections of this template completed
- [ ] **Evidence Attached**: Supporting evidence and test results included
- [ ] **Stakeholders Notified**: Relevant stakeholders notified of changes
- [ ] **Timeline Realistic**: Proposed timeline is achievable
- [ ] **Resources Identified**: Required resources and dependencies identified

---

## 📅 **PR Information**

- **Created**: [Date]
- **Author**: [Name]
- **Reviewers**: [Names]
- **Target Branch**: [Branch name]
- **Estimated Merge**: [Date]

---

> **Note**: This template ensures all PRs maintain anchor fidelity and governance compliance. Incomplete submissions will be rejected.
