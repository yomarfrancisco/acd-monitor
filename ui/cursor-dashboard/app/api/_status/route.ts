import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    mode: process.env.NEXT_PUBLIC_DATA_MODE ?? 'mock'
  })
}
