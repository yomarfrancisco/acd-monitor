# ACD Monitor UI Data Contract

## Overview
This document defines the exact JSON data structures expected by the ACD Monitor UI components. All data should be provided via REST API endpoints and WebSocket events.

## Core Data Types

### Risk Assessment
```typescript
interface RiskAssessment {
  riskScore: number;           // 0-100 scale
  riskBand: 'LOW' | 'AMBER' | 'RED';
  confidence: number;          // 0-100 confidence level
  updatedAt: string;          // ISO timestamp
  dataSource: string;         // e.g., "Bloomberg Terminal"
  isLive: boolean;            // Real-time monitoring status
}
```

### Key Metrics
```typescript
interface KeyMetrics {
  priceStability: number;              // 0-100
  priceSynchronization: number;        // 0-100  
  environmentalSensitivity: number;    // 0-100 (Brief 55+ core metric)
  lastUpdated: string;                 // ISO timestamp
}
```

### Chart Data
```typescript
interface ChartDataPoint {
  date: string;                        // Format: "Jan '25" or "Aug 6"
  fnb: number;                         // CDS spread in bps
  absa: number;                        // CDS spread in bps
  standard: number;                    // CDS spread in bps
  nedbank: number;                     // CDS spread in bps
}

interface ChartData {
  timeframe: '30d' | '6m' | '1y' | 'YTD';
  data: ChartDataPoint[];
  dataSource: string;                  // e.g., "Bloomberg Terminal"
}
```

### System Integrity
```typescript
interface SystemIntegrity {
  convergenceRate: number;             // 0-100
  dataIntegrity: number;               // 0-100
  evidenceChain: number;               // 0-100
  runtimeStability: number;            // 0-100
  overallStatus: 'PASS' | 'WARN' | 'FAIL';
  lastUpdated: string;                 // ISO timestamp
  dataSource: string;                  // e.g., "Internal Monitoring"
}
```

### Events
```typescript
interface Event {
  id: string;
  title: string;                       // e.g., "Market coordination detected"
  description: string;                 // e.g., "3 banks moved within 2 minutes"
  riskScore: number;                   // 0-100
  riskStatus: 'LOW' | 'AMBER' | 'RED';
  timestamp: string;                   // ISO timestamp
  duration: string;                    // e.g., "2m 15s"
  eventType: 'SYSTEM' | 'USER' | 'MARKET';
  icon: string;                        // Icon name for display
}
```

### Configuration
```typescript
interface Configuration {
  autoDetectMarketChanges: boolean;
  priceChangeThreshold: number;        // Percentage (5-25)
  confidenceLevel: number;             // Percentage (70-95)
  updateFrequency: string;             // e.g., "5m", "1h"
  sensitivityLevel: 'Low' | 'Medium' | 'High';
  maxDataAge: string;                  // e.g., "10m", "24h"
  enableLiveMonitoring: boolean;
  checkDataQuality: boolean;
  bloombergDataFeed: boolean;
}
```

### Data Sources
```typescript
interface DataSource {
  id: string;
  name: string;                        // e.g., "Bloomberg Terminal"
  type: 'API' | 'FILE' | 'DATABASE' | 'CLOUD';
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
  lastUpdate: string;                  // ISO timestamp
  dataQuality: number;                 // 0-100
}
```

### AI Agents
```typescript
interface AIAgent {
  id: string;
  name: string;                        // e.g., "General Analysis"
  type: 'ECONOMIST' | 'LAWYER' | 'STATISTICIAN';
  accuracy: number;                    // Percentage
  responseTime: string;                // e.g., "1.2s"
  status: 'AVAILABLE' | 'BUSY' | 'OFFLINE';
}

interface QuickAnalysis {
  id: string;
  title: string;                       // e.g., "Analyze pricing patterns"
  description: string;                 // e.g., "Identify trends and anomalies"
  icon: string;                        // Icon name
}
```

### Billing
```typescript
interface BillingInfo {
  currentPeriod: string;               // e.g., "September 2025"
  amount: number;                      // USD
  usage: number;                       // Current usage
  limit: number;                       // Usage limit
  currency: string;                    // e.g., "USD"
  nextBillingDate: string;             // ISO timestamp
}
```

### Compliance Reports
```typescript
interface ComplianceReport {
  id: string;
  title: string;                       // e.g., "Monthly Compliance Report"
  description: string;                 // e.g., "Healthy: 3 instances of competitive adaptation"
  type: 'MONTHLY' | 'QUARTERLY' | 'ANNUAL' | 'AD_HOC';
  status: 'READY' | 'GENERATING' | 'ERROR';
  createdAt: string;                   // ISO timestamp
  downloadUrl?: string;                // URL for download
}
```

## API Endpoints

### Overview Page
- `GET /api/v1/overview/risk-assessment` → RiskAssessment
- `GET /api/v1/overview/metrics` → KeyMetrics
- `GET /api/v1/overview/chart?timeframe={timeframe}` → ChartData

### Health Checks
- `GET /api/v1/health/system-integrity` → SystemIntegrity

### Events Log
- `GET /api/v1/events?limit={limit}&offset={offset}` → Event[]
- `POST /api/v1/events` → Create user event

### Configuration
- `GET /api/v1/configuration` → Configuration
- `PUT /api/v1/configuration` → Update configuration

### Data Sources
- `GET /api/v1/data-sources` → DataSource[]
- `POST /api/v1/data-sources/connect` → Connect data source

### AI Agents
- `GET /api/v1/agents` → AIAgent[]
- `GET /api/v1/agents/quick-analysis` → QuickAnalysis[]
- `POST /api/v1/agents/analyze` → Trigger analysis

### Billing
- `GET /api/v1/billing/current` → BillingInfo

### Compliance Reports
- `GET /api/v1/compliance/reports` → ComplianceReport[]
- `POST /api/v1/compliance/reports/generate` → Generate report
- `GET /api/v1/compliance/reports/{id}/download` → Download report

## WebSocket Events

### Real-time Updates
- `risk_update` → RiskAssessment
- `system_health_update` → SystemIntegrity
- `new_event` → Event
- `data_source_status` → DataSource

## Error Handling

All API responses should follow this structure:
```typescript
interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}
```

## Data Validation

- All numeric values should be within expected ranges (0-100 for scores)
- All timestamps should be ISO 8601 format
- All enum values should match exactly (case-sensitive)
- Required fields must always be present
- Optional fields can be null or undefined
