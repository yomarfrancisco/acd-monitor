// lib/backendAdapter.ts
const MODE = process.env.NEXT_PUBLIC_DATA_MODE ?? 'mock';
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';

/**
 * Joins base + path safely (handles duplicate/missing slashes)
 */
function join(base: string, path: string) {
  if (!base) return path;
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

/**
 * Always build an absolute URL in Preview (MODE=live),
 * keep relative only when MODE=mock (Production mock mode).
 */
export async function fetchTyped<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = MODE === 'live' ? join(BASE, path) : join('', path);

  // Temporary runtime verification
  // (visible in browser console + Vercel logs)
  // eslint-disable-next-line no-console
  console.log('[ENV CHECK]', { MODE, BASE, url });

  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
    // Don't send cookies cross-origin
    credentials: MODE === 'live' ? 'omit' : init?.credentials,
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText} at ${url} :: ${text}`);
  }
  return (await res.json()) as T;
}
