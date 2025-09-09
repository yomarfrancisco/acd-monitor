import { NextResponse } from 'next/server';

// Simple deterministic pseudo-random with jitter for "live-ish" feel
const jitter = (base: number, span: number) => {
  const r = Math.sin(Date.now()/60000) * 0.5 + 0.5; // 0..1 minute wave
  return Math.round(base + (r - 0.5) * span);
};

export async function GET(request: Request) {
  const url = new URL(request.url);
  const mode = url.searchParams.get('mode') ?? 'normal'; // normal|degraded

  const systemHealth = mode === 'degraded' ? jitter(65, 15) : jitter(84, 8);
  const complianceReadiness = mode === 'degraded' ? jitter(45, 12) : jitter(67, 6);
  
  const band = systemHealth >= 80 ? 'PASS' : systemHealth >= 60 ? 'WATCH' : 'FAIL';

  // Generate spark data (12 points for mini chart)
  const spark = [];
  const now = new Date();
  for (let i = 11; i >= 0; i--) {
    const ts = new Date(now.getTime() - (i * 30 * 60 * 1000)); // 30 min intervals
    spark.push({
      ts: ts.toISOString(),
      convergence: jitter(25, 5),
      dataIntegrity: jitter(18, 4),
      evidenceChain: jitter(82, 6),
      runtimeStability: jitter(81, 5)
    });
  }

  const payload = {
    updatedAt: new Date().toISOString(),
    summary: {
      systemHealth,
      complianceReadiness,
      band
    },
    spark,
    source: {
      name: 'Simulated: Internal Monitoring',
      freshnessSec: mode === 'degraded' ? 120 : 24,
      quality: mode === 'degraded' ? 0.78 : 0.95
    }
  };

  return NextResponse.json(payload);
}
