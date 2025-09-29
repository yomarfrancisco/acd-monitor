// ui/cursor-dashboard/lib/env.ts

// NOTE: In Node, process.env values are always string | undefined.
// Never type them as boolean. Parse explicitly.

type Boolish = string | undefined;

const toBool = (v: Boolish, def = false): boolean => {
  if (v == null) return def;
  switch (v.trim().toLowerCase()) {
    case '1':
    case 'true':
    case 'yes':
    case 'y':
    case 'on':
      return true;
    case '0':
    case 'false':
    case 'no':
    case 'n':
    case 'off':
      return false;
    default:
      return def;
  }
};

const toStr = (v: string | undefined, def = ''): string => (v ?? def);

// Detect Vercel preview reliably (also allow local override)
const vercelEnv = toStr(process.env.VERCEL_ENV, toStr(process.env.NEXT_PUBLIC_VERCEL_ENV));
const IS_PREVIEW = vercelEnv === 'preview';

const RAW_USE_DEMO = process.env.NEXT_PUBLIC_USE_DEMO;           // string | undefined
const RAW_FEED_MODE = process.env.NEXT_PUBLIC_FEED_MODE ?? process.env.FEED_MODE;

// Enforce LIVE for preview; otherwise honor env with safe defaults
export const USE_DEMO: boolean = IS_PREVIEW ? false : toBool(RAW_USE_DEMO, false);
export const FEED_MODE: 'live' | 'demo' = IS_PREVIEW ? 'live' : (toStr(RAW_FEED_MODE, 'live') === 'demo' ? 'demo' : 'live');

// Optional: surface a console hint in preview if anything was overridden
// (Will show in browser console in preview builds)
if (IS_PREVIEW && (RAW_USE_DEMO || RAW_FEED_MODE)) {
  // eslint-disable-next-line no-console
  console.warn('[env] Preview mode: forcing USE_DEMO=false and FEED_MODE=live (overriding env vars).');
}

export const ENV = {
  IS_PREVIEW,
  USE_DEMO,
  FEED_MODE,
};
export type EnvConfig = typeof ENV;
