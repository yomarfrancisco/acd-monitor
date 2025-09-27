/**
 * Environment configuration for ACD Monitor
 * Fixes boolean typing and enforces LIVE data in preview mode
 */

// helpers (top of file)
const toBool = (v: string | boolean | undefined, def = false): boolean => {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    return ['1', 'true', 'yes', 'on'].includes(s);
  }
  return def;
};
const toStr = (v: string | undefined, def = ''): string => (v ?? def);

// detect vercel preview
const IS_PREVIEW =
  (process.env.VERCEL_ENV ?? process.env.NEXT_PUBLIC_VERCEL_ENV ?? '').toLowerCase() === 'preview';

// normalize raw envs
const RAW_USE_DEMO = process.env.NEXT_PUBLIC_USE_DEMO as string | boolean | undefined;
const RAW_FEED_MODE = process.env.FEED_MODE as string | undefined;

// hard force LIVE in preview
export const USE_DEMO: boolean = IS_PREVIEW ? false : toBool(RAW_USE_DEMO, false);
export const FEED_MODE: string = IS_PREVIEW ? 'live' : toStr(RAW_FEED_MODE, 'live');

// optional: console guard in preview
if (IS_PREVIEW) {
  // eslint-disable-next-line no-console
  console.warn('[env] Preview mode: forcing USE_DEMO=false and FEED_MODE=live');
}

export const EnvConfig = {
  isPreview: IS_PREVIEW,
  useDemo: USE_DEMO,
  feedMode: FEED_MODE,
};
export type EnvConfigT = typeof EnvConfig;

// Legacy interface for backward compatibility
export interface EnvConfigLegacy {
  isLive: boolean;
  isPreview: boolean;
  isProduction: boolean;
  useDemo: boolean;
  feedMode: 'live' | 'demo' | 'synthetic';
  wsUrl: string;
  apiUrl: string;
}

function getEnvConfig(): EnvConfigLegacy {
  const isVercel = typeof process !== 'undefined' && process.env.VERCEL;
  const isProduction = isVercel && process.env.VERCEL_ENV === 'production';
  
  // Use normalized values
  const isLive = !USE_DEMO && FEED_MODE === 'live';
  
  // API endpoints
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'wss://acd-monitor-backend.railway.app/ws';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://acd-monitor-backend.railway.app';
  
  return {
    isLive,
    isPreview: IS_PREVIEW,
    isProduction,
    useDemo: USE_DEMO,
    feedMode: FEED_MODE as 'live' | 'demo' | 'synthetic',
    wsUrl,
    apiUrl
  };
}

export const env = getEnvConfig();

// Runtime validation
if (typeof window !== 'undefined') {
  console.log('[ENV] Configuration:', {
    isLive: env.isLive,
    isPreview: env.isPreview,
    isProduction: env.isProduction,
    useDemo: env.useDemo,
    feedMode: env.feedMode
  });
  
  // Warn if demo mode is active in preview
  if (env.isPreview && env.useDemo) {
    console.error('[ENV] ERROR: Demo mode detected in preview environment!');
  }
}
