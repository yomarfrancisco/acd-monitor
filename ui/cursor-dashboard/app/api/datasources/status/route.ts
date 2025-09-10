import { NextResponse } from 'next/server';
import { proxyJson } from '@/lib/proxy-utils';

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

// Generate mock data sources
function generateMockDataSources(mode: string) {
  return {
    updatedAt: new Date().toISOString(),
    items: [
      {
        id: 'ds1',
        name: 'Internal Monitoring',
        tier: 'T2',
        status: mode === 'degraded' ? 'DEGRADED' : 'OK',
        freshnessSec: mode === 'degraded' ? jitter(300, 60) : jitter(15, 5),
        quality: mode === 'degraded' ? 0.85 : 0.98
      },
      {
        id: 'ds2',
        name: 'External Data Feed',
        tier: 'T1',
        status: 'OK',
        freshnessSec: jitter(30, 10),
        quality: 0.98
      },
      {
        id: 'ds3',
        name: 'Regulatory Notices',
        tier: 'T3',
        status: 'OK',
        freshnessSec: jitter(3600, 300),
        quality: 0.90
      },
      {
        id: 'ds4',
        name: 'Market Data Feed',
        tier: 'T1',
        status: mode === 'degraded' ? 'DEGRADED' : 'OK',
        freshnessSec: mode === 'degraded' ? jitter(120, 30) : jitter(8, 3),
        quality: mode === 'degraded' ? 0.85 : 0.97
      }
    ]
  };
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const mode = url.searchParams.get('mode') ?? 'normal';
  
  const result = await proxyJson('/api/datasources/status', {
    mockFallback: () => generateMockDataSources(mode)
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