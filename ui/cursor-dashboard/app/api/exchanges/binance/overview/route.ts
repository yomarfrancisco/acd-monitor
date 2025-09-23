import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "5m";

  try {
    const klUrl = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${tf}&limit=288`;
    const tkUrl = `https://api.binance.com/api/v3/ticker/bookTicker?symbol=${symbol}`;

    const [klRes, tkRes] = await Promise.all([
      fetch(klUrl, { cache: "no-store" }),
      fetch(tkUrl, { cache: "no-store" }),
    ]);

    console.log(`[UI API] klines status=${klRes.status} ok=${klRes.ok} url=${klUrl}`);
    console.log(`[UI API] ticker status=${tkRes.status} ok=${tkRes.ok} url=${tkUrl}`);

    if (!klRes.ok || !tkRes.ok) {
      const klTxt = await klRes.text().catch(() => "");
      const tkTxt = await tkRes.text().catch(() => "");
      throw new Error(`binance fetch bad: kl=${klRes.status}(${klTxt.slice(0,200)}) tk=${tkRes.status}(${tkTxt.slice(0,200)})`);
    }

    const rawBars: any[] = await klRes.json();
    const ticker: any = await tkRes.json();

    const bars = (rawBars ?? []).map(([t,o,h,l,c,v]) =>
      [new Date(Number(t)).toISOString(), +o, +h, +l, +c, +v]
    );

    console.log(`[UI API] mapped bars=${bars.length}`);

    if (bars.length === 0) throw new Error("binance returned 0 bars");

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
    console.error("[UI API] direct binance failed:", err);
    return NextResponse.json({
      venue: "binance",
      symbol,
      asOf: new Date().toISOString(),
      ticker: { bid: 0, ask: 0, mid: 0, ts: new Date().toISOString() },
      ohlcv: [],
      error: "binance_unavailable"
    }, { status: 502 });
  }
}
