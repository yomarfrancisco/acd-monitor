# UI API Mocking Documentation

## Overview
This document explains the mock API system for the ACD Monitor dashboard. The system provides simulated data via Next.js API routes to enable frontend development and testing without requiring a full backend implementation.

## Schema & Contracts

### Risk Summary Contract
**Endpoint:** `/api/risk/summary`  
**Method:** GET  
**Query Parameters:**
- `timeframe` (optional): `'30d'|'6m'|'1y'|'ytd'` (default: `'30d'`)
- `mode` (optional): `'normal'|'degraded'` (default: `'normal'`)

**Response Schema:**
```typescript
interface RiskSummary {
  score: number;           // 0–100
  band: RiskBand;          // LOW | AMBER | RED
  confidence: number;      // 0–100 (%)
  updatedAt: string;       // ISO timestamp
  timeframe: '30d'|'6m'|'1y'|'ytd';
  source: { 
    name: string; 
    freshnessSec: number; 
    quality: number;       // 0–1
  };
}
```

## Example Payloads

### Normal Mode (timeframe=30d)
```json
{
  "score": 14,
  "band": "LOW",
  "confidence": 96,
  "updatedAt": "2025-01-27T10:30:00.000Z",
  "timeframe": "30d",
  "source": {
    "name": "Simulated: Internal Monitoring",
    "freshnessSec": 20,
    "quality": 0.96
  }
}
```

### Degraded Mode (timeframe=30d&mode=degraded)
```json
{
  "score": 58,
  "band": "AMBER",
  "confidence": 78,
  "updatedAt": "2025-01-27T10:30:00.000Z",
  "timeframe": "30d",
  "source": {
    "name": "Simulated: Internal Monitoring",
    "freshnessSec": 1800,
    "quality": 0.78
  }
}
```

## Data Behavior

### Deterministic Jitter
The mock system uses a deterministic pseudo-random function based on time to create "live-ish" data that feels realistic but is reproducible for testing:

- **Base values** are modified by a sine wave function
- **Jitter range** varies by data type (score: ±8, confidence: ±4)
- **Time-based** using `Date.now()/60000` for minute-level variation

### Mode Variations
- **Normal Mode:** Low risk scores (14±8), high confidence (96±4), fresh data (20s)
- **Degraded Mode:** Higher risk scores (58±20), lower confidence (78±10), stale data (30min)

### Band Calculation
Risk bands are calculated based on score ranges:
- **LOW:** 0-33
- **AMBER:** 34-66  
- **RED:** 67-100

## Running Mock Mode

### Development Server
```bash
# From ui/cursor-dashboard/
npm run dev
# Server runs on http://localhost:3004
```

### Testing Endpoints
```bash
# Risk Summary
curl "http://localhost:3004/api/risk/summary?timeframe=30d"
curl "http://localhost:3004/api/risk/summary?timeframe=30d&mode=degraded"

# Metrics Overview
curl "http://localhost:3004/api/metrics/overview?timeframe=30d"
curl "http://localhost:3004/api/metrics/overview?timeframe=6m&mode=degraded"

# Health Run
curl "http://localhost:3004/api/health/run"
curl "http://localhost:3004/api/health/run?mode=degraded"

# Events
curl "http://localhost:3004/api/events?timeframe=30d"
curl "http://localhost:3004/api/events?timeframe=ytd"

# Data Sources Status
curl "http://localhost:3004/api/datasources/status"
curl "http://localhost:3004/api/datasources/status?mode=degraded"

# Evidence Export
curl "http://localhost:3004/api/evidence/export"
curl "http://localhost:3004/api/evidence/export?mode=queued"
```

## Validation

### Zod Schema Validation
All API responses are validated using Zod schemas defined in `types/api.schemas.ts`:

```typescript
import { RiskSummarySchema } from '@/types/api.schemas';

const response = await fetch('/api/risk/summary');
const json = await response.json();
const validated = RiskSummarySchema.parse(json);
```

### Error Handling
- **Schema validation errors** are caught and logged
- **Network errors** are handled with retry logic
- **Degraded mode** simulates real-world data quality issues

## Additional Endpoints

### Metrics Overview Contract
**Endpoint:** `/api/metrics/overview`  
**Method:** GET  
**Query Parameters:**
- `timeframe` (optional): `'30d'|'6m'|'1y'|'ytd'` (default: `'30d'`)
- `mode` (optional): `'normal'|'degraded'` (default: `'normal'`)

**Response Schema:**
```typescript
interface MetricsOverview {
  timeframe: '30d'|'6m'|'1y'|'ytd';
  updatedAt: string;
  items: Array<{
    key: 'stability'|'synchronization'|'environmentalSensitivity';
    label: string;
    score: number; // 0-100
    direction: 'UP'|'DOWN'|'FLAT';
    note?: string;
  }>;
}
```

**Example Response:**
```json
{
  "timeframe": "30d",
  "updatedAt": "2025-09-09T00:05:08.273Z",
  "items": [
    {
      "key": "stability",
      "label": "Price Stability",
      "score": 66,
      "direction": "DOWN",
      "note": "Normal spread volatility"
    },
    {
      "key": "synchronization",
      "label": "Price Synchronization",
      "score": 19,
      "direction": "UP",
      "note": "Movements mostly independent"
    },
    {
      "key": "environmentalSensitivity",
      "label": "Environmental Sensitivity",
      "score": 83,
      "direction": "FLAT",
      "note": "Strong adaptation to shocks"
    }
  ]
}
```

### Health Run Contract
**Endpoint:** `/api/health/run`  
**Method:** GET  
**Query Parameters:**
- `mode` (optional): `'normal'|'degraded'` (default: `'normal'`)

**Response Schema:**
```typescript
interface HealthRun {
  updatedAt: string;
  summary: {
    systemHealth: number; // 0-100
    complianceReadiness: number; // 0-100
    band: 'PASS'|'WATCH'|'FAIL';
  };
  spark: Array<{
    ts: string;
    convergence: number;
    dataIntegrity: number;
    evidenceChain: number;
    runtimeStability: number;
  }>;
  source: {
    name: string;
    freshnessSec: number;
    quality: number; // 0-1
  };
}
```

### Events Contract
**Endpoint:** `/api/events`  
**Method:** GET  
**Query Parameters:**
- `timeframe` (optional): `'30d'|'6m'|'1y'|'ytd'` (default: `'30d'`)

**Response Schema:**
```typescript
interface EventsResponse {
  timeframe: '30d'|'6m'|'1y'|'ytd';
  updatedAt: string;
  items: Array<{
    id: string;
    ts: string;
    type: 'MARKET'|'COORDINATION'|'INFO_FLOW'|'REGIME_SWITCH'|'USER';
    title: string;
    description: string;
    severity: 'LOW'|'MEDIUM'|'HIGH';
    riskScore: number; // 0-100
    durationMin?: number;
    affects?: string[];
  }>;
}
```

### Data Sources Status Contract
**Endpoint:** `/api/datasources/status`  
**Method:** GET  
**Query Parameters:**
- `mode` (optional): `'normal'|'degraded'` (default: `'normal'`)

**Response Schema:**
```typescript
interface DataSources {
  updatedAt: string;
  items: Array<{
    id: string;
    name: string;
    tier: 'T1'|'T2'|'T3'|'T4';
    status: 'OK'|'DEGRADED'|'DOWN';
    freshnessSec: number;
    quality: number; // 0-1
  }>;
}
```

### Evidence Export Contract
**Endpoint:** `/api/evidence/export`  
**Method:** GET/POST  
**Query Parameters:**
- `mode` (optional): `'ready'|'queued'` (default: `'ready'`)

**Response Schema:**
```typescript
interface EvidenceExport {
  requestedAt: string;
  status: 'READY'|'QUEUED';
  url?: string; // present when READY
  bundleId: string;
  estSeconds?: number; // present when QUEUED
}
```

## Integration Notes

- **UI Components** fetch data using the same contracts as the real backend
- **Timeframe changes** propagate to all dependent API calls
- **Loading states** are handled with skeleton components
- **Error states** include retry mechanisms and user feedback
