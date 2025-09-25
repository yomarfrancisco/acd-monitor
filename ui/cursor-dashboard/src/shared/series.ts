import { VENUES, VenueKey } from './venues';

export type DayMs = number; // UTC midnight in ms

export type NormalizedOverview = {
  venue: VenueKey;
  ohlcv: Array<[DayMs, number | null]>; // [ts, close]
};

const toMsUtcMidnight = (ts: number) => {
  // handles seconds or ms
  const ms = ts < 2e10 ? ts * 1000 : ts;
  const d = new Date(ms);
  // clamp to UTC midnight
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
};

export const normalizeOverview = (raw: {
  venue: string;
  ohlcv: any[];
}): NormalizedOverview => {
  const venue = raw.venue as VenueKey;
  const out: Array<[DayMs, number | null]> = [];

  for (const row of raw.ohlcv ?? []) {
    // support coinbase array order [t, low, high, open, close, vol]
    // and other venues that already return {t, c} or similar
    const t = Array.isArray(row) ? row[0] : row.t ?? row[0];
    const cRaw = Array.isArray(row) ? row[4] : row.c ?? row[4];

    const ts = toMsUtcMidnight(Number(t));
    const c = cRaw === null || cRaw === undefined ? null : Number(cRaw);
    out.push([ts, Number.isFinite(c) ? c : null]);
  }

  // sort ascending by ts and de-dup
  out.sort((a, b) => a[0] - b[0]);
  const dedup: typeof out = [];
  let prev = -1;
  for (const [ts, v] of out) {
    if (ts !== prev) {
      dedup.push([ts, v]);
      prev = ts;
    }
  }

  return { venue, ohlcv: dedup };
};
