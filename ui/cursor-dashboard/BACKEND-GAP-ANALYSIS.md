# Backend Gap Analysis: Existing vs Required

## Overview
Analysis of existing backend capabilities vs UI requirements for ACD Monitor integration.

## Existing Backend Capabilities

### ✅ VMM Engine (src/acd/vmm/)
**Status:** Fully Implemented
**Files:**
- `engine.py` - Main VMM orchestration with VMMOutput class
- `metrics.py` - VMMMetrics with regime_confidence, structural_stability, environment_quality, dynamic_validation_score
- `moments.py` - Moment conditions and targets
- `updates.py` - Variational updates and parameters
- `profiles.py` - VMM configuration
- `adaptive_thresholds.py` - Adaptive threshold management

**Outputs Available:**
```python
@dataclass
class VMMOutput:
    regime_confidence: float  # ∈ [0,1] - coordination-like vs competitive-like
    structural_stability: float  # ∈ [0,1] - higher = more invariant
    environment_quality: float  # ∈ [0,1] - data/context quality proxy
    dynamic_validation_score: float  # ∈ [0,1] - self-consistency + predictive checks
    window_size: int
    convergence_status: str
    iterations: int
    elbo_final: float
```

### ✅ Monitoring System (src/acd/monitoring/)
**Status:** Fully Implemented
**Files:**
- `health_check.py` - HealthChecker with HealthCheckResult
- `metrics.py` - RunMetrics with comprehensive system metrics
- `regression_detector.py` - Regression detection capabilities

**Outputs Available:**
```python
@dataclass
class HealthCheckResult:
    overall_status: HealthStatus  # PASS/WARN/FAIL
    gates: List[HealthGate]
    summary: str
    recommendations: List[str]

@dataclass
class RunMetrics:
    spurious_regime_rate: float
    auroc: float
    f1: float
    structural_stability_median: float
    vmm_convergence_rate: float
    runtime_p50: float
    runtime_p95: float
    timestamp_success_rate: float
    quality_overall: float
    schema_validation_pass_rate: float
    bundle_export_success_rate: float
```

### ✅ Data Pipeline (src/acd/data/)
**Status:** Implemented
**Files:**
- `ingest.py` - Data ingestion capabilities
- `quality.py` - Data quality assessment
- `features.py` - Feature engineering
- `quality_profiles.py` - Quality profile management

### ✅ Evidence System (src/acd/evidence/)
**Status:** Implemented
**Files:**
- `bundle.py` - Evidence bundle generation
- `export.py` - Export capabilities
- `timestamping.py` - RFC 3161 timestamping

### ⚠️ Backend API (src/backend/)
**Status:** Basic Implementation
**Files:**
- `main.py` - Basic FastAPI app with CORS
- `models.py` - Basic Pydantic models
- `analytics.py` - Analytics functions

**Current Endpoints:**
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /cases/{case_id}/summary` - Risk summary (TODO implementation)

## Required UI Integration Points

### 1. Overview Page APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/overview/risk-assessment`
- `GET /api/v1/overview/metrics`
- `GET /api/v1/overview/chart?timeframe={timeframe}`

**Backend Mapping:**
- Risk Assessment → VMMOutput.regime_confidence
- Metrics → VMMOutput components
- Chart Data → Data pipeline outputs

**Effort:** Medium (2-3 days)
**Gap:** Need API endpoints that consume VMM engine outputs

### 2. Health Checks APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/health/system-integrity`

**Backend Mapping:**
- System Integrity → HealthCheckResult + RunMetrics

**Effort:** Small (1 day)
**Gap:** Need API endpoint that consumes health check outputs

### 3. Events Log APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/events`
- `POST /api/v1/events`

**Backend Mapping:**
- Events → Need event storage and retrieval system

**Effort:** Medium (3-4 days)
**Gap:** Need event management system

### 4. Configuration APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/configuration`
- `PUT /api/v1/configuration`

**Backend Mapping:**
- Configuration → Need configuration storage

**Effort:** Small (1-2 days)
**Gap:** Need configuration management system

### 5. Data Sources APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/data-sources`

**Backend Mapping:**
- Data Sources → Data pipeline status

**Effort:** Small (1 day)
**Gap:** Need data source status endpoint

### 6. AI Agents APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/agents`
- `GET /api/v1/agents/quick-analysis`

**Backend Mapping:**
- AI Agents → Need agent management system

**Effort:** Medium (2-3 days)
**Gap:** Need agent management system

### 7. Billing APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/billing/current`

**Backend Mapping:**
- Billing → Need billing system

**Effort:** Small (1 day)
**Gap:** Need basic billing tracking

### 8. Compliance Reports APIs
**Status:** ❌ Missing
**Required Endpoints:**
- `GET /api/v1/compliance/reports`
- `POST /api/v1/compliance/reports/generate`

**Backend Mapping:**
- Reports → Evidence bundle system

**Effort:** Medium (2-3 days)
**Gap:** Need report generation system

## Missing Backend Components

### 1. Database Layer
**Status:** ❌ Missing
**Required:**
- Configuration storage
- Event storage
- User session management
- Audit trail storage

**Effort:** Large (1 week)
**Priority:** High

### 2. Real-time Updates
**Status:** ❌ Missing
**Required:**
- WebSocket server
- Event broadcasting
- Real-time data streaming

**Effort:** Medium (3-4 days)
**Priority:** High

### 3. Authentication & Authorization
**Status:** ❌ Missing
**Required:**
- User authentication
- API key management
- Role-based access control

**Effort:** Medium (2-3 days)
**Priority:** Medium

### 4. File Storage
**Status:** ❌ Missing
**Required:**
- Evidence package storage
- Report file storage
- Export file management

**Effort:** Small (1-2 days)
**Priority:** Medium

## Effort Sizing Summary

### Small Effort (1-2 days each)
- Configuration APIs
- Data Sources APIs
- Billing APIs
- File Storage

### Medium Effort (2-4 days each)
- Overview Page APIs
- Events Log APIs
- AI Agents APIs
- Compliance Reports APIs
- Real-time Updates
- Authentication

### Large Effort (1 week)
- Database Layer

## Implementation Priority

### Phase 1 (Week 1-2): Core Functionality
1. **Database Layer** (Large) - Foundation for everything
2. **Overview Page APIs** (Medium) - Core risk assessment
3. **Health Checks APIs** (Small) - System monitoring
4. **Configuration APIs** (Small) - User settings

### Phase 2 (Week 3-4): Extended Features
1. **Events Log APIs** (Medium) - Event management
2. **Data Sources APIs** (Small) - Data pipeline status
3. **Real-time Updates** (Medium) - Live monitoring
4. **File Storage** (Small) - Export capabilities

### Phase 3 (Week 5-6): Advanced Features
1. **AI Agents APIs** (Medium) - Agent management
2. **Compliance Reports APIs** (Medium) - Report generation
3. **Authentication** (Medium) - Security
4. **Billing APIs** (Small) - Usage tracking

## Risk Assessment

### High Risk
- **Database Layer:** Critical foundation, any delays block everything
- **VMM Engine Integration:** Complex integration, may need iteration

### Medium Risk
- **Real-time Updates:** Performance implications, may need optimization
- **Event Management:** Complex state management

### Low Risk
- **Configuration Management:** Straightforward implementation
- **Data Source Status:** Simple status reporting

## Conclusion

**Backend Readiness: 60%**

**Strengths:**
- ✅ VMM engine fully implemented with required outputs
- ✅ Monitoring system complete with health checks
- ✅ Data pipeline and evidence systems ready
- ✅ Basic FastAPI structure in place

**Gaps:**
- ❌ Missing API endpoints for UI integration
- ❌ No database layer for persistence
- ❌ No real-time update system
- ❌ No authentication/authorization

**Total Effort Estimate: 4-6 weeks**
- Phase 1: 2 weeks (core functionality)
- Phase 2: 2 weeks (extended features)
- Phase 3: 2 weeks (advanced features)

**Recommendation:** Start with Phase 1 to get core functionality working, then iterate based on user feedback and requirements.
