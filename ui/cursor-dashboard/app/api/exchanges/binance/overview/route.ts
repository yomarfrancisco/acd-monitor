import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com'
const IS_PREVIEW_BINANCE = process.env.NEXT_PUBLIC_PREVIEW_BINANCE === 'true'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'BTCUSDT';
  const tf = searchParams.get('tf') || '5m';

  // Only use Binance API in preview mode with the flag enabled
  if (!IS_PREVIEW_BINANCE) {
    return NextResponse.json(
      { error: 'Binance preview not enabled' },
      { status: 404 }
    );
  }

  try {
    const response = await fetch(`${BACKEND_URL}/exchanges/binance/overview?symbol=${symbol}&tf=${tf}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 15 }, // 15 second cache
    });

    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Binance overview fetch failed:', error);
    
    // Return fallback data structure
    return NextResponse.json({
      venue: 'binance',
      symbol,
      asOf: new Date().toISOString(),
      ticker: {
        bid: 0,
        ask: 0,
        mid: 0,
        ts: new Date().toISOString()
      },
      ohlcv: [],
      error: 'binance_unavailable'
    });
  }
}
