import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

// Environment variables
const PROXY_HOST = process.env.PROXY_HOST ?? process.env.EXCHANGE_PROXY_ORIGIN ?? 'https://binance-proxy-broken-night-96.fly.dev';

// Timeframe to interval mapping for Coinbase
const timeframeToInterval: Record<string, string> = {
  '30d': '2h',
  '6m': '12h', 
  'ytd': '1d',
  '1y': '1d'
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
  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get('symbol') || 'BTC-USD';
    const timeframe = searchParams.get('tf') || 'ytd';
    
    const interval = timeframeToInterval[timeframe] || '1d';
    
    console.log(`🛰️ [route] coinbase request: symbol=${symbol}, tf=${timeframe}, interval=${interval}`);
    
    // Fetch ticker and candles in parallel
    const [tickerResponse, candlesResponse] = await Promise.all([
      fetch(`${PROXY_HOST}/coinbase/products/${symbol}/ticker`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
          'Accept': 'application/json,text/plain,*/*'
        }
      }),
      fetch(`${PROXY_HOST}/coinbase/products/${symbol}/candles?granularity=${interval}&limit=300`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
          'Accept': 'application/json,text/plain,*/*'
        }
      })
    ]);
    
    if (!tickerResponse.ok) {
      console.log(`❌ [route] coinbase ticker failed: status=${tickerResponse.status}`);
      return NextResponse.json({ error: 'Ticker fetch failed' }, { status: tickerResponse.status });
    }
    
    if (!candlesResponse.ok) {
      console.log(`❌ [route] coinbase candles failed: status=${candlesResponse.status}`);
      return NextResponse.json({ error: 'Candles fetch failed' }, { status: candlesResponse.status });
    }
    
    const tickerData = await tickerResponse.json();
    const candlesData = await candlesResponse.json();
    
    // Parse and validate
    const ticker = CoinbaseTickerSchema.parse(tickerData);
    const candles = z.array(CoinbaseCandleSchema).parse(candlesData);
    
    // Normalize ticker data
    const price = Number(ticker.price);
    const tickerNormalized = {
      bid: price * 0.999, // Approximate bid (slightly below price)
      ask: price * 1.001, // Approximate ask (slightly above price)
      mid: price,
      ts: new Date(ticker.time).toISOString()
    };
    
    // Normalize candles data (Coinbase format: [timestamp, low, high, open, close, volume])
    const ohlcv = candles.map(candle => {
      const [timestamp, low, high, open, close, volume] = candle;
      const isoTime = new Date(Number(timestamp) * 1000).toISOString();
      return [isoTime, Number(open), Number(high), Number(low), Number(close), Number(volume)];
    });
    
    // Limit to 300 bars
    const limitedOhlcv = ohlcv.slice(-300);
    
    const response = {
      venue: 'coinbase',
      symbol: symbol,
      asOf: new Date().toISOString(),
      ticker: tickerNormalized,
      ohlcv: limitedOhlcv
    };
    
    console.log(`✅ [route] coinbase ok: bars=${limitedOhlcv.length}, symbol=${symbol}`);
    
    return NextResponse.json(response, {
      headers: {
        'x-debug-coinbase-branch': 'proxy',
        'x-debug-proxy-host': PROXY_HOST,
        'x-upstream-ticker-status': tickerResponse.status.toString(),
        'x-upstream-candles-status': candlesResponse.status.toString()
      }
    });
    
  } catch (error) {
    console.log(`❌ [route] coinbase failed:`, error);
    return NextResponse.json(
      { 
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      }, 
      { status: 500 }
    );
  }
}
