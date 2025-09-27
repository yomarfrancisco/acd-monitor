import { NextRequest, NextResponse } from 'next/server'
import { proxyJson } from '@/lib/proxy-utils'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const result = await proxyJson('/api/_status', {
      enableWarmup: true,
      mockFallback: () => ({
        status: 'ok',
        timestamp: new Date().toISOString(),
        mode: 'mock'
      })
    })

    if (!result.success) {
      console.error('Proxy failed for /api/_status:', {
        status: result.status,
        headers: result.headers
      });
      return NextResponse.json(
        { error: 'Service unavailable' },
        { status: 503 }
      )
    }

    const response = NextResponse.json(result.data, { 
      status: result.status,
      headers: {
        'Cache-Control': 'no-store',
        ...(result.headers || {})
      }
    })

    return response
  } catch (error) {
    console.error('Error in /api/status:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}