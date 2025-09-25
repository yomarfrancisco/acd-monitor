import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

// Environment variables
const PROXY_HOST = process.env.PROXY_HOST ?? process.env.EXCHANGE_PROXY_ORIGIN ?? 'https://binance-proxy-broken-night-96.fly.dev';

// Timeframe to granularity mapping for Coinbase Advanced Trade API
const timeframeToGranularity: Record<string, string> = {
  '30d': 'ONE_HOUR',
  '6m': 'ONE_DAY', 
  'ytd': 'ONE_DAY',
  '1y': 'ONE_DAY'
};

// Zod schemas for Coinbase API responses
const CoinbaseTickerSchema = z.object({
  price: z.string(),
  time: z.string()
});

const CoinbaseCandleSchema = z.array(z.union([z.string(), z.number()])).length(6);

const CoinbaseResponseSchema = z.object({
  ticker: CoinbaseTickerSchema,
  candles: z.array(CoinbaseCandleSchema)
});

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'BTC-USD';
  const timeframe = searchParams.get('tf') || 'ytd';
  
  try {
    
    const granularity = timeframeToGranularity[timeframe] || 'ONE_DAY';
    
    // Calculate start and end times
    const end = new Date();
    const start = new Date();
    if (timeframe === '30d') {
      start.setDate(start.getDate() - 30);
    } else if (timeframe === '6m') {
      start.setMonth(start.getMonth() - 6);
    } else if (timeframe === 'ytd') {
      start.setMonth(0, 1); // January 1st
    } else if (timeframe === '1y') {
      start.setFullYear(start.getFullYear() - 1);
    }
    
    const startISO = start.toISOString();
    const endISO = end.toISOString();
    
    const candlesUrl = `${PROXY_HOST}/coinbase/api/v3/brokerage/products/${symbol}/candles?granularity=${granularity}&start=${startISO}&end=${endISO}`;
    console.log(`🛰️ [route] coinbase request: symbol=${symbol}, tf=${timeframe}, granularity=${granularity}, start=${startISO}, end=${endISO}`);
    console.log(`🛰️ [route] coinbase candles URL: ${candlesUrl}`);
    
    // Fetch candles first (required), ticker is optional
    const candlesResponse = await fetch(candlesUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/json,text/plain,*/*'
      }
    });
    
    if (!candlesResponse.ok) {
      console.log(`❌ [route] coinbase candles failed: status=${candlesResponse.status}`);
      // Return fallback data instead of error
      return NextResponse.json({
        venue: 'coinbase',
        symbol: symbol,
        asOf: new Date().toISOString(),
        ticker: null,
        ohlcv: [],
        source: 'fallback'
      }, { status: 200 });
    }
    
    // Try to fetch ticker (optional)
    let tickerData = null;
    try {
      const tickerResponse = await fetch(`${PROXY_HOST}/coinbase/products/${symbol}/ticker`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
          'Accept': 'application/json,text/plain,*/*'
        }
      });
      
      if (tickerResponse.ok) {
        tickerData = await tickerResponse.json();
        console.log(`✅ [route] coinbase ticker ok`);
      } else {
        console.log(`⚠️ [route] coinbase ticker failed: status=${tickerResponse.status} (continuing without ticker)`);
      }
    } catch (tickerError) {
      console.log(`⚠️ [route] coinbase ticker error: ${tickerError} (continuing without ticker)`);
    }
    
    const candlesData = await candlesResponse.json();
    
    // Parse and validate candles
    const candles = z.array(CoinbaseCandleSchema).parse(candlesData);
    
    // Normalize ticker data (if available)
    let tickerNormalized = null;
    if (tickerData) {
      try {
        const ticker = CoinbaseTickerSchema.parse(tickerData);
        const price = Number(ticker.price);
        tickerNormalized = {
          bid: price * 0.999, // Approximate bid (slightly below price)
          ask: price * 1.001, // Approximate ask (slightly above price)
          mid: price,
          ts: new Date(ticker.time).toISOString()
        };
      } catch (parseError) {
        console.log(`⚠️ [route] coinbase ticker parse error: ${parseError} (continuing without ticker)`);
      }
    }
    
    // Normalize candles data (Coinbase format: [timestamp, low, high, open, close, volume])
    const ohlcv = candles.map(candle => {
      const [timestamp, low, high, open, close, volume] = candle;
      const isoTime = new Date(Number(timestamp) * 1000).toISOString();
      return [isoTime, Number(open), Number(high), Number(low), Number(close), Number(volume)];
    });
    
    console.log(`📊 [route] coinbase candles: received ${candles.length} bars, normalized ${ohlcv.length} bars`);
    
    // Guard: if no candles, return empty response
    if (ohlcv.length === 0) {
      console.log(`⚠️ [route] coinbase: no candles returned, returning empty response`);
      return NextResponse.json({
        venue: 'coinbase',
        symbol: symbol,
        asOf: new Date().toISOString(),
        ticker: null,
        ohlcv: [],
        source: 'empty'
      }, { status: 200 });
    }
    
    // Limit to 300 bars
    const limitedOhlcv = ohlcv.slice(-300);
    
    const response = {
      venue: 'coinbase',
      symbol: symbol,
      asOf: new Date().toISOString(),
      ticker: tickerNormalized,
      ohlcv: limitedOhlcv,
      source: 'live'
    };
    
    console.log(`✅ [route] coinbase ok: bars=${limitedOhlcv.length}, symbol=${symbol}, ticker=${tickerNormalized ? 'ok' : 'none'}`);
    
    return NextResponse.json(response, {
      headers: {
        'x-debug-coinbase-branch': 'proxy',
        'x-debug-proxy-host': PROXY_HOST,
        'x-upstream-candles-status': candlesResponse.status.toString(),
        'x-upstream-ticker-status': tickerData ? '200' : 'none'
      }
    });
    
  } catch (error) {
    console.log(`❌ [route] coinbase failed:`, error);
    
    // Return 502 so UI can drop the venue
    return NextResponse.json({
      error: 'Coinbase API failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 502 });
  }
}

// Generate fallback data based on timeframe
function generateFallbackData(timeframe: string): any[] {
  const now = new Date();
  const bars: any[] = [];
  
  let intervalMs: number;
  let barCount: number;
  
  switch (timeframe) {
    case '30d':
      intervalMs = 24 * 60 * 60 * 1000; // 1 day
      barCount = 30;
      break;
    case '6m':
      intervalMs = 7 * 24 * 60 * 60 * 1000; // 1 week
      barCount = 26;
      break;
    case 'ytd':
      intervalMs = 7 * 24 * 60 * 60 * 1000; // 1 week
      barCount = 52;
      break;
    case '1y':
      intervalMs = 7 * 24 * 60 * 60 * 1000; // 1 week
      barCount = 52;
      break;
    default:
      intervalMs = 7 * 24 * 60 * 60 * 1000;
      barCount = 52;
  }
  
  // Generate synthetic data with some variation
  let basePrice = 50000;
  for (let i = 0; i < barCount; i++) {
    const timestamp = new Date(now.getTime() - (barCount - i - 1) * intervalMs);
    const variation = (Math.random() - 0.5) * 0.1; // ±5% variation
    const price = basePrice * (1 + variation);
    const high = price * (1 + Math.random() * 0.02);
    const low = price * (1 - Math.random() * 0.02);
    const volume = Math.random() * 1000;
    
    bars.push([
      timestamp.toISOString(),
      price,
      high,
      low,
      price,
      volume
    ]);
    
    basePrice = price; // Next bar starts from current price
  }
  
  return bars;
}
