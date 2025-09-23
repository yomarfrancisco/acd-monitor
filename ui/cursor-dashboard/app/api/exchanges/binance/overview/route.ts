// ui/cursor-dashboard/app/api/exchanges/binance/overview/route.ts
import { NextResponse } from "next/server";
const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "5m";

  // 1) Try backend first
  try {
    const url = `${BACKEND_URL}/exchanges/binance/overview?symbol=${symbol}&tf=${tf}`;
    const res = await fetch(url, { cache: "no-store" });
    const ctype = res.headers.get("content-type") || "";
    const isJson = ctype.includes("application/json");
    let data: any = null;
    if (isJson) data = await res.json();

    console.log(`[UI API] backend → ${res.status}, json=${isJson}, bars=${data?.ohlcv?.length ?? "n/a"}`);

    if (res.ok && isJson && Array.isArray(data?.ohlcv) && data.ohlcv.length > 0) {
      return NextResponse.json(data, { status: 200 });
    }
    // fall through to direct Binance fetch
  } catch (e) {
    console.log("[UI API] backend fetch threw → using direct binance fallback", e);
  }

  // 2) Direct Binance fallback
  try {
    const [klRes, tkRes] = await Promise.all([
      fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${tf}&limit=288`, { cache: "no-store" }),
      fetch(`https://api.binance.com/api/v3/ticker/bookTicker?symbol=${symbol}`, { cache: "no-store" }),
    ]);

    if (!klRes.ok || !tkRes.ok) throw new Error(`fallback fetch bad: kl=${klRes.status} tk=${tkRes.status}`);

    const rawBars: any[] = await klRes.json();
    const ticker: any = await tkRes.json();

    const bars = (rawBars ?? []).map(([t,o,h,l,c,v]) => [new Date(Number(t)).toISOString(), +o, +h, +l, +c, +v]);
    console.log(`[UI API] using direct binance fallback (bars=${bars.length})`);
    if (bars.length === 0) throw new Error("fallback returned 0 bars");

    const bid = Number(ticker?.bidPrice ?? 0);
    const ask = Number(ticker?.askPrice ?? 0);
    const mid = bid && ask ? (bid + ask) / 2 : 0;

    return NextResponse.json({
      venue: "binance",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid, ask, mid, ts: new Date().toISOString() },
      ohlcv: bars,
    }, { status: 200 });
  } catch (err) {
    console.error("[UI API] fallback failed:", err);
    return NextResponse.json({
      venue: "binance",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid: 0, ask: 0, mid: 0, ts: new Date().toISOString() },
      ohlcv: [],
      error: "binance_unavailable",
    }, { status: 502 });
  }
}
