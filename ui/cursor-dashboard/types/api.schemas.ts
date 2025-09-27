import { z } from 'zod';

export const RiskSummarySchema = z.object({
  score: z.number().min(0).max(100),
  band: z.enum(['LOW','AMBER','RED']),
  confidence: z.number().min(0).max(100),
  updatedAt: z.string().datetime(),
  timeframe: z.enum(['30d','6m','1y','ytd']),
  source: z.object({
    name: z.string(),
    freshnessSec: z.number().min(0),
    quality: z.number().min(0).max(1),
  }),
});

export type RiskSummary = z.infer<typeof RiskSummarySchema>;

// Metrics Overview Schema
export const MetricSchema = z.object({
  key: z.enum(['stability','synchronization','environmentalSensitivity']),
  label: z.string(),
  score: z.number().min(0).max(100),
  direction: z.enum(['UP','DOWN','FLAT']), // last-interval movement
  note: z.string().optional(),
});

export const MetricsOverviewSchema = z.object({
  timeframe: z.enum(['30d','6m','1y','ytd']),
  updatedAt: z.string().datetime(),
  items: z.array(MetricSchema).length(3),
});
export type MetricsOverview = z.infer<typeof MetricsOverviewSchema>;

// Binance Overview Schema
export const BinanceOverviewSchema = z.object({
  venue: z.string(),
  symbol: z.string(),
  asOf: z.string().datetime(),
  ticker: z.object({
    bid: z.number(),
    ask: z.number(),
    mid: z.number(),
    ts: z.string().datetime(),
  }),
  ohlcv: z.array(z.array(z.union([z.string(), z.number()]))),
  error: z.string().optional(),
});
export type BinanceOverview = z.infer<typeof BinanceOverviewSchema>;

// Health Run Schema
export const HealthPointSchema = z.object({
  ts: z.string().datetime(),
  convergence: z.number().min(0).max(100),
  dataIntegrity: z.number().min(0).max(100),
  evidenceChain: z.number().min(0).max(100),
  runtimeStability: z.number().min(0).max(100),
});

export const HealthRunSchema = z.object({
  updatedAt: z.string().datetime(),
  summary: z.object({
    systemHealth: z.number().min(0).max(100),
    complianceReadiness: z.number().min(0).max(100),
    band: z.enum(['PASS','WATCH','FAIL']),
  }),
  spark: z.array(HealthPointSchema).min(12), // small history for the mini chart
  source: z.object({ name: z.string(), freshnessSec: z.number(), quality: z.number().min(0).max(1) })
});
export type HealthRun = z.infer<typeof HealthRunSchema>;

// Events Schema
export const EventSchema = z.object({
  id: z.string(),
  ts: z.string().datetime(),
  type: z.enum(['MARKET','COORDINATION','INFO_FLOW','REGIME_SWITCH','USER']),
  title: z.string(),
  description: z.string(),
  severity: z.enum(['LOW','MEDIUM','HIGH']),
  riskScore: z.number().min(0).max(100),
  durationMin: z.number().min(0).max(10080).optional(),
  affects: z.array(z.string()).optional() // e.g., ['FNB','Absa']
});

export const EventsResponseSchema = z.object({
  timeframe: z.enum(['30d','6m','1y','ytd']),
  updatedAt: z.string().datetime(),
  items: z.array(EventSchema)
});
export type EventsResponse = z.infer<typeof EventsResponseSchema>;

// Data Sources Schema
export const DataSourceSchema = z.object({
  id: z.string(),
  name: z.string(),                 // e.g., 'Bloomberg', 'Internal Feed'
  tier: z.enum(['T1','T2','T3','T4']),
  status: z.enum(['OK','DEGRADED','DOWN']),
  freshnessSec: z.number().min(0),
  quality: z.number().min(0).max(1),
});

export const DataSourcesSchema = z.object({
  updatedAt: z.string().datetime(),
  items: z.array(DataSourceSchema).min(1),
});
export type DataSources = z.infer<typeof DataSourcesSchema>;

// Evidence Export Schema
export const EvidenceExportSchema = z.object({
  requestedAt: z.string().datetime(),
  status: z.enum(['READY','QUEUED']),
  url: z.string().url().optional(), // present when READY
  bundleId: z.string(),
  estSeconds: z.number().min(0).optional()
});
export type EvidenceExport = z.infer<typeof EvidenceExportSchema>;
