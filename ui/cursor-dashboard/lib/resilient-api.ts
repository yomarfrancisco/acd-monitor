import { toast } from 'sonner';

export interface ResilientApiOptions {
  maxRetries?: number;
  retryDelay?: number;
  showWarmingToast?: boolean;
  warmingToastDelay?: number;
}

export interface ResilientApiResult<T> {
  ok: true;
  data: T;
} | {
  ok: false;
  error: string;
  isWarming?: boolean;
}

/**
 * Resilient API client that handles 202 warm-up responses and shows user feedback
 */
export async function resilientFetch<T>(
  path: string,
  schema: any,
  options: ResilientApiOptions = {}
): Promise<ResilientApiResult<T>> {
  const {
    maxRetries = 3,
    retryDelay = 2000,
    showWarmingToast = true,
    warmingToastDelay = 5000
  } = options;

  // Always use Next.js API routes - prepend /api if not already present
  const url = path.startsWith('/api/') ? path : `/api${path.startsWith('/') ? '' : '/'}${path}`;

  let warmingToastId: string | number | undefined;
  let warmingToastShown = false;
  const startTime = Date.now();

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      });

      // Handle 202 warm-up response
      if (res.status === 202) {
        const retryAfter = res.headers.get('retry-after');
        const delay = retryAfter ? parseInt(retryAfter) * 1000 : retryDelay;
        
        // Show warming toast if it's been more than 5 seconds and we haven't shown it yet
        if (showWarmingToast && !warmingToastShown && (Date.now() - startTime) > warmingToastDelay) {
          warmingToastId = toast.loading('Warming backend...', {
            description: 'The backend is starting up, please wait a moment.',
            duration: Infinity, // Keep it until we succeed or fail
          });
          warmingToastShown = true;
        }

        if (attempt < maxRetries) {
          console.log(`Backend warming up, retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        // If we've exhausted retries and still getting 202, return warming error
        if (warmingToastId) {
          toast.dismiss(warmingToastId);
        }
        toast.error('Backend is taking longer than expected to start up');
        
        return {
          ok: false,
          error: 'Backend is warming up, please try again in a moment',
          isWarming: true
        };
      }

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${res.statusText} at ${url} :: ${text}`);
      }

      // Success! Dismiss warming toast if it was shown
      if (warmingToastId) {
        toast.dismiss(warmingToastId);
        toast.success('Backend ready');
      }

      const data = await res.json();
      return { ok: true, data: data as T };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // If this was a timeout or connection error and we have retries left
      if (attempt < maxRetries && (
        errorMessage.includes('fetch') ||
        errorMessage.includes('Failed to fetch') ||
        errorMessage.includes('504') ||
        errorMessage.includes('502')
      )) {
        console.log(`API call failed, retrying in ${retryDelay}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
        
        // Show warming toast if it's been more than 5 seconds and we haven't shown it yet
        if (showWarmingToast && !warmingToastShown && (Date.now() - startTime) > warmingToastDelay) {
          warmingToastId = toast.loading('Connecting to backend...', {
            description: 'The backend may be starting up, please wait a moment.',
            duration: Infinity,
          });
          warmingToastShown = true;
        }
        
        await new Promise(resolve => setTimeout(resolve, retryDelay));
        continue;
      }

      // All attempts failed
      if (warmingToastId) {
        toast.dismiss(warmingToastId);
      }
      
      return {
        ok: false,
        error: errorMessage
      };
    }
  }

  // This should never be reached, but just in case
  return {
    ok: false,
    error: 'All retry attempts failed'
  };
}

/**
 * Enhanced safe wrapper that works with resilient fetch
 */
export async function resilientSafe<T>(
  promise: Promise<ResilientApiResult<T>>
): Promise<{ ok: true; data: T } | { ok: false; error: string; isWarming?: boolean }> {
  try {
    const result = await promise;
    return result;
  } catch (e: any) {
    return {
      ok: false,
      error: e?.message ?? "unknown"
    };
  }
}
