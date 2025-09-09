export type RiskBand = 'LOW' | 'AMBER' | 'RED';
export type Timeframe = '30d' | '6m' | '1y' | 'ytd';

export interface RiskSummary {
  score: number;           // 0–100
  band: RiskBand;          // LOW | AMBER | RED
  confidence: number;      // 0–100 (%)
  updatedAt: string;       // ISO timestamp
  timeframe: Timeframe;
  source: { 
    name: string; 
    freshnessSec: number; 
    quality: number;       // 0–1
  };
}

export interface MetricItem {
  key: string;         // e.g., "stability", "synchronization", "environmentalSensitivity"
  label: string;       // e.g., "Price Stability"
  score: number;       // 0-100
  direction: "UP" | "DOWN" | "FLAT";
}

export interface MetricsOverview {
  items: MetricItem[]; // [stability, synchronization, environmental]
  updatedAt: string;
}

export interface HealthRun {
  updatedAt: string;
  summary: {
    systemHealth: number;     // 0-100
    complianceReadiness: number; // %
    band: "PASS" | "WATCH" | "FAIL";
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
    quality: number;
  };
}

export interface Event {
  id: string;
  ts: string;
  type: string;
  title: string;
  description: string;
  severity: string;
  riskScore: number;
  durationMin?: number;
  affects?: string[];
}

export interface EventsResponse {
  timeframe: string;
  updatedAt: string;
  items: Event[];
}

export interface DataSource {
  id: string;
  name: string;
  status: string;
  freshnessSec: number;
  quality: number;
}

export interface DataSources {
  updatedAt: string;
  items: DataSource[];
}

export interface EvidenceExport {
  requestedAt: string;
  status: string;
  url?: string;
  bundleId: string;
  estSeconds?: number;
}
