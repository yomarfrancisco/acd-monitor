import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/_status`, {
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
      status: 'ok',
      timestamp: new Date().toISOString(),
      mode: 'fallback'
    })
  }
}
