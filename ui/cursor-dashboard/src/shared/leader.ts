import { VENUES, VenueKey } from './venues';

export const latestCommonIndex = (
  aligned: Record<VenueKey, Array<[number, number | null]>>,
): { ts: number | null; values: Record<VenueKey, number> | null } => {
  // assume all arrays share the same axis (same length / same ts order)
  const anyVenue = VENUES[0];
  const rows = aligned[anyVenue] ?? [];
  for (let i = rows.length - 1; i >= 0; i--) {
    const ts = rows[i]?.[0];
    if (ts == null) continue;

    const vals: Record<VenueKey, number> = {} as any;
    let ok = true;
    for (const v of VENUES) {
      const val = aligned[v]?.[i]?.[1];
      if (!Number.isFinite(val)) { ok = false; break; }
      vals[v] = val as number;
    }
    if (ok) return { ts, values: vals };
  }
  return { ts: null, values: null };
};
