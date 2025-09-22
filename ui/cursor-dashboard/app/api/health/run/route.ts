import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'
const IS_PREVIEW = process.env.VERCEL_ENV === 'preview' || process.env.NEXT_PUBLIC_DATA_MODE === 'live'

export async function GET() {
  // In production, always use mock data
  if (!IS_PREVIEW) {
    const response = NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'healthy',
        external_apis: 'healthy',
        memory_usage: 'healthy'
      },
      mode: 'mock'
    });
    response.headers.set('x-acd-bundle-version', 'v1.9+');
    response.headers.set('x-case-library-version', 'v1.9');
    return response;
  }

  // In preview, try to fetch from backend
  try {
    const response = await fetch(`${BACKEND_URL}/api/health/run`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`)
    }
    
    const data = await response.json()
    const res = NextResponse.json(data)
    res.headers.set('x-acd-bundle-version', 'v1.9+');
    res.headers.set('x-case-library-version', 'v1.9');
    return res
  } catch (error) {
    console.error('Failed to fetch from backend:', error)
    
    // Fallback to mock data if backend is unavailable
    const response = NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'healthy',
        external_apis: 'healthy',
        memory_usage: 'healthy'
      },
      mode: 'fallback'
    });
    response.headers.set('x-acd-bundle-version', 'v1.9+');
    response.headers.set('x-case-library-version', 'v1.9');
    return response;
  }
}