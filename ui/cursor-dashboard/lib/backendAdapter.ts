import type { ZodTypeAny } from "zod";

const DATA_MODE = (process.env.NEXT_PUBLIC_DATA_MODE ?? "mock") as "mock"|"live";
const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? "";

export async function fetchTyped<T>(
  path: string,
  schema: ZodTypeAny,
  init?: RequestInit
): Promise<T> {
  const url =
    DATA_MODE === "live"
      ? `${BACKEND_BASE_URL}${path}`
      : `${process.env.NEXT_PUBLIC_API_BASE ?? "/api"}${path}`;

  const res = await fetch(url, { ...init, next: { revalidate: 0 } });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}`);
  }
  const json = await res.json();
  const parsed = schema.parse(json); // Zod contract check
  return parsed as T;
}
