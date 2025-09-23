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
    console.log(`🔍 [UI API] Fetching Binance overview: symbol=${symbol}, tf=${tf}`);
    console.log(`🔍 [UI API] Backend URL: ${BACKEND_URL}/exchanges/binance/overview`);
    
    const response = await fetch(`${BACKEND_URL}/exchanges/binance/overview?symbol=${symbol}&tf=${tf}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 15 }, // 15 second cache
    });

    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    
    let data: any = null;
    if (isJson) {
      try {
        data = await response.json();
      } catch (e) {
        // JSON parse failed
      }
    }
    
    console.log(`[UI API] backend →`, response.status, 'json=', isJson, 'bars=', data?.ohlcv?.length ?? 'n/a');
    
    // Check if backend response is good
    if (response.ok && isJson && data?.ohlcv?.length > 0) {
      console.log(`✅ [UI API] Backend OK → pass-through (${data.ohlcv.length} bars)`);
      return NextResponse.json(data);
    }
    
    // Backend failed or returned empty data - use direct Binance fallback
    console.log(`🔄 [UI API] Backend failed or empty, using direct Binance fallback`);
    
  } catch (error) {
    console.log(`❌ [UI API] Backend fetch failed: ${error}`);
    console.log(`🔄 [UI API] Backend failed, using direct Binance fallback`);
  }
  
  // Direct Binance API fallback
  try {
    console.log(`📡 [UI API] Fetching directly from Binance: ${symbol} ${tf}`);
    
    const [klinesRes, tickerRes] = await Promise.all([
      fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${tf}&limit=288`),
      fetch(`https://api.binance.com/api/v3/ticker/bookTicker?symbol=${symbol}`)
    ]);
    
    if (!klinesRes.ok || !tickerRes.ok) {
      throw new Error(`Binance API failed: klines=${klinesRes.status}, ticker=${tickerRes.status}`);
    }
    
    const [klines, ticker] = await Promise.all([
      klinesRes.json(),
      tickerRes.json()
    ]);
    
    // Map Binance data to our format
    const mappedData = {
      venue: 'binance',
      symbol,
      asOf: new Date().toISOString(),
      ticker: {
        bid: Number(ticker.bidPrice),
        ask: Number(ticker.askPrice),
        mid: (Number(ticker.bidPrice) + Number(ticker.askPrice)) / 2,
        ts: new Date().toISOString()
      },
      ohlcv: klines.map(([t, o, h, l, c, v]: any[]) => [
        new Date(Number(t)).toISOString(),
        Number(o),
        Number(h),
        Number(l),
        Number(c),
        Number(v)
      ])
    };
    
    console.log(`[UI API] using direct binance fallback (bars=`, mappedData.ohlcv.length, ')');
    return NextResponse.json(mappedData);
    
  } catch (fallbackError) {
    console.error(`❌ [UI API] Direct Binance fallback also failed:`, fallbackError);
    
    // Final fallback - return empty data with error
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
    }, { status: 502 });
  }
}
