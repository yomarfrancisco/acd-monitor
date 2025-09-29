import { NextResponse } from "next/server";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE = process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE;
export const runtime = "nodejs";

// Timeframe to interval mapping for Bybit v5
function timeframeToInterval(timeframe: string): string {
  const mapping: Record<string, string> = {
    "30d": "120",  // 2h in minutes
    "6m": "720",   // 12h in minutes
    "1y": "D",     // 1d
    "ytd": "D"     // 1d
  };
  return mapping[timeframe] || "120";
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "30d";
  const interval = timeframeToInterval(tf);
  try {
    const url = `${BACKEND_URL}/exchanges/bybit/overview?symbol=${symbol}&tf=${tf}`;
    const r = await fetch(url, { cache: "no-store" });
    const ct = r.headers.get("content-type") || "";
    const isJson = ct.includes("application/json");
    const data = isJson ? await r.json() : null;
    if (r.ok && Array.isArray(data?.ohlcv) && data.ohlcv.length > 0) {
      return NextResponse.json(data, { status: 200 });
    }
  } catch {}
  try {
    const [barsRes, tkRes] = await Promise.all([
      fetch(`${PROXY_BASE}/bybit/v5/market/kline?category=linear&symbol=${symbol}&interval=${interval}&limit=300`, { cache: "no-store" }),
      fetch(`${PROXY_BASE}/bybit/v5/market/tickers?category=linear&symbol=${symbol}`, { cache: "no-store" }),
    ]);
    const barsJson = await barsRes.json();
    const tkJson = await tkRes.json();
    const list = ((barsJson.result || {}).list) || [];
    const ohlcv = list.reverse().map((c: any[]) => [
      new Date(Number(c[0])).toISOString(), +c[1], +c[2], +c[3], +c[4], +c[5]
    ]);
    const d = ((tkJson.result || {}).list || [])[0] || {};
    const bid = +(d.bid1Price || 0), ask = +(d.ask1Price || 0);
    const payload = {
      venue: "bybit",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid, ask, mid: bid && ask ? (bid + ask)/2 : 0, ts: new Date().toISOString() },
      ohlcv,
    };
    if (ohlcv.length > 0) return NextResponse.json(payload, { status: 200 });
  } catch (e) {
    console.error("[UI API bybit] fallback failed:", e);
  }
  return NextResponse.json({ venue: "bybit", symbol, asOf: new Date().toISOString(), ticker: { bid:0, ask:0, mid:0, ts:new Date().toISOString() }, ohlcv: [], error: "bybit_unavailable" }, { status: 502 });
}
