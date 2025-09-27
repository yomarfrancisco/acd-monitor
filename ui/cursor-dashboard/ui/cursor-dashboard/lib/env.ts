/**
 * Environment configuration for ACD Monitor
 * Normalizes env vars to booleans/strings safely and forces LIVE when VERCEL_ENV === 'preview'
 */

type Boolish = string | boolean | undefined;

function toBool(v: Boolish, def = false): boolean {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    return s === '1' || s === 'true' || s === 'yes' || s === 'on';
  }
  return def;
}

function toStr(v: string | undefined, def = ''): string {
  return (v ?? def).trim();
}

const isPreview = toStr(process.env.VERCEL_ENV, '').toLowerCase() === 'preview';

// Raw env (as provided by Vercel/GitHub)
const RAW_USE_DEMO: Boolish = process.env.NEXT_PUBLIC_USE_DEMO;
const RAW_FEED_MODE = toStr(process.env.FEED_MODE);

// Normalize
let USE_DEMO = toBool(RAW_USE_DEMO, false);
let FEED_MODE = RAW_FEED_MODE || 'live';

// **Enforce live-only in preview**
if (isPreview) {
  USE_DEMO = false;
  FEED_MODE = 'live';
  // Optional: noisy log to surface misconfig
  // eslint-disable-next-line no-console
  console.warn('[env] Preview mode: forcing USE_DEMO=false and FEED_MODE=live');
}

export const Env = {
  isPreview,
  USE_DEMO,         // boolean
  FEED_MODE,        // 'live' | 'demo' (but 'live' in preview)
};

// Legacy interface for backward compatibility
export interface EnvConfig {
  isLive: boolean;
  isPreview: boolean;
  isProduction: boolean;
  useDemo: boolean;
  feedMode: 'live' | 'demo' | 'synthetic';
  wsUrl: string;
  apiUrl: string;
}

function getEnvConfig(): EnvConfig {
  const isVercel = typeof process !== 'undefined' && process.env.VERCEL;
  const isProduction = isVercel && process.env.VERCEL_ENV === 'production';
  
  // Use normalized values
  const isLive = !USE_DEMO && FEED_MODE === 'live';
  
  // API endpoints
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'wss://acd-monitor-backend.railway.app/ws';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://acd-monitor-backend.railway.app';
  
  return {
    isLive,
    isPreview,
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
