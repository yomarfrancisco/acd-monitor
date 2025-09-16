import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface ChatMessage {
  role?: 'user' | 'assistant' | 'system';
  type?: 'user' | 'agent' | 'assistant' | 'bot';
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

// Normalize UI messages to Chatbase schema - preserve system messages
const normalizeMessagesForChatbase = (messages: ChatMessage[]): {role: "user" | "assistant"; content: string}[] => {
  const sysParts: string[] = [];
  const norm: { role: "user" | "assistant"; content: string }[] = [];

  for (const m of messages) {
    // Preserve system messages by collecting them
    if (m.role === "system") {
      if (m.content) sysParts.push(m.content);
      continue;
    }
    
    // Handle role-based messages
    if (m.role && m.content) {
      if (m.role === "user" || m.role === "assistant") {
        norm.push({ role: m.role, content: m.content });
      }
      continue;
    }
    
    // Handle type-based messages (legacy support)
    if (m.type && m.content) {
      let role: "user" | "assistant";
      if (m.type === "user") {
        role = "user";
      } else if (m.type === "agent" || m.type === "assistant" || m.type === "bot") {
        role = "assistant";
      } else {
        continue; // Skip unknown types
      }
      norm.push({ role, content: m.content });
    }
  }

  // Prepend system messages to first user message to preserve guidance
  if (sysParts.length && norm.length) {
    const firstUserIndex = norm.findIndex(m => m.role === "user");
    if (firstUserIndex >= 0) {
      norm[firstUserIndex].content = `${sysParts.join("\n\n")}\n\n${norm[firstUserIndex].content}`;
    }
  }

  return norm;
};

// Gentle trimming that preserves conversation continuity
const trimMessagesForTokenLimit = (
  messages: { role: "user" | "assistant"; content: string }[],
  maxChars = 15000
): { role: "user" | "assistant"; content: string }[] => {
  let total = 0;
  const out: typeof messages = [];

  // Walk from the end (most recent first) to preserve recent context
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    const len = (m.content || "").length;
    if (total + len > maxChars && out.length) break;
    out.push(m);
    total += len;
  }
  
  return out.reverse(); // restore chronological order
};

// Streaming response handler for Chatbase
async function handleStreamingResponse(
  chatbasePayload: any,
  apiKey: string,
  endpoint: string,
  sessionId: string,
  debugMode: boolean
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

  try {
    // Debug logging for preview environment
    if (process.env.VERCEL_ENV === 'preview') {
      console.info('CHATBASE: Attempting streaming API call');
      console.info('CHATBASE: URL:', endpoint);
      console.info('CHATBASE: Headers:', {
        'Authorization': `Bearer ${apiKey.substring(0, 8)}...`,
        'Content-Type': 'application/json'
      });
      console.info('CHATBASE: Payload:', JSON.stringify(chatbasePayload, null, 2));
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(chatbasePayload),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Chatbase streaming API responded with ${response.status}: ${response.statusText}`);
    }

    // Check if response is actually streaming
    if (!response.headers.get('content-type')?.includes('text/event-stream')) {
      throw new Error('Response is not a streaming response');
    }

    // Create a streaming response with proper reader guards
    const stream = new ReadableStream({
      start(streamController) {
        const reader = response.body?.getReader();
        if (!reader) {
          streamController.close();
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        function pump(): Promise<void> {
          // TypeScript guard: reader is guaranteed to be non-null here
          if (!reader) {
            streamController.close();
            return Promise.resolve();
          }
          
          return reader.read().then(({ done, value }) => {
            if (done) {
              streamController.close();
              if (reader) reader.releaseLock();
              return;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.trim() === '') continue;
              
              try {
                // Handle SSE format: data: {...}
                if (line.startsWith('data: ')) {
                  const data = line.slice(6);
                  if (data === '[DONE]') {
                    streamController.close();
                    if (reader) reader.releaseLock();
                    return;
                  }
                  
                  const parsed = JSON.parse(data);
                  if (parsed.text) {
                    // Send the text chunk to client
                    streamController.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ text: parsed.text })}\n\n`));
                  }
                }
              } catch (e) {
                // Ignore malformed JSON
                if (process.env.VERCEL_ENV === 'preview') {
                  console.warn('CHATBASE: Ignoring malformed streaming data:', line);
                }
              }
            }

            return pump();
          }).catch((error) => {
            if (process.env.VERCEL_ENV === 'preview') {
              console.error('CHATBASE: Streaming error:', error);
            }
            streamController.close();
            if (reader) reader.releaseLock();
          });
        }

        return pump();
      }
    });

    const headers: Record<string, string> = {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'x-agent-mode': 'live'
    };

    if (debugMode) {
      headers['x-agent-payload'] = JSON.stringify(chatbasePayload).substring(0, 120);
    }

    return new Response(stream, { headers });

  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

export async function POST(request: NextRequest): Promise<NextResponse<ChatResponse> | Response> {
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
    
    // Single source of truth for URL and ID
    const CHATBASE_API_URL = process.env.CHATBASE_BASE_URL?.replace(/\/+$/, '') || "https://www.chatbase.co/api";
    const CHATBASE_CHAT_ENDPOINT = `${CHATBASE_API_URL}/v1/chat`;
    const CHATBASE_ID = process.env.CHATBASE_ASSISTANT_ID || '2wO054pAvier4ISsuZd_X';
    const CHATBASE_ID_FIELD = "chatbotId"; // Use correct field name for Chatbase API

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

    // Normalize UI messages to Chatbase schema and apply token limit
    const normalizedMessages = normalizeMessagesForChatbase(messages);
    const trimmedMessages = trimMessagesForTokenLimit(normalizedMessages);
    
    // Prepare correct Chatbase API payload - ALWAYS include required fields
    const streamEnabled = process.env.NEXT_PUBLIC_AGENT_CHAT_STREAM === 'true' ? true : false;
    const maxOutputTokens = Number(process.env.NEXT_PUBLIC_AGENT_MAX_TOKENS ?? 1200);
    
    const chatbasePayload = {
      [CHATBASE_ID_FIELD]: CHATBASE_ID,       // Use correct field name
      messages: trimmedMessages,              // [{ role, content }]
      conversationId: sessionId || undefined, // map from our sessionId (optional but correct name)
      stream: streamEnabled,                  // optional; defaults false
      temperature: 0,                         // optional; keep deterministic
      maxTokens: maxOutputTokens,             // Add runtime knobs for better responses
      useKnowledge: true                      // Enable knowledge base usage
    };

    // If streaming is enabled, try streaming first with fallback to non-streaming
    if (streamEnabled) {
      try {
        return await handleStreamingResponse(chatbasePayload, apiKey, CHATBASE_CHAT_ENDPOINT, sessionId || `session_${Date.now()}`, debugMode);
      } catch (error) {
        if (process.env.VERCEL_ENV === 'preview') {
          console.info('CHATBASE: Streaming failed, falling back to non-streaming:', error);
        }
        // Fall through to non-streaming implementation
      }
    }

    // Call Chatbase API with retries (only for 5xx errors)
    let lastError: Error | null = null;
    let lastUpstreamStatus: number | null = null;
    let lastUpstreamBody: string | null = null;
    const maxRetries = 1; // Single retry for 5xx errors only
    const retryDelay = 500; // 500ms backoff

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Preview-only diagnostics
        if (process.env.VERCEL_ENV === 'preview') {
          console.info('CHATBASE OUTBOUND', {
            chatbotIdPresent: Boolean(chatbasePayload.chatbotId),
            messageCount: chatbasePayload.messages?.length ?? 0,
            firstRoles: chatbasePayload.messages?.slice(0, 3).map(m => m.role),
          });
          console.info('CHATBASE: Attempting API call');
          console.info('CHATBASE: URL:', CHATBASE_CHAT_ENDPOINT);
          console.info('CHATBASE: Headers:', {
            'Authorization': `Bearer ${apiKey.substring(0, 8)}...`,
            'Content-Type': 'application/json'
          });
          console.info('CHATBASE: Payload:', JSON.stringify(chatbasePayload, null, 2));
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

        const response = await fetch(CHATBASE_CHAT_ENDPOINT, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(chatbasePayload),
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          
          const headers: Record<string, string> = { 'x-agent-mode': 'live' };
          if (debugMode) {
            headers['x-agent-payload'] = JSON.stringify(chatbasePayload).substring(0, 120);
          }
          // Preview-only debug headers
          if (process.env.VERCEL_ENV === 'preview') {
            headers['x-agent-payload-has-chatbotid'] = Boolean(chatbasePayload.chatbotId).toString();
            headers['x-agent-payload-message-count'] = (chatbasePayload.messages?.length ?? 0).toString();
          }
          
          return NextResponse.json(
            { 
              reply: data.text || data.reply || data.message || 'No response from agent',
              sessionId: data.conversationId || chatbasePayload.conversationId,
              usage: data.usage
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
          console.info(`CHATBASE: API call failed with ${response.status}:`, lastUpstreamBody.substring(0, 200));
        }

                    // Handle 4xx client errors - return error response, don't fall back to mock
                    if (response.status >= 400 && response.status < 500) {
                      const headers: Record<string, string> = { 'x-agent-mode': 'error' };
                      if (process.env.VERCEL_ENV === 'preview') {
                        headers['x-agent-upstream-status'] = response.status.toString();
                        headers['x-agent-upstream-body'] = lastUpstreamBody ? lastUpstreamBody.substring(0, 120).replace(/[^\x20-\x7E]/g, '') : 'No body';
                        headers['x-agent-payload-has-chatbotid'] = Boolean(chatbasePayload.chatbotId).toString();
                        headers['x-agent-payload-message-count'] = (chatbasePayload.messages?.length ?? 0).toString();
                      }
          
          return NextResponse.json(
            { 
              error: 'Chatbase API client error',
              upstream_status: response.status,
              upstream_body: lastUpstreamBody ? lastUpstreamBody.substring(0, 120) : null,
              sessionId: sessionId || `session_${Date.now()}`
            },
            { 
              status: 400, 
              headers
            }
          );
        }

        // Only retry on 5xx server errors
        if (attempt < maxRetries && response.status >= 500 && response.status < 600) {
          console.log(`Retrying in ${retryDelay}ms (attempt ${attempt + 1}/${maxRetries + 1}) - Server error ${response.status}`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          continue;
        }

        // If we've exhausted retries or it's a non-retryable error, break
        break;

      } catch (error) {
        lastError = error as Error;
        if (process.env.VERCEL_ENV === 'preview') {
          console.info(`CHATBASE: API call error:`, error);
        }

        // Only retry on network/timeout errors (not 4xx client errors)
        if (attempt < maxRetries && (
          error instanceof Error && (
            error.name === 'AbortError' || 
            error.message.includes('fetch') ||
            error.message.includes('ECONNREFUSED') ||
            error.message.includes('ETIMEDOUT')
          )
        )) {
          console.log(`Retrying in ${retryDelay}ms (attempt ${attempt + 1}/${maxRetries + 1}) - Network error`);
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          continue;
        }

        // If we've exhausted retries or it's a non-retryable error, break
        break;
      }
    }

    // All attempts failed - check if we should mock or return error
    const inMockMode = process.env.NEXT_PUBLIC_DATA_MODE === "mock";

    if (!inMockMode) {
      // Return proper error instead of silent mocking
      return NextResponse.json(
        {
          error: "chatbase_unavailable",
          upstream_status: lastUpstreamStatus,
          upstream_body: lastUpstreamBody?.slice(0, 200),
          detail: lastError?.message,
          sessionId: sessionId || `session_${Date.now()}`
        },
        { 
          status: 502, 
          headers: { 'x-agent-mode': 'error' } 
        }
      );
    }

    // Explicit mock mode fallback
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
          reason: 'api_failed', 
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
