import { NextRequest, NextResponse } from 'next/server';
import { z } from "zod";

// Zod validation for timeframe
const TF = z.enum(["30d", "6m", "1y", "ytd"]);
type Timeframe = z.infer<typeof TF>;

// Allowed Coinbase granularities (seconds)
const GRAN = { '30d': 86400, '6m': 86400, '1y': 86400, 'ytd': 86400 } as const;
const daysByTf = { '30d': 30, '6m': 180, '1y': 365, 'ytd': 365 } as const;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'BTC-USD';
  const tf = TF.parse(searchParams.get('tf') ?? 'ytd');

  try {
    const g = GRAN[tf];
    const gMs = g * 1000;
    const now = Date.now();

    // snap end to bucket boundary (avoid partial candle)
    const endTs = Math.floor(now / gMs) * gMs;

    // naïve range by timeframe
    const naiveStartTs = endTs - daysByTf[tf] * 24 * 60 * 60 * 1000;

    // cap to 300 buckets (Coinbase hard limit)
    let startTs = Math.max(naiveStartTs, endTs - 300 * gMs);

    // special-case YTD: clamp to 00:00:00 **UTC** on Jan 1
    if (tf === 'ytd') {
      const jan1UTC = Date.UTC(new Date(endTs).getUTCFullYear(), 0, 1, 0, 0, 0, 0);
      startTs = Math.max(startTs, jan1UTC);
    }

    // snap start to boundary too
    startTs = Math.floor(startTs / gMs) * gMs;

    // build URL against the proxy; Coinbase path is `/products/{pair}/candles`
    const startISO = new Date(startTs).toISOString();
    const endISO   = new Date(endTs).toISOString();

    const url = `${process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE}/coinbase/products/${symbol}/candles?granularity=${g}&start=${encodeURIComponent(startISO)}&end=${encodeURIComponent(endISO)}`;

    // DEBUG (preview only)
    if (process.env.NEXT_PUBLIC_DATA_MODE !== 'production') {
      const bucketCount = Math.floor((endTs - startTs) / gMs);
      console.log('[coinbase]', { tf, symbol, g, startISO, endISO, bucketCount, url });
    }

    const r = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!r.ok) {
      const errText = await r.text().catch(()=>'');
      if (process.env.NEXT_PUBLIC_DATA_MODE !== 'production') {
        console.log('[coinbase] HTTP', r.status, errText);
      }
      return NextResponse.json({ error: 'Candles fetch failed' }, { status: r.status });
    }

    // Response: [ time, low, high, open, close, volume ] newest-first
    type Row = [number, number, number, number, number, number];
    const raw: Row[] = await r.json();
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
    if (process.env.NEXT_PUBLIC_DATA_MODE !== 'production') {
      console.log('[coinbase] failed:', error);
    }

    // Return 502 so UI can drop the venue
    return NextResponse.json({
      error: 'Coinbase API failed',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 502 });
  }
}