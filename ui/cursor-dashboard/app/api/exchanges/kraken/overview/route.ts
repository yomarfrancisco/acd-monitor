import { NextResponse } from "next/server";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE = process.env.NEXT_PUBLIC_CRYPTO_PROXY_BASE; // https://...fly.dev

function kPair(symbol: string) {
  // BTCUSDT -> XBTUSDT (Kraken uses XBT)
  if (symbol.startsWith("BTC")) return symbol.replace(/^BTC/, "XBT");
  return symbol;
}

export const runtime = "nodejs";
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "5m";
  // 1) backend
  try {
    const url = `${BACKEND_URL}/exchanges/kraken/overview?symbol=${symbol}&tf=${tf}`;
    const r = await fetch(url, { cache: "no-store" });
    const ct = r.headers.get("content-type") || "";
    const isJson = ct.includes("application/json");
    const data = isJson ? await r.json() : null;
    if (r.ok && Array.isArray(data?.ohlcv) && data.ohlcv.length > 0) {
      return NextResponse.json(data, { status: 200 });
    }
  } catch {}
  // 2) proxy fallback (direct)
  try {
    const pair = kPair(symbol);
    const [barsRes, tkRes] = await Promise.all([
      fetch(`${PROXY_BASE}/kraken/OHLC?pair=${pair}&interval=${tf.replace("m","")}`, { cache: "no-store" }),
      fetch(`${PROXY_BASE}/kraken/Ticker?pair=${pair}`, { cache: "no-store" }),
    ]);
    const barsJson = await barsRes.json();
    const tkJson = await tkRes.json();
    const list = Object.values(barsJson.result || {})[0] || [];
    const ohlcv = list.map((c: any[]) => [
      new Date(Number(c[0]) * 1000).toISOString(),
      +c[1], +c[2], +c[3], +c[4], +c[6],
    ]);
    const d: any = Object.values(tkJson.result || {})[0] || {};
    const bid = +(d.b?.[0] || 0), ask = +(d.a?.[0] || 0);
    const payload = {
      venue: "kraken",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid, ask, mid: bid && ask ? (bid + ask)/2 : 0, ts: new Date().toISOString() },
      ohlcv,
    };
    if (ohlcv.length > 0) return NextResponse.json(payload, { status: 200 });
  } catch (e) {
    console.error("[UI API kraken] fallback failed:", e);
  }
  return NextResponse.json({ venue: "kraken", symbol, asOf: new Date().toISOString(), ticker: { bid:0, ask:0, mid:0, ts:new Date().toISOString() }, ohlcv: [], error: "kraken_unavailable" }, { status: 502 });
}
