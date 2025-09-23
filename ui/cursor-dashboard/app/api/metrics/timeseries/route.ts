// ui/cursor-dashboard/app/api/metrics/timeseries/route.ts
import { NextRequest, NextResponse } from "next/server";

type Band = { amber: number; red: number; critical: number };

function makeSeries(days = 30) {
  const now = new Date();
  const series: { t: string; v: number }[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setUTCDate(d.getUTCDate() - i);
    // simple mock walk
    const base = 5.8; // around amber
    const noise = Math.sin(i / 4) * 0.4 + (Math.random() - 0.5) * 0.2;
    series.push({ t: d.toISOString(), v: +(base + noise).toFixed(2) });
  }
  return series;
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const metric = searchParams.get("metric") ?? "ci";
  const timeframe = searchParams.get("timeframe") ?? "30d";
  const region = searchParams.get("region") ?? "US";
  const industry = searchParams.get("industry") ?? "CRYPTO";

  if (metric !== "ci") {
    return NextResponse.json(
      { error: "Unsupported metric", code: "bad_metric", details: { metric } },
      { status: 400 }
    );
  }

  const days =
    timeframe === "6m" ? 180 : timeframe === "1y" ? 365 : timeframe.toLowerCase() === "ytd" ? 240 : 30;

  const thresholds: Band = { amber: 6.1, red: 8.0, critical: 8.5 };

  const body = {
    series: makeSeries(days),
    baseline: 5.2, // optional reference line
    thresholds,
    context: { timeframe, region, industry },
  };

  const res = NextResponse.json(body, { status: 200 });
  res.headers.set("x-acd-bundle-version", "v1.9+");
  res.headers.set("x-case-library-version", "v1.9");
  return res;
}
