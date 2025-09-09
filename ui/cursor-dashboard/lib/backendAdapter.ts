import type { ZodTypeAny } from "zod";

const MODE = process.env.NEXT_PUBLIC_DATA_MODE; // 'mock' | 'live'
const BASE = process.env.NEXT_PUBLIC_API_BASE;  // e.g. https://acd-monitor-backend.onrender.com

function join(base: string, path: string) {
  return base.endsWith('/') ? `${base.slice(0, -1)}${path}` : `${base}${path}`;
}

export async function fetchTyped<T>(
  path: string,
  schema: ZodTypeAny,
  init?: RequestInit
): Promise<T> {
  const url =
    MODE === 'live'
      ? join(BASE || '', path.startsWith('/') ? path : `/${path}`)
      : // mock mode keeps using the app's built-in API routes
        (path.startsWith('/api') ? path : `/api${path.startsWith('/') ? '' : '/'}${path}`);
  
  const res = await fetch(url, { 
    ...init, 
    headers: { 
      'Content-Type': 'application/json', 
      ...(init?.headers || {}) 
    },
    next: { revalidate: 0 }
  });
  
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  
  const json = await res.json();
  const parsed = schema.parse(json); // Zod contract check
  return parsed as T;
}
