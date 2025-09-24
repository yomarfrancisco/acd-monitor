// ui/cursor-dashboard/lib/leadership.ts
export type UiVenue = 'binance' | 'coinbase' | 'bybit' | 'kraken';

export type ChartPoint = {
  // existing shape you already use for the line chart
  date: string | number;       // timestamp or label
  fnb?: number;                // binance
  absa?: number;               // coinbase (OKX in UI)
  nedbank?: number;            // bybit
  standard?: number;           // kraken
};

export type DataKey = 'fnb' | 'absa' | 'nedbank' | 'standard';

export function computePriceLeadership(points: ChartPoint[], keys: DataKey[]) {
  // keep only keys that actually exist in the data
  const active = keys.filter(k => points.some(p => typeof p[k] === 'number'));
  if (active.length < 2 || points.length < 10) {
    return { leader: null as UiVenue | null, pct: null as number | null, total: 0 };
  }

  // epsilon to ignore tiny moves (use a fraction of median price)
  const samplePrices: number[] = [];
  for (const p of points) for (const k of active) if (typeof p[k] === 'number') samplePrices.push(p[k] as number);
  const medianPrice = samplePrices.sort((a,b)=>a-b)[Math.floor(samplePrices.length/2)] || 1;
  const eps = Math.max(1e-6 * medianPrice, 0.5); // ~50 cents minimum

  // map DataKey -> UiVenue
  const key2venue: Record<DataKey, UiVenue> = {
    fnb: 'binance',
    absa: 'coinbase',
    nedbank: 'bybit',
    standard: 'kraken',
  };

  const counts: Record<UiVenue, number> = { binance:0, coinbase:0, bybit:0, kraken:0 };
  let totalLeadEvents = 0;

  // iterate bars t=1..n-2 (we look ahead one bar)
  for (let t = 1; t < points.length - 1; t++) {
    // returns at t
    const prev = points[t-1];
    const cur  = points[t];
    const next = points[t+1];

    const returns: { key: DataKey; ret: number }[] = [];
    for (const k of active) {
      const a = cur[k], b = prev[k];
      if (typeof a === 'number' && typeof b === 'number') {
        returns.push({ key: k, ret: (a as number) - (b as number) });
      }
    }
    if (returns.length < 2) continue;

    // pick candidate leader at t by |ret|
    returns.sort((x,y)=>Math.abs(y.ret)-Math.abs(x.ret));
    const cand = returns[0];
    if (Math.abs(cand.ret) < eps) continue; // ignore tiny move

    // median cross-venue return sign at t+1
    const nextRets: number[] = [];
    for (const k of active) {
      const a = next[k], b = cur[k];
      if (typeof a === 'number' && typeof b === 'number') nextRets.push((a as number) - (b as number));
    }
    if (nextRets.length < 2) continue;

    nextRets.sort((a,b)=>a-b);
    const mid = nextRets.length % 2
      ? nextRets[(nextRets.length-1)/2]
      : 0.5*(nextRets[nextRets.length/2 - 1] + nextRets[nextRets.length/2]);

    const sameSign = (cand.ret > 0 && mid > 0) || (cand.ret < 0 && mid < 0);
    if (sameSign) {
      counts[key2venue[cand.key]] += 1;
      totalLeadEvents += 1;
    }
  }

  if (totalLeadEvents === 0) {
    return { leader: null, pct: null, total: 0 };
  }

  // leader & percent
  const pairs = Object.entries(counts) as [UiVenue, number][];
  pairs.sort((a,b)=>b[1]-a[1]);
  const [leader, wins] = pairs[0];
  const pct = (wins / totalLeadEvents) * 100;
  return { leader, pct, total: totalLeadEvents };
}
