# ONYX (Manus Internal) - Architecture Document

**Project:** Manus Internal - M3rcury's Strategic Intelligence System  
**Author:** Winston (Architect), working with darius  
**Date:** 2025-11-10  
**Version:** 1.0  
**Status:** Approved for Implementation

---

## Executive Summary

Manus Internal is a **multi-service, self-hosted strategic AI platform** combining real-time chat, company-wide RAG, persistent memory, and autonomous agent execution. The architecture prioritizes **operational simplicity, data privacy, and low-latency performance** within a resource-constrained environment (KVM 4: 4 vCPU, 16GB RAM).

**Core Design Principle:** "Boring technology that works" – prefer proven, stable solutions (Next.js, PostgreSQL, Docker) over cutting-edge complexity.

**Deployment Model:** Docker Compose orchestration on Hostinger KVM 4 VPS, with all data and processing internal (no vendor lock-in).

---

## Project Initialization

### Frontend Setup (Week 1, Story 1.1)

```bash
# Create Next.js 14 frontend with TypeScript + Tailwind
npx create-next-app@latest manus-frontend \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias '@/*' \
  --no-eslint \
  --no-git

# Layer Suna UI components on top
# (Suna provides: <ChatInterface>, <MessageList>, <ToolPanel>, etc.)
```

**Starter Template Decisions:**
- ✅ **Framework:** Next.js 14 (App Router, Server Components, streaming)
- ✅ **Styling:** Tailwind CSS + custom Manus dark theme
- ✅ **Language:** TypeScript (strict mode)
- ✅ **Layering:** Suna UI components provide pre-built agent patterns
- ✅ **Backend Services:** Docker Compose handles (not monolithic starter)

**Why Not a Full-Stack Starter:**
- Manus is **multi-service** (Node.js + Python + Qdrant + Supabase + Redis)
- Each service has independent scaling/deployment
- Docker Compose is the "orchestration layer" (more appropriate than a starter template)

---

## Decision Summary

| Category | Decision | Applies To | Version | Rationale |
|----------|----------|-----------|---------|-----------|
| **Frontend Framework** | Next.js 14 | All UI work | 14.0+ | SSR, streaming, App Router, Suna integration |
| **Frontend Styling** | Tailwind CSS + custom theme | All UI | v3.4+ | Performance, consistency with Suna, dark mode native |
| **Language** | TypeScript (strict mode) | All JS/TS | 5.3+ | Type safety, IDE support, catch errors early |
| **Backend API Pattern** | REST + Server Actions | Suna ↔ Frontend | N/A | Simple, streaming-friendly, Next.js native |
| **Data Persistence** | PostgreSQL (Docker) + Redis | All stateful data | PostgreSQL 15+ | Self-hosted, low-latency, full control |
| **Vector Database** | Qdrant (Docker) | RAG layer | 1.7+ | Open-source, hybrid search, self-hosted |
| **Session/Cache** | Redis (Docker) | Memory layer, rate limiting | 7.0+ | Fast, simple, included in Docker |
| **LLM Orchestration** | LiteLLM proxy | Chat, agents | Latest | Multi-provider routing, fallback support |
| **Primary LLM** | DeepSeek (via Together AI) | Reasoning, synthesis | Latest 2024 | Best cost/performance, 128k context |
| **Fallback LLM** | Ollama 7B (local) | If API fails | Latest | Free, local, maintains function |
| **Real-Time Updates** | Server-Sent Events (SSE) | Agent progress | HTTP standard | Uni-directional, low complexity |
| **Workspace Control** | WebSocket (raw) | VNC input/output | Node.js ws | Bidirectional, low-latency |
| **Authentication** | Google OAuth2 | User identity | OAuth 2.0 | Single sign-on, zero password management |
| **Authorization** | Environment-based + IP whitelist | Access control | Custom | Single-user MVP with optional team expansion |
| **Secret Management** | Docker Compose `.env` + encrypted values | API keys, credentials | Custom | Dev/staging/prod separation |
| **File Storage** | Google Drive (streaming) | User data source | Google API v3 | Native integration, permission-aware, no local disk needed |
| **Background Jobs** | BullMQ (Redis queue) | Sync, async tasks | 4.9+ | Simple, Redis-based, job persistence |
| **Testing Framework** | Jest + React Testing Library | Unit, integration | v29+ | Industry standard, good tooling |
| **Build/Bundle** | Next.js native (Webpack) | Build pipeline | 14.0+ | Optimized for Next.js, zero-config |
| **Deployment Target** | Docker (Hostinger KVM 4) | Production | Docker 24+ | Self-hosted, reproducible, scalable |
| **Container Orchestration** | Docker Compose | Local + production | v2.20+ | Simple, single-machine deployment |
| **Monitoring** | Prometheus + Grafana | Observability | Latest | Open-source, self-hosted, proven |
| **Error Tracking** | Sentry (optional, self-hosted) | Error aggregation | Latest | Real-time alerts, stack traces |
| **Logging** | Structured JSON logs → centralized | Observability | Custom format | Parse-friendly, searchable, audit trail |
| **CI/CD** | GitHub Actions | Automation | Native | Free, integrated with GitHub, simple YAML |
| **Code Linting** | ESLint + Prettier | Code quality | Latest | Type-safe linting with TypeScript support |

---

## Project Structure

```
manus-internal/
├── README.md
├── docker-compose.yaml              # Orchestration: Suna, Onyx, Qdrant, Postgres, Redis
├── docker-compose.prod.yaml         # Production overrides
├── .env.example                     # Template for environment variables
├── .github/
│   └── workflows/
│       └── ci-cd.yaml               # GitHub Actions: lint → test → build → deploy
│
├── suna/                            # Next.js 14 frontend (output of create-next-app)
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # Root layout + Manus theme
│   │   │   ├── page.tsx             # Chat home page
│   │   │   ├── api/
│   │   │   │   ├── chat/route.ts    # POST /api/chat - streaming endpoint
│   │   │   │   ├── agent/route.ts   # POST /api/agent - task execution
│   │   │   │   ├── memory/route.ts  # GET/POST /api/memory - user memories
│   │   │   │   ├── auth/[...nextauth]/route.ts # Google OAuth
│   │   │   │   └── workspace/route.ts # VNC control
│   │   │   └── workspace/           # Live workspace page
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx    # Main chat UI
│   │   │   ├── MessageList.tsx      # Conversation history
│   │   │   ├── ToolPanel.tsx        # Agent tool selector
│   │   │   ├── MemoryPanel.tsx      # Memory management UI
│   │   │   └── WorkspaceOverlay.tsx # noVNC embed
│   │   ├── hooks/
│   │   │   ├── useChat.ts           # Chat streaming logic
│   │   │   ├── useAgent.ts          # Agent task execution
│   │   │   └── useMemory.ts         # Memory CRUD
│   │   ├── lib/
│   │   │   ├── api-client.ts        # Fetch utilities
│   │   │   ├── auth.ts              # Session management
│   │   │   └── types.ts             # Shared TypeScript interfaces
│   │   ├── styles/
│   │   │   └── globals.css          # Global styles + Manus dark theme
│   │   └── middleware.ts            # Auth guard, logging
│   └── public/
│       └── favicon.ico
│
├── onyx-core/                       # Python RAG service (separate repo, Docker image)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                      # FastAPI server
│   ├── config/
│   │   ├── qdrant_config.py
│   │   └── connectors.py            # Google Drive, Slack connectors
│   └── services/
│       ├── rag_service.py           # Vector search + BM25 hybrid
│       └── sync_service.py          # Auto-sync jobs
│
├── nginx/                           # Reverse proxy
│   ├── Dockerfile
│   └── nginx.conf                   # Routes /api/* → Suna, /vnc/* → noVNC
│
├── docker/                          # Build contexts
│   ├── Dockerfile.suna              # Next.js production build
│   ├── Dockerfile.onyx              # Python environment
│   └── init-postgres.sql            # Schema + migrations
│
└── docs/
    ├── API.md                       # API specification
    ├── DEVELOPMENT.md               # Setup guide for developers
    ├── DEPLOYMENT.md                # VPS deployment steps
    └── TROUBLESHOOTING.md           # Common issues + fixes

# docker-compose.yaml services:
# - suna (Next.js): 3000
# - onyx-core (Python): 8080
# - postgres: 5432
# - redis: 6379
# - qdrant: 6333
# - nginx: 80, 443
# - litellm-proxy: 4000 (routes to DeepSeek/Ollama)
```

---

## Epic to Architecture Mapping

### Epic 1: Foundation & Infrastructure
- **Deliverable:** Docker Compose, CI/CD, environment setup
- **Owns:** docker-compose.yaml, .github/workflows/
- **Key Services:** All 6 containers, health checks
- **Dependencies:** None (foundation blocker)
- **Stories:** 1.1-1.5 (Project setup, Nginx config, env management, CI/CD, dev setup)

### Epic 2: Chat Foundation
- **Deliverable:** Suna UI, message history, response streaming
- **Owns:** suna/app/page.tsx, suna/components/ChatInterface, suna/app/api/chat/route.ts
- **Key Features:** Infinite scroll, markdown rendering, copy/share
- **Integration:** LiteLLM proxy (HTTP POST)
- **Stories:** 2.1-2.5

### Epic 3: RAG Integration
- **Deliverable:** Connectors (Drive, Slack, local), Qdrant search, citations
- **Owns:** onyx-core/ directory, qdrant service, sync jobs
- **Key Services:** Google Drive API, Slack API, Qdrant vector DB
- **Architecture Pattern:** Background jobs (BullMQ) for auto-sync
- **Stories:** 3.1-3.6

### Epic 4: Memory Layer
- **Deliverable:** Supabase memory schema, injection, standing instructions
- **Owns:** postgres service, suna/app/api/memory/, memory logic in LLM system prompt
- **Key Tables:** users, memories, standing_instructions
- **Injection Point:** Before every chat, top-5 facts added to LLM context
- **Stories:** 4.1-4.5

### Epic 5: Agent Mode
- **Deliverable:** Tool selection, approval gates, task tracking
- **Owns:** suna/app/api/agent/, suna/components/ToolPanel, task history UI
- **Key Tools:** search_web, create_doc, run_code, fill_form, screenshot
- **Safety Pattern:** Approval gates for sensitive actions (file create/delete, code execution)
- **Stories:** 5.1-5.7

### Epic 6: Google Workspace Tools
- **Deliverable:** OAuth flow, doc/sheet CRUD, Drive querying
- **Owns:** onyx-core/services/google_tools.py, suna/app/api/workspace/
- **Key Integrations:** Google Drive API v3, Google Docs API, Google Sheets API
- **Auth:** Google OAuth2, token refresh, credential encryption
- **Stories:** 6.1-6.7

### Epic 7: Web Automation
- **Deliverable:** Playwright browser, web search, URL scraping, form filling
- **Owns:** onyx-core/services/browser_tools.py, Playwright container
- **Key Services:** Playwright headless browser, SerpAPI (or Exa), Cheerio (HTML parsing)
- **Architecture:** Headless browser in Docker, <5s per action
- **Stories:** 7.1-7.5

### Epic 8: Live Workspace
- **Deliverable:** noVNC embed, real-time desktop control, intervention
- **Owns:** suna/components/WorkspaceOverlay, nginx routes /vnc/*
- **Key Services:** noVNC server, VNC-over-WebSocket, VPS desktop/Manus PC display
- **Latency Requirement:** <500ms round-trip
- **Stories:** 8.1-8.5

### Epic 9: Monitoring & DevOps
- **Deliverable:** Prometheus, Grafana, backups, incident response
- **Owns:** prometheus/ docker service, grafana service, backup cron jobs
- **Key Metrics:** CPU, RAM, request latency, error rate, uptime
- **Backup:** Daily snapshots of postgres + qdrant volumes
- **Stories:** 9.1-9.6

---

## Technology Stack Details

### Core Technologies

#### **Frontend: Next.js 14**
- **Purpose:** Server-rendered React, streaming responses, API routes
- **Key Features Used:**
  - App Router (not Pages Router)
  - Server Components for RAG context, memory injection
  - Streaming Response API for chat
  - Server Actions for form submissions
  - Middleware for auth guard
- **Paired With:** Tailwind CSS, TypeScript, Suna UI components
- **Config:** `next.config.js` with custom webpack rules for Qdrant SDK

#### **Backend API: Express (via Suna) or Node.js HTTP**
- **Suna already provides:** Node.js backend, REST API routing, session management
- **Our additions:** Custom /api/chat, /api/agent, /api/memory routes
- **Integration:** Suna's built-in server extends our endpoints

#### **Database: PostgreSQL (Docker)**
- **Schema:**
  - `users` – User identity, OAuth metadata
  - `conversations` – Chat sessions
  - `messages` – Chat history with streaming/citations
  - `memories` – User facts, cross-session recall
  - `standing_instructions` – User directives
  - `tasks` – Agent execution history
  - `documents` – RAG index metadata
- **Scaling:** Currently single instance; can add read replicas later
- **Backup:** Daily snapshots via Docker volumes

#### **Vector Database: Qdrant**
- **Purpose:** Semantic search over documents (embeddings)
- **Hybrid Search:** Combine semantic (vector) + keyword (BM25) scoring
- **Collections:**
  - `documents` – Google Drive/Slack documents
  - `memories` – User facts (for similarity-based recall)
- **Embedding Model:** OpenAI text-embedding-3-small (1536 dims) or open-source alternative
- **Scaling:** Currently self-hosted; can scale to distributed Qdrant later

#### **Cache/Session: Redis (Docker)**
- **Uses:**
  - Session store for auth (user logged in?)
  - Rate limit counters (100 req/min per user)
  - BullMQ job queue for background sync
  - Short-lived memory cache (<5min)
- **Persistence:** RDB snapshots for crash recovery

#### **LLM Orchestration: LiteLLM Proxy**
- **Purpose:** Single interface for multiple LLM providers
- **Configuration:**
  ```yaml
  # litellm config
  model_list:
    - model_name: "deepseek-main"
      litellm_params:
        model: "together/deepseek-chat"
        api_key: "${TOGETHER_API_KEY}"
    - model_name: "ollama-fallback"
      litellm_params:
        model: "ollama/mistral:latest"
        api_base: "http://ollama:11434"
  ```
- **Routing:** Try DeepSeek first, fallback to Ollama if error

#### **Primary LLM: DeepSeek (via Together AI)**
- **Capabilities:** 128k context, strong reasoning, cost-effective
- **Rate Limits:** Handle with exponential backoff + fallback
- **API:** REST, streaming support

#### **Fallback LLM: Ollama 7B**
- **Model:** mistral:7b or neural-chat:7b
- **Deployment:** Docker service (ollama:latest)
- **Use Case:** API outage, rate limit exceeded
- **Trade-off:** Slower (local inference) but free + always available

#### **Background Jobs: BullMQ**
- **Queue Broker:** Redis
- **Jobs:**
  - `sync-google-drive` (every 10 min)
  - `sync-slack` (every 10 min)
  - `auto-summarize-memories` (every 100 messages)
  - `embed-new-documents` (on upload)
- **Retry:** Exponential backoff, max 3 retries

#### **Styling: Tailwind CSS + Custom Theme**
- **Manus Dark Theme:**
  ```css
  /* Tailwind config */
  theme: {
    colors: {
      "manus-bg": "#0f0f0f",       /* Rich black */
      "manus-surface": "#1a1a1a",  /* Dark gray */
      "manus-accent": "#3b82f6",   /* Blue */
      "manus-text": "#e5e7eb",     /* Light gray */
    }
  }
  ```
- **Components:** shadcn/ui (Tailwind component library) + custom Manus adjustments

#### **Authentication: Google OAuth2**
- **Flow:**
  1. User clicks "Sign in with Google"
  2. Redirects to Google consent
  3. Returns auth code
  4. Backend exchanges for access token
  5. Store token encrypted in Supabase
  6. Set session cookie (httpOnly, secure)
- **Libraries:** `next-auth` or `@auth0/nextjs-auth0` (choose one)
- **Scopes:** `openid profile email` + optional `drive.readonly` + `https://www.googleapis.com/auth/spreadsheets`

#### **File Upload/Storage: Google Drive (Streaming)**
- **No local `/uploads` folder initially** – stream directly from Drive to Qdrant
- **Future:** Add `/uploads` for local file imports

---

## Integration Points

### Frontend ↔ Backend (Suna)

**Chat Endpoint:**
```
POST /api/chat
{
  "message": "What's our Q3 revenue trend?",
  "conversationId": "uuid",
  "mode": "chat" | "agent"
}

Response: Server-Sent Events stream
data: {"type": "content", "text": "Based on..."}
data: {"type": "citation", "source": "Q3-Revenue-Report.pdf"}
data: {"type": "done"}
```

**Agent Endpoint:**
```
POST /api/agent
{
  "task": "Create a draft strategy doc comparing us to Anthropic",
  "approvalRequired": true
}

Response: Streaming task progress
{
  "status": "executing",
  "step": "Searching for Anthropic info...",
  "progress": 30
}
```

### Suna ↔ Onyx Core (Python RAG)

**HTTP REST:**
```
POST http://onyx-core:8080/search
{
  "query": "M3rcury competitive positioning",
  "top_k": 5
}

Response:
{
  "results": [
    {"doc_id": "...", "score": 0.92, "text": "..."},
    ...
  ]
}
```

**Sync Jobs:**
```
POST http://onyx-core:8080/sync/google-drive
{
  "folder_id": "M3rcury shared folder ID"
}
```

### Onyx Core ↔ External Services

**Google Drive API:**
```python
# service.py
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# List files in folder
results = drive_service.files().list(
    q=f"'{folder_id}' in parents and trashed=false",
    spaces="drive",
    fields="files(id, name, mimeType, modifiedTime)"
).execute()
```

**Slack API:**
```python
# Use slack_sdk for message/channel enumeration
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
response = client.conversations_list()
```

**Qdrant Vector DB:**
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="qdrant", port=6333)
results = client.search(
    collection_name="documents",
    query_vector=embedding,
    limit=5
)
```

### Frontend ↔ LiteLLM Proxy

**Within Suna backend (Node.js → LiteLLM):**
```javascript
// suna backend routes to LiteLLM
const response = await fetch('http://litellm-proxy:4000/chat/completions', {
  method: 'POST',
  body: JSON.stringify({
    model: 'deepseek-main',
    messages: [...],
    stream: true,
  })
});
```

### VNC Workspace (noVNC)

**Nginx Route:**
```
/vnc/* → http://novnc:6080/vnc.html
```

**WebSocket Upgrade:**
- noVNC embeds websockify proxy
- Client → Nginx (WebSocket upgrade) → noVNC WebSocket → VNC Server

---

## Implementation Patterns

These patterns ensure consistent implementation across all AI agent implementations:

### **Naming Patterns**

#### API Routes (REST Conventions)
```
POST   /api/chat              # Send message, get streaming response
GET    /api/conversations     # List user chats
GET    /api/conversations/:id # Get conversation history
POST   /api/agent             # Submit task for execution
GET    /api/agent/:taskId     # Get task status/logs
POST   /api/memory            # Store new user memory
GET    /api/memory            # List user memories
PATCH  /api/memory/:id        # Edit memory
DELETE /api/memory/:id        # Delete memory
```

#### Database Tables (snake_case, plural)
```sql
users                    -- User identity
conversations           -- Chat sessions
messages               -- Individual messages
memories               -- User facts
standing_instructions  -- Permanent directives
tasks                  -- Agent execution history
documents              -- RAG metadata
api_keys              -- Encrypted credentials
audit_logs            -- Security audit trail
```

#### TypeScript Interfaces (PascalCase, singular)
```typescript
interface User {
  id: string;
  email: string;
  createdAt: Date;
}

interface Message {
  id: string;
  conversationId: string;
  content: string;
  role: 'user' | 'assistant';
}
```

#### Component Names (PascalCase, descriptive)
```
ChatInterface        -- Main chat UI
MessageList         -- Conversation display
ToolPanel           -- Agent tool selector
MemoryManager       -- Memory CRUD UI
WorkspaceOverlay    -- VNC embed
ResponseStreamer    -- LLM streaming display
```

#### Hook Names (use* prefix, camelCase)
```typescript
useChat()       -- Chat streaming logic
useAgent()      -- Agent task execution
useMemory()     -- Memory CRUD
useAuth()       -- Session/OAuth
useWebSocket()  -- Real-time updates
```

#### Environment Variables (SCREAMING_SNAKE_CASE)
```
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
DEEPSEEK_API_KEY
TOGETHER_API_KEY
SUPABASE_URL
SUPABASE_KEY
QDRANT_API_KEY
POSTGRES_PASSWORD
REDIS_PASSWORD
```

---

### **Structure Patterns**

#### Frontend File Organization
```
src/
├── app/
│   ├── api/                    # API routes
│   │   ├── chat/
│   │   ├── agent/
│   │   ├── memory/
│   │   └── auth/
│   ├── (chat)/                 # Chat pages (route group)
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── [conversationId]/page.tsx
│   ├── workspace/              # Workspace pages
│   └── layout.tsx              # Root layout
├── components/                 # Reusable UI
│   ├── Chat/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageList.tsx
│   │   └── InputBox.tsx
│   ├── Agent/
│   │   ├── ToolPanel.tsx
│   │   └── TaskHistory.tsx
│   ├── Memory/
│   │   └── MemoryManager.tsx
│   └── shared/                 # Shared across features
│       ├── Header.tsx
│       └── Sidebar.tsx
├── hooks/                      # Custom React hooks
│   ├── useChat.ts
│   ├── useAgent.ts
│   └── useMemory.ts
├── lib/                        # Utilities, no React
│   ├── api-client.ts          # Fetch wrappers
│   ├── auth.ts                # Session handling
│   ├── types.ts               # Shared TypeScript defs
│   └── constants.ts           # App-wide constants
├── styles/
│   ├── globals.css            # Tailwind + Manus theme
│   └── variables.css          # CSS custom properties
└── middleware.ts              # Auth, logging middleware
```

#### Tests Colocated with Source
```
src/
├── components/
│   ├── ChatInterface.tsx
│   └── ChatInterface.test.tsx
├── lib/
│   ├── api-client.ts
│   └── api-client.test.ts
└── __tests__/                 # E2E tests
    └── chat.e2e.ts
```

---

### **Format Patterns**

#### API Response Format (Standard)
```typescript
// Success response
{
  "success": true,
  "data": {
    "conversationId": "uuid",
    "message": "The Q3 revenue was..."
  }
}

// Error response
{
  "success": false,
  "error": {
    "code": "RAG_SEARCH_FAILED",
    "message": "Failed to retrieve documents",
    "details": "Qdrant connection timeout"
  }
}
```

#### Stream Response Format
```
data: {"type": "content", "text": "Generated"}
data: {"type": "citation", "source": "file.pdf", "link": "..."}
data: {"type": "toolCall", "tool": "search_web", "args": {...}}
data: {"type": "done", "conversationId": "uuid"}
```

#### Database Timestamp Format
```sql
-- Always UTC ISO 8601
created_at TIMESTAMP DEFAULT NOW()  -- PostgreSQL gives UTC
updated_at TIMESTAMP DEFAULT NOW()
-- TypeScript: new Date().toISOString()
```

#### Error Codes (Consistent across backend + frontend)
```typescript
enum ErrorCode {
  AUTH_REQUIRED = "AUTH_REQUIRED",
  RAG_SEARCH_FAILED = "RAG_SEARCH_FAILED",
  LLM_RATE_LIMITED = "LLM_RATE_LIMITED",
  AGENT_APPROVAL_DENIED = "AGENT_APPROVAL_DENIED",
  GOOGLE_API_ERROR = "GOOGLE_API_ERROR",
  WORKSPACE_NOT_AVAILABLE = "WORKSPACE_NOT_AVAILABLE",
}
```

---

### **Communication Patterns**

#### Chat Streaming (SSE)
```javascript
// Frontend
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message, conversationId }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // Parse: data: {"type": "content", ...}
}
```

#### Agent Task Updates (Polling or WebSocket)
```javascript
// Option 1: Poll for status
setInterval(async () => {
  const status = await fetch(`/api/agent/${taskId}`);
  // Update UI with progress
}, 1000);

// Option 2: WebSocket (future)
const ws = new WebSocket('ws://localhost:3000/ws/agent');
ws.send(JSON.stringify({ taskId }));
```

#### Memory Injection (System Prompt)
```
You are a strategic advisor for M3rcury.

Current user context:
- Name: Darius
- Role: Founder
- Key focus: Defense contracts, AI infrastructure
- Recent decision: Prioritizing Onyx development

Answer questions with this context in mind.
```

---

## Consistency Rules

### Error Handling

**Pattern: Try-Catch with Error Mapping**

```typescript
// Frontend
async function submitMessage(message: string) {
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`${error.error.code}: ${error.error.message}`);
    }

    // Process response...
  } catch (error) {
    // Map error to user-friendly message
    const message = getErrorMessage(error);
    showErrorToast(message);
  }
}

function getErrorMessage(error: Error): string {
  if (error.message.includes('AUTH_REQUIRED')) {
    return 'Please sign in to continue';
  }
  if (error.message.includes('RAG_SEARCH_FAILED')) {
    return 'Failed to search documents. Try again?';
  }
  return 'Something went wrong. Please try again.';
}
```

**Pattern: Backend Error Handling**

```typescript
// Suna backend route
export async function POST(req: Request) {
  try {
    const body = await req.json();
    validateInput(body); // throws ValidationError

    const response = await fetch('http://onyx-core:8080/search', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return ErrorResponse('RAG_SEARCH_FAILED', response.statusText);
    }

    return response; // Stream to client
  } catch (error: any) {
    if (error instanceof ValidationError) {
      return ErrorResponse('INVALID_INPUT', error.message);
    }
    return ErrorResponse('INTERNAL_ERROR', error.message);
  }
}

function ErrorResponse(code: string, message: string) {
  return new Response(
    JSON.stringify({ success: false, error: { code, message } }),
    { status: 400, headers: { 'Content-Type': 'application/json' } }
  );
}
```

### Logging Strategy

**Pattern: Structured JSON Logging**

```typescript
// Logger utility
interface LogEntry {
  timestamp: ISO8601string;
  level: 'info' | 'warn' | 'error' | 'debug';
  service: string;
  userId?: string;
  action: string;
  details: Record<string, any>;
  error?: string;
}

function log(level: string, action: string, details: any) {
  const entry: LogEntry = {
    timestamp: new Date().toISOString(),
    level,
    service: 'suna',
    userId: getCurrentUserId?.(),
    action,
    details,
  };
  console.log(JSON.stringify(entry));
}

// Usage
log('info', 'chat_message_received', {
  conversationId: 'abc123',
  messageLength: 42,
});

log('error', 'rag_search_failed', {
  error: 'Qdrant timeout',
  query: 'Q3 revenue',
});
```

**Logs → Stored in: Docker container STDOUT** (captured by Docker logs, can pipe to ELK/Datadog)

**Log Levels:**
- `info` – Normal operations (message received, sync completed)
- `warn` – Degraded (fallback LLM used, API rate limited)
- `error` – Failures (RAG error, auth failure)
- `debug` – Development (detailed step-by-step)

---

## Data Architecture

### PostgreSQL Schema

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  google_id TEXT UNIQUE,
  display_name TEXT,
  encrypted_google_token BYTEA,  -- AES-256 encrypted
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title TEXT DEFAULT 'Untitled',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  role 'user' | 'assistant' NOT NULL,
  content TEXT NOT NULL,
  citations JSONB,  -- [{"source": "file.pdf", "text": "...", "link": "..."}]
  created_at TIMESTAMP DEFAULT NOW()
);

-- User Memories
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  fact TEXT NOT NULL,
  source TEXT,  -- 'manual' | 'extracted_from_chat'
  embedding VECTOR(1536),  -- pgvector for similarity search
  expires_at TIMESTAMP,  -- NULL = permanent
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Standing Instructions
CREATE TABLE standing_instructions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  instruction TEXT NOT NULL,  -- "Always cite sources", "Prioritize X"
  created_at TIMESTAMP DEFAULT NOW()
);

-- Agent Tasks
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  conversation_id UUID REFERENCES conversations(id),
  description TEXT NOT NULL,
  status 'pending' | 'running' | 'success' | 'failed' NOT NULL DEFAULT 'pending',
  steps JSONB,  -- [{"step": 1, "action": "search_web", "status": "done", "output": "..."}]
  result TEXT,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);

-- Document Metadata (RAG)
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type 'google_drive' | 'slack' | 'upload' NOT NULL,
  source_id TEXT,  -- Google file ID, Slack message ID, etc.
  title TEXT NOT NULL,
  content_hash TEXT UNIQUE,  -- For deduplication
  embedding_model TEXT,  -- "text-embedding-3-small"
  synced_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys (Encrypted)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  service_name TEXT NOT NULL,  -- "google_drive", "slack", etc.
  encrypted_key BYTEA NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Audit Logs (Security)
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  action TEXT NOT NULL,  -- "agent_created_doc", "memory_updated", etc.
  details JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Qdrant Vector Collections

```yaml
# documents
{
  "vectors": {
    "size": 1536,  # text-embedding-3-small
    "distance": "Cosine",
    "on_disk": true
  },
  "payload": {
    "doc_id": "string",  # postgres documents.id
    "title": "string",
    "source": "string",  # "google_drive", "slack", etc.
    "chunk_index": "integer",
    "created_at": "string",  # ISO 8601
  }
}

# memories
{
  "vectors": {
    "size": 1536,
    "distance": "Cosine"
  },
  "payload": {
    "memory_id": "string",  # postgres memories.id
    "fact": "string",
    "user_id": "string",
    "expires_at": "string or null"
  }
}
```

---

## API Contracts

### Chat Streaming API

```http
POST /api/chat
Content-Type: application/json

{
  "message": "What's our competitive advantage vs Anthropic?",
  "conversationId": "550e8400-e29b-41d4-a716-446655440000",
  "mode": "chat"
}
```

**Response: Server-Sent Events (streaming)**
```
event: content
data: {"type":"content","text":"Based on your recent "}

event: content
data: {"type":"content","text":"strategic documents..."}

event: citation
data: {"type":"citation","source":"Strategy Doc 2025.pdf","link":"https://drive.google.com/...","text":"M3rcury focuses on..."}

event: done
data: {"type":"done","conversationId":"550e8400-..."}
```

### Agent Task API

```http
POST /api/agent
Content-Type: application/json

{
  "task": "Create a draft competitive analysis doc comparing us to Anthropic and OpenAI",
  "mode": "agent",
  "approvalRequired": true
}
```

**Response:**
```json
{
  "success": true,
  "taskId": "task-uuid",
  "status": "queued"
}
```

**Poll for status:**
```http
GET /api/agent/task-uuid
```

**Response:**
```json
{
  "taskId": "task-uuid",
  "status": "running",
  "progress": 45,
  "currentStep": {
    "step": 2,
    "action": "search_web",
    "description": "Gathering Anthropic market data...",
    "status": "in_progress"
  },
  "steps": [
    {
      "step": 1,
      "action": "search_web",
      "description": "Gather competitive intelligence",
      "status": "completed",
      "output": "Found 5 relevant articles..."
    }
  ]
}
```

### Memory API

```http
GET /api/memory
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "mem-uuid",
      "fact": "Darius prioritizes defense contracts above all else",
      "source": "extracted_from_chat",
      "createdAt": "2025-11-10T15:30:00Z",
      "expiresAt": null
    }
  ]
}
```

```http
POST /api/memory
Content-Type: application/json

{
  "fact": "We're evaluating an acquisition of XYZ company",
  "expiresAt": "2025-12-31T00:00:00Z"
}
```

```http
PATCH /api/memory/mem-uuid
Content-Type: application/json

{
  "fact": "We're evaluating an acquisition of XYZ company (updated)",
  "expiresAt": "2025-12-15T00:00:00Z"
}
```

```http
DELETE /api/memory/mem-uuid
```

---

## Security Architecture

### Authentication Flow

1. **Initiation:** User clicks "Sign in with Google"
2. **Redirect:** Frontend redirects to Google OAuth consent screen
3. **Authorization:** User grants access to email + Drive (if needed)
4. **Callback:** Google returns auth code to `/api/auth/callback/google`
5. **Token Exchange:** Backend exchanges code for access token + refresh token
6. **Encryption:** Store access token encrypted (AES-256) in Supabase
7. **Session:** Set httpOnly, secure cookie with session ID
8. **Subsequent Requests:** Include session cookie; backend validates with Redis

### Authorization Rules

- **Single-user MVP:** Only authenticated user can access their data
- **Team expansion (future):** Role-based access control (RBAC)
  - `owner` – Full access
  - `editor` – Can create/edit documents and memories
  - `viewer` – Read-only

### Credential Management

**Encrypted at rest:**
```typescript
import crypto from 'crypto';

const CIPHER = 'aes-256-cbc';
const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex'); // 32 bytes

function encryptToken(token: string): Buffer {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv(CIPHER, key, iv);
  const encrypted = Buffer.concat([cipher.update(token), cipher.final()]);
  return Buffer.concat([iv, encrypted]);
}

function decryptToken(encrypted: Buffer): string {
  const iv = encrypted.slice(0, 16);
  const decipher = crypto.createDecipheriv(CIPHER, key, iv);
  const decrypted = Buffer.concat([decipher.update(encrypted.slice(16)), decipher.final()]);
  return decrypted.toString();
}
```

**Scopes Requested:**
- Google OAuth: `openid`, `profile`, `email`, `https://www.googleapis.com/auth/drive.readonly`, `https://www.googleapis.com/auth/spreadsheets`
- Never request: write access to user's entire Google account

**Session Invalidation:**
- Auto-logout after 30 minutes of inactivity
- Manual logout clears session cookie + invalidates Redis session

### Approval Gates

**Sensitive Actions (require human approval):**
- Creating Google Docs/Sheets
- Executing code (Python sandbox)
- Accessing workspace (VNC desktop)
- Sensitive Agent Mode tasks

**Implementation:**
```typescript
// Before executing sensitive action
const requiresApproval = ['create_doc', 'run_code', 'workspace_control'].includes(toolName);

if (requiresApproval && !userApproved) {
  return {
    status: 'awaiting_approval',
    message: 'Agent wants to create a document. Approve? (y/n)',
    toolName,
    args
  };
}
```

### Data Access Control

**Google Drive Permission Check:**
```python
# Before syncing a document
user_has_access = drive_service.files().get(
  fileId=doc_id,
  fields='permissions'
).execute()

if user_has_access:
  # Sync document
else:
  # Log unauthorized access attempt
  audit_log(user_id, 'unauthorized_drive_access')
```

---

## Performance Considerations

### Latency Targets

| Operation | Target | How We Achieve |
|-----------|--------|----------------|
| Chat response start | <500ms | Stream first token immediately; inject memories in parallel |
| Message display | <100ms | Client-side rendering optimized; React.memo for list items |
| RAG search | <200ms | Hybrid search (semantic + BM25); index caching in Redis |
| VNC round-trip | <500ms | Same-VPS deployment; WebSocket over direct TCP |
| Page load (SPA) | <2s | Code splitting; Suna pre-optimized |
| Memory injection | <50ms | In-memory cache; no DB hit per chat |

### Optimization Strategies

**Frontend:**
- **Code Splitting:** Route-based chunks (Next.js automatic)
- **Image Optimization:** next/image with lazy loading
- **Memoization:** React.memo for MessageList items
- **Virtual Scrolling:** Large message lists use react-window

**Backend:**
- **Database Indexing:**
  ```sql
  CREATE INDEX idx_conversations_user ON conversations(user_id);
  CREATE INDEX idx_messages_conversation ON messages(conversation_id);
  CREATE INDEX idx_memories_user ON memories(user_id);
  CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
  ```
- **Query Optimization:** Load only necessary columns; pagination for lists
- **Connection Pooling:** pgBouncer for PostgreSQL (max 20 connections)
- **Redis Caching:** Cache frequent RAG results for 5 minutes

**LLM:**
- **Context Optimization:** Inject only top-5 memories + top-3 documents
- **Token Counting:** Monitor token usage; warn if approaching limits
- **Streaming:** Return results as they arrive (don't wait for full response)

**Qdrant:**
- **Vector Quantization:** Use scalar quantization to reduce size (if latency critical)
- **On-Disk Vectors:** Keep vectors on disk; load frequently-accessed to memory

---

## Deployment Architecture

### Docker Compose Layout

```yaml
version: '3.8'
services:
  # Frontend
  suna:
    image: manus/suna:latest
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_BASE: "/"
      DATABASE_URL: "postgresql://user:pass@postgres:5432/manus"
    depends_on:
      - postgres
      - redis

  # Python RAG service
  onyx-core:
    image: manus/onyx-core:latest
    ports:
      - "8080:8080"
    environment:
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      QDRANT_URL: "http://qdrant:6333"
      DATABASE_URL: "postgresql://user:pass@postgres:5432/manus"
    depends_on:
      - qdrant
      - postgres

  # PostgreSQL database
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: manus
      POSTGRES_USER: manus
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/init-postgres.sql:/docker-entrypoint-initdb.d/01-schema.sql

  # Redis cache + job queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Qdrant vector database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  # LiteLLM proxy
  litellm-proxy:
    image: manus/litellm-proxy:latest
    ports:
      - "4000:4000"
    environment:
      TOGETHER_API_KEY: ${TOGETHER_API_KEY}
      OLLAMA_BASE_URL: "http://ollama:11434"
    depends_on:
      - ollama

  # Ollama (fallback LLM)
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama

  # Nginx reverse proxy
  nginx:
    image: manus/nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - suna
      - onyx-core

  # Prometheus monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  # Grafana dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  ollama_models:
  prometheus_data:
  grafana_data:
```

### Production Deployment

**VPS Setup (Hostinger KVM 4):**
1. Install Docker + Docker Compose
2. Clone manus-internal repo
3. Create `.env.prod` with production secrets
4. Run: `docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d`
5. Verify health: `curl http://localhost/api/health`

**SSL/TLS:**
- Self-signed cert for development
- Let's Encrypt for production (certbot + auto-renewal)

**Backups:**
```bash
# Daily backup (cron job at 2 AM UTC)
0 2 * * * /scripts/backup.sh

# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec manus-postgres pg_dump -U manus manus > backups/postgres_$DATE.sql
docker volume inspect manus_qdrant_data | tar czf backups/qdrant_$DATE.tar.gz
```

---

## Development Environment

### Prerequisites

- Docker Desktop or Docker Engine
- Node.js 18+ (for local development if not using Docker)
- Python 3.10+ (for Onyx Core if developing locally)
- Git
- PostgreSQL client (optional, for manual SQL queries)

### Setup Commands

```bash
# Clone repository
git clone https://github.com/m3rcury/manus-internal.git
cd manus-internal

# Create environment file
cp .env.example .env.local

# Edit .env.local with your credentials:
# - GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (from Google Cloud Console)
# - TOGETHER_API_KEY (from Together AI)
# - POSTGRES_PASSWORD (generate a random string)
# - Other API keys...

# Start all services
docker compose up -d

# Verify services are running
docker compose ps

# View logs
docker compose logs -f suna

# Stop services
docker compose down
```

### Development Workflow

```bash
# 1. Frontend changes (auto-reload with Next.js)
cd suna
npm install
npm run dev  # Runs on localhost:3000

# 2. Backend changes (Python RAG service)
cd onyx-core
pip install -r requirements.txt
python -m uvicorn main:app --reload  # Runs on localhost:8080

# 3. Run tests
npm run test

# 4. Lint code
npm run lint
npm run format

# 5. Build for production
npm run build
docker build -f docker/Dockerfile.suna -t manus/suna:latest .
```

---

## Architecture Decision Records (ADRs)

### ADR-001: Next.js 14 with Streaming for Chat

**Decision:** Use Next.js 14 App Router with Server Components and streaming responses for chat.

**Rationale:**
- Native streaming support via Response.readable()
- Server Components reduce bundle size
- Built-in API routes
- Suna already uses Next.js, so consistency

**Alternatives Considered:**
- Remix: More web standards; less ecosystem
- SvelteKit: Smaller but less mature
- Vite + custom server: More control; more complexity

---

### ADR-002: PostgreSQL + Qdrant Separation

**Decision:** Use PostgreSQL for transactional data + Qdrant for semantic search, not a single DB.

**Rationale:**
- PostgreSQL excels at ACID transactions, auth, task history
- Qdrant excels at vector similarity search
- Single DB would require adding vector extensions (pgvector), adding complexity
- Separation allows independent scaling

**Trade-off:** Data consistency between two stores; mitigated by transactional design (write to Postgres first, then update Qdrant).

---

### ADR-003: Self-Hosted vs. Managed Supabase

**Decision:** Use self-hosted PostgreSQL (Docker) instead of Supabase managed.

**Rationale:**
- Same-VPS deployment → <1ms latency
- Full data control (no third-party servers)
- Lower cost (~$25-100/month savings)
- Aligns with self-hosted philosophy

**Trade-off:** We manage backups + upgrades; acceptable for MVP.

---

### ADR-004: Google OAuth2 Single Sign-On

**Decision:** Use Google OAuth2 for authentication, not username/password.

**Rationale:**
- Zero password management
- Seamless for M3rcury team (already using Google Workspace)
- Industry standard
- Easy integration with Google Drive/Sheets APIs (same OAuth token)

**Trade-off:** Dependency on Google; can add alternative auth later.

---

### ADR-005: LiteLLM Proxy with Fallback

**Decision:** Use LiteLLM proxy routing to DeepSeek + Ollama fallback.

**Rationale:**
- DeepSeek: Best cost/performance for 128k context
- Ollama fallback: Ensures function if API fails
- LiteLLM: Easy switching; can add more providers later

**Trade-off:** One more service to manage; outweighed by flexibility + reliability.

---

### ADR-006: RAG Pattern: Hybrid Search

**Decision:** Use hybrid search combining semantic (vector) + keyword (BM25) scoring.

**Rationale:**
- Semantic captures meaning ("competitive positioning" ≈ "market differentiation")
- Keyword catches exact matches ("Q3 revenue")
- Combined > either alone
- Qdrant supports both natively

---

### ADR-007: Server-Sent Events for Agent Progress

**Decision:** Use SSE (Server-Sent Events) for uni-directional agent updates, raw WebSocket for VNC bidirectional.

**Rationale:**
- SSE: Simpler than Socket.io; lower overhead
- WebSocket: Needed for true bidirectional (VNC input + output)
- Mix appropriate: use best tool for each use case

---

## Appendix: Environment Variables

```bash
# Google OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxxx
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google

# LLM
TOGETHER_API_KEY=xxxxxx
DEEPSEEK_MODEL=together/deepseek-chat

# Database
DATABASE_URL=postgresql://manus:password@postgres:5432/manus
POSTGRES_PASSWORD=xxxxxx

# Redis
REDIS_URL=redis://redis:6379

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=xxxxxx (optional)

# Encryption
ENCRYPTION_KEY=xxxxxx (32-byte hex string, 64 chars)

# Monitoring
GRAFANA_PASSWORD=xxxxxx

# Features
ENABLE_WORKSPACE=true
ENABLE_CODE_EXECUTION=true
```

---

## Next Steps

1. **Week 1 (Foundation):** Stories 1.1-1.5 (Docker Compose, Nginx, CI/CD, dev setup)
2. **Week 2 (Chat + RAG):** Stories 2.1-3.6 (Suna UI, LiteLLM proxy, connectors, Qdrant)
3. **Week 3 (Memory + Agent):** Stories 4.1-8.5 (Memory layer, Agent Mode, tools, workspace)
4. **Week 4 (Launch):** Stories 9.1-9.6 (Monitoring, testing, deployment, documentation)

**Ready to begin implementation. Contact architect (Winston) with any design questions.**

---

**Architecture Document Status:** ✅ **APPROVED FOR IMPLEMENTATION**

**Signed by:** darius (approver), Winston (architect)  
**Date:** 2025-11-10  
**Validation Checklist:** All items passed ✓
