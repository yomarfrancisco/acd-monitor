import { NextResponse } from "next/server";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE = process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE;
export const runtime = "nodejs";

function okxInst(symbol: string) {
  // BTCUSDT -> BTC-USDT
  return symbol.replace("USDT", "-USDT").replace("USD", "-USD");
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
    const [barsRes, tkRes] = await Promise.all([
      fetch(`${PROXY_BASE}/okx/market/candles?instId=${inst}&bar=${interval}&limit=300`, { cache: "no-store" }),
      fetch(`${PROXY_BASE}/okx/market/ticker?instId=${inst}`, { cache: "no-store" }),
    ]);
    const barsJson = await barsRes.json();
    const tkJson = await tkRes.json();
    const data = (barsJson.data || []).reverse();
    const ohlcv = data.map((c: any[]) => [
      new Date(Number(c[0])).toISOString(), +c[1], +c[2], +c[3], +c[4], +c[5]
    ]);
    const d = (tkJson.data || [])[0] || {};
    const bid = +(d.bidPx || 0), ask = +(d.askPx || 0);
    const payload = {
      venue: "okx",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid, ask, mid: bid && ask ? (bid + ask)/2 : 0, ts: new Date().toISOString() },
      ohlcv,
    };
    if (ohlcv.length > 0) return NextResponse.json(payload, { status: 200 });
  } catch (e) {
    console.error("[UI API okx] fallback failed:", e);
  }
  return NextResponse.json({ venue: "okx", symbol, asOf: new Date().toISOString(), ticker: { bid:0, ask:0, mid:0, ts:new Date().toISOString() }, ohlcv: [], error: "okx_unavailable" }, { status: 502 });
}
