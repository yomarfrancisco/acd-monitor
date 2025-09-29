import { toMsUtcMidnight } from './time';

export type DayMs = number; // UTC midnight ms

export type NormalizedOverview = {
  venue: 'binance' | 'okx' | 'bybit' | 'kraken' | 'coinbase';
  ohlcv: Array<[DayMs, number | null]>; // [ts, close]
};

const toNum = (x: unknown): number | null => {
  const n = typeof x === 'string' ? Number(x) : (x as number);
  return Number.isFinite(n) ? n : null;
};

export const normalizeOverview = (raw: { venue: string; ohlcv: any[] }): NormalizedOverview => {
  const venue = raw.venue as NormalizedOverview['venue'];
  const out: Array<[DayMs, number | null]> = [];

  for (const row of raw.ohlcv ?? []) {
    // Support Coinbase array: [t, low, high, open, close, vol]
    // and object styles: { t, c } (already normalized by backend)
    const t = Array.isArray(row) ? row[0] : row.t ?? row[0] ?? row.time ?? row.timestamp;
    const closeRaw = Array.isArray(row) ? row[4] : row.c ?? row.close ?? row[4];

    const ts = toMsUtcMidnight(t as any);
    const close = toNum(closeRaw);
    out.push([ts, close]);
  }

  // sort + de-dup
  out.sort((a, b) => a[0] - b[0]);
  const dedup: typeof out = [];
  let last = -1;
  for (const [ts, v] of out) {
    if (ts !== last) dedup.push([ts, v]);
    last = ts;
  }

  return { venue, ohlcv: dedup };
};
