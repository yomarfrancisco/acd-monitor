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
  const tf = TF.parse(searchParams.get('tf') ?? 'ytd') as Tf; // after zod validation

  try {
    const cfg = TIMEFRAMES[tf]; // typed
    const gran = cfg.granularity;
    
    // YTD example - snap times and cap to ≤300 buckets
    const now = new Date();
    const end = new Date(Math.floor(now.getTime()/1000/gran)*gran*1000);  // snap down
    const maxBuckets = 300;
    const start = new Date(end.getTime() - (maxBuckets-1)*gran*1000);
    
    const qs = new URLSearchParams({
      start: start.toISOString(),
      end: end.toISOString(),
      granularity: String(gran),
    });
    
    const url = `${process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE}/coinbase/products/${symbol}/candles?${qs}`;

    // Add temporary logging (server-side)
    console.log('[coinbase] url', url);
    const r = await fetch(url, { headers: { 'User-Agent': 'acd-monitor' }});
    const text = await r.text();
    console.log('[coinbase] status', r.status, 'body', text.slice(0, 500));

    if (!r.ok) {
      return NextResponse.json({ error: 'Candles fetch failed' }, { status: r.status });
    }

    // Response: [ time, low, high, open, close, volume ] newest-first
    type Row = [number, number, number, number, number, number];
    const raw: Row[] = JSON.parse(text);
    raw.sort((a,b)=>a[0]-b[0]);

    const ohlcv = raw.map(([t, low, high, open, close, volume]) => ({
      ts: t*1000, o: open, h: high, l: low, c: close, v: volume
    }));

    return NextResponse.json({
      venue: 'coinbase',
      symbol,
      asOf: end.toISOString(),
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