# UI Mock Integration Status

## Overview

This document tracks the status of UI mock API integration for the ACD Monitor dashboard. All integrations use mock endpoints that return realistic data for development and testing purposes.

## Integration Status

| Route | Page | Status | Last Commit | Description |
|-------|------|--------|-------------|-------------|
| `/api/health/run` | Health Checks | ✅ Complete | `452031f` | System health metrics, compliance readiness, spark chart data |
| `/api/events` | Events Log | ✅ Complete | `cc2890f` | Event timeline with severity/type filters, risk scores |
| `/api/datasources/status` | Data Sources | ✅ Complete | `65d1fff` | Data source status, tier, freshness, quality metrics |
| `/api/evidence/export` | AI Agents | ✅ Complete | `98df7b2` | Evidence package generation with QUEUED→READY flow |
| `/api/risk/summary` | Overview | ✅ Complete | `18d6559` | Risk summary with confidence bands |
| `/api/metrics/overview` | Overview | ✅ Complete | `18d6559` | Metrics overview with stability indicators |

## Mock API Endpoints

### Health Checks - `/api/health/run`

**Method:** GET  
**Parameters:** `?timeframe=30d|6m|1y|ytd`  
**Response:**
```json
{
  "updatedAt": "2025-09-09T09:17:08Z",
  "summary": {
    "systemHealth": 84,
    "complianceReadiness": 67,
    "band": "PASS"
  },
  "spark": [
    {
      "ts": "2025-09-09T09:00:00Z",
      "convergence": 25,
      "dataIntegrity": 18,
      "evidenceChain": 82,
      "runtimeStability": 81
    }
  ],
  "source": {
    "name": "Simulated: Internal Monitoring",
    "freshnessSec": 24,
    "quality": 0.95
  }
}
```

**Curl Example:**
```bash
curl "http://localhost:3004/api/health/run?timeframe=ytd"
```

### Events - `/api/events`

**Method:** GET  
**Parameters:** `?timeframe=30d|6m|1y|ytd`  
**Response:**
```json
{
  "timeframe": "ytd",
  "updatedAt": "2025-09-09T09:17:08Z",
  "items": [
    {
      "id": "evt-001",
      "ts": "2025-09-09T09:00:00Z",
      "type": "MARKET",
      "title": "ZAR depreciates 1.9%",
      "description": "Broad CDS widening; sensitivity ↑ to 84",
      "severity": "HIGH",
      "riskScore": 66,
      "durationMin": 45,
      "affects": ["FNB", "Absa"]
    }
  ]
}
```

**Curl Example:**
```bash
curl "http://localhost:3004/api/events?timeframe=ytd"
```

### Data Sources - `/api/datasources/status`

**Method:** GET  
**Response:**
```json
{
  "updatedAt": "2025-09-09T09:17:08Z",
  "items": [
    {
      "id": "ds-001",
      "name": "Bloomberg Terminal",
      "tier": "T1",
      "status": "OK",
      "freshnessSec": 30,
      "quality": 0.98
    }
  ]
}
```

**Curl Example:**
```bash
curl "http://localhost:3004/api/datasources/status"
```

### Evidence Export - `/api/evidence/export`

**Method:** POST  
**Body:** `{"mode": "queued"|"ready"}`  
**Response:**
```json
{
  "requestedAt": "2025-09-09T09:17:08Z",
  "status": "QUEUED",
  "bundleId": "mock-20250909-0917",
  "estSeconds": 45
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:3004/api/evidence/export" \
  -H "Content-Type: application/json" \
  -d '{"mode": "queued"}'
```

## How to Run

### Prerequisites
- Node.js 20+
- npm

### Setup
```bash
cd ui/cursor-dashboard
npm install
```

### Development Server
```bash
npm run dev
```
The application will be available at `http://localhost:3004`

### Build
```bash
npm run build
```

### Type Checking
```bash
npx tsc --noEmit
```

## CI Gating

The CI workflow has been configured with path-based job gating:

- **UI Job**: Runs only when `ui/**` files change
- **Backend Job**: Runs only when backend files change (`src/**`, `tests/**`, etc.)

**Verification:**
- UI-only changes trigger: `detect ✅`, `ui ✅`, `backend ⏭ skipped`
- Backend changes trigger: `detect ✅`, `ui ⏭ skipped`, `backend ✅`

## Features Implemented

### Health Checks Page
- ✅ Real-time system health metrics
- ✅ Compliance readiness percentage
- ✅ Interactive spark chart with 4 health metrics
- ✅ Individual health metric tiles with pass/fail indicators
- ✅ Data source indicators
- ✅ Timeframe-aware data fetching

### Events Log Page
- ✅ Event timeline with API data
- ✅ Client-side filtering by severity (HIGH/MEDIUM/LOW)
- ✅ Client-side filtering by type (MARKET/COORDINATION/USER)
- ✅ Functional timeframe tabs (30d/6m/1y/ytd)
- ✅ Loading states and error handling
- ✅ Dynamic pagination counts

### Data Sources Page
- ✅ Data source status display
- ✅ Status pills (OK/DEGRADED/DOWN)
- ✅ Tier, freshness, and quality metrics
- ✅ Loading states and error handling
- ✅ Consistent tile styling

### Evidence Export (AI Agents Page)
- ✅ Generate Evidence Package button
- ✅ QUEUED → READY state transitions
- ✅ Progress indicators and loading spinners
- ✅ Download functionality when ready
- ✅ Automatic status polling

## Technical Implementation

### State Management
- React hooks (`useState`, `useEffect`) for local state
- Timeframe-aware data fetching
- Error handling with retry functionality
- Loading states for better UX

### Type Safety
- Zod schemas for API response validation
- TypeScript interfaces for all data structures
- Strict typing throughout the application

### API Integration
- Shared `fetchJSON` utility in `lib/api.ts`
- Consistent error handling
- Proper HTTP status code handling
- Request/response validation

### UI/UX
- Consistent styling with existing design system
- Loading skeletons and progress indicators
- Error states with retry options
- Responsive design maintained

## Next Steps

1. **Backend Integration**: Replace mock endpoints with real backend APIs
2. **Authentication**: Add user authentication and authorization
3. **Real-time Updates**: Implement WebSocket connections for live data
4. **Advanced Filtering**: Server-side filtering and pagination
5. **Performance**: Add caching and optimization strategies

## Pull Requests

- [PR 1: Health Checks Integration](https://github.com/yomarfrancisco/acd-monitor/pull/new/feat/ui-wire-health-checks)
- [PR 2: Events Integration](https://github.com/yomarfrancisco/acd-monitor/pull/new/feat/ui-wire-events)
- [PR 3: Data Sources Integration](https://github.com/yomarfrancisco/acd-monitor/pull/new/feat/ui-wire-data-sources)
- [PR 4: Evidence Export Integration](https://github.com/yomarfrancisco/acd-monitor/pull/new/feat/ui-wire-evidence-export)

## Verification

All integrations have been verified with:
- ✅ TypeScript compilation (`npx tsc --noEmit`)
- ✅ Next.js build (`npm run build`)
- ✅ CI gating (backend skipped on UI-only changes)
- ✅ No `any` type leaks in API responses
- ✅ Consistent timeframe handling (`'30d' | '6m' | '1y' | 'ytd'`)
