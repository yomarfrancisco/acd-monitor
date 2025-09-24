import { NextResponse } from "next/server";

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const revalidate = 0;

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";

// Timeframe to interval mapping for Binance
function timeframeToInterval(timeframe: string): string {
  const mapping: Record<string, string> = {
    "30d": "2h",
    "6m": "12h", 
    "1y": "1d",
    "ytd": "1d"
  };
  return mapping[timeframe] || "2h";
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "30d";
  const interval = timeframeToInterval(tf);

  // Log environment and region
  console.log('[UI API] runtime=node, region=', process.env.VERCEL_REGION, 'env=', process.env.NODE_ENV);

  // Control fetch to test outbound connectivity
  try {
    const ctrl = await fetch('https://httpbin.org/get', { cache: 'no-store' });
    console.log('[UI API] control httpbin status=', ctrl.status);
  } catch (e) {
    console.log('[UI API] control httpbin failed:', e);
  }

  // Backend fetch with fallback
  try {
    const url = `${BACKEND_URL}/exchanges/binance/overview?symbol=${symbol}&tf=${tf}`;
    const res = await fetch(url, { cache:'no-store' });
    const ct = res.headers.get('content-type') || '';
    const isJson = ct.includes('application/json');
    const data = isJson ? await res.json() : null;
    console.log(`[UI API] backend → ${res.status}, json=${isJson}, bars=${data?.ohlcv?.length ?? 'n/a'}`);
    if (res.ok && isJson && Array.isArray(data?.ohlcv) && data.ohlcv.length > 0) {
      return NextResponse.json(data, { 
        status: 200,
        headers: {
          'x-debug-binance-branch': 'backend',
          'x-debug-proxy-host': 'none'
        }
      });
    }
  } catch (e) {
    console.log('[UI API] backend fetch threw → will fallback:', e);
  }

  // Fallback: direct Binance via Fly.io proxy
  // Use PROXY_HOST or EXCHANGE_PROXY_ORIGIN as per UI_DEPLOYMENT_ANCHOR.md
  const PROXY_HOST = process.env.PROXY_HOST ?? process.env.EXCHANGE_PROXY_ORIGIN ?? "https://binance-proxy-broken-night-96.fly.dev";
  const PROXY_BASE = `${PROXY_HOST}/binance`;
  
  const klinesUrl = `${PROXY_BASE}/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=300`;
  const tickerUrl = `${PROXY_BASE}/api/v3/ticker/bookTicker?symbol=${symbol}`;
  
  const opt = { 
    cache: 'no-store' as RequestCache, 
    headers: {
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      'Accept': 'application/json,text/plain,*/*'
    }, 
    signal: AbortSignal.timeout(8000) 
  };

  try {
    console.log(`[UI API] using proxy fallback: ${klinesUrl}`);
    const [klRes, tkRes] = await Promise.all([
      fetch(klinesUrl, opt),
      fetch(tickerUrl, opt),
    ]);
    console.log('[UI API] klines status=', klRes.status, 'ticker status=', tkRes.status);
    
    const rawBars: any[] = klRes.ok ? await klRes.json() : [];
    const ticker: any = tkRes.ok ? await tkRes.json() : null;

    const bars = (rawBars || []).map(([t, o, h, l, c, v]) => [new Date(+t).toISOString(), +o, +h, +l, +c, +v]);
    console.log(`[UI API] using direct binance fallback (bars=${bars.length})`);

    if (bars.length > 0) {
      const bid = Number(ticker?.bidPrice ?? 0);
      const ask = Number(ticker?.askPrice ?? 0);
      const mid = bid && ask ? (bid + ask) / 2 : 0;
      
      return NextResponse.json({
        venue: 'binance', 
        symbol, 
        asOf: new Date().toISOString(),
        ticker: { bid, ask, mid, ts: new Date().toISOString() },
        ohlcv: bars
      }, { 
        status: 200,
        headers: {
          'x-debug-binance-branch': 'proxy',
          'x-debug-proxy-host': PROXY_HOST,
          'x-upstream-ticker-status': tkRes.status.toString(),
          'x-upstream-klines-status': klRes.status.toString()
        }
      });
    }
    throw new Error('fallback returned 0 bars');
  } catch (err) {
    console.error('[UI API] fallback failed:', err);
    return NextResponse.json({
      stage: 'proxy',
      status: 502,
      url: `${PROXY_BASE}/api/v3/klines`,
      bodySnippet: err instanceof Error ? err.message.substring(0, 200) : 'Unknown error',
      venue: 'binance', 
      symbol, 
      asOf: new Date().toISOString(),
      ticker: { bid: 0, ask: 0, mid: 0, ts: new Date().toISOString() },
      ohlcv: [], 
      error: 'binance_unavailable'
    }, { status: 502 });
  }
}