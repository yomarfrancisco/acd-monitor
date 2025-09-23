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

  let response: Response | null = null;
  
  try {
    console.log(`🔍 [UI API] Fetching Binance overview: symbol=${symbol}, tf=${tf}`);
    console.log(`🔍 [UI API] Backend URL: ${BACKEND_URL}/exchanges/binance/overview`);
    
    response = await fetch(`${BACKEND_URL}/exchanges/binance/overview?symbol=${symbol}&tf=${tf}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 15 }, // 15 second cache
    });

    console.log(`📊 [UI API] Response status: ${response.status}`);
    console.log(`📊 [UI API] Response headers:`, Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      console.log(`❌ [UI API] Response not OK: ${response.status}`);
      // Check if it's a specific Binance error
      try {
        const errorData = await response.json();
        console.log(`📊 [UI API] Error response data:`, errorData);
        if (errorData.error === 'binance_no_ohlcv') {
          console.log(`⚠️ [UI API] Detected binance_no_ohlcv error, returning empty OHLCV`);
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
            error: 'binance_no_ohlcv'
          });
        }
      } catch (e) {
        console.log(`❌ [UI API] Failed to parse error response:`, e);
        // Fall through to generic error
      }
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data = await response.json();
    console.log(`✅ [UI API] Successfully received data from backend`);
    console.log(`📊 [UI API] Raw JSON response keys:`, Object.keys(data));
    console.log(`📊 [UI API] Venue: ${data.venue}`);
    console.log(`📊 [UI API] Symbol: ${data.symbol}`);
    console.log(`📊 [UI API] AsOf: ${data.asOf}`);
    console.log(`📊 [UI API] Ticker:`, data.ticker);
    console.log(`📊 [UI API] OHLCV length: ${data.ohlcv ? data.ohlcv.length : 'undefined'}`);
    console.log(`📊 [UI API] OHLCV type: ${typeof data.ohlcv}`);
    console.log(`📊 [UI API] OHLCV is array: ${Array.isArray(data.ohlcv)}`);
    
    if (data.ohlcv && data.ohlcv.length > 0) {
      console.log(`📊 [UI API] First OHLCV bar:`, data.ohlcv[0]);
      console.log(`📊 [UI API] Last OHLCV bar:`, data.ohlcv[data.ohlcv.length - 1]);
    } else {
      console.log(`⚠️ [UI API] OHLCV data is empty or undefined!`);
    }
    
    console.log(`🎯 [UI API] Returning data to frontend with ${data.ohlcv ? data.ohlcv.length : 0} OHLCV bars`);
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
