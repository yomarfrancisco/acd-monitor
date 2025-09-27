import { NextResponse } from "next/server";
import { z } from "zod";

export const runtime = "nodejs";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE =
  process.env.NEXT_PUBLIC_BINANCE_PROXY_BASE ??
  "https://binance-proxy-broken-night-96.fly.dev";

// ---- Kraken response shapes ----
const KrakenOHLC = z.object({
  error: z.array(z.any()).optional(),
  result: z
    .object({
      last: z.number().optional(),
    })
    .catchall(
      z.array(
        z.tuple([
          z.number(), // ts (seconds)
          z.string(), // o
          z.string(), // h
          z.string(), // l
          z.string(), // c
          z.string(), // v
          z.number().optional(), // trade count (ignored)
        ])
      )
    ),
});

const KrakenTicker = z.object({
  error: z.array(z.any()).optional(),
  result: z.record(
    z.object({
      a: z.tuple([z.string(), z.string().optional(), z.string().optional()]), // ask, ...
      b: z.tuple([z.string(), z.string().optional(), z.string().optional()]), // bid, ...
      // other fields ignored
    })
  ),
});

// Utility: first value from object map
function firstValue<T>(obj: Record<string, T>): T | undefined {
  for (const k in obj) return obj[k];
  return undefined;
}

// Map Kraken pair for BTCUSDT -> XBTUSDT
function toKrakenPair(symbol: string): string {
  if (symbol.toUpperCase() === "BTCUSDT") return "XBTUSDT";
  return symbol.toUpperCase();
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "5m";

  // --- 1) Try backend first ---
  try {
    const url = `${BACKEND_URL}/exchanges/kraken/overview?symbol=${symbol}&tf=${tf}`;
    const res = await fetch(url, { cache: "no-store" });
    const ctype = res.headers.get("content-type") || "";
    const isJson = ctype.includes("application/json");
    let data: unknown = null;
    if (isJson) data = await res.json();

    console.log(
      `[UI API KRK] backend → ${res.status}, json=${isJson}, bars=${
        (data as any)?.ohlcv?.length ?? "n/a"
      }`
    );

    if (
      res.ok &&
      isJson &&
      data &&
      Array.isArray((data as any).ohlcv) &&
      (data as any).ohlcv.length > 0
    ) {
      return NextResponse.json(data, { status: 200 });
    }
  } catch (e) {
    console.log("[UI API KRK] backend fetch threw → using proxy fallback", e);
  }

  // --- 2) Direct proxy fallback via Fly multi-exchange proxy ---
  try {
    const krPair = toKrakenPair(symbol);
    // Map timeframe → minutes per Kraken:
    // supports: 1, 5, 15, 30, 60, 240, 1440, 10080, 21600
    const intervalMap: Record<string, number> = {
      "1m": 1,
      "5m": 5,
      "15m": 15,
      "30m": 30,
      "1h": 60,
      "4h": 240,
      "1d": 1440,
    };
    const interval = intervalMap[tf] ?? 5;

    // Use our proxy's kraken endpoints
    const [ohlcRes, tickRes] = await Promise.all([
      fetch(
        `${PROXY_BASE}/kraken/ohlc?pair=${encodeURIComponent(
          krPair
        )}&interval=${interval}`,
        { cache: "no-store" }
      ),
      fetch(
        `${PROXY_BASE}/kraken/ticker?pair=${encodeURIComponent(krPair)}`,
        { cache: "no-store" }
      ),
    ]);

    if (!ohlcRes.ok || !tickRes.ok) {
      const t1 = await ohlcRes.text().catch(() => "");
      const t2 = await tickRes.text().catch(() => "");
      throw new Error(`proxy bad: ohlc=${ohlcRes.status}(${t1.slice(0, 120)}) ticker=${tickRes.status}(${t2.slice(0, 120)})`);
    }

    const ohlcJson = KrakenOHLC.parse(await ohlcRes.json());
    const tickJson = KrakenTicker.parse(await tickRes.json());

    // Extract first pair arrays from result
    const pairBars = firstValue(ohlcJson.result);
    if (!Array.isArray(pairBars)) {
      throw new Error("proxy parse: OHLC payload missing array");
    }

    const bars = pairBars.map(([ts, o, h, l, c, v]) => [
      new Date(Number(ts) * 1000).toISOString(),
      +o,
      +h,
      +l,
      +c,
      +v,
    ]);

    const t = firstValue(tickJson.result);
    const bid = t ? Number(t.b[0]) : 0;
    const ask = t ? Number(t.a[0]) : 0;
    const mid = bid && ask ? (bid + ask) / 2 : 0;

    console.log(`[UI API KRK] using proxy fallback (bars=${bars.length})`);

    if (bars.length === 0) {
      throw new Error("proxy returned 0 bars");
    }

    const payload = {
      venue: "kraken" as const,
      symbol: symbol.toUpperCase(),
      asOf: new Date().toISOString(),
      ticker: {
        bid,
        ask,
        mid,
        ts: new Date().toISOString(),
      },
      ohlcv: bars,
    };

    return NextResponse.json(payload, { status: 200 });
  } catch (err) {
    console.error("[UI API KRK] proxy fallback failed:", err);
    return NextResponse.json(
      {
        venue: "kraken",
        symbol: symbol.toUpperCase(),
        asOf: new Date().toISOString(),
        ticker: { bid: 0, ask: 0, mid: 0, ts: new Date().toISOString() },
        ohlcv: [],
        error: "kraken_unavailable",
      },
      { status: 200 }
    );
  }
}
