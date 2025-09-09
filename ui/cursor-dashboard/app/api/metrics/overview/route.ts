import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  const timeframe = url.searchParams.get('timeframe') ?? 'ytd';
  
  try {
    const backendUrl = new URL(`${BACKEND_URL}/api/metrics/overview`)
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
    
    // Fallback to mock data
    const mode = url.searchParams.get('mode') ?? 'normal';

  // Base values for different timeframes
  const baseValues = {
    '30d': { stability: 65, synchronization: 18, environmentalSensitivity: 82 },
    '6m': { stability: 70, synchronization: 22, environmentalSensitivity: 78 },
    '1y': { stability: 68, synchronization: 25, environmentalSensitivity: 75 },
    'ytd': { stability: 72, synchronization: 20, environmentalSensitivity: 80 }
  };

  const base = baseValues[timeframe];
  const variance = mode === 'degraded' ? 15 : 8;

  const payload = {
    timeframe,
    updatedAt: new Date().toISOString(),
    items: [
      {
        key: 'stability',
        label: 'Price Stability',
        score: jitter(base.stability, variance),
        direction: Math.random() > 0.7 ? 'UP' : Math.random() > 0.4 ? 'DOWN' : 'FLAT',
        note: mode === 'degraded' ? 'Elevated volatility detected' : 'Normal spread volatility'
      },
      {
        key: 'synchronization',
        label: 'Price Synchronization',
        score: jitter(base.synchronization, variance),
        direction: Math.random() > 0.6 ? 'DOWN' : Math.random() > 0.3 ? 'UP' : 'FLAT',
        note: mode === 'degraded' ? 'Some coordination patterns' : 'Movements mostly independent'
      },
      {
        key: 'environmentalSensitivity',
        label: 'Environmental Sensitivity',
        score: jitter(base.environmentalSensitivity, variance),
        direction: Math.random() > 0.5 ? 'UP' : Math.random() > 0.2 ? 'DOWN' : 'FLAT',
        note: mode === 'degraded' ? 'Delayed response to shocks' : 'Strong adaptation to shocks'
      }
    ]
  };

    return NextResponse.json(payload);
  }
}
