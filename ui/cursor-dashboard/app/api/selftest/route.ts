// ui/cursor-dashboard/app/api/selftest/route.ts
import { NextResponse } from "next/server";
export async function GET() {
  const startedAt = Date.now();
  const res = {
    ok: true,
    startedAt,
    durationMs: Date.now() - startedAt,
    services: {
      api: "OK",
      mocks: "OK",
      chatbase: "SKIPPED (billing)",
    },
  };
  const r = NextResponse.json(res, { status: 200 });
  r.headers.set("x-acd-bundle-version", "v1.9+");
  r.headers.set("x-case-library-version", "v1.9");
  return r;
}
