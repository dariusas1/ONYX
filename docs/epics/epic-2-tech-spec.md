# Epic 2: Chat Interface & Core Intelligence - Technical Specification

**Project:** ONYX (Manus Internal)
**Epic ID:** epic-2
**Author:** Technical Architect
**Date:** 2025-11-13
**Version:** 1.0
**Status:** Ready for Implementation

---

## Executive Summary

Epic 2 delivers the core chat experience that transforms ONYX from infrastructure into a functional strategic intelligence system. This epic implements a production-ready chat interface with streaming LLM responses, persistent message history, strategic advisor tone, and source attribution - all built on the foundation established in Epic 1.

**Goal:** Enable strategic founder conversations with system intelligence and source transparency

**Success Criteria:**
- Founder can ask questions and receive streamed responses with sources
- Chat persists across sessions with searchable history
- System prompt ensures strategic advisor tone consistently
- Response latency <1.5s average (95th percentile)
- First token latency <500ms (streaming start)
- All citations include source links and metadata

**Timeline:** Week 1 of development (following Epic 1 completion)

**Dependencies:**
- Epic 1 (Foundation & Infrastructure) must be complete
- Docker environment running (Suna, Postgres, Redis, Nginx)
- Environment variables configured

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Epic 2 Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Browser    │────────▶│  Suna (Next) │                 │
│  │   (User)     │◀────────│   Frontend   │                 │
│  └──────────────┘  HTTP   └──────┬───────┘                 │
│                            SSE    │                          │
│                                   │                          │
│                            ┌──────▼───────┐                 │
│                            │  API Routes  │                 │
│                            │ /api/chat    │                 │
│                            └──────┬───────┘                 │
│                                   │                          │
│                    ┌──────────────┼──────────────┐          │
│                    │              │              │          │
│             ┌──────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐    │
│             │ LiteLLM    │ │ Postgres  │ │   Redis   │    │
│             │   Proxy    │ │  (Msgs)   │ │  (Cache)  │    │
│             └──────┬─────┘ └───────────┘ └───────────┘    │
│                    │                                        │
│         ┌──────────┴──────────┐                            │
│         │                     │                            │
│  ┌──────▼─────┐      ┌────────▼────────┐                  │
│  │  DeepSeek  │      │  Ollama (7B)    │                  │
│  │ (Together) │      │   (Fallback)    │                  │
│  └────────────┘      └─────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow (Typical Chat Message)

1. **User Input** → Browser sends POST to `/api/chat`
2. **Message Saved** → Postgres stores user message
3. **Context Assembly** → Load last N messages + system prompt
4. **LLM Request** → Route to DeepSeek via LiteLLM proxy
5. **Stream Response** → Server-Sent Events (SSE) back to browser
6. **Save Assistant Message** → Postgres stores complete response
7. **UI Update** → Display message with citations

---

## Story-by-Story Technical Details

### Story 2.1: Suna UI Deployment with Manus Theme

**Objective:** Deploy functional Next.js chat interface with Manus dark theme

#### Implementation Details

**Frontend Stack:**
- Next.js 14 (App Router)
- React 18 with Server Components
- Tailwind CSS with custom Manus theme
- TypeScript (strict mode)

**Manus Theme Specification:**
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'manus': {
          'bg': '#0F172A',        // Deep navy background
          'surface': '#1E293B',   // Elevated surface
          'accent': '#2563EB',    // Primary blue
          'text': '#E2E8F0',      // Light gray text
          'muted': '#64748B',     // Muted text
          'border': '#334155',    // Border color
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      }
    }
  }
}
```

**Key Components:**
```typescript
// src/app/page.tsx - Main chat page
interface ChatPageProps {
  searchParams: { conversationId?: string };
}

export default function ChatPage({ searchParams }: ChatPageProps) {
  return (
    <main className="h-screen flex flex-col bg-manus-bg">
      <Header />
      <ChatInterface conversationId={searchParams.conversationId} />
    </main>
  );
}

// src/components/ChatInterface.tsx - Core chat component
interface ChatInterfaceProps {
  conversationId?: string;
}

export function ChatInterface({ conversationId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  // Implementation in Story 2.4
  const handleSubmit = useCallback(async (message: string) => {
    // Stream message handling
  }, []);

  return (
    <div className="flex-1 flex flex-col">
      <MessageList messages={messages} />
      <InputBox
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={isStreaming}
      />
    </div>
  );
}
```

**Responsive Design:**
- Desktop: Full-width single column (max 900px centered)
- Tablet: Full-width with adjusted padding
- Mobile: Full viewport, optimized touch targets

**Accessibility Requirements:**
- WCAG AA contrast ratios (4.5:1 minimum)
- Keyboard navigation support
- Screen reader compatibility
- Focus indicators on all interactive elements

**Acceptance Criteria:**
- ✓ Chat interface loads in <2s on localhost
- ✓ Dark theme with Manus colors applied
- ✓ Inter font family loaded and applied
- ✓ Single-column minimalist layout
- ✓ Responsive on desktop, tablet, mobile
- ✓ Passes accessibility audit (Lighthouse >90)

---

### Story 2.2: LiteLLM Proxy Setup & Model Routing

**Objective:** Unified LLM interface with DeepSeek primary and Ollama fallback

#### Implementation Details

**LiteLLM Configuration:**
```yaml
# litellm-config.yaml
model_list:
  - model_name: "manus-primary"
    litellm_params:
      model: "together_ai/deepseek-chat"
      api_key: "${TOGETHER_API_KEY}"
      max_tokens: 4096
      temperature: 0.7
      stream: true

  - model_name: "manus-fallback"
    litellm_params:
      model: "ollama/mistral:7b-instruct"
      api_base: "http://ollama:11434"
      stream: true

# Fallback routing
router_settings:
  routing_strategy: "simple-fallback"
  allowed_fails: 3
  fallback_models: ["manus-fallback"]

# Rate limiting
litellm_settings:
  success_callback: ["prometheus"]
  failure_callback: ["sentry"]
  rate_limit:
    rpm: 100
    tpm: 100000
```

**Docker Service:**
```yaml
# docker-compose.yaml addition
services:
  litellm-proxy:
    image: ghcr.io/berriai/litellm:latest
    container_name: onyx-litellm
    ports:
      - "4000:4000"
    environment:
      TOGETHER_API_KEY: ${TOGETHER_API_KEY}
      LITELLM_CONFIG_PATH: /app/config.yaml
    volumes:
      - ./litellm-config.yaml:/app/config.yaml
    depends_on:
      - ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: onyx-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
```

**Backend Integration:**
```typescript
// src/lib/llm-client.ts
import { OpenAI } from 'openai';

export const llmClient = new OpenAI({
  apiKey: 'dummy-key', // LiteLLM doesn't validate
  baseURL: 'http://litellm-proxy:4000',
});

export async function streamChatCompletion(
  messages: Array<{ role: string; content: string }>,
  onChunk: (chunk: string) => void,
  onError: (error: Error) => void
) {
  try {
    const stream = await llmClient.chat.completions.create({
      model: 'manus-primary',
      messages,
      stream: true,
      max_tokens: 4096,
      temperature: 0.7,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        onChunk(content);
      }
    }
  } catch (error) {
    console.error('LLM streaming error:', error);
    onError(error as Error);
  }
}
```

**Circuit Breaker Pattern:**
```typescript
// src/lib/circuit-breaker.ts
class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime = 0;
  private readonly failureThreshold = 3;
  private readonly resetTimeout = 60000; // 1 minute

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.isOpen()) {
      throw new Error('Circuit breaker is OPEN - using fallback');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private isOpen(): boolean {
    if (this.failureCount >= this.failureThreshold) {
      const timeSinceLastFailure = Date.now() - this.lastFailureTime;
      return timeSinceLastFailure < this.resetTimeout;
    }
    return false;
  }

  private onSuccess() {
    this.failureCount = 0;
  }

  private onFailure() {
    this.failureCount++;
    this.lastFailureTime = Date.now();
  }
}
```

**Logging & Monitoring:**
```typescript
// Structured logging for LLM calls
interface LLMLogEntry {
  timestamp: string;
  model: string;
  tokens: {
    prompt: number;
    completion: number;
    total: number;
  };
  latency_ms: number;
  success: boolean;
  error?: string;
}

function logLLMCall(entry: LLMLogEntry) {
  console.log(JSON.stringify({
    level: 'info',
    service: 'llm-proxy',
    action: 'completion',
    ...entry,
  }));
}
```

**Acceptance Criteria:**
- ✓ LiteLLM proxy running on port 4000
- ✓ DeepSeek requests route successfully
- ✓ Ollama fallback activates on DeepSeek failure
- ✓ Streaming responses work end-to-end
- ✓ Rate limiting enforced (100 req/min per user)
- ✓ Logs include model, tokens, latency

---

### Story 2.3: Message History & Persistence

**Objective:** All messages saved to Postgres with efficient retrieval

#### Implementation Details

**Database Schema:**
```sql
-- Conversations table
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT DEFAULT 'New Conversation',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(user_id, updated_at DESC);

-- Messages table
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at ASC);
CREATE INDEX idx_messages_search ON messages USING gin(to_tsvector('english', content));

-- Update conversation timestamp trigger
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE conversations
  SET updated_at = NOW()
  WHERE id = NEW.conversation_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_update_conversation
  AFTER INSERT ON messages
  FOR EACH ROW
  EXECUTE FUNCTION update_conversation_timestamp();
```

**API Routes:**
```typescript
// src/app/api/conversations/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { db } from '@/lib/db';

export async function GET(req: NextRequest) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const limit = parseInt(searchParams.get('limit') || '50');
  const offset = parseInt(searchParams.get('offset') || '0');

  const conversations = await db.query(
    `SELECT id, title, created_at, updated_at
     FROM conversations
     WHERE user_id = $1
     ORDER BY updated_at DESC
     LIMIT $2 OFFSET $3`,
    [session.user.id, limit, offset]
  );

  return NextResponse.json({
    success: true,
    data: conversations.rows
  });
}

export async function POST(req: NextRequest) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { title } = await req.json();

  const result = await db.query(
    `INSERT INTO conversations (user_id, title)
     VALUES ($1, $2)
     RETURNING id, title, created_at, updated_at`,
    [session.user.id, title || 'New Conversation']
  );

  return NextResponse.json({
    success: true,
    data: result.rows[0]
  });
}

// src/app/api/conversations/[id]/messages/route.ts
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const limit = parseInt(searchParams.get('limit') || '100');
  const before = searchParams.get('before'); // For pagination

  let query = `
    SELECT m.id, m.role, m.content, m.metadata, m.created_at
    FROM messages m
    JOIN conversations c ON m.conversation_id = c.id
    WHERE c.id = $1 AND c.user_id = $2
  `;

  const queryParams: any[] = [params.id, session.user.id];

  if (before) {
    query += ` AND m.created_at < $3`;
    queryParams.push(before);
  }

  query += ` ORDER BY m.created_at DESC LIMIT $${queryParams.length + 1}`;
  queryParams.push(limit);

  const messages = await db.query(query, queryParams);

  return NextResponse.json({
    success: true,
    data: messages.rows.reverse() // Return chronological order
  });
}
```

**Frontend Hooks:**
```typescript
// src/hooks/useConversation.ts
import { useState, useEffect } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata: Record<string, any>;
  created_at: string;
}

export function useConversation(conversationId: string | undefined) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    if (!conversationId) return;

    async function loadMessages() {
      setLoading(true);
      try {
        const res = await fetch(
          `/api/conversations/${conversationId}/messages?limit=100`
        );
        const { data } = await res.json();
        setMessages(data);
        setHasMore(data.length === 100);
      } catch (error) {
        console.error('Failed to load messages:', error);
      } finally {
        setLoading(false);
      }
    }

    loadMessages();
  }, [conversationId]);

  const loadMoreMessages = async () => {
    if (!conversationId || !messages.length) return;

    const oldestMessage = messages[0];
    const res = await fetch(
      `/api/conversations/${conversationId}/messages?limit=50&before=${oldestMessage.created_at}`
    );
    const { data } = await res.json();

    setMessages(prev => [...data, ...prev]);
    setHasMore(data.length === 50);
  };

  return { messages, loading, hasMore, loadMoreMessages };
}
```

**Search Implementation:**
```typescript
// src/app/api/search/route.ts
export async function GET(req: NextRequest) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const query = searchParams.get('q');

  if (!query) {
    return NextResponse.json({ error: 'Query required' }, { status: 400 });
  }

  const results = await db.query(
    `SELECT
       m.id, m.content, m.created_at,
       c.id as conversation_id, c.title,
       ts_rank(to_tsvector('english', m.content), plainto_tsquery('english', $2)) as rank
     FROM messages m
     JOIN conversations c ON m.conversation_id = c.id
     WHERE c.user_id = $1
       AND to_tsvector('english', m.content) @@ plainto_tsquery('english', $2)
     ORDER BY rank DESC, m.created_at DESC
     LIMIT 50`,
    [session.user.id, query]
  );

  return NextResponse.json({
    success: true,
    data: results.rows
  });
}
```

**Acceptance Criteria:**
- ✓ Messages saved to Postgres on send
- ✓ Load last 100 messages per conversation
- ✓ Infinite scroll loads older messages (paginated)
- ✓ Full-text search across all messages works
- ✓ Query performance <100ms for message retrieval
- ✓ Conversation list sorted by recent activity

---

### Story 2.4: Message Streaming & Real-Time Response Display

**Objective:** Real-time streaming LLM responses with <500ms first token latency

#### Implementation Details

**Streaming API Route:**
```typescript
// src/app/api/chat/route.ts
import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { db } from '@/lib/db';
import { streamChatCompletion } from '@/lib/llm-client';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return new Response('Unauthorized', { status: 401 });
  }

  const { message, conversationId } = await req.json();

  // Save user message
  const userMessage = await db.query(
    `INSERT INTO messages (conversation_id, role, content)
     VALUES ($1, 'user', $2)
     RETURNING id, created_at`,
    [conversationId, message]
  );

  // Load conversation history
  const history = await db.query(
    `SELECT role, content
     FROM messages
     WHERE conversation_id = $1
     ORDER BY created_at ASC
     LIMIT 50`,
    [conversationId]
  );

  const messages = [
    { role: 'system', content: await getSystemPrompt(session.user.id) },
    ...history.rows.map(row => ({ role: row.role, content: row.content })),
  ];

  // Create streaming response
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let assistantMessage = '';
      let messageId: string | null = null;

      try {
        await streamChatCompletion(
          messages,
          // On chunk received
          (chunk: string) => {
            assistantMessage += chunk;

            // Send chunk to client
            const data = JSON.stringify({
              type: 'content',
              content: chunk
            });
            controller.enqueue(encoder.encode(`data: ${data}\n\n`));
          },
          // On error
          (error: Error) => {
            const data = JSON.stringify({
              type: 'error',
              error: error.message
            });
            controller.enqueue(encoder.encode(`data: ${data}\n\n`));
            controller.close();
          }
        );

        // Save complete assistant message
        const result = await db.query(
          `INSERT INTO messages (conversation_id, role, content)
           VALUES ($1, 'assistant', $2)
           RETURNING id`,
          [conversationId, assistantMessage]
        );
        messageId = result.rows[0].id;

        // Send completion
        const data = JSON.stringify({
          type: 'done',
          messageId
        });
        controller.enqueue(encoder.encode(`data: ${data}\n\n`));
        controller.close();

      } catch (error) {
        console.error('Streaming error:', error);
        const data = JSON.stringify({
          type: 'error',
          error: 'Failed to generate response'
        });
        controller.enqueue(encoder.encode(`data: ${data}\n\n`));
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

**Frontend Streaming Hook:**
```typescript
// src/hooks/useChat.ts
import { useState, useCallback } from 'react';

interface StreamMessage {
  type: 'content' | 'citation' | 'done' | 'error';
  content?: string;
  messageId?: string;
  error?: string;
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');

  const sendMessage = useCallback(async (content: string) => {
    // Add user message optimistically
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Start streaming
    setIsStreaming(true);
    setStreamingContent('');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, conversationId }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No response body');

      let assistantMessage = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;

          const data: StreamMessage = JSON.parse(line.slice(6));

          if (data.type === 'content') {
            assistantMessage += data.content;
            setStreamingContent(assistantMessage);
          } else if (data.type === 'done') {
            // Add complete assistant message
            setMessages(prev => [...prev, {
              id: data.messageId!,
              role: 'assistant',
              content: assistantMessage,
              created_at: new Date().toISOString(),
            }]);
            setStreamingContent('');
          } else if (data.type === 'error') {
            console.error('Stream error:', data.error);
            alert('Failed to get response: ' + data.error);
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message');
    } finally {
      setIsStreaming(false);
    }
  }, [conversationId]);

  return {
    messages,
    isStreaming,
    streamingContent,
    sendMessage,
  };
}
```

**UI Components:**
```typescript
// src/components/MessageList.tsx
interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
}

export function MessageList({ messages, streamingContent }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map(message => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {streamingContent && (
        <MessageBubble
          message={{
            id: 'streaming',
            role: 'assistant',
            content: streamingContent,
            created_at: new Date().toISOString(),
          }}
          isStreaming
        />
      )}

      <div ref={bottomRef} />
    </div>
  );
}

// src/components/MessageBubble.tsx
interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-manus-accent text-white'
            : 'bg-manus-surface text-manus-text'
        }`}
      >
        <ReactMarkdown className="prose prose-invert prose-sm max-w-none">
          {message.content}
        </ReactMarkdown>

        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
        )}

        <div className="mt-2 text-xs opacity-60">
          {new Date(message.created_at).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
```

**Performance Monitoring:**
```typescript
// src/lib/metrics.ts
interface StreamMetrics {
  firstTokenLatency: number;
  totalDuration: number;
  tokenCount: number;
  tokensPerSecond: number;
}

export function measureStreamPerformance(): {
  recordFirstToken: () => void;
  recordComplete: (tokenCount: number) => StreamMetrics;
} {
  const startTime = Date.now();
  let firstTokenTime: number | null = null;

  return {
    recordFirstToken() {
      if (!firstTokenTime) {
        firstTokenTime = Date.now();
      }
    },

    recordComplete(tokenCount: number) {
      const endTime = Date.now();
      const totalDuration = endTime - startTime;
      const firstTokenLatency = firstTokenTime
        ? firstTokenTime - startTime
        : 0;
      const tokensPerSecond = (tokenCount / totalDuration) * 1000;

      const metrics: StreamMetrics = {
        firstTokenLatency,
        totalDuration,
        tokenCount,
        tokensPerSecond,
      };

      // Log metrics
      console.log(JSON.stringify({
        level: 'info',
        action: 'stream_complete',
        ...metrics,
      }));

      return metrics;
    },
  };
}
```

**Acceptance Criteria:**
- ✓ First token arrives within 500ms
- ✓ Tokens stream continuously (no batching)
- ✓ Typing indicator during streaming
- ✓ Copy button on complete response
- ✓ Latency displayed in UI
- ✓ Auto-scroll to latest message

---

### Story 2.5: System Prompt & Strategic Advisor Tone

**Objective:** Consistent strategic advisor persona across all responses

#### Implementation Details

**System Prompt Template:**
```typescript
// src/lib/prompts.ts
export function buildSystemPrompt(userContext?: {
  name?: string;
  role?: string;
  standingInstructions?: string[];
}): string {
  const basePrompt = `You are Manus, M3rcury's strategic intelligence advisor. You assist the founding team with high-stakes strategic decisions.

CORE PRINCIPLES:
1. Think step-by-step - show your reasoning process
2. Cite sources for all factual claims - reference specific documents
3. Focus on strategic implications, not just facts
4. Provide actionable recommendations
5. Be concise and direct - no fluff or unnecessary pleasantries
6. Disclose uncertainty when data is incomplete
7. Challenge assumptions constructively

RESPONSE FORMAT:
- Start with a direct answer to the question
- Follow with supporting reasoning (2-3 key points)
- Include relevant citations [1], [2] at end
- End with strategic recommendation or next steps

TONE:
- Professional but conversational
- Confident yet humble about limitations
- Focus on "why" and "what next" not just "what"
- Avoid speculation without clearly marking it as such`;

  let contextSection = '';

  if (userContext) {
    contextSection = '\n\nUSER CONTEXT:';
    if (userContext.name) {
      contextSection += `\n- Name: ${userContext.name}`;
    }
    if (userContext.role) {
      contextSection += `\n- Role: ${userContext.role}`;
    }
    if (userContext.standingInstructions?.length) {
      contextSection += '\n- Standing Instructions:';
      userContext.standingInstructions.forEach(instruction => {
        contextSection += `\n  * ${instruction}`;
      });
    }
  }

  return basePrompt + contextSection;
}
```

**Dynamic System Prompt Loading:**
```typescript
// src/lib/system-prompt.ts
import { db } from './db';

export async function getSystemPrompt(userId: string): Promise<string> {
  // Load user profile
  const userResult = await db.query(
    `SELECT display_name, email FROM users WHERE id = $1`,
    [userId]
  );
  const user = userResult.rows[0];

  // Load standing instructions
  const instructionsResult = await db.query(
    `SELECT instruction
     FROM standing_instructions
     WHERE user_id = $1 AND enabled = true
     ORDER BY created_at ASC`,
    [userId]
  );

  const standingInstructions = instructionsResult.rows.map(
    row => row.instruction
  );

  return buildSystemPrompt({
    name: user.display_name,
    role: 'Founder', // Could be fetched from user profile
    standingInstructions,
  });
}
```

**Example Prompts for Testing:**
```typescript
// tests/fixtures/test-prompts.ts
export const TEST_PROMPTS = [
  {
    query: "What's our competitive advantage vs Anthropic?",
    expectedTone: [
      'step-by-step reasoning',
      'cited sources',
      'strategic implications',
      'actionable recommendation'
    ]
  },
  {
    query: "Should we pivot to defense contracts?",
    expectedTone: [
      'direct answer first',
      'pros and cons analysis',
      'risk assessment',
      'clear recommendation with rationale'
    ]
  },
  {
    query: "What was Q3 revenue?",
    expectedTone: [
      'specific number with source',
      'context (vs target, vs Q2)',
      'implications for strategy',
      'data quality disclosure if uncertain'
    ]
  }
];
```

**Tone Evaluation Criteria:**
```typescript
// src/lib/tone-validator.ts
interface ToneCheck {
  hasCitations: boolean;
  hasReasoning: boolean;
  hasRecommendation: boolean;
  isConcise: boolean;
  avoidsSpeculation: boolean;
}

export function validateTone(response: string): ToneCheck {
  return {
    hasCitations: /\[\d+\]/.test(response),
    hasReasoning: response.toLowerCase().includes('because') ||
                   response.toLowerCase().includes('since'),
    hasRecommendation: response.toLowerCase().includes('recommend') ||
                        response.toLowerCase().includes('should'),
    isConcise: response.split(' ').length < 500,
    avoidsSpeculation: !response.toLowerCase().includes('maybe') ||
                        response.includes('uncertain') ||
                        response.includes('unclear')
  };
}
```

**Standing Instructions Management:**
```sql
-- Standing instructions table
CREATE TABLE standing_instructions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  instruction TEXT NOT NULL,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_standing_instructions_user ON standing_instructions(user_id, enabled);
```

**Acceptance Criteria:**
- ✓ System prompt prepended to all LLM requests
- ✓ Responses include step-by-step reasoning
- ✓ Sources cited for factual claims
- ✓ Strategic implications highlighted
- ✓ Actionable recommendations provided
- ✓ Tone is professional and direct
- ✓ Standing instructions loaded from database

---

### Story 2.6: Response Citation & Source Attribution

**Objective:** Every fact traceable to source document with clickable links

#### Implementation Details

**Citation Format:**
```typescript
// src/lib/citations.ts
export interface Citation {
  id: string;
  source_type: 'google_drive' | 'slack' | 'upload' | 'web';
  source_id: string;
  title: string;
  url?: string;
  snippet?: string;
  timestamp?: string;
}

export interface CitedResponse {
  content: string;
  citations: Citation[];
}

// Parse citations from LLM response
export function parseCitations(response: string): CitedResponse {
  const citationRegex = /\[(\d+)\]/g;
  const citations: Citation[] = [];
  const matches = response.matchAll(citationRegex);

  for (const match of matches) {
    const citationNumber = parseInt(match[1]);
    // Citations will be populated by RAG system (Epic 3)
    // For now, placeholder
  }

  return {
    content: response,
    citations,
  };
}

// Format citation for display
export function formatCitation(citation: Citation, index: number): string {
  const parts = [
    `[${index + 1}]`,
    citation.timestamp ? new Date(citation.timestamp).toLocaleDateString() : '',
    citation.source_type === 'google_drive' ? 'Google Drive' :
    citation.source_type === 'slack' ? 'Slack' :
    citation.source_type === 'upload' ? 'Upload' : 'Web',
    citation.title,
  ].filter(Boolean);

  return parts.join(' | ');
}
```

**Citation UI Component:**
```typescript
// src/components/CitationList.tsx
interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (!citations.length) return null;

  return (
    <div className="mt-4 pt-4 border-t border-manus-border">
      <h4 className="text-sm font-semibold text-manus-muted mb-2">
        Sources
      </h4>
      <ul className="space-y-2">
        {citations.map((citation, index) => (
          <li key={citation.id} className="text-sm">
            <a
              href={citation.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="text-manus-accent hover:underline flex items-center gap-2"
            >
              <span className="font-mono text-xs">[{index + 1}]</span>
              <span>{formatCitation(citation, index)}</span>
              {citation.url && (
                <ExternalLinkIcon className="w-3 h-3" />
              )}
            </a>
            {citation.snippet && (
              <p className="ml-6 mt-1 text-manus-muted italic">
                "{citation.snippet}"
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// Update MessageBubble to include citations
export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const { content, citations } = parseCitations(message.content);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={/* ... */}>
        <ReactMarkdown>{content}</ReactMarkdown>

        {!isUser && <CitationList citations={citations} />}

        {/* ... */}
      </div>
    </div>
  );
}
```

**Database Schema for Citations:**
```sql
-- Store citations with messages
ALTER TABLE messages
ADD COLUMN citations JSONB DEFAULT '[]'::jsonb;

CREATE INDEX idx_messages_citations ON messages USING gin(citations);

-- Example citation JSON structure
/*
{
  "citations": [
    {
      "id": "cite-1",
      "source_type": "google_drive",
      "source_id": "1a2b3c4d",
      "title": "Q3 Board Deck",
      "url": "https://drive.google.com/...",
      "snippet": "Revenue increased 45% YoY",
      "timestamp": "2025-11-10T14:30:00Z"
    }
  ]
}
*/
```

**Citation Extraction from RAG Results:**
```typescript
// src/lib/rag-citations.ts (Interface for Epic 3)
export interface RAGResult {
  doc_id: string;
  score: number;
  text: string;
  metadata: {
    source_type: string;
    source_id: string;
    title: string;
    url?: string;
    timestamp?: string;
  };
}

export function createCitationsFromRAG(ragResults: RAGResult[]): Citation[] {
  return ragResults.map((result, index) => ({
    id: `cite-${index}`,
    source_type: result.metadata.source_type as Citation['source_type'],
    source_id: result.metadata.source_id,
    title: result.metadata.title,
    url: result.metadata.url,
    snippet: result.text.slice(0, 200) + '...',
    timestamp: result.metadata.timestamp,
  }));
}
```

**LLM Prompt Enhancement for Citations:**
```typescript
// src/lib/prompts.ts - Addition to system prompt
export function buildSystemPromptWithRAG(
  userContext: any,
  ragResults: RAGResult[]
): string {
  const basePrompt = buildSystemPrompt(userContext);

  if (!ragResults.length) {
    return basePrompt + '\n\nNo relevant documents found in company knowledge base.';
  }

  const contextSection = '\n\nRELEVANT DOCUMENTS:\n' +
    ragResults.map((result, index) =>
      `[${index + 1}] ${result.metadata.title}\n${result.text}\n`
    ).join('\n');

  const citationInstructions = `\n\nIMPORTANT: When citing information from the documents above, use inline citations like [1], [2] immediately after the relevant claim. Be specific about which document supports each claim.`;

  return basePrompt + contextSection + citationInstructions;
}
```

**Acceptance Criteria:**
- ✓ Each factual claim has citation [1], [2], etc.
- ✓ Citation list appears at end of message
- ✓ Citations show: date, source type, document name
- ✓ Citations are clickable links (when URL available)
- ✓ Reasoning-only claims marked as such (no citation)
- ✓ Citations stored in database with messages

---

## Integration Points

### Story Dependencies

```
Story 2.1 (Suna UI)
    ↓
Story 2.2 (LiteLLM) ──→ Story 2.4 (Streaming)
    ↓                        ↓
Story 2.3 (Persistence) ──→ Story 2.5 (System Prompt)
                                ↓
                         Story 2.6 (Citations)
```

**Critical Path:**
1. Stories 2.1 and 2.2 must be complete before 2.4
2. Story 2.3 (persistence) blocks all others
3. Story 2.5 can proceed in parallel with 2.4
4. Story 2.6 requires 2.4 and 2.5 complete
5. Full Epic 2 requires all stories complete

### External Dependencies

**From Epic 1:**
- ✓ Docker Compose environment running
- ✓ Postgres database initialized
- ✓ Redis cache available
- ✓ Nginx reverse proxy configured
- ✓ Environment variables set

**For Epic 3 (RAG):**
- Citation infrastructure ready (Story 2.6)
- Message storage for indexing (Story 2.3)
- System prompt template extensible (Story 2.5)

---

## Testing Strategy

### Unit Tests

```typescript
// __tests__/lib/prompts.test.ts
describe('buildSystemPrompt', () => {
  it('generates base prompt correctly', () => {
    const prompt = buildSystemPrompt();
    expect(prompt).toContain('Manus');
    expect(prompt).toContain('strategic advisor');
    expect(prompt).toContain('cite sources');
  });

  it('includes user context when provided', () => {
    const prompt = buildSystemPrompt({
      name: 'Darius',
      role: 'Founder',
      standingInstructions: ['Prioritize defense contracts'],
    });
    expect(prompt).toContain('Darius');
    expect(prompt).toContain('defense contracts');
  });
});

// __tests__/lib/citations.test.ts
describe('parseCitations', () => {
  it('extracts citation numbers', () => {
    const response = 'Revenue increased [1] and costs decreased [2].';
    const { content, citations } = parseCitations(response);
    expect(content).toBe(response);
  });

  it('formats citations correctly', () => {
    const citation: Citation = {
      id: 'cite-1',
      source_type: 'google_drive',
      source_id: '123',
      title: 'Q3 Report',
      timestamp: '2025-11-10',
    };
    const formatted = formatCitation(citation, 0);
    expect(formatted).toContain('[1]');
    expect(formatted).toContain('Google Drive');
    expect(formatted).toContain('Q3 Report');
  });
});
```

### Integration Tests

```typescript
// __tests__/api/chat.integration.test.ts
describe('POST /api/chat', () => {
  it('streams response successfully', async () => {
    const response = await fetch('http://localhost:3000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': testSessionCookie,
      },
      body: JSON.stringify({
        message: 'What is our strategy?',
        conversationId: testConversationId,
      }),
    });

    expect(response.headers.get('Content-Type')).toBe('text/event-stream');

    const reader = response.body.getReader();
    const chunks: string[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(new TextDecoder().decode(value));
    }

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.some(c => c.includes('type":"content'))).toBe(true);
    expect(chunks.some(c => c.includes('type":"done'))).toBe(true);
  });

  it('saves messages to database', async () => {
    // Send message
    await sendTestMessage('Test message');

    // Verify in database
    const messages = await db.query(
      'SELECT * FROM messages WHERE conversation_id = $1 ORDER BY created_at',
      [testConversationId]
    );

    expect(messages.rows.length).toBeGreaterThanOrEqual(2); // User + assistant
    expect(messages.rows[0].content).toBe('Test message');
    expect(messages.rows[0].role).toBe('user');
    expect(messages.rows[1].role).toBe('assistant');
  });
});
```

### E2E Tests

```typescript
// __tests__/e2e/chat-flow.e2e.ts
import { test, expect } from '@playwright/test';

test('complete chat flow', async ({ page }) => {
  // Navigate to app
  await page.goto('http://localhost:3000');

  // Sign in (if needed)
  await page.click('text=Sign in with Google');
  // ... OAuth flow ...

  // Start new conversation
  await page.click('button:has-text("New Chat")');

  // Type and send message
  await page.fill('[data-testid="chat-input"]', 'What is our Q3 revenue?');
  await page.press('[data-testid="chat-input"]', 'Enter');

  // Wait for streaming to start
  await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();

  // Wait for response
  await expect(page.locator('.message.assistant').first()).toBeVisible({
    timeout: 10000,
  });

  // Verify response has content
  const responseText = await page.locator('.message.assistant').first().textContent();
  expect(responseText).toBeTruthy();
  expect(responseText.length).toBeGreaterThan(10);

  // Verify citations appear (if any)
  const hasCitations = await page.locator('.citation-list').count() > 0;
  // Citations expected after Epic 3
});
```

### Performance Tests

```typescript
// __tests__/performance/streaming.perf.ts
describe('Streaming Performance', () => {
  it('achieves <500ms first token latency', async () => {
    const startTime = Date.now();
    let firstTokenTime: number | null = null;

    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: 'Quick question',
        conversationId: testConversationId,
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const { value } = await reader.read();
    firstTokenTime = Date.now();

    const firstTokenLatency = firstTokenTime - startTime;

    expect(firstTokenLatency).toBeLessThan(500);
  });

  it('maintains streaming throughput', async () => {
    const tokens: number[] = [];
    let lastTokenTime = Date.now();

    // Measure time between tokens
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: 'Give me a detailed explanation',
        conversationId: testConversationId,
      }),
    });

    const reader = response.body.getReader();

    while (true) {
      const { done } = await reader.read();
      if (done) break;

      const now = Date.now();
      const delta = now - lastTokenTime;
      tokens.push(delta);
      lastTokenTime = now;
    }

    const avgTokenLatency = tokens.reduce((a, b) => a + b, 0) / tokens.length;

    // Expect < 50ms average between tokens
    expect(avgTokenLatency).toBeLessThan(50);
  });
});
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All Epic 1 stories complete
- [ ] Docker Compose services healthy
- [ ] Environment variables configured:
  - [ ] `TOGETHER_API_KEY` set
  - [ ] `DATABASE_URL` set
  - [ ] `REDIS_URL` set
  - [ ] `NEXTAUTH_SECRET` generated
- [ ] Database migrations applied
- [ ] SSL certificate configured (Nginx)

### Deployment Steps

1. **Build Frontend:**
   ```bash
   cd suna
   npm run build
   docker build -f ../docker/Dockerfile.suna -t onyx/suna:latest .
   ```

2. **Start Services:**
   ```bash
   docker compose up -d litellm-proxy ollama
   docker compose up -d suna
   ```

3. **Verify Health:**
   ```bash
   curl http://localhost:3000/api/health
   curl http://localhost:4000/health
   ```

4. **Run Smoke Tests:**
   ```bash
   npm run test:e2e:smoke
   ```

### Post-Deployment

- [ ] Monitor first 10 chat messages
- [ ] Verify streaming latency <500ms
- [ ] Check database for saved messages
- [ ] Confirm LiteLLM fallback works (test by stopping Together AI)
- [ ] Review logs for errors
- [ ] Update sprint status: `epic-2: contexted`

---

## Monitoring & Metrics

### Key Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| First Token Latency | <500ms | LiteLLM logs, frontend timing |
| Full Response Latency | <1.5s (p95) | End-to-end timing |
| Message Save Latency | <50ms | Database query time |
| Streaming Throughput | >20 tokens/sec | Token count / duration |
| Error Rate | <1% | Failed requests / total |
| Database Connection Pool | <10 active | Postgres stats |

### Logging

```typescript
// Structured logging format
interface ChatLogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  service: 'suna' | 'litellm' | 'postgres';
  action: string;
  userId?: string;
  conversationId?: string;
  latency_ms?: number;
  tokens?: number;
  error?: string;
}

// Example log entries
{
  "timestamp": "2025-11-13T10:30:00Z",
  "level": "info",
  "service": "suna",
  "action": "chat_message_sent",
  "userId": "user-123",
  "conversationId": "conv-456"
}

{
  "timestamp": "2025-11-13T10:30:01Z",
  "level": "info",
  "service": "litellm",
  "action": "stream_complete",
  "latency_ms": 1247,
  "tokens": 342,
  "model": "manus-primary"
}
```

### Alerts

- **Critical:**
  - First token latency >1000ms (5 consecutive)
  - Error rate >5% (1-minute window)
  - Database connection pool exhausted
  - LiteLLM proxy down

- **Warning:**
  - First token latency >500ms (10 consecutive)
  - Error rate >2%
  - Ollama fallback activated

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| DeepSeek API outage | Medium | High | Ollama fallback, circuit breaker |
| Streaming breaks on network issues | Medium | Medium | Retry logic, chunked fallback |
| Database connection pool exhaustion | Low | High | Connection limits, pooling |
| System prompt too large (context limit) | Low | Medium | Truncate old messages, summarization |
| Citation parsing fails | Low | Low | Graceful degradation, log errors |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Users expect instant responses | High | Low | Set expectations (500ms target shown) |
| Token costs exceed budget | Low | Medium | Rate limiting, cost monitoring |
| Message history grows unbounded | Medium | High | Pagination, archival strategy |

---

## Success Criteria Validation

### Functional Requirements

- ✓ Chat interface loads and accepts input
- ✓ Messages stream from LLM in real-time
- ✓ All messages persist to database
- ✓ Conversation history loads correctly
- ✓ System prompt applied consistently
- ✓ Citations appear in responses

### Non-Functional Requirements

- ✓ First token latency <500ms (95th percentile)
- ✓ Full response latency <1.5s (95th percentile)
- ✓ UI responsive (<100ms interactions)
- ✓ Messages saved in <50ms
- ✓ Search returns results in <200ms

### User Experience

- ✓ Typing indicator during streaming
- ✓ Auto-scroll to latest message
- ✓ Copy button on responses
- ✓ Mobile responsive
- ✓ Keyboard shortcuts work
- ✓ Error messages are clear

---

## Next Steps

### After Epic 2 Completion

1. **Epic 3: Knowledge Retrieval (RAG)**
   - Integrate Qdrant vector search
   - Add Google Drive connector
   - Populate citations from RAG results

2. **Epic 4: Persistent Memory**
   - Store user facts across sessions
   - Inject memories into system prompt
   - Build memory management UI

3. **Enhancements**
   - Add message editing
   - Implement message search UI
   - Add conversation sharing
   - Voice input (optional)

---

## Appendix

### Environment Variables Reference

```bash
# Epic 2 Required Variables
TOGETHER_API_KEY=sk-...              # Together AI API key
DATABASE_URL=postgresql://...        # Postgres connection string
REDIS_URL=redis://...                # Redis connection string
NEXTAUTH_SECRET=...                  # NextAuth.js secret (32+ chars)
NEXTAUTH_URL=http://localhost:3000   # App URL

# Optional
OLLAMA_BASE_URL=http://ollama:11434  # Ollama fallback
SENTRY_DSN=https://...               # Error tracking
```

### API Endpoint Reference

```
POST   /api/chat                      # Send message, stream response
GET    /api/conversations             # List user conversations
POST   /api/conversations             # Create new conversation
GET    /api/conversations/:id/messages # Get conversation messages
GET    /api/search                    # Search all messages
GET    /api/health                    # Health check
```

### Database Schema Reference

See full schema in Story 2.3 section above.

---

## Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-13 | Technical Architect | Initial epic tech spec |

**Approval:**

- [ ] Technical Lead Review
- [ ] Product Owner Review
- [ ] Security Review (if needed)
- [ ] Ready for Sprint Planning

**Status:** Ready for Implementation

---

_This technical specification provides comprehensive implementation guidance for Epic 2: Chat Interface & Core Intelligence. All stories are scoped, architecturally sound, and ready for development._
