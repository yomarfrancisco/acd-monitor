/**
 * Environment configuration for ACD Monitor
 * Forces LIVE data in preview mode, prevents synthetic fallbacks
 */

const isPreview = process.env.VERCEL_ENV === 'preview';
const useDemoEnv = String(process.env.NEXT_PUBLIC_USE_DEMO ?? '').toLowerCase();
const useDemo = ['1','true','yes','on'].includes(useDemoEnv);

let USE_DEMO: boolean = useDemo;
let FEED_MODE: string = String(process.env.FEED_MODE ?? 'live');

if (isPreview) {
  console.warn('[env] Preview mode: forcing USE_DEMO=false and FEED_MODE=live');
  USE_DEMO = false;
  FEED_MODE = 'live';
}

export const Env = { USE_DEMO, FEED_MODE };

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
    isPreview: isPreview,
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
