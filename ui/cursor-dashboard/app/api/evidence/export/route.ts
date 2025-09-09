import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const url = new URL(request.url);
  const mode = url.searchParams.get('mode') ?? 'ready'; // ready|queued

  const now = new Date();
  const bundleId = `mock-${now.toISOString().slice(0, 10).replace(/-/g, '')}-${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}`;

  if (mode === 'queued') {
    const payload = {
      requestedAt: now.toISOString(),
      status: 'QUEUED',
      bundleId,
      estSeconds: 45
    };
    return NextResponse.json(payload);
  }

  // Default: READY status
  const payload = {
    requestedAt: now.toISOString(),
    status: 'READY',
    url: 'https://example.com/mock/evidence/fake.pdf',
    bundleId
  };

  return NextResponse.json(payload);
}

export async function POST(request: Request) {
  // Handle POST requests for evidence export
  const body = await request.json().catch(() => ({}));
  const mode = body.mode ?? 'ready';

  const now = new Date();
  const bundleId = `mock-${now.toISOString().slice(0, 10).replace(/-/g, '')}-${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}`;

  if (mode === 'queued') {
    const payload = {
      requestedAt: now.toISOString(),
      status: 'QUEUED',
      bundleId,
      estSeconds: 45
    };
    return NextResponse.json(payload);
  }

  // Default: READY status
  const payload = {
    requestedAt: now.toISOString(),
    status: 'READY',
    url: 'https://example.com/mock/evidence/fake.pdf',
    bundleId
  };

  return NextResponse.json(payload);
}
