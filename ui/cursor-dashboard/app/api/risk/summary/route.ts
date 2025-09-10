import { NextResponse } from 'next/server';
import { proxyJson } from '@/lib/proxy-utils';

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  try {
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
      console.error('Proxy failed for /api/risk/summary:', {
        status: result.status,
        headers: result.headers,
        timeframe,
        mode
      });
      return NextResponse.json(
        { error: 'Service unavailable' },
        { status: 503 }
      );
    }

    const response = NextResponse.json(result.data, { 
      status: result.status,
      headers: {
        'Cache-Control': 'no-store',
        ...(result.headers || {})
      }
    });

    return response;
  } catch (error) {
    console.error('Error in /api/risk/summary:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
