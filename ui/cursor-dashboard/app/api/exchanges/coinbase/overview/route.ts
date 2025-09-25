import { NextRequest, NextResponse } from 'next/server';

// Environment variables
const PROXY_HOST = process.env.PROXY_HOST ?? process.env.EXCHANGE_PROXY_ORIGIN ?? 'https://binance-proxy-broken-night-96.fly.dev';

// helpers
const DAY = 24 * 60 * 60 * 1000;

const TF_TO_RANGE = {
  '30d': { days: 30,  granularity: 21600 }, // 6h
  '6m' : { days: 180, granularity: 86400 }, // 1d
  '1y' : { days: 365, granularity: 86400 }, // 1d
  'ytd': { days: (() => {
              const now = new Date();
              const y0 = new Date(now.getFullYear(), 0, 1);
              return Math.max(1, Math.ceil((+now - +y0)/DAY));
            })(), granularity: 86400 },        // 1d
} as const;

type RawCandle = [number, number, number, number, number, number]; // [time, low, high, open, close, volume]

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get('symbol') || 'BTC-USD';
  const tf = searchParams.get('tf') || 'ytd';

  try {
    // Build the request URL. Prefer proxy if available, else hit Coinbase directly
    const base =
      process.env.PROXY_HOST?.replace(/\/+$/,'') ||
      process.env.CRYPTO_PROXY_BASE?.replace(/\/+$/,'') ||
      'https://api.exchange.coinbase.com';

    const path = base.includes('coinbase') || base.includes('http')
      ? `${base.includes('exchange.coinbase') ? '' : base}/coinbase/products/${symbol}/candles`
      : `${base}/coinbase/products/${symbol}/candles`;

    // Compute window and query
    const now = new Date();
    const { days, granularity } = TF_TO_RANGE[tf] ?? TF_TO_RANGE['ytd'];
    const start = new Date(now.getTime() - days * DAY);

    const qs = new URLSearchParams({
      start: start.toISOString(),
      end: now.toISOString(),
      granularity: String(granularity),
    });
    const url = `${path}?${qs.toString()}`;

    console.log(`[coinbase] url`, url, `tf=${tf}`, `days=${days}`, `granularity=${granularity}`);

    // Fetch + normalize
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    const raw = res.ok ? await res.json() : (() => { throw new Error(`HTTP ${res.status}`); })();

    console.log(`[coinbase] url`, url, `status`, res.status, `ok`, res.ok, `len`, Array.isArray(raw) ? raw.length : -1);

    let ohlcv = (Array.isArray(raw) ? raw : [])
      .map(([t, low, high, open, close, volume]: RawCandle) =>
        ({ ts: t * 1000, o: open, h: high, l: low, c: close, v: volume }))
      .sort((a, b) => a.ts - b.ts);

    // Fallback if empty (coarser window)
    if (!ohlcv.length) {
      const fb = new URLSearchParams({
        start: new Date(now.getTime() - 180 * DAY).toISOString(),
        end: now.toISOString(),
        granularity: '86400',
      });
      const fbUrl = `${path}?${fb.toString()}`;
      const fbRes = await fetch(fbUrl);
      const fbRaw = fbRes.ok ? await fbRes.json() : [];
      console.log(`[coinbase] fallback url`, fbUrl, `status`, fbRes.status, `len`, Array.isArray(fbRaw) ? fbRaw.length : -1);
      ohlcv = (Array.isArray(fbRaw) ? fbRaw : [])
        .map(([t, low, high, open, close, volume]: RawCandle) =>
          ({ ts: t * 1000, o: open, h: high, l: low, c: close, v: volume }))
        .sort((a, b) => a.ts - b.ts);
    }

    // Convert to our expected format: [isoTime, open, high, low, close, volume]
    const normalizedOhlcv = ohlcv.map(candle => [
      new Date(candle.ts).toISOString(),
      candle.o,
      candle.h,
      candle.l,
      candle.c,
      candle.v
    ]);

    // Try to fetch ticker (non-fatal)
    let tickerNormalized = null;
    try {
      const tickerUrl = `${base}/coinbase/products/${symbol}/ticker`;
      const tickerRes = await fetch(tickerUrl, { headers: { Accept: 'application/json' } });
      if (tickerRes.ok) {
        const tickerData = await tickerRes.json();
        const price = Number(tickerData.price);
        tickerNormalized = {
          bid: price * 0.999, // Approximate bid (slightly below price)
          ask: price * 1.001, // Approximate ask (slightly above price)
          mid: price,
          ts: new Date(tickerData.time).toISOString()
        };
        console.log(`[coinbase] ticker ok: price=${price}`);
      } else {
        console.log(`[coinbase] ticker failed: status=${tickerRes.status} (continuing without ticker)`);
      }
    } catch (tickerError) {
      console.log(`[coinbase] ticker error: ${tickerError} (continuing without ticker)`);
    }

    console.log(`[coinbase] final result: bars=${normalizedOhlcv.length}, ticker=${tickerNormalized ? 'ok' : 'none'}`);

    return NextResponse.json({
      venue: 'coinbase',
      symbol: symbol,
      asOf: new Date().toISOString(),
      ticker: tickerNormalized,
      ohlcv: normalizedOhlcv,
      source: 'live'
    }, {
      headers: {
        'x-debug-coinbase-branch': 'proxy-fixed',
        'x-debug-proxy-host': PROXY_HOST,
        'x-debug-candles-count': normalizedOhlcv.length.toString(),
        'x-debug-ticker-status': tickerNormalized ? 'ok' : 'none'
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