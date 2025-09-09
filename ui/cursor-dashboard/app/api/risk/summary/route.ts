import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'
const IS_PREVIEW = process.env.VERCEL_ENV === 'preview' || process.env.NEXT_PUBLIC_DATA_MODE === 'live'

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  const timeframe = url.searchParams.get('timeframe') ?? 'ytd';
  const mode = url.searchParams.get('mode') ?? 'normal';
  
  // In production, always use mock data
  if (!IS_PREVIEW) {
    const score = mode === 'degraded' ? jitter(58, 20) : jitter(14, 8);
    const band = score <= 33 ? 'LOW' : score <= 66 ? 'AMBER' : 'RED';
    const confidence = mode === 'degraded' ? jitter(78, 10) : jitter(96, 4);

    const payload = {
      score,
      band,
      confidence,
      updatedAt: new Date().toISOString(),
      timeframe,
      source: {
        name: 'Simulated: Internal Monitoring',
        freshnessSec: mode === 'degraded' ? 1800 : 20,
        quality: mode === 'degraded' ? 0.78 : 0.96,
      },
    };

    return NextResponse.json(payload);
  }

  // In preview, try to fetch from backend
  try {
    const backendUrl = new URL(`${BACKEND_URL}/api/risk/summary`)
    backendUrl.searchParams.set('timeframe', timeframe)
    
    const response = await fetch(backendUrl.toString(), {
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`)
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch from backend:', error)
    
    // Fallback to mock data if backend is unavailable
    const score = mode === 'degraded' ? jitter(58, 20) : jitter(14, 8);
    const band = score <= 33 ? 'LOW' : score <= 66 ? 'AMBER' : 'RED';
    const confidence = mode === 'degraded' ? jitter(78, 10) : jitter(96, 4);

    const payload = {
      score,
      band,
      confidence,
      updatedAt: new Date().toISOString(),
      timeframe,
      source: {
        name: 'Simulated: Internal Monitoring (Fallback)',
        freshnessSec: mode === 'degraded' ? 1800 : 20,
        quality: mode === 'degraded' ? 0.78 : 0.96,
      },
    };

    return NextResponse.json(payload);
  }
}
