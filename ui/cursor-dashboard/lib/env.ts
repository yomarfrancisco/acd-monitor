/**
 * Environment configuration for ACD Monitor
 * Forces live data in preview mode, prevents synthetic fallbacks
 */

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
  const isPreview = isVercel && process.env.VERCEL_ENV === 'preview';
  const isProduction = isVercel && process.env.VERCEL_ENV === 'production';
  
  // Force live data in preview mode
  const forceLiveInPreview = isPreview;
  const useDemo = forceLiveInPreview ? false : (process.env.NEXT_PUBLIC_USE_DEMO === '1');
  const feedMode = forceLiveInPreview ? 'live' : (process.env.FEED_MODE as 'live' | 'demo' | 'synthetic') || 'live';
  
  // Live data configuration
  const isLive = !useDemo && feedMode === 'live';
  
  // API endpoints
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'wss://acd-monitor-backend.railway.app/ws';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://acd-monitor-backend.railway.app';
  
  return {
    isLive,
    isPreview,
    isProduction,
    useDemo,
    feedMode,
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
