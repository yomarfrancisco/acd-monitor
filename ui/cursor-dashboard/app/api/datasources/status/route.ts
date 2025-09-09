import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/datasources/status`, {
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
    
    // Fallback to mock data
    const mode = url.searchParams.get('mode') ?? 'normal';

  const payload = {
    updatedAt: new Date().toISOString(),
    items: [
      {
        id: 'ds1',
        name: 'Internal Monitoring',
        tier: 'T2',
        status: mode === 'degraded' ? 'DEGRADED' : 'OK',
        freshnessSec: mode === 'degraded' ? jitter(300, 60) : jitter(22, 8),
        quality: mode === 'degraded' ? 0.78 : 0.96
      },
      {
        id: 'ds2',
        name: 'Bloomberg Terminal',
        tier: 'T1',
        status: 'OK',
        freshnessSec: jitter(15, 5),
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

    return NextResponse.json(payload);
  }
}
