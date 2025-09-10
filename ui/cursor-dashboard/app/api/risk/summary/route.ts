import { NextResponse } from 'next/server';
import { proxyJson } from '@/lib/proxy-utils';

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  const timeframe = url.searchParams.get('timeframe') ?? 'ytd';
  const mode = url.searchParams.get('mode') ?? 'normal';
  
  const result = await proxyJson(`/api/risk/summary?timeframe=${timeframe}`, {
    mockFallback: () => {
      const score = mode === 'degraded' ? jitter(58, 20) : jitter(14, 8);
      const band = score <= 33 ? 'LOW' : score <= 66 ? 'AMBER' : 'RED';
      const confidence = mode === 'degraded' ? jitter(78, 10) : jitter(96, 4);

      return {
        score,
        band,
        confidence,
        updatedAt: new Date().toISOString(),
        timeframe,
        source: {
          name: result.isFallback ? 'Simulated: Internal Monitoring (Fallback)' : 'Simulated: Internal Monitoring',
          freshnessSec: mode === 'degraded' ? 1800 : 20,
          quality: mode === 'degraded' ? 0.78 : 0.96,
        },
      };
    }
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
