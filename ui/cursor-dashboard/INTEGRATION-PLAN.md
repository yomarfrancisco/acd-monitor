# ACD Monitor UI ⇄ Backend Integration Plan

## Overview
This document outlines the phased approach to connect the existing UI to the backend VMM engine and monitoring system.

## Phase A: Stub Wiring (2 weeks)
**Goal:** Replace hardcoded data with API endpoints using mock data

### Endpoints to Implement

#### 1. Overview Page APIs
```typescript
// Risk Assessment
GET /api/v1/overview/risk-assessment
Response: {
  riskScore: 14,
  riskBand: "LOW",
  confidence: 95,
  updatedAt: "2025-09-08T19:30:00Z",
  dataSource: "Bloomberg Terminal",
  isLive: true
}

// Key Metrics
GET /api/v1/overview/metrics
Response: {
  priceStability: 65,
  priceSynchronization: 18,
  environmentalSensitivity: 82,
  lastUpdated: "2025-09-08T19:30:00Z"
}

// Chart Data
GET /api/v1/overview/chart?timeframe=YTD
Response: {
  timeframe: "YTD",
  data: [
    { date: "Jan '25", fnb: 100, absa: 95, standard: 105, nedbank: 98 },
    // ... more data points
  ],
  dataSource: "Bloomberg Terminal"
}
```

#### 2. Health Checks APIs
```typescript
// System Integrity
GET /api/v1/health/system-integrity
Response: {
  convergenceRate: 25,
  dataIntegrity: 18,
  evidenceChain: 82,
  runtimeStability: 81,
  overallStatus: "PASS",
  lastUpdated: "2025-09-08T19:30:00Z",
  dataSource: "Internal Monitoring"
}
```

#### 3. Events Log APIs
```typescript
// Get Events
GET /api/v1/events?limit=10&offset=0
Response: [
  {
    id: "evt_001",
    title: "ZAR depreciates 1.9%",
    description: "Broad CDS widening; sensitivity ↑ to 84",
    riskScore: 66,
    riskStatus: "AMBER",
    timestamp: "2025-09-08T19:28:00Z",
    duration: "45s",
    eventType: "MARKET",
    icon: "CalendarCheck2"
  }
  // ... more events
]

// Create Event
POST /api/v1/events
Request: {
  title: "User reported event",
  description: "Custom event description",
  eventType: "USER"
}
```

#### 4. Configuration APIs
```typescript
// Get Configuration
GET /api/v1/configuration
Response: {
  autoDetectMarketChanges: true,
  priceChangeThreshold: 5,
  confidenceLevel: 95,
  updateFrequency: "5m",
  sensitivityLevel: "Medium",
  maxDataAge: "10m",
  enableLiveMonitoring: true,
  checkDataQuality: true,
  bloombergDataFeed: false
}

// Update Configuration
PUT /api/v1/configuration
Request: {
  priceChangeThreshold: 10,
  confidenceLevel: 90
}
```

#### 5. Data Sources APIs
```typescript
// Get Data Sources
GET /api/v1/data-sources
Response: [
  {
    id: "bloomberg",
    name: "Bloomberg Terminal",
    type: "API",
    status: "CONNECTED",
    lastUpdate: "2025-09-08T19:30:00Z",
    dataQuality: 98
  }
]
```

#### 6. AI Agents APIs
```typescript
// Get Agents
GET /api/v1/agents
Response: [
  {
    id: "general",
    name: "General Analysis",
    type: "ECONOMIST",
    accuracy: 94.2,
    responseTime: "1.2s",
    status: "AVAILABLE"
  }
]

// Get Quick Analysis Options
GET /api/v1/agents/quick-analysis
Response: [
  {
    id: "analyze_patterns",
    title: "Analyze pricing patterns",
    description: "Identify trends and anomalies in market data",
    icon: "Zap"
  }
]
```

#### 7. Billing APIs
```typescript
// Get Billing Info
GET /api/v1/billing/current
Response: {
  currentPeriod: "September 2025",
  amount: 0,
  usage: 0,
  limit: 6000,
  currency: "USD",
  nextBillingDate: "2025-10-01T00:00:00Z"
}
```

#### 8. Compliance Reports APIs
```typescript
// Get Reports
GET /api/v1/compliance/reports
Response: [
  {
    id: "monthly_2025_09",
    title: "Monthly Compliance Report",
    description: "Healthy: 3 instances of competitive adaptation to regime breaks",
    type: "MONTHLY",
    status: "READY",
    createdAt: "2025-09-08T19:30:00Z",
    downloadUrl: "/api/v1/compliance/reports/monthly_2025_09/download"
  }
]
```

### Implementation Tasks
1. Create Next.js API routes in `app/api/v1/`
2. Replace hardcoded data with API calls in UI components
3. Add loading states and error handling
4. Implement basic data persistence (localStorage for now)

## Phase B: Backend Adapter (3 weeks)
**Goal:** Connect APIs to actual VMM engine and monitoring system

### Backend Integration Points

#### 1. VMM Engine Integration
```python
# src/acd/vmm/engine.py → API endpoints
from src.acd.vmm.engine import VMMEngine, VMMOutput

def get_risk_assessment():
    vmm_output = VMMEngine.process_latest_window()
    return {
        "riskScore": int(vmm_output.regime_confidence * 100),
        "riskBand": classify_risk_band(vmm_output.regime_confidence),
        "confidence": int(vmm_output.dynamic_validation_score * 100),
        "updatedAt": datetime.utcnow().isoformat(),
        "dataSource": "VMM Engine",
        "isLive": True
    }
```

#### 2. Monitoring System Integration
```python
# src/acd/monitoring/health_check.py → API endpoints
from src.acd.monitoring.health_check import HealthChecker

def get_system_integrity():
    health_result = HealthChecker.run_health_checks()
    return {
        "convergenceRate": health_result.gates[0].value,
        "dataIntegrity": health_result.gates[1].value,
        "evidenceChain": health_result.gates[2].value,
        "runtimeStability": health_result.gates[3].value,
        "overallStatus": health_result.overall_status.value,
        "lastUpdated": datetime.utcnow().isoformat(),
        "dataSource": "Internal Monitoring"
    }
```

#### 3. Data Pipeline Integration
```python
# src/acd/data/ingest.py → Chart data
from src.acd.data.ingest import DataIngester

def get_chart_data(timeframe: str):
    data = DataIngester.get_timeframe_data(timeframe)
    return {
        "timeframe": timeframe,
        "data": format_chart_data(data),
        "dataSource": "Bloomberg Terminal"
    }
```

### Implementation Tasks
1. Create FastAPI backend service
2. Implement data adapters between UI APIs and VMM engine
3. Add database integration for persistence
4. Implement real-time data processing
5. Add error handling and logging

## Phase C: Live Integration (2 weeks)
**Goal:** Real-time updates and production-ready features

### WebSocket/SSE Implementation
```typescript
// Real-time updates
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'risk_update':
      updateRiskAssessment(data.data);
      break;
    case 'system_health_update':
      updateSystemIntegrity(data.data);
      break;
    case 'new_event':
      addNewEvent(data.data);
      break;
  }
};
```

### Export Evidence Package
```typescript
// Evidence export
POST /api/v1/evidence/export
Response: {
  bundleId: "evt_20250908_193000",
  downloadUrl: "/api/v1/evidence/export/evt_20250908_193000",
  expiresAt: "2025-09-15T19:30:00Z"
}
```

### Implementation Tasks
1. Implement WebSocket server for real-time updates
2. Add evidence package generation
3. Implement file download endpoints
4. Add authentication and authorization
5. Performance optimization and caching

## Technical Architecture

### Frontend (Next.js)
```
ui/cursor-dashboard/
├── app/
│   ├── api/v1/           # API routes
│   ├── page.tsx          # Main dashboard
│   └── globals.css       # Styles
├── components/
│   └── ui/               # UI components
├── types/
│   └── api.ts            # TypeScript interfaces
└── lib/
    └── api.ts            # API client
```

### Backend (FastAPI)
```
src/
├── acd/
│   ├── vmm/              # VMM engine
│   ├── monitoring/       # Health checks
│   └── data/             # Data pipeline
├── backend/
│   ├── api/              # FastAPI routes
│   ├── models/           # Data models
│   └── services/         # Business logic
└── tests/                # Test suite
```

## Success Metrics

### Phase A (Stub Wiring)
- ✅ All hardcoded data replaced with API calls
- ✅ Loading states implemented
- ✅ Basic error handling added
- ✅ Configuration persistence working

### Phase B (Backend Adapter)
- ✅ Real VMM engine outputs connected
- ✅ Health check system integrated
- ✅ Data pipeline working
- ✅ Database persistence implemented

### Phase C (Live Integration)
- ✅ Real-time updates working
- ✅ Evidence package export functional
- ✅ Authentication implemented
- ✅ Performance optimized

## Risk Mitigation

### Technical Risks
1. **VMM Engine Integration Complexity**
   - Mitigation: Start with simple data adapters, iterate
   - Fallback: Use mock data until engine is stable

2. **Real-time Performance**
   - Mitigation: Implement efficient WebSocket handling
   - Fallback: Use polling if WebSocket issues

3. **Data Consistency**
   - Mitigation: Implement proper error handling and retry logic
   - Fallback: Cache last known good state

### Timeline Risks
1. **Backend Integration Delays**
   - Mitigation: Parallel development of stub and real APIs
   - Fallback: Extended Phase A with more mock data

2. **VMM Engine Stability**
   - Mitigation: Thorough testing with golden datasets
   - Fallback: Use simplified risk scoring initially

## Conclusion

This phased approach allows for incremental progress while maintaining a working UI throughout the integration process. Phase A provides immediate value by making the UI functional, Phase B connects to real data, and Phase C adds production-ready features.
