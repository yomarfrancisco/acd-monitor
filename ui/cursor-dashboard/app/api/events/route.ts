import { NextResponse } from 'next/server';

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  const timeframe = (url.searchParams.get('timeframe') ?? '30d') as '30d'|'6m'|'1y'|'ytd';
  const mode = url.searchParams.get('mode') ?? 'normal'; // normal|degraded

  // Generate events based on timeframe
  const events = [];
  const now = new Date();
  
  // Base events for different timeframes
  const baseEvents = {
    '30d': [
      { type: 'MARKET', title: 'ZAR depreciates 1.9%', description: 'Broad CDS widening; sensitivity ↑', severity: 'MEDIUM', riskScore: 42 },
      { type: 'MARKET', title: 'SARB guidance unchanged', description: 'No regime break detected', severity: 'LOW', riskScore: 15 },
      { type: 'MARKET', title: 'Sovereign outlook stable', description: 'Idiosyncratic responses across banks', severity: 'LOW', riskScore: 12 }
    ],
    '6m': [
      { type: 'COORDINATION', title: 'Price leadership shift detected', description: 'FNB → ABSA transition', severity: 'MEDIUM', riskScore: 38 },
      { type: 'MARKET', title: 'Economic policy uncertainty', description: 'Increased correlation patterns', severity: 'HIGH', riskScore: 65 },
      { type: 'INFO_FLOW', title: 'Information flow anomaly', description: 'Unusual cross-bank timing', severity: 'MEDIUM', riskScore: 45 }
    ],
    '1y': [
      { type: 'REGIME_SWITCH', title: 'Market regime change', description: 'Volatility clustering detected', severity: 'HIGH', riskScore: 72 },
      { type: 'COORDINATION', title: 'Synchronized price movements', description: 'Multi-bank coordination pattern', severity: 'HIGH', riskScore: 68 },
      { type: 'MARKET', title: 'Regulatory announcement', description: 'Industry-wide response', severity: 'MEDIUM', riskScore: 35 }
    ],
    'ytd': [
      { type: 'MARKET', title: 'YTD market volatility spike', description: 'Coordinated response across banks', severity: 'HIGH', riskScore: 58 },
      { type: 'COORDINATION', title: 'Price leadership established', description: 'FNB leading price movements', severity: 'MEDIUM', riskScore: 42 },
      { type: 'INFO_FLOW', title: 'Information cascade event', description: 'Rapid price propagation', severity: 'MEDIUM', riskScore: 38 }
    ]
  };

  const baseEventList = baseEvents[timeframe];
  
  baseEventList.forEach((event, index) => {
    const hoursAgo = (index + 1) * 2 + Math.random() * 4; // 2-6 hours apart
    const eventTime = new Date(now.getTime() - (hoursAgo * 60 * 60 * 1000));
    
    events.push({
      id: `e${index + 1}`,
      ts: eventTime.toISOString(),
      type: event.type,
      title: event.title,
      description: event.description,
      severity: event.severity,
      riskScore: mode === 'degraded' ? jitter(event.riskScore + 20, 15) : jitter(event.riskScore, 8),
      durationMin: Math.random() > 0.5 ? Math.round(Math.random() * 120) : undefined,
      affects: Math.random() > 0.3 ? ['FNB', 'ABSA', 'Nedbank', 'Standard Bank'] : undefined
    });
  });

  // Sort by timestamp (most recent first)
  events.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());

  const payload = {
    timeframe,
    updatedAt: new Date().toISOString(),
    items: events
  };

  return NextResponse.json(payload);
}
