export type RiskBand = 'LOW' | 'AMBER' | 'RED';

export interface RiskSummary {
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
