import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ChatRequest {
  messages: ChatMessage[];
  sessionId?: string;
  userId?: string;
}

interface ChatResponse {
  reply: string;
  sessionId: string;
  usage?: any;
}

// Mock fallback responses for when Chatbase is unavailable
const getMockResponse = (messages: ChatMessage[]): string => {
  const lastMessage = messages[messages.length - 1];
  const content = lastMessage?.content?.toLowerCase() || '';
  
  // Deterministic mock responses based on message content
  if (content.includes('pricing') || content.includes('competitive') || content.includes('collusive')) {
    return '[mock] I can help you analyze pricing behavior patterns. Based on your query, I recommend examining the correlation between market participants and their pricing decisions over time. Would you like me to run a specific analysis on your data?';
  }
  
  if (content.includes('compliance') || content.includes('status')) {
    return '[mock] Your current compliance status shows no immediate concerns. The system has detected normal competitive behavior patterns in recent market activity. I can provide a detailed compliance report if needed.';
  }
  
  if (content.includes('report') || content.includes('generate')) {
    return '[mock] I can generate a comprehensive market analysis report for you. This would include risk assessment, compliance metrics, and recommendations. What specific time period and market participants should I focus on?';
  }
  
  if (content.includes('event') || content.includes('log')) {
    return '[mock] I can help you log this market event for analysis. Please provide details about what you observed, when it occurred, and which participants were involved. This will help our system better understand market dynamics.';
  }
  
  // Default response
  return '[mock] Thank you for your message. I\'m your AI economist assistant and I\'m here to help you analyze market data, check compliance, and generate reports. How can I assist you today?';
};

export async function POST(request: NextRequest): Promise<NextResponse<ChatResponse>> {
  try {
    const body: ChatRequest = await request.json();
    const { messages, sessionId, userId } = body;
    const url = new URL(request.url);
    const debugMode = url.searchParams.get('debug') === '1' && process.env.VERCEL_ENV === 'preview';

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { reply: '[mock] Please provide a valid message.', sessionId: sessionId || 'default' },
        { status: 400, headers: { 'x-agent-mode': 'mock' } }
      );
    }

    // Environment variables
    const apiKey = process.env.CHATBASE_API_KEY;
    const assistantId = process.env.CHATBASE_ASSISTANT_ID || '2wO054pAvier4ISsuZd_X';
    const baseUrl = process.env.CHATBASE_BASE_URL || 'https://www.chatbase.co/api';

    // If no API key, use mock response
    if (!apiKey) {
      const mockReply = getMockResponse(messages);
      return NextResponse.json(
        { 
          reply: mockReply, 
          sessionId: sessionId || `session_${Date.now()}`,
          usage: { mode: 'mock', reason: 'no_api_key' }
        },
        { 
          status: 200, 
          headers: { 'x-agent-mode': 'mock' } 
        }
      );
    }

    // Define payload variants to try
    const payloadVariants = [
      // Variant A (current): { assistant_id, messages: [{ role, content }], session_id }
      {
        name: 'A',
        payload: {
          assistant_id: assistantId,
          messages: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          session_id: sessionId || `session_${Date.now()}`,
          user_id: userId || 'anonymous'
        }
      },
      // Variant B (common): { assistant_id, input: "<user text>", session_id }
      {
        name: 'B',
        payload: {
          assistant_id: assistantId,
          input: messages.filter(msg => msg.role === 'user').map(msg => msg.content).join('\n'),
          session_id: sessionId || `session_${Date.now()}`,
          user_id: userId || 'anonymous'
        }
      },
      // Variant C (alt message shape): { assistant_id, messages: [{ sender, text }], session_id }
      {
        name: 'C',
        payload: {
          assistant_id: assistantId,
          messages: messages.map(msg => ({
            sender: msg.role,
            text: msg.content
          })),
          session_id: sessionId || `session_${Date.now()}`,
          user_id: userId || 'anonymous'
        }
      }
    ];

    // Try each payload variant
    let lastError: Error | null = null;
    let lastUpstreamStatus: number | null = null;
    let lastUpstreamBody: string | null = null;

    for (const variant of payloadVariants) {
      try {
        // Debug logging for preview environment
        if (process.env.VERCEL_ENV === 'preview') {
          console.info('CHATBASE: Attempting variant', variant.name);
          console.info('CHATBASE: URL:', `${baseUrl}/v1/chat`);
          console.info('CHATBASE: Headers:', {
            'Authorization': `Bearer ${apiKey.substring(0, 8)}...`,
            'Content-Type': 'application/json'
          });
          console.info('CHATBASE: Payload:', JSON.stringify(variant.payload, null, 2));
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        const response = await fetch(`${baseUrl}/v1/chat`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(variant.payload),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          
          const headers: Record<string, string> = { 'x-agent-mode': 'live' };
          if (debugMode) {
            headers['x-agent-variant'] = variant.name;
            headers['x-agent-payload'] = JSON.stringify(variant.payload).substring(0, 120);
          }
          
          return NextResponse.json(
            { 
              reply: data.reply || data.message || 'No response from agent',
              sessionId: data.sessionId || variant.payload.session_id,
              usage: { ...data.usage, variant: variant.name }
            },
            { 
              status: 200, 
              headers
            }
          );
        }

        // Capture upstream error details for debugging
        lastUpstreamStatus = response.status;
        try {
          lastUpstreamBody = await response.text();
        } catch (e) {
          lastUpstreamBody = 'Failed to read response body';
        }

        if (process.env.VERCEL_ENV === 'preview') {
          console.info(`CHATBASE: Variant ${variant.name} failed with ${response.status}:`, lastUpstreamBody.substring(0, 200));
        }

        // Continue to next variant
        continue;

      } catch (error) {
        lastError = error as Error;
        if (process.env.VERCEL_ENV === 'preview') {
          console.info(`CHATBASE: Variant ${variant.name} error:`, error);
        }
        continue;
      }
    }

    // All variants failed, use mock fallback with debug info
    const mockReply = getMockResponse(messages);
    const headers: Record<string, string> = { 'x-agent-mode': 'mock' };
    
    if (process.env.VERCEL_ENV === 'preview') {
      if (lastUpstreamStatus) {
        headers['x-agent-upstream-status'] = lastUpstreamStatus.toString();
        headers['x-agent-upstream-body'] = lastUpstreamBody ? lastUpstreamBody.substring(0, 120).replace(/[^\x20-\x7E]/g, '') : 'No body';
      }
    }
    
    return NextResponse.json(
      { 
        reply: mockReply, 
        sessionId: sessionId || `session_${Date.now()}`,
        usage: { 
          mode: 'mock', 
          reason: 'all_variants_failed', 
          error: lastError?.message,
          error_details: process.env.VERCEL_ENV === 'preview' ? {
            upstream_status: lastUpstreamStatus,
            upstream_body: lastUpstreamBody ? lastUpstreamBody.substring(0, 120) : null
          } : undefined
        }
      },
      { 
        status: 200, 
        headers
      }
    );

  } catch (error) {
    console.error('Error in /api/agent/chat:', error);
    
    // Fallback to mock response on any error
    const mockReply = '[mock] I apologize, but I\'m experiencing technical difficulties. Please try again in a moment.';
    
    return NextResponse.json(
      { 
        reply: mockReply, 
        sessionId: `session_${Date.now()}`,
        usage: { mode: 'mock', reason: 'server_error', error: error instanceof Error ? error.message : 'Unknown error' }
      },
      { 
        status: 200, 
        headers: { 'x-agent-mode': 'mock' } 
      }
    );
  }
}
