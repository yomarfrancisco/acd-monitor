import { z } from "zod";

const ZEvent = z.object({
  id: z.string().optional().default(() => `evt-${Math.random().toString(36).slice(2)}`),
  ts: z.union([z.number(), z.string(), z.date()]),
  label: z.string().default("Event"),
  color: z.string().optional(),
});
const ZEventsShapes = z.union([
  z.array(ZEvent),                          // plain array
  z.object({ events: z.array(ZEvent) }),    // { events: [...] }
  z.object({ items: z.array(ZEvent) }),     // { items: [...] }
  z.object({ data: z.array(ZEvent) }),      // { data: [...] }
]);

const toMs = (v: unknown): number | null => {
  if (typeof v === "number") {
    if (!Number.isFinite(v) || v <= 0) return null;
    return v < 1e12 ? Math.round(v * 1000) : v; // seconds → ms
  }
  if (typeof v === "string" && v) {
    const n = Date.parse(v);
    return Number.isFinite(n) ? n : null;
  }
  if (v instanceof Date) return v.getTime();
  return null;
};

export type EnvEvent = { id: string; ts: number; label: string; color?: string };

export function normalizeEvents(raw: unknown, fallback: EnvEvent[]): EnvEvent[] {
  const parsed = ZEventsShapes.safeParse(raw);
  const src =
    parsed.success
      ? (Array.isArray(parsed.data) ? parsed.data : (parsed.data as any).events || (parsed.data as any).items || (parsed.data as any).data)
      : [];

  const norm = (src as any[])
    .map((e) => {
      const ms = toMs(e.ts);
      return ms ? { id: e.id ?? `evt-${ms}`, ts: ms, label: e.label ?? "Event", color: e.color } : null;
    })
    .filter(Boolean) as EnvEvent[];

  // ensure we always have something
  return norm.length > 0 ? norm : fallback;
}

export const defaultSeeds: EnvEvent[] = [
  { id: "env-1", ts: Date.parse("2025-02-01T00:00:00Z"), label: "Regime A→B", color: "#ef4444" },
  { id: "env-2", ts: Date.parse("2025-06-01T00:00:00Z"), label: "Policy Shift", color: "#f59e0b" },
  { id: "env-3", ts: Date.parse("2025-07-01T00:00:00Z"), label: "Liquidity ↑", color: "#10b981" },
];

export async function fetchEnvEvents(timeframe: string): Promise<EnvEvent[]> {
  const res = await fetch(`/api/events?timeframe=${timeframe}`, { cache: "no-store" });
  const json = await res.json().catch(() => ({}));

  if (process.env.NEXT_PUBLIC_UI_DEBUG === "true") {
    console.log("[ENV] /api/events status", res.status);
    console.log("[ENV] keys", Object.keys(json || {}));
    console.log("[ENV] raw sample", Array.isArray(json) ? json.slice(0,3) : json?.events?.slice(0,3) ?? json?.items?.slice(0,3) ?? json?.data?.slice(0,3));
  }

  const events = normalizeEvents(json, defaultSeeds);

  if (process.env.NEXT_PUBLIC_UI_DEBUG === "true") {
    console.log("[ENV] normalized", events.map(e => ({ id: e.id, ts: e.ts, label: e.label })));
  }
  return events;
}
