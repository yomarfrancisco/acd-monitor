import { NextRequest, NextResponse } from 'next/server'
import { proxyJson } from '@/lib/proxy-utils'

export async function GET(request: NextRequest) {
  const result = await proxyJson('/api/_status', {
    enableWarmup: true,
    mockFallback: () => ({
      status: 'ok',
      timestamp: new Date().toISOString(),
      mode: 'mock'
    })
  })

  if (!result.success) {
    return NextResponse.json(
      { error: 'Service unavailable' },
      { status: 503 }
    )
  }

  const response = NextResponse.json(result.data, { status: result.status })
  
  // Add custom headers
  if (result.headers) {
    Object.entries(result.headers).forEach(([key, value]) => {
      response.headers.set(key, value)
    })
  }

  return response
}