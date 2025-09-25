import { NextRequest, NextResponse } from 'next/server';
import { z } from "zod";

// Zod validation for timeframe
const TF = z.enum(["30d", "6m", "1y", "ytd"]);
type Timeframe = z.infer<typeof TF>;

// Public Exchange API granularities (seconds)
const TIMEFRAMES = {
  '30d': { days: 30,  granularity: 21600 }, // 6h
  '6m' : { days: 180, granularity: 86400 }, // 1d
  '1y' : { days: 365, granularity: 86400 }, // 1d
  'ytd': { days: 365, granularity: 86400 }, // 1d (bounded by start-of-year at runtime)
} as const;

type Tf = keyof typeof TIMEFRAMES; // '30d' | '6m' | '1y' | 'ytd'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'BTC-USD';
  const tf = TF.parse(searchParams.get('tf') ?? 'ytd') as Tf;

  try {
    const cfg = TIMEFRAMES[tf];
    const granularity = cfg.granularity;
    
    // Calculate start and end times
    const now = new Date();
    const endISO = now.toISOString();
    
    // For YTD, clamp to start of year
    let startDate: Date;
    if (tf === 'ytd') {
      startDate = new Date(new Date().getUTCFullYear(), 0, 1);
    } else {
      startDate = new Date(now.getTime() - cfg.days * 24 * 60 * 60 * 1000);
    }
    
    const startISO = startDate.toISOString();

    // Use server env var (not NEXT_PUBLIC)
    const PROXY = process.env.PROXY_HOST; // e.g., https://<LIVE_FLY_APP_HOST>
    
    // Log environment for debugging
    if (process.env.NODE_ENV !== 'production') {
      console.log('[env] PROXY_HOST=', process.env.PROXY_HOST);
    }
    
    // Build URL with fallback to direct Coinbase
    const base = PROXY ?? 'https://api.exchange.coinbase.com';
    const url = new URL(`/coinbase/products/${symbol}/candles`, PROXY ? PROXY : 'https://api.exchange.coinbase.com');
    
    // If using direct Coinbase, omit '/coinbase' prefix
    if (!PROXY) {
      url.pathname = `/products/${symbol}/candles`;
    }
    
    url.searchParams.set('granularity', String(granularity));
    url.searchParams.set('start', startISO);
    url.searchParams.set('end', endISO);

    // Add logs (only when not production)
    if (process.env.NODE_ENV !== 'production') {
      console.log('[coinbase] usingProxy=', !!PROXY);
      console.log('[coinbase] url=', url.toString());
      console.log('[coinbase] params=', { granularity, start: startISO, end: endISO });
    }

    const resp = await fetch(url, { headers: { Accept: 'application/json' }});
    
    if (process.env.NODE_ENV !== 'production') {
      console.log('[coinbase] status', resp.status);
    }
    
    if (!resp.ok) {
      const text = await resp.text();
      if (process.env.NODE_ENV !== 'production') {
        console.log('[coinbase] error body:', text.slice(0, 500));
      }
      return NextResponse.json({ 
        error: 'Candles fetch failed', 
        detail: text.slice(0, 500) 
      }, { status: resp.status });
    }

    // Response: [ time, low, high, open, close, volume ] newest-first
    type Row = [number, number, number, number, number, number];
    const raw: Row[] = await resp.json();
    raw.sort((a,b)=>a[0]-b[0]);

    const ohlcv = raw.map(([t, low, high, open, close, volume]) => ({
      ts: t*1000, o: open, h: high, l: low, c: close, v: volume
    }));

    return NextResponse.json({
      venue: 'coinbase',
      symbol,
      asOf: endISO,
      ticker: { last: ohlcv.at(-1)?.c ?? null },
      ohlcv,
    });

  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      console.log('[coinbase] failed:', error);
    }

    // Return 502 so UI can drop the venue
    return NextResponse.json({
      error: 'Coinbase API failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 502 });
  }
}