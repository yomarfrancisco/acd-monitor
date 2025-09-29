export function toMsTs(v: unknown): number | null {
  // Accepts ms numbers, second numbers, Date, ISO string
  if (typeof v === "number") {
    if (!Number.isFinite(v) || v <= 0) return null;
    // Heuristic: 10-digit → seconds → convert to ms
    if (v < 1e12) return Math.round(v * 1000);
    return v;
  }
  if (v instanceof Date) return v.getTime();
  if (typeof v === "string" && v) {
    const n = Date.parse(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

export function finiteMsOrNull(v: unknown): number | null {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) && n > 0 ? n : null;
}
