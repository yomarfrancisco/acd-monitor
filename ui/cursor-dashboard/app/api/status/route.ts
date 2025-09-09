import { NextRequest, NextResponse } from 'next/server'

const IS_PREVIEW = process.env.VERCEL_ENV === 'preview' || process.env.NEXT_PUBLIC_DATA_MODE === 'live'
const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'

export async function GET(request: NextRequest) {
  if (IS_PREVIEW) {
    try {
      // Proxy to Render backend
      const response = await fetch(`${BACKEND_URL}/api/_status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (response.ok) {
        const data = await response.json()
        return NextResponse.json(data)
      }
    } catch (error) {
      console.error('Backend proxy failed, falling back to mock:', error)
    }
  }
  
  // Fallback to mock data
  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    mode: 'mock'
  })
}