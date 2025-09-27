import { NextResponse } from 'next/server';
import { PUBLIC_RUNTIME_DEBUG } from '@/lib/env';

export const GET = async () => NextResponse.json(PUBLIC_RUNTIME_DEBUG);
