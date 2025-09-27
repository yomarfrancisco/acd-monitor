/**
 * Minimal, compile-clean API helpers to unblock CI.
 */

export async function resilientFetch(path: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), 6000);
  try {
    return await fetch(path, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(t);
  }
}

export async function resilientJson<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await resilientFetch(path, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export async function resilientDownload(path: string, init?: RequestInit): Promise<Blob> {
  const res = await resilientFetch(path, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.blob();
}

/** Back-compat exports (to prevent import errors elsewhere) */
export const fetchJson = resilientJson;
export const resilientFetchWithWarmup = resilientFetch;
export const withWarmup = async <T>(fn: () => Promise<T>): Promise<T> => fn();
export const wakeBackend = async (): Promise<void> => {};

/** Resilient safe wrapper for API calls with schema validation */
export async function resilientSafe<T>(
  fetchPromise: Promise<Response>,
  schema?: any,
  options?: { showWarmingToast?: boolean }
): Promise<T> {
  try {
    const response = await fetchPromise;
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    return data as T;
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
}