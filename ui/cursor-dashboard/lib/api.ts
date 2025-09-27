import { IS_PREVIEW } from '@/lib/env';

const LIVE_BASE = process.env.NEXT_PUBLIC_BACKEND_BASE_LIVE || 'https://api.acd.live';
const DEMO_BASE = process.env.NEXT_PUBLIC_BACKEND_BASE_DEMO || 'https://api.acd.demo';

export const BACKEND_BASE = IS_PREVIEW ? LIVE_BASE : (process.env.NEXT_PUBLIC_BACKEND_BASE || LIVE_BASE);
export const DATASOURCE_MODE = IS_PREVIEW ? 'live' : (process.env.NEXT_PUBLIC_DATASOURCE_MODE || 'live');
