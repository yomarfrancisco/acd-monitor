import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Single source of truth for Chatbase configuration
const ROOT = 'https://www.chatbase.co/api/v1';
const CHATBOT_ID = process.env.CHATBASE_ASSISTANT_ID!;   // same ID the widget uses

const MESSAGE_URL = `${ROOT}/chatbot/${CHATBOT_ID}/message`;
const STREAM_URL = `${ROOT}/chatbot/${CHATBOT_ID}/message/stream`;

// Identity Verification helper
function ivHeaders(userId: string): Record<string, string> {
  const secret = process.env.CHATBASE_SIGNING_SECRET;
  if (!secret || !userId) return {};
  const user_hash = crypto.createHmac('sha256', secret).update(userId).digest('hex');
  return {
    'X-Chatbase-User-Id': userId,
    'X-Chatbase-User-Hash': user_hash
  };
}

interface ChatMessage {
  role?: 'user' | 'assistant' | 'system';
  type?: 'user' | 'agent' | 'assistant' | 'bot';
  content: string;
}

interface ChatRequest {
  messages: ChatMessage[];
  sessionId?: string;
  userId?: string;
  stream?: boolean;
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
  response: Response,
  endpoint: string
): Promise<ReadableStream> {
  if (!response.body) {
    throw new Error("No response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  return new ReadableStream({
    start(controller) {
      const pump = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              controller.close();
              break;
            }

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                  controller.close();
                  return;
                }

                try {
                  const parsed = JSON.parse(data);
                  if (parsed.content) {
                    controller.enqueue(
                      new TextEncoder().encode(`data: ${JSON.stringify({ content: parsed.content })}\n\n`)
                    );
                  }
                } catch (e) {
                  // Skip malformed JSON
                }
              }
            }
          }
        } catch (error) {
          console.error('Streaming error:', error);
          controller.error(error);
        }
      };

      pump();
    }
  });
}

export async function POST(request: NextRequest): Promise<NextResponse<ChatResponse> | Response> {
  try {
    const body: ChatRequest = await request.json();
    const { messages, sessionId, userId, stream = false } = body;

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return NextResponse.json(
        { reply: '[mock] Please provide a valid message.', sessionId: sessionId || 'default' },
        { status: 400, headers: { 'x-agent-mode': 'mock' } }
      );
    }

    // Check if Chatbase is enabled
    const isChatbaseEnabled = process.env.NEXT_PUBLIC_AGENT_CHAT_ENABLED === 'true';
    const isStreamingEnabled = process.env.NEXT_PUBLIC_AGENT_CHAT_STREAM === 'true';

    if (!isChatbaseEnabled) {
      return NextResponse.json({ 
        message: "Chatbase integration is disabled",
        mock: true 
      });
    }

    // If no API key, use mock response
    if (!process.env.CHATBASE_API_KEY) {
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

    // Normalize and trim messages
    const normalizedMessages = normalizeMessagesForChatbase(messages);
    const trimmedMessages = trimMessagesForTokenLimit(normalizedMessages);

    // Build minimal payload according to Chatbase API docs
    const payload = {
      messages: trimmedMessages,   // roles ONLY "user"|"assistant"
      stream: stream && isStreamingEnabled,       // true only if using STREAM_URL
      temperature: 0
    };

    // Use correct endpoint based on streaming preference
    const url = (stream && isStreamingEnabled) ? STREAM_URL : MESSAGE_URL;

    // Diagnostic logging
    console.error("[CB] URL:", url);
    console.error("[CB] METHOD:", "POST");
    console.error("[CB] CHATBOT_ID present:", Boolean(CHATBOT_ID), "len:", (CHATBOT_ID||"").length);
    console.error("[CB] HEADERS:", { auth: !!process.env.CHATBASE_API_KEY });
    console.error("[CB] BODY.keys:", Object.keys(payload));

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.CHATBASE_API_KEY}`,
          'Content-Type': 'application/json',
          ...ivHeaders(userId || '')
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      const body = await response.text();
      console.error("[CB] STATUS:", response.status);
      console.error("[CB] RESP BODY (first 300):", body.slice(0,300));

      if (!response.ok) {
        console.error('Chatbase API error:', response.status, body);
        return NextResponse.json(
          { error: `Chatbase API error: ${response.status} ${body}` },
          { status: response.status }
        );
      }

      if (stream && isStreamingEnabled) {
        const stream = await handleStreamingResponse(response, url);
        return new NextResponse(stream, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        });
      } else {
        const data = JSON.parse(body);
        return NextResponse.json(data);
      }

    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error && error.name === 'AbortError') {
        console.error('Chatbase API timeout');
        return NextResponse.json(
          { error: 'Chatbase API timeout' },
          { status: 504 }
        );
      }

      console.error('Chatbase API error:', error);
      return NextResponse.json(
        { error: 'Chatbase API client error' },
        { status: 502 }
      );
    }

  } catch (error) {
    console.error('Route error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}