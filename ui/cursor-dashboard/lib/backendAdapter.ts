// lib/backendAdapter.ts

/**
 * Always use Next.js API routes - no direct backend calls from browser
 * This ensures we go through our server-side proxy which handles CORS properly
 */
export async function fetchTyped<T>(
  path: string,
  schema: any,
  init?: RequestInit
): Promise<T> {
  // Always use Next.js API routes - prepend /api if not already present
  const url = path.startsWith('/api/') ? path : `/api${path.startsWith('/') ? '' : '/'}${path}`;

  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText} at ${url} :: ${text}`);
  }
  return (await res.json()) as T;
}
