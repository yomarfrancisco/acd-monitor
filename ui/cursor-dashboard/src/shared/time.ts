export const toMsUtcMidnight = (input: number | string): number => {
  let d: Date;

  if (typeof input === 'number') {
    // seconds vs ms
    const ms = input < 1e12 ? input * 1000 : input;
    d = new Date(ms);
  } else {
    // If ISO lacks Z or explicit offset, treat as UTC (append Z)
    const hasTZ = /Z|[+-]\d{2}:\d{2}$/.test(input);
    d = new Date(hasTZ ? input : (input + 'Z'));
  }

  // Guard: if still NaN, use epoch to avoid undefined Map keys
  if (!Number.isFinite(d.valueOf())) {
    d = new Date(0);
  }

  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
};
