import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'https://acd-monitor-backend.onrender.com';
const IS_PREVIEW = process.env.VERCEL_ENV === 'preview' || process.env.NEXT_PUBLIC_DATA_MODE === 'live';

export interface ProxyOptions {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  mockFallback?: () => any;
  enableWarmup?: boolean;
}

export interface ProxyResult {
  success: boolean;
  data?: any;
  status?: number;
  headers?: Record<string, string>;
  isWarmup?: boolean;
  isFallback?: boolean;
}

/**
 * Resilient proxy utility with timeout, retry logic, and mock fallback
 * Handles cold starts with 202 warm-up responses
 */
export async function proxyJson(
  endpoint: string,
  options: ProxyOptions = {}
): Promise<ProxyResult> {
  const {
    timeout = 6000, // 6 seconds
    retries = 2,
    retryDelay = 1000,
    mockFallback,
    enableWarmup = false
  } = options;

  // In production, always use mock data
  if (!IS_PREVIEW) {
    if (mockFallback) {
      return {
        success: true,
        data: mockFallback(),
        status: 200,
        headers: { 'x-fallback': 'mock' },
        isFallback: true
      };
    }
    return { success: false };
  }

  const url = `${BACKEND_URL}${endpoint}`;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle warm-up response (202)
      if (response.status === 202 && enableWarmup) {
        const retryAfter = response.headers.get('retry-after');
        const retryDelayMs = retryAfter ? parseInt(retryAfter) * 1000 : 2000;
        
        if (attempt < retries) {
          console.log(`Backend warming up, retrying in ${retryDelayMs}ms (attempt ${attempt + 1}/${retries + 1})`);
          await new Promise(resolve => setTimeout(resolve, retryDelayMs));
          continue;
        }
        
        // If we've exhausted retries and still getting 202, return warmup response
        return {
          success: true,
          data: {
            status: 'warming',
            message: 'Backend is warming up, please retry',
            retryAfter: retryDelayMs / 1000
          },
          status: 202,
          headers: { 'retry-after': String(retryDelayMs / 1000) },
          isWarmup: true
        };
      }

      if (response.ok) {
        const data = await response.json();
        
        // Filter out problematic headers that cause double-decoding
        const filteredHeaders: Record<string, string> = {};
        for (const [key, value] of response.headers.entries()) {
          const lowerKey = key.toLowerCase();
          // Skip content-encoding, content-length, and transfer-encoding headers
          if (!['content-encoding', 'content-length', 'transfer-encoding'].includes(lowerKey)) {
            filteredHeaders[key] = value;
          }
        }
        
        return {
          success: true,
          data,
          status: response.status,
          headers: filteredHeaders
        };
      }

      // If not 202 or successful, treat as error
      throw new Error(`Backend responded with ${response.status}: ${response.statusText}`);

    } catch (error) {
      lastError = error as Error;
      console.error(`Proxy attempt ${attempt + 1} failed:`, error);

      // If this was a timeout or connection error and we have retries left
      if (attempt < retries && (
        error instanceof Error && (
          error.name === 'AbortError' || 
          error.message.includes('fetch') ||
          error.message.includes('ECONNREFUSED') ||
          error.message.includes('ETIMEDOUT')
        )
      )) {
        console.log(`Retrying in ${retryDelay}ms (attempt ${attempt + 1}/${retries + 1})`);
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        continue;
      }

      // If we've exhausted retries or it's a non-retryable error, break
      break;
    }
  }

  // All attempts failed, use mock fallback if available
  if (mockFallback) {
    console.log('All proxy attempts failed, using mock fallback');
    return {
      success: true,
      data: mockFallback(),
      status: 200,
      headers: { 'x-fallback': 'mock' },
      isFallback: true
    };
  }

  // No fallback available
  return {
    success: false,
    status: 504,
    headers: { 'x-error': 'Backend unavailable' }
  };
}

/**
 * Wake up the backend (for cron jobs)
 */
export async function wakeBackend(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/_status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000) // 10 second timeout for wake calls
    });
    
    return response.ok;
  } catch (error) {
    console.error('Failed to wake backend:', error);
    return false;
  }
}
