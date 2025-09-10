import { NextResponse } from 'next/server';
import { EventsResponse, Event } from '@/types/api';
import { proxyJson } from '@/lib/proxy-utils';

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

// Generate mock events
function generateMockEvents(timeframe: string, mode: string): EventsResponse {
  const events: Event[] = [];
  const now = new Date();
  
  const baseEvents = {
    '30d': [
      { type: 'MARKET', title: 'Market coordination', description: 'Detected potential coordination patterns', severity: 'LOW', riskScore: 16 },
      { type: 'INFO_FLOW', title: 'Information flow anomaly', description: 'Unusual information propagation detected', severity: 'LOW', riskScore: 12 },
      { type: 'REGIME_SWITCH', title: 'Regime switch', description: 'Market regime transition detected', severity: 'LOW', riskScore: 18 },
      { type: 'COORDINATION', title: 'Price leadership change', description: 'Shift in price leadership patterns', severity: 'MEDIUM', riskScore: 35 },
      { type: 'MARKET', title: 'Volume spike', description: 'Unusual volume increase detected', severity: 'LOW', riskScore: 8 }
    ],
    '6m': [
      { type: 'MARKET', title: 'Market coordination', description: 'Detected potential coordination patterns', severity: 'LOW', riskScore: 16 },
      { type: 'INFO_FLOW', title: 'Information flow anomaly', description: 'Unusual information propagation detected', severity: 'LOW', riskScore: 12 },
      { type: 'REGIME_SWITCH', title: 'Regime switch', description: 'Market regime transition detected', severity: 'LOW', riskScore: 18 },
      { type: 'COORDINATION', title: 'Price leadership change', description: 'Shift in price leadership patterns', severity: 'MEDIUM', riskScore: 35 },
      { type: 'MARKET', title: 'Volume spike', description: 'Unusual volume increase detected', severity: 'LOW', riskScore: 8 }
    ],
    '1y': [
      { type: 'MARKET', title: 'Market coordination', description: 'Detected potential coordination patterns', severity: 'LOW', riskScore: 16 },
      { type: 'INFO_FLOW', title: 'Information flow anomaly', description: 'Unusual information propagation detected', severity: 'LOW', riskScore: 12 },
      { type: 'REGIME_SWITCH', title: 'Regime switch', description: 'Market regime transition detected', severity: 'LOW', riskScore: 18 },
      { type: 'COORDINATION', title: 'Price leadership change', description: 'Shift in price leadership patterns', severity: 'MEDIUM', riskScore: 35 },
      { type: 'MARKET', title: 'Volume spike', description: 'Unusual volume increase detected', severity: 'LOW', riskScore: 8 }
    ],
    'ytd': [
      { type: 'MARKET', title: 'Market coordination', description: 'Detected potential coordination patterns', severity: 'LOW', riskScore: 16 },
      { type: 'INFO_FLOW', title: 'Information flow anomaly', description: 'Unusual information propagation detected', severity: 'LOW', riskScore: 12 },
      { type: 'REGIME_SWITCH', title: 'Regime switch', description: 'Market regime transition detected', severity: 'LOW', riskScore: 18 },
      { type: 'COORDINATION', title: 'Price leadership change', description: 'Shift in price leadership patterns', severity: 'MEDIUM', riskScore: 35 },
      { type: 'MARKET', title: 'Volume spike', description: 'Unusual volume increase detected', severity: 'LOW', riskScore: 8 }
    ]
  };

  const eventsToGenerate = baseEvents[timeframe as keyof typeof baseEvents] || baseEvents.ytd;
  
  eventsToGenerate.forEach((event, index) => {
    const hoursAgo = (index + 1) * 5;
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

  events.sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());

  return {
    timeframe,
    updatedAt: new Date().toISOString(),
    items: events
  };
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const timeframe = url.searchParams.get('timeframe') ?? 'ytd';
  const mode = url.searchParams.get('mode') ?? 'normal';
  
  const result = await proxyJson(`/api/events?timeframe=${timeframe}`, {
    mockFallback: () => generateMockEvents(timeframe, mode)
  });

  if (!result.success) {
    return NextResponse.json(
      { error: 'Service unavailable' },
      { status: 503 }
    );
  }

  const response = NextResponse.json(result.data, { status: result.status });
  
  // Add custom headers
  if (result.headers) {
    Object.entries(result.headers).forEach(([key, value]) => {
      response.headers.set(key, value);
    });
  }

  return response;
}