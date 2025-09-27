import { NextResponse } from "next/server";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE = process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE;
export const runtime = "nodejs";

function bybitInterval(tf: string) {
  return ({ "1m":"1", "5m":"5", "15m":"15", "30m":"30", "1h":"60", "4h":"240", "1d":"D" } as any)[tf] || "5";
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "5m";
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
    const iv = bybitInterval(tf);
    const [barsRes, tkRes] = await Promise.all([
      fetch(`${PROXY_BASE}/bybit/kline?category=spot&symbol=${symbol}&interval=${iv}&limit=288`, { cache: "no-store" }),
      fetch(`${PROXY_BASE}/bybit/tickers?category=spot&symbol=${symbol}`, { cache: "no-store" }),
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
  return NextResponse.json({ venue: "bybit", symbol, asOf: new Date().toISOString(), ticker: { bid:0, ask:0, mid:0, ts:new Date().toISOString() }, ohlcv: [], error: "bybit_unavailable" }, { status: 200 });
}
