export async function safe<T>(p: Promise<T>): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try { 
    const data = await p;
    return { ok: true, data }; 
  }
  catch (e: any) { 
    return { ok: false, error: e?.message ?? "unknown" }; 
  }
}
