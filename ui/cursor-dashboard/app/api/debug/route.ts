import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  // Only allow in preview environment for security
  if (process.env.VERCEL_ENV !== 'preview') {
    return NextResponse.json({ error: 'Not available in production' }, { status: 403 });
  }

  const debug = {
    CHATBOT_ID: process.env.CHATBASE_ASSISTANT_ID,
    CHATBOT_ID_PRESENT: Boolean(process.env.CHATBASE_ASSISTANT_ID),
    CHATBOT_ID_LENGTH: (process.env.CHATBASE_ASSISTANT_ID || '').length,
    API_KEY_PRESENT: Boolean(process.env.CHATBASE_API_KEY),
    API_KEY_LENGTH: (process.env.CHATBASE_API_KEY || '').length,
    SIGNING_SECRET_PRESENT: Boolean(process.env.CHATBASE_SIGNING_SECRET),
    MESSAGE_URL: `https://www.chatbase.co/api/v1/chatbot/${process.env.CHATBASE_ASSISTANT_ID}/message`,
    STREAM_URL: `https://www.chatbase.co/api/v1/chatbot/${process.env.CHATBASE_ASSISTANT_ID}/message/stream`,
  };

  return NextResponse.json(debug);
}
