import { NextResponse } from "next/server";
import { z } from "zod";

export const runtime = "nodejs";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001";
const PROXY_BASE =
  process.env.PROXY_HOST ??
  process.env.NEXT_PUBLIC_BINANCE_PROXY_BASE ??
  "https://binance-proxy-broken-night-96.fly.dev";

// ---- Kraken response shapes (permissive) ----
const KrakenOHLC = z.object({
  error: z.array(z.any()).optional(),
  result: z.record(z.union([z.array(z.any()), z.number()])), // Accept arrays or numbers (like 'last')
});

const KrakenTicker = z.object({
  error: z.array(z.any()).optional(),
  result: z.record(z.any()), // Accept any structure, we'll extract bid/ask
});

// Utility: first value from object map
function firstValue<T>(obj: Record<string, T>): T | undefined {
  for (const k in obj) return obj[k];
  return undefined;
}

// Map Kraken pair for BTCUSDT -> XBTUSDT (with fallback)
function toKrakenPair(symbol: string): string {
  if (symbol.toUpperCase() === "BTCUSDT") return "XBTUSDT";
  return symbol.toUpperCase();
}

// Get fallback pair for unknown asset errors
function getKrakenFallbackPair(pair: string): string | null {
  if (pair === "XBTUSDT") return "XBTUSD";
  return null;
}

// Timeframe to interval mapping for Kraken
function timeframeToInterval(timeframe: string): number {
  const mapping: Record<string, number> = {
    "30d": 120,   // 2h in minutes
    "6m": 720,    // 12h in minutes
    "1y": 1440,   // 1d in minutes
    "ytd": 1440   // 1d in minutes
  };
  return mapping[timeframe] || 120;
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const symbol = searchParams.get("symbol") ?? "BTCUSDT";
  const tf = searchParams.get("tf") ?? "30d";
  const interval = timeframeToInterval(tf);
  
  // Server-side diagnostics
  console.log(`🛰️ [route] kraken env: PROXY_HOST=${process.env.PROXY_HOST}`);
  console.log(`🛰️ [route] kraken env: NEXT_PUBLIC_BINANCE_PROXY_BASE=${process.env.NEXT_PUBLIC_BINANCE_PROXY_BASE}`);
  console.log(`🛰️ [route] kraken timeframe: ${tf} → interval: ${interval}`);

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
  let krPair = toKrakenPair(symbol);
  let fallbackAttempted = false;
  
  while (true) {
    try {
      const ohlcUrl = `${PROXY_BASE}/kraken/0/public/OHLC?pair=${encodeURIComponent(krPair)}&interval=${interval}`;
      const tickerUrl = `${PROXY_BASE}/kraken/0/public/Ticker?pair=${encodeURIComponent(krPair)}`;
      
      console.log(`🛰️ [route] kraken request: ${ohlcUrl} pair=${krPair}`);

    // Use our proxy's kraken endpoints
    const [ohlcRes, tickRes] = await Promise.all([
      fetch(ohlcUrl, { cache: "no-store" }),
      fetch(tickerUrl, { cache: "no-store" }),
    ]);

      if (!ohlcRes.ok || !tickRes.ok) {
        const t1 = await ohlcRes.text().catch(() => "");
        const t2 = await tickRes.text().catch(() => "");
        console.log(`❌ [route] kraken failed: ohlc_status=${ohlcRes.status} ohlc_body=${t1.slice(0, 300)} ticker_status=${tickRes.status} ticker_body=${t2.slice(0, 300)}`);
        
        // Check for unknown asset pair error and try fallback
        if (!fallbackAttempted && (t1.includes("EQuery:Unknown asset pair") || t2.includes("EQuery:Unknown asset pair"))) {
          const fallbackPair = getKrakenFallbackPair(krPair);
          if (fallbackPair) {
            console.log(`↩️ [route] kraken fallback: ${krPair} → ${fallbackPair} (unknown pair)`);
            krPair = fallbackPair;
            fallbackAttempted = true;
            continue; // Retry with fallback pair
          }
        }
        throw new Error(`proxy bad: ohlc=${ohlcRes.status}(${t1.slice(0, 120)}) ticker=${tickRes.status}(${t2.slice(0, 120)})`);
      }

      const ohlcJson = KrakenOHLC.parse(await ohlcRes.json());
      const tickJson = KrakenTicker.parse(await tickRes.json());

      // Check for Kraken API errors
      if (ohlcJson.error && ohlcJson.error.length > 0) {
        const errorMsg = ohlcJson.error.join(", ");
        if (!fallbackAttempted && errorMsg.includes("EQuery:Unknown asset pair")) {
          const fallbackPair = getKrakenFallbackPair(krPair);
          if (fallbackPair) {
            console.log(`↩️ [route] kraken fallback: ${krPair} → ${fallbackPair} (unknown pair)`);
            krPair = fallbackPair;
            fallbackAttempted = true;
            continue; // Retry with fallback pair
          }
        }
        throw new Error(`Kraken API error: ${errorMsg}`);
      }

      // Extract first pair arrays from result
      const pairBars = firstValue(ohlcJson.result);
      if (!Array.isArray(pairBars)) {
        throw new Error("proxy parse: OHLC payload missing array");
      }

      // Normalize Kraken OHLC (8-field format: [time, open, high, low, close, vwap, volume, count])
      const bars = pairBars
        .map((bar: any[]) => {
          if (!Array.isArray(bar) || bar.length < 5) {
            return null; // Skip invalid bars
          }
          const [ts, o, h, l, c, vwap, volume, count] = bar;
          return [
            new Date(Number(ts) * 1000).toISOString(), // Convert seconds to ISO string
            Number(o) || 0, // Open
            Number(h) || 0, // High
            Number(l) || 0, // Low
            Number(c) || 0, // Close
            Number(volume) || 0, // Volume (use volume field, not vwap)
          ];
        })
        .filter(bar => bar !== null) // Remove invalid bars
        .slice(-300); // Limit to last 300 bars

      // Extract ticker data
      const tickerData = firstValue(tickJson.result);
      let bid = 0, ask = 0;
      
      if (tickerData && typeof tickerData === 'object') {
        // Handle both array and object formats for bid/ask
        if (Array.isArray(tickerData.b)) {
          bid = Number(tickerData.b[0]) || 0;
        } else if (typeof tickerData.b === 'string') {
          bid = Number(tickerData.b) || 0;
        }
        
        if (Array.isArray(tickerData.a)) {
          ask = Number(tickerData.a[0]) || 0;
        } else if (typeof tickerData.a === 'string') {
          ask = Number(tickerData.a) || 0;
        }
      }
      
      const mid = bid && ask ? (bid + ask) / 2 : 0;
      
      console.log(`✅ [route] kraken ok: bars=${bars.length} pair=${krPair}`);

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
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      console.log(`❌ [route] kraken failed: err=${errorMsg}`);
      
      // If we haven't tried fallback yet and this is an unknown pair error, try fallback
      if (!fallbackAttempted && errorMsg.includes("EQuery:Unknown asset pair")) {
        const fallbackPair = getKrakenFallbackPair(krPair);
        if (fallbackPair) {
          console.log(`↩️ [route] kraken fallback: ${krPair} → ${fallbackPair} (unknown pair)`);
          krPair = fallbackPair;
          fallbackAttempted = true;
          continue; // Retry with fallback pair
        }
      }
      
      // If we've tried fallback or no fallback available, break out of retry loop
      break;
    }
  }
  
  // If we get here, all attempts failed
  return NextResponse.json(
    {
      venue: "kraken",
      symbol: symbol.toUpperCase(),
      asOf: new Date().toISOString(),
      ticker: { bid: 0, ask: 0, mid: 0, ts: new Date().toISOString() },
      ohlcv: [],
      error: "kraken_unavailable",
    },
    { status: 502 }
  );
}
