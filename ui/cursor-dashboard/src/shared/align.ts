import { VENUES, VenueKey } from './venues';

export const buildAxis = (startMs: number, endExclusiveMs: number): number[] => {
  const out: number[] = [];
  for (let ts = startMs; ts < endExclusiveMs; ts += 86400000) out.push(ts);
  return out;
};

export type AlignedSeries = Record<VenueKey, Array<[number, number | null]>>;

export const alignSeries = (
  series: Record<VenueKey, Array<[number, number | null]>>,
  axis: number[],
): AlignedSeries => {
  const maps: Record<VenueKey, Map<number, number | null>> = Object.fromEntries(
    VENUES.map(v => [v, new Map(series[v] ?? [])]),
  ) as any;

  const result = {} as AlignedSeries;
  for (const v of VENUES) {
    result[v] = axis.map(ts => [ts, maps[v].get(ts) ?? null]);
  }
  return result;
};
