export const toMsUtcMidnight = (input: number | string): number => {
  let ms: number;

  if (typeof input === 'number') {
    // seconds vs ms
    ms = input < 2e10 ? input * 1000 : input;
  } else {
    // string: try numeric first, then Date
    const num = Number(input);
    if (Number.isFinite(num)) {
      ms = num < 2e10 ? num * 1000 : num;
    } else {
      const d = new Date(input); // supports ISO like "2025-01-01T00:00:00Z"
      ms = d.valueOf();
    }
  }

  // Guard: if still NaN, skip to epoch to avoid undefined Map keys
  if (!Number.isFinite(ms)) ms = 0;

  const d = new Date(ms);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
};
