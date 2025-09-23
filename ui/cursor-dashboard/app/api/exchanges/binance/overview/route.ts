import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get('symbol') ?? 'BTCUSDT';
  const tf = searchParams.get('tf') ?? '5m';

  const BACKEND = process.env.NEXT_PUBLIC_API_BASE
    ? `${process.env.NEXT_PUBLIC_API_BASE}`
    : `${process.env.NEXT_PUBLIC_API_BASE || ''}`; // keep existing behavior

  // Helper to map klines
  const mapBars = (rows: any[]): any[] =>
    rows.map(([t, o, h, l, c, v]: any[]) => [
      new Date(Number(t)).toISOString(),
      +o, +h, +l, +c, +v,
    ]);

  // ---- 1) Try backend first; treat any issue as hard fail ----
  try {
    const url = `${BACKEND}/exchanges/binance/overview?symbol=${symbol}&tf=${tf}`;
    const res = await fetch(url, { cache: 'no-store' });
    const isJson = res.headers.get('content-type')?.includes('application/json');
    const data = isJson ? await res.json() : null;

    console.log('[UI API] backend →', res.status, 'json=', !!isJson, 'bars=', data?.ohlcv?.length ?? 'n/a');

    if (res.ok && isJson && Array.isArray(data?.ohlcv) && data.ohlcv.length > 0) {
      // backend is good
      return NextResponse.json(data, { status: 200 });
    }

    // backend not OK or zero bars → fall through to fallback
    throw new Error(`backend-bad-${res.status}`);
  } catch (e) {
    // continue to fallback
  }

  // ---- 2) Direct Binance fallback ----
  try {
    const [klRes, tkRes] = await Promise.all([
      fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${tf}&limit=288`, { cache: 'no-store' }),
      fetch(`https://api.binance.com/api/v3/ticker/bookTicker?symbol=${symbol}`, { cache: 'no-store' }),
    ]);

    const klines = await klRes.json();
    const ticker = await tkRes.json();

    const bars = Array.isArray(klines) ? mapBars(klines) : [];
    console.log('[UI API] using direct binance fallback (bars=', bars.length, ')');

    if (bars.length > 0 && ticker?.bidPrice && ticker?.askPrice) {
      const bid = Number(ticker.bidPrice);
      const ask = Number(ticker.askPrice);
      const mid = (bid + ask) / 2;

      const payload = {
        venue: 'binance',
        symbol,
        asOf: new Date().toISOString(),
        ticker: {
          bid,
          ask,
          mid,
          ts: new Date().toISOString(),
        },
        ohlcv: bars,
      };

      // ✅ Important: Always 200 when fallback succeeds
      return NextResponse.json(payload, { status: 200 });
    }
  } catch (e) {
    console.error('[UI API] direct binance fallback failed:', e);
  }

  // ---- 3) Both paths failed → return 502 once ----
  const errorPayload = {
    venue: 'binance',
    symbol,
    asOf: new Date().toISOString(),
    ticker: { bid: 0, ask: 0, mid: 0, ts: new Date().toISOString() },
    ohlcv: [],
    error: 'binance_unavailable',
  };
  return NextResponse.json(errorPayload, { status: 502 });
}
