/**
 * Environment configuration for ACD Monitor
 * Forces LIVE data in preview mode, prevents synthetic fallbacks
 */

const toBool = (v: unknown, def = false) =>
  typeof v === 'boolean'
    ? v
    : typeof v === 'string'
      ? ['1','true','yes','on'].includes(v.trim().toLowerCase())
      : def;

const VERCEL_ENV = process.env.VERCEL_ENV || process.env.NEXT_PUBLIC_VERCEL_ENV || '';
export const IS_PREVIEW = VERCEL_ENV === 'preview' || process.env.GITHUB_REF?.includes('/preview');

const RAW_USE_DEMO = process.env.NEXT_PUBLIC_USE_DEMO ?? process.env.USE_DEMO;
const RAW_FEED_MODE = process.env.FEED_MODE ?? process.env.NEXT_PUBLIC_FEED_MODE;

// 🔒 Force LIVE on Preview no matter what is set in Vercel/CI
export const FEED_MODE = IS_PREVIEW ? 'live' : (RAW_FEED_MODE || 'live');
export const USE_DEMO = IS_PREVIEW ? false : toBool(RAW_USE_DEMO, false);

// Useful flags (server + client)
export const NEXT_PUBLIC_FEED_MODE = FEED_MODE;
export const NEXT_PUBLIC_USE_DEMO = USE_DEMO ? '1' : '0';

// Optional: surface in /api/debug/env (non-secret)
export const PUBLIC_RUNTIME_DEBUG = {
  vercelEnv: VERCEL_ENV,
  isPreview: IS_PREVIEW,
  feedMode: FEED_MODE,
  useDemo: USE_DEMO,
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
    isPreview: IS_PREVIEW,
    isProduction: Boolean(isProduction),
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