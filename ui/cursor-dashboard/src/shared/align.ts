export const buildAxis = (startMs: number, endExclusiveMs: number): number[] => {
  const days = [];
  for (let ts = startMs; ts < endExclusiveMs; ts += 86400000) days.push(ts);
  return days;
};

export const alignOnAxis = (
  perVenue: Record<string, Array<[number, number | null]>>,
  axis: number[],
) => {
  // Map lookup per venue
  const maps: Record<string, Map<number, number | null>> = {};
  for (const [v, arr] of Object.entries(perVenue)) {
    maps[v] = new Map(arr ?? []);
  }
  // aligned arrays
  const out: Record<string, Array<[number, number | null]>> = {};
  for (const v of Object.keys(perVenue)) {
    out[v] = axis.map(ts => [ts, maps[v].get(ts) ?? null]);
  }
  return out;
};
