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
```

### Testing Endpoints
```bash
# Normal mode
curl http://localhost:3000/api/risk/summary?timeframe=30d

# Degraded mode
curl http://localhost:3000/api/risk/summary?timeframe=30d&mode=degraded

# Different timeframes
curl http://localhost:3000/api/risk/summary?timeframe=6m
curl http://localhost:3000/api/risk/summary?timeframe=1y
curl http://localhost:3000/api/risk/summary?timeframe=ytd
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

## Future Endpoints

This mock system will be extended to include:
- `/api/metrics/overview` - Stability, synchronization, environmental sensitivity
- `/api/health/run` - System integrity metrics
- `/api/events` - Event timeline and filtering
- `/api/datasources/status` - Data source status and quality
- `/api/evidence/export` - Evidence package generation

## Integration Notes

- **UI Components** fetch data using the same contracts as the real backend
- **Timeframe changes** propagate to all dependent API calls
- **Loading states** are handled with skeleton components
- **Error states** include retry mechanisms and user feedback
