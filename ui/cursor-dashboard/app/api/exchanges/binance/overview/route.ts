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

    // Check if backend response is good
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    
    if (!response.ok || !isJson) {
      console.log(`❌ [UI API] Backend response not OK or not JSON: status=${response.status}, contentType=${contentType}`);
      throw new Error(`Backend responded with ${response.status}`);
    }

    const data = await response.json();
    console.log(`📊 [UI API] Backend response:`, JSON.stringify(data, null, 2));
    
    // Check if backend returned valid OHLCV data
    if (data.ohlcv && data.ohlcv.length > 0) {
      console.log(`✅ [UI API] Backend OK → pass-through (${data.ohlcv.length} bars)`);
      return NextResponse.json(data);
    } else {
      console.log(`⚠️ [UI API] Backend returned empty OHLCV, trying direct Binance fallback`);
      throw new Error('Backend returned empty OHLCV');
    }

  } catch (error) {
    console.log(`❌ [UI API] Backend failed: ${error}`);
    console.log(`🔄 [UI API] Backend bad → using direct Binance fallback`);
    
    try {
      // Direct Binance API fallback
      const binanceBaseUrl = 'https://api.binance.com';
      const interval = tf === '5m' ? '5m' : '5m'; // Default to 5m
      
      console.log(`📡 [UI API] Fetching directly from Binance: ${symbol} ${interval}`);
      
      // Fetch OHLCV and ticker data concurrently
      const [klinesRes, tickerRes] = await Promise.all([
        fetch(`${binanceBaseUrl}/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=288`),
        fetch(`${binanceBaseUrl}/api/v3/ticker/bookTicker?symbol=${symbol}`)
      ]);
      
      if (!klinesRes.ok || !tickerRes.ok) {
        throw new Error(`Binance API failed: klines=${klinesRes.status}, ticker=${tickerRes.status}`);
      }
      
      const [klines, ticker] = await Promise.all([
        klinesRes.json(),
        tickerRes.json()
      ]);
      
      console.log(`📊 [UI API] Direct Binance response: klines=${klines.length} bars, ticker=${ticker.symbol}`);
      
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
      
      console.log(`✅ [UI API] Direct Binance fallback success (${mappedData.ohlcv.length} bars)`);
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
}
