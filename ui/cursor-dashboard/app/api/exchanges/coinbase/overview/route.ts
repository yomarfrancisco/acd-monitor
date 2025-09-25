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
      const yearStart = new Date(now.getFullYear(), 0, 1);
      startDate = yearStart;
    } else {
      startDate = new Date(now.getTime() - cfg.days * 24 * 60 * 60 * 1000);
    }
    
    const startISO = startDate.toISOString();

    // Build URL using server environment variable
    const base = process.env.PROXY_HOST!; // e.g. https://binance-proxy-...fly.dev/
    const url = new URL('/coinbase/products/BTC-USD/candles', base);
    url.searchParams.set('granularity', String(granularity));
    url.searchParams.set('start', startISO);
    url.searchParams.set('end', endISO);

    // Debug logging
    console.log('[coinbase] url', url.toString());
    const res = await fetch(url, { headers: { Accept: 'application/json' }});
    console.log('[coinbase] status', res.status);
    
    if (!res.ok) {
      const errorText = await res.text();
      console.log('[coinbase] text', errorText.slice(0, 120));
      return NextResponse.json({ 
        error: 'Candles fetch failed', 
        detail: errorText 
      }, { status: res.status });
    }

    // Response: [ time, low, high, open, close, volume ] newest-first
    type Row = [number, number, number, number, number, number];
    const raw: Row[] = await res.json();
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
    console.log('[coinbase] failed:', error);

    // Return 502 so UI can drop the venue
    return NextResponse.json({
      error: 'Coinbase API failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 502 });
  }
}