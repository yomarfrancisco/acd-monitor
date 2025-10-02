import { NextResponse } from "next/server";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE = process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE;
export const runtime = "nodejs";

function okxInst(symbol: string) {
  // BTCUSDT -> BTC-USDT (fix double dash issue)
  return symbol.replace("USDT", "-USDT").replace("USD", "-USD").replace("--", "-");
}

// Timeframe to interval mapping for OKX
function timeframeToInterval(timeframe: string): string {
  const mapping: Record<string, string> = {
    "30d": "2H",
    "6m": "12H", 
    "1y": "1D",
    "ytd": "1D"
  };
  return mapping[timeframe] || "2H";
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "30d";
  const interval = timeframeToInterval(tf);
  
  // Server-side diagnostics
  console.log(`🛰️ [route] okx env: NEXT_PUBLIC_CRYPTO_PROXY_BASE=${PROXY_BASE}`);
  console.log(`🛰️ [route] okx timeframe: ${tf} → interval: ${interval}`);
  
  try {
    const url = `${BACKEND_URL}/exchanges/okx/overview?symbol=${symbol}&tf=${tf}`;
    const r = await fetch(url, { cache: "no-store" });
    const ct = r.headers.get("content-type") || "";
    const isJson = ct.includes("application/json");
    const data = isJson ? await r.json() : null;
    if (r.ok && Array.isArray(data?.ohlcv) && data.ohlcv.length > 0) {
      return NextResponse.json(data, { status: 200 });
    }
  } catch {}
  try {
    const inst = okxInst(symbol);
    const candlesUrl = `${PROXY_BASE}/okx/market/candles?instId=${inst}&bar=${interval}&limit=300`;
    const tickerUrl = `${PROXY_BASE}/okx/market/ticker?instId=${inst}`;
    
    console.log(`🛰️ [route] okx request: ${candlesUrl}`);
    console.log(`🛰️ [route] okx request: ${tickerUrl}`);
    
    const [barsRes, tkRes] = await Promise.all([
      fetch(candlesUrl, { cache: "no-store" }),
      fetch(tickerUrl, { cache: "no-store" }),
    ]);
    // Check response status and log diagnostics
    if (!barsRes.ok || !tkRes.ok) {
      const barsText = await barsRes.text().catch(() => "");
      const tickerText = await tkRes.text().catch(() => "");
      console.log(`❌ [route] okx failed: bars_status=${barsRes.status} bars_body=${barsText.slice(0, 300)} ticker_status=${tkRes.status} ticker_body=${tickerText.slice(0, 300)}`);
      throw new Error(`OKX proxy failed: bars=${barsRes.status}, ticker=${tkRes.status}`);
    }
    
    const barsJson = await barsRes.json();
    const tkJson = await tkRes.json();
    const data = (barsJson.data || []).reverse();
    const ohlcv = data.map((c: any[]) => [
      new Date(Number(c[0])).toISOString(), +c[1], +c[2], +c[3], +c[4], +c[5]
    ]);
    const d = (tkJson.data || [])[0] || {};
    const bid = +(d.bidPx || 0), ask = +(d.askPx || 0);
    
    console.log(`✅ [route] okx ok: bars=${ohlcv.length}`);
    
    const payload = {
      venue: "okx",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid, ask, mid: bid && ask ? (bid + ask)/2 : 0, ts: new Date().toISOString() },
      ohlcv,
    };
    if (ohlcv.length > 0) return NextResponse.json(payload, { status: 200 });
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : String(e);
    console.log(`❌ [route] okx failed: err=${errorMsg}`);
  }
  return NextResponse.json({ venue: "okx", symbol, asOf: new Date().toISOString(), ticker: { bid:0, ask:0, mid:0, ts:new Date().toISOString() }, ohlcv: [], error: "okx_unavailable" }, { status: 502 });
}
