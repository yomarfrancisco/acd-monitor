import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'
const IS_PREVIEW = process.env.VERCEL_ENV === 'preview' || process.env.NEXT_PUBLIC_DATA_MODE === 'live'

export async function GET() {
  // In production, always use mock data
  if (!IS_PREVIEW) {
    return NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'healthy',
        external_apis: 'healthy',
        memory_usage: 'healthy'
      },
      mode: 'mock'
    });
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
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch from backend:', error)
    
    // Fallback to mock data if backend is unavailable
    return NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      checks: {
        database: 'healthy',
        external_apis: 'healthy',
        memory_usage: 'healthy'
      },
      mode: 'fallback'
    });
  }
}