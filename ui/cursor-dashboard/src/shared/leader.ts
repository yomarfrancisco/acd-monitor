const isNum = (x: unknown): x is number => Number.isFinite(x as number);

export const latestCommonIndex = (
  aligned: Record<string, Array<[number, number | null]>>,
  venues: string[],
) => {
  if (!venues.length) return { ts: null, values: null as null };
  const n = aligned[venues[0]]?.length ?? 0;
  for (let i = n - 1; i >= 0; i--) {
    const ts = aligned[venues[0]][i]?.[0];
    if (ts == null) continue;
    const vals: Record<string, number> = {};
    let ok = true;
    for (const v of venues) {
      const val = aligned[v]?.[i]?.[1];
      if (!isNum(val)) { ok = false; break; }
      vals[v] = val;
    }
    if (ok) return { ts, values: vals };
  }
  return { ts: null, values: null };
};
