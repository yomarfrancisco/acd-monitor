import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const timeframe = searchParams.get("timeframe") ?? "ytd";
  
  const results: Record<string, any> = {};
  
  // Test each venue's overview endpoint
  const venues = ["binance", "okx", "bybit", "kraken"];
  
  for (const venue of venues) {
    try {
      const response = await fetch(
        `${req.url.split('/api/health/proxy')[0]}/api/exchanges/${venue}/overview?symbol=BTCUSDT&tf=${timeframe}`,
        { cache: "no-store" }
      );
      
      if (response.ok) {
        const data = await response.json();
        results[venue] = {
          ok: true,
          status: response.status,
          bars: data.ohlcv?.length ?? 0,
          venue: data.venue,
          symbol: data.symbol
        };
      } else {
        const errorText = await response.text().catch(() => "");
        results[venue] = {
          ok: false,
          status: response.status,
          note: errorText.slice(0, 200)
        };
      }
    } catch (error) {
      results[venue] = {
        ok: false,
        status: "error",
        note: error instanceof Error ? error.message : String(error)
      };
    }
  }
  
  return NextResponse.json({
    timeframe,
    timestamp: new Date().toISOString(),
    results
  });
}
