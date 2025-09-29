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

  console.log(`🔍 [fetchTyped] Making request to: ${url}`);
  console.log(`🔍 [fetchTyped] Original path: ${path}`);
  console.log(`🔍 [fetchTyped] Schema:`, schema);

  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
    cache: 'no-store',
  });

  console.log(`📊 [fetchTyped] Response status: ${res.status}`);
  console.log(`📊 [fetchTyped] Response headers:`, Object.fromEntries(res.headers.entries()));

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    console.log(`❌ [fetchTyped] Response not OK: ${res.status} ${res.statusText}`);
    console.log(`❌ [fetchTyped] Response text: ${text}`);
    throw new Error(`HTTP ${res.status} ${res.statusText} at ${url} :: ${text}`);
  }
  
  const jsonData = await res.json();
  console.log(`✅ [fetchTyped] Successfully parsed JSON response`);
  console.log(`📊 [fetchTyped] Response keys:`, Object.keys(jsonData));
  console.log(`📊 [fetchTyped] Response type: ${typeof jsonData}`);
  
  if (jsonData.ohlcv) {
    console.log(`📊 [fetchTyped] OHLCV length: ${jsonData.ohlcv.length}`);
    console.log(`📊 [fetchTyped] OHLCV type: ${typeof jsonData.ohlcv}`);
    console.log(`📊 [fetchTyped] OHLCV is array: ${Array.isArray(jsonData.ohlcv)}`);
  }
  
  return jsonData as T;
}
