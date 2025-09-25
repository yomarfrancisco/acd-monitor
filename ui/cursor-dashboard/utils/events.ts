import { z } from "zod";

export type EnvEvent = { id: string; ts: number; label?: string; color?: string };

export const SEED_EVENTS_YTD: EnvEvent[] = [
  { id: "env-1", ts: Date.parse("2025-02-01T00:00:00Z"), label: "Regime A → B", color: "#ef4444" },
  { id: "env-2", ts: Date.parse("2025-06-01T00:00:00Z"), label: "Policy Shift",   color: "#f59e0b" },
  { id: "env-3", ts: Date.parse("2025-07-01T00:00:00Z"), label: "Liquidity ↑",    color: "#10b981" },
];

const E = z.object({ id: z.string().optional().default("evt"), ts: z.union([z.number(), z.string(), z.date()]), label: z.string().optional(), color: z.string().optional() });
const Arr = z.array(E);
const Box = z.object({ events: Arr.optional(), items: Arr.optional(), data: Arr.optional() }).passthrough();

function toMs(x: unknown): number | null {
  if (x instanceof Date) return x.getTime();
  if (typeof x === "number") return x > 1e12 ? x : x * 1000;      // seconds→ms
  if (typeof x === "string") {
    const n = Number(x);
    if (!Number.isNaN(n)) return toMs(n);
    const p = Date.parse(x);
    return Number.isNaN(p) ? null : p;
  }
  return null;
}

export function normalizeEvents(input: unknown): EnvEvent[] {
  const d = Arr.safeParse(input);
  if (d.success) return d.data.map(v => ({ ...v, ts: toMs(v.ts)! })).filter(v => v.ts);
  const b = Box.safeParse(input);
  if (b.success) {
    const pick = b.data.events ?? b.data.items ?? b.data.data ?? [];
    return pick.map(v => ({ ...v, ts: toMs((v as any).ts)! })).filter(v => v.ts);
  }
  return [];
}

export function pickEventsInDomain(evts: EnvEvent[], min: number, max: number): EnvEvent[] {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min >= max) return [];
  return evts.filter(e => e.ts >= min && e.ts <= max);
}