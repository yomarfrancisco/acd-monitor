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

    // Prepare Chatbase API request
    const chatbaseRequest = {
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content
      })),
      assistantId,
      sessionId: sessionId || `session_${Date.now()}`,
      userId: userId || 'anonymous'
    };

    // Call Chatbase API with retries
    let lastError: Error | null = null;
    const retries = [250, 750]; // 250ms, 750ms delays

    for (let attempt = 0; attempt <= retries.length; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        const response = await fetch(`${baseUrl}/v1/chat`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(chatbaseRequest),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          
          return NextResponse.json(
            { 
              reply: data.reply || data.message || 'No response from agent',
              sessionId: data.sessionId || chatbaseRequest.sessionId,
              usage: data.usage
            },
            { 
              status: 200, 
              headers: { 'x-agent-mode': 'live' } 
            }
          );
        }

        // If not successful, throw error for retry logic
        throw new Error(`Chatbase API responded with ${response.status}: ${response.statusText}`);

      } catch (error) {
        lastError = error as Error;
        console.error(`Chatbase API attempt ${attempt + 1} failed:`, error);

        // If this was a timeout or connection error and we have retries left
        if (attempt < retries.length && (
          error instanceof Error && (
            error.name === 'AbortError' || 
            error.message.includes('fetch') ||
            error.message.includes('ECONNREFUSED') ||
            error.message.includes('ETIMEDOUT')
          )
        )) {
          console.log(`Retrying in ${retries[attempt]}ms (attempt ${attempt + 1}/${retries.length + 1})`);
          await new Promise(resolve => setTimeout(resolve, retries[attempt]));
          continue;
        }

        // If we've exhausted retries or it's a non-retryable error, break
        break;
      }
    }

    // All attempts failed, use mock fallback
    console.log('All Chatbase API attempts failed, using mock fallback');
    const mockReply = getMockResponse(messages);
    
    return NextResponse.json(
      { 
        reply: mockReply, 
        sessionId: sessionId || `session_${Date.now()}`,
        usage: { mode: 'mock', reason: 'api_failed', error: lastError?.message }
      },
      { 
        status: 200, 
        headers: { 'x-agent-mode': 'mock' } 
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
