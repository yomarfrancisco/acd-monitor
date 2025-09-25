import { NextRequest, NextResponse } from 'next/server';
import { z } from "zod";

// Environment variables
const PROXY_HOST = process.env.PROXY_HOST ?? process.env.EXCHANGE_PROXY_ORIGIN ?? 'https://binance-proxy-broken-night-96.fly.dev';

// Zod validation for timeframe
const TF = z.enum(["30d", "6m", "1y", "ytd"]);
type Timeframe = z.infer<typeof TF>;

// helpers
const DAY = 24 * 60 * 60 * 1000;

const TIMEFRAME_CFG = {
  "30d": { days: 30,  granularity: 21600 }, // 6h
  "6m":  { days: 180, granularity: 86400 }, // 1d
  "1y":  { days: 365, granularity: 86400 }, // 1d
  "ytd": { days: 365, granularity: 86400 }, // 1d (bounded by start-of-year at runtime)
} as const;

type RawCandle = [number, number, number, number, number, number]; // [time, low, high, open, close, volume]

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'BTC-USD';
  const tf = TF.parse(searchParams.get('tf') ?? 'ytd'); // <- narrows to Timeframe

  try {
    // Build the request URL using proxy
    const base = process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE || PROXY_HOST;
    const path = `${base}/coinbase/products/${symbol}/candles`;

    // Compute window and query
    const now = new Date();
    const { days, granularity } = TIMEFRAME_CFG[tf]; // <- type-safe now
    
    // For YTD, clamp to start of year
    let start: Date;
    if (tf === 'ytd') {
      const y0 = new Date(now.getFullYear(), 0, 1);
      start = y0;
    } else {
      start = new Date(now.getTime() - days * DAY);
    }

    const startISO = start.toISOString();
    const endISO = now.toISOString();
    const url = `${path}?granularity=${granularity}&start=${startISO}&end=${endISO}`;

    // Add compact logging (only in Preview)
    const dbg = process.env.NEXT_PUBLIC_DATA_MODE !== "production";
    if (dbg) console.log("[coinbase] GET candles", { symbol, tf, startISO, endISO, granularity, url });

    // Fetch via our proxy
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error("[coinbase] HTTP", res.status, text);
      return NextResponse.json({ error: "Candles fetch failed" }, { status: res.status });
    }

    type RawRow = [number, number, number, number, number, number]; // [time, low, high, open, close, volume]
    const raw: RawRow[] = await res.json();

    const ohlcv = raw
      .map(([time, low, high, open, close, volume]) => ({
        ts: time * 1000,
        o: open,
        h: high,
        l: low,
        c: close,
        v: volume,
      }))
      .sort((a, b) => a.ts - b.ts);

    // Convert to our expected format: [isoTime, open, high, low, close, volume]
    const normalizedOhlcv = ohlcv.map(candle => [
      new Date(candle.ts).toISOString(),
      candle.o,
      candle.h,
      candle.l,
      candle.c,
      candle.v
    ]);

    console.log(`[coinbase] final result: bars=${normalizedOhlcv.length}`);

    return NextResponse.json({
      venue: 'coinbase',
      symbol,
      asOf: new Date().toISOString(),
      ticker: { price: ohlcv.length ? ohlcv[ohlcv.length - 1].c : null },
      ohlcv: normalizedOhlcv,
      source: 'live'
    }, {
      headers: {
        'x-debug-coinbase-branch': 'proxy-fixed',
        'x-debug-proxy-host': PROXY_HOST,
        'x-debug-candles-count': normalizedOhlcv.length.toString()
      }
    });

  } catch (error) {
    console.log(`[coinbase] failed:`, error);

    // Return 502 so UI can drop the venue
    return NextResponse.json({
      error: 'Coinbase API failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 502 });
  }
}