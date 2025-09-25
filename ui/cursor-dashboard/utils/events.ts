// ui/cursor-dashboard/utils/events.ts
import { z } from "zod";

// Seed events (always safe fallback)
export const SEED_EVENTS_YTD = [
  { id: "env-1", ts: Date.parse("2025-02-01T00:00:00Z"), label: "Regime A → B", color: "#ef4444" },
  { id: "env-2", ts: Date.parse("2025-06-01T00:00:00Z"), label: "Policy Shift", color: "#f59e0b" },
  { id: "env-3", ts: Date.parse("2025-07-01T00:00:00Z"), label: "Liquidity ↑", color: "#10b981" },
];

const EventZ = z.object({
  id: z.string().optional().default("evt"),
  ts: z.union([z.number(), z.string(), z.date()]),
  label: z.string().optional().default(""),
  color: z.string().optional(),
});

const ArrZ = z.array(EventZ);
const AnyContainerZ = z.object({
  events: ArrZ.optional(),
  items: ArrZ.optional(),
  data: ArrZ.optional(),
}).passthrough();

function toMs(x: number | string | Date): number | null {
  if (x instanceof Date) return x.getTime();
  if (typeof x === "number") return x > 1e12 ? x : x * 1000; // allow seconds
  if (typeof x === "string") {
    const n = Number(x);
    if (!Number.isNaN(n)) return toMs(n);
    const p = Date.parse(x);
    return Number.isNaN(p) ? null : p;
  }
  return null;
}

export type EnvEvent = { id: string; ts: number; label?: string; color?: string };

export function normalizeEvents(input: unknown): EnvEvent[] {
  // Accept plain array
  const direct = ArrZ.safeParse(input);
  if (direct.success) {
    return direct.data
      .map(e => ({ ...e, ts: toMs(e.ts) }))
      .filter(e => e.ts !== null) as EnvEvent[];
  }
  // Accept container {events|items|data}
  const boxed = AnyContainerZ.safeParse(input);
  if (boxed.success) {
    const pick = boxed.data.events ?? boxed.data.items ?? boxed.data.data ?? [];
    return pick
      .map(e => ({ ...e, ts: toMs(e.ts) }))
      .filter(e => e.ts !== null) as EnvEvent[];
  }
  return [];
}

export function pickEventsInDomain(events: EnvEvent[], xMin: number, xMax: number): EnvEvent[] {
  if (!Number.isFinite(xMin) || !Number.isFinite(xMax) || xMin >= xMax) return [];
  return events.filter(e => e.ts >= xMin && e.ts <= xMax);
}
