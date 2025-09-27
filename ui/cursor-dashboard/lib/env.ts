/**
 * Environment configuration for ACD Monitor
 * Forces LIVE data in preview mode, prevents synthetic fallbacks
 */

const rawUseDemo = process.env.NEXT_PUBLIC_USE_DEMO; // string | undefined
const rawFeedMode = process.env.FEED_MODE;           // string | undefined

const toBool = (v: unknown): boolean => {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    return ['1','true','yes','on'].includes(s);
  }
  return false;
};

let USE_DEMO = toBool(rawUseDemo);
let FEED_MODE: 'live' | 'demo' | 'synthetic' = (rawFeedMode?.trim().toLowerCase() as any) || 'live';

// Force live in preview
if (process.env.VERCEL_ENV === 'preview') {
  USE_DEMO = false;
  FEED_MODE = 'live';
  if (typeof console !== 'undefined') {
    // eslint-disable-next-line no-console
    console.warn('[env] Preview mode: forcing USE_DEMO=false and FEED_MODE=live');
  }
}

export { USE_DEMO, FEED_MODE };

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
    isPreview: process.env.VERCEL_ENV === 'preview',
    isProduction: Boolean(isProduction),
    useDemo: USE_DEMO,
    feedMode: FEED_MODE,
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
