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

  // Debug logging helper (Preview only)
  const dbg = process.env.NEXT_PUBLIC_DATA_MODE !== "production";
  function log(...args: any[]) { if (dbg) console.log("[coinbase]", ...args); }

  try {
    const { granularity } = TIMEFRAME_CFG[tf]; // <- type-safe now
    
    // granularity is seconds; convert to ms
    const gMs = granularity * 1000;
    const now = Date.now();

    // snap end to the last full bucket boundary (avoid partial future candle)
    const endTs = Math.floor(now / gMs) * gMs;

    // desired range by timeframe
    const desiredDays = TIMEFRAME_CFG[tf].days;

    // compute a naïve start by days, then cap to 300 buckets
    const naiveStartTs = endTs - desiredDays * 24 * 60 * 60 * 1000;
    const maxStartBy300 = endTs - 300 * gMs;
    let startTs = Math.max(naiveStartTs, maxStartBy300);

    // ensure start ≤ end - 1 bucket
    if (startTs > endTs - gMs) startTs = endTs - gMs;

    // YTD: clamp start to Jan 1 UTC if later than current start
    if (tf === "ytd") {
      const jan1UTC = Date.UTC(new Date(endTs).getUTCFullYear(), 0, 1, 0, 0, 0, 0);
      startTs = Math.max(startTs, jan1UTC);
      // snap start to bucket boundary
      startTs = Math.floor(startTs / gMs) * gMs;
    }

    // final bucket count
    const bucketCount = Math.floor((endTs - startTs) / gMs);
    log({ tf, symbol, granularity, gMs, startTs, endTs, bucketCount, startISO: new Date(startTs).toISOString(), endISO: new Date(endTs).toISOString() });

    const startISO = new Date(startTs).toISOString();
    const endISO = new Date(endTs).toISOString();

    const url = `${process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE}/coinbase/products/${symbol}/candles?granularity=${granularity}&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`;

    log("GET", url);

    const res = await fetch(url, { headers: { "Accept": "application/json" } });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      log("HTTP", res.status, "error body:", txt);
      return NextResponse.json({ error: "Candles fetch failed" }, { status: res.status });
    }

    type RawRow = [number, number, number, number, number, number]; // [time, low, high, open, close, volume]
    const raw: RawRow[] = await res.json();

    // Coinbase returns newest-first; convert to ascending
    raw.sort((a, b) => a[0] - b[0]);

    const ohlcv = raw.map(([t, low, high, open, close, volume]) => ({
      ts: t * 1000,
      o: open, h: high, l: low, c: close, v: volume
    }));

    // Convert to our expected format: [isoTime, open, high, low, close, volume]
    const normalizedOhlcv = ohlcv.map(candle => [
      new Date(candle.ts).toISOString(),
      candle.o,
      candle.h,
      candle.l,
      candle.c,
      candle.v
    ]);

    log("final result: bars=", normalizedOhlcv.length);

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
    log("failed:", error);

    // Return 502 so UI can drop the venue
    return NextResponse.json({
      error: 'Coinbase API failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 502 });
  }
}