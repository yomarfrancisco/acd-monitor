// ACD Monitor API Type Definitions
// Generated from README-ui-data-contract.md

export interface RiskAssessment {
  riskScore: number;           // 0-100 scale
  riskBand: 'LOW' | 'AMBER' | 'RED';
  confidence: number;          // 0-100 confidence level
  updatedAt: string;          // ISO timestamp
  dataSource: string;         // e.g., "Bloomberg Terminal"
  isLive: boolean;            // Real-time monitoring status
}

export interface KeyMetrics {
  priceStability: number;              // 0-100
  priceSynchronization: number;        // 0-100  
  environmentalSensitivity: number;    // 0-100 (Brief 55+ core metric)
  lastUpdated: string;                 // ISO timestamp
}

export interface ChartDataPoint {
  date: string;                        // Format: "Jan '25" or "Aug 6"
  fnb: number;                         // CDS spread in bps
  absa: number;                        // CDS spread in bps
  standard: number;                    // CDS spread in bps
  nedbank: number;                     // CDS spread in bps
}

export interface ChartData {
  timeframe: '30d' | '6m' | '1y' | 'YTD';
  data: ChartDataPoint[];
  dataSource: string;                  // e.g., "Bloomberg Terminal"
}

export interface SystemIntegrity {
  convergenceRate: number;             // 0-100
  dataIntegrity: number;               // 0-100
  evidenceChain: number;               // 0-100
  runtimeStability: number;            // 0-100
  overallStatus: 'PASS' | 'WARN' | 'FAIL';
  lastUpdated: string;                 // ISO timestamp
  dataSource: string;                  // e.g., "Internal Monitoring"
}

export interface Event {
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

export interface Configuration {
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

export interface DataSource {
  id: string;
  name: string;                        // e.g., "Bloomberg Terminal"
  type: 'API' | 'FILE' | 'DATABASE' | 'CLOUD';
  status: 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
  lastUpdate: string;                  // ISO timestamp
  dataQuality: number;                 // 0-100
}

export interface AIAgent {
  id: string;
  name: string;                        // e.g., "General Analysis"
  type: 'ECONOMIST' | 'LAWYER' | 'STATISTICIAN';
  accuracy: number;                    // Percentage
  responseTime: string;                // e.g., "1.2s"
  status: 'AVAILABLE' | 'BUSY' | 'OFFLINE';
}

export interface QuickAnalysis {
  id: string;
  title: string;                       // e.g., "Analyze pricing patterns"
  description: string;                 // e.g., "Identify trends and anomalies"
  icon: string;                        // Icon name
}

export interface BillingInfo {
  currentPeriod: string;               // e.g., "September 2025"
  amount: number;                      // USD
  usage: number;                       // Current usage
  limit: number;                       // Usage limit
  currency: string;                    // e.g., "USD"
  nextBillingDate: string;             // ISO timestamp
}

export interface ComplianceReport {
  id: string;
  title: string;                       // e.g., "Monthly Compliance Report"
  description: string;                 // e.g., "Healthy: 3 instances of competitive adaptation"
  type: 'MONTHLY' | 'QUARTERLY' | 'ANNUAL' | 'AD_HOC';
  status: 'READY' | 'GENERATING' | 'ERROR';
  createdAt: string;                   // ISO timestamp
  downloadUrl?: string;                // URL for download
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  timestamp: string;
}

// WebSocket Event Types
export interface WebSocketEvent<T = any> {
  type: string;
  data: T;
  timestamp: string;
}

export type RiskUpdateEvent = WebSocketEvent<RiskAssessment>;
export type SystemHealthUpdateEvent = WebSocketEvent<SystemIntegrity>;
export type NewEventEvent = WebSocketEvent<Event>;
export type DataSourceStatusEvent = WebSocketEvent<DataSource>;
