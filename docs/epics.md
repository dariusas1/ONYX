# ONYX - Epics & Stories Breakdown

**Project:** Manus Internal - Strategic Intelligence System  
**Author:** darius  
**Date:** 2025-11-10  
**Version:** 1.0

---

## Overview

This document decomposes the PRD (docs/PRD.md) into 9 epics and 58 implementable stories organized for 4-week delivery by Dec 15, 2025.

**Delivery Timeline:**
- **Week 1:** Epics 1, 2, 3 (Foundation + Chat + RAG MVP)
- **Week 2:** Epics 4, 5, 6 (Memory + Agent Mode + Tools)
- **Week 3:** Epics 5, 6, 7 (continued) + Epic 8 (Workspace)
- **Week 4:** Epic 9 (DevOps + Launch) + polish & monitoring

**Total Stories:** 58 (avg 6-7 per epic)

---

## Epic 1: Foundation & Infrastructure

**Goal:** Establish stable technical foundation enabling all subsequent feature development

**Scope:** Project setup, Docker environment, deployment pipeline, core service orchestration, CI/CD basics

**Success Criteria:**
- All 5 core Docker services (Suna, Onyx, Qdrant, Supabase, Redis) running locally
- Nginx reverse proxy routing correctly
- Deployment pipeline working (push to GitHub → Docker build → test → deploy)
- All services have health checks and auto-restart
- Team can spin up complete environment with single command

---

### Story 1.1: Project Setup & Repository Initialization

**As a** DevOps engineer  
**I want** a clean repository structure with Docker Compose base setup  
**So that** all team members can develop consistently and deploy predictably

**Acceptance Criteria:**
- Given: Fresh GitHub repo (or branch)
- When: `git clone` + `docker compose up`
- Then: All services start without manual configuration
- And: Health check endpoints return 200 for all services
- And: Logs are aggregated and readable via `docker compose logs`

**Prerequisites:** None (Epic 1.1 is the foundation blocker)

**Technical Notes:**
- Set up Docker Compose with service definitions (suna, onyx-core, qdrant, supabase, redis)
- Include `.env.example` with all required variables
- Add health check scripts for each service
- Document setup in README.md with troubleshooting

---

### Story 1.2: Nginx Reverse Proxy Configuration

**As a** deployment engineer  
**I want** Nginx reverse proxy routing traffic to internal services  
**So that** all external requests use standard HTTP/HTTPS and services remain isolated

**Acceptance Criteria:**
- Given: Nginx container in Docker Compose
- When: Request comes to `http://localhost/api/*`
- Then: Proxied to Suna backend (:3000) and responds correctly
- And: Request to `/chat/*` proxies to Suna (:3000)
- And: Request to `/vnc/*` proxies to noVNC (:6080) [future]
- And: CORS headers configured for frontend ↔ backend

**Prerequisites:** Story 1.1

**Technical Notes:**
- Use nginx:latest image
- Configure upstream blocks for each service
- Add SSL/TLS support (self-signed cert for dev)
- Cache static assets where applicable

---

### Story 1.3: Environment Configuration & Secrets Management

**As a** security engineer  
**I want** a safe way to manage API keys and secrets across environments  
**So that** credentials are never committed to git and prod/dev separation is maintained

**Acceptance Criteria:**
- Given: `.env.example` in repo with all required variables
- When: Dev creates `.env.local` (git-ignored)
- Then: `docker compose up` loads environment variables into containers
- And: No secrets appear in Docker images
- And: `docker compose config` shows masked secrets
- And: Different `.env.*` files work for dev/staging/prod

**Prerequisites:** Story 1.1

**Technical Notes:**
- Use Docker Compose `env_file` directive
- Required vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, DEEPSEEK_API_KEY, SUPABASE_URL, SUPABASE_KEY, QDRANT_API_KEY
- Document in setup guide
- Use `dotenv` npm package for Node services

---

### Story 1.4: CI/CD Pipeline (GitHub Actions)

**As a** DevOps engineer  
**I want** automated testing, building, and deployment on git push  
**So that** code quality is maintained and deployments are fast and reliable

**Acceptance Criteria:**
- Given: Code pushed to GitHub
- When: Workflow triggers on `push` to main/dev branches
- Then: Runs linter, tests, builds Docker images
- And: Pushes images to container registry (optional: Docker Hub)
- And: Deployment script runs (optional: auto-deploy to VPS)
- And: Slack notification sent with status

**Prerequisites:** Story 1.1

**Technical Notes:**
- Create `.github/workflows/main.yml`
- Steps: lint → test → build → push → notify
- Use GitHub secrets for registry credentials
- Support manual approval for prod deployments

---

### Story 1.5: Local Development Environment Setup Guide

**As a** new team member  
**I want** clear, step-by-step instructions to get Manus running locally  
**So that** onboarding is <30 minutes and I can start developing immediately

**Acceptance Criteria:**
- Given: Fresh macOS/Linux/Windows machine
- When: Follow `DEVELOPMENT.md`
- Then: All prerequisites are installed (Docker, Node, Python)
- And: `./scripts/setup.sh` runs without errors
- And: `docker compose up` starts all services
- And: Suna UI accessible at `http://localhost:3000`
- And: All health checks pass

**Prerequisites:** Stories 1.1-1.4

**Technical Notes:**
- Create DEVELOPMENT.md with:
  - System requirements (Docker, Node 18+, Python 3.10+)
  - Step-by-step setup
  - Troubleshooting for common issues
  - Port conflicts resolution
- Create `./scripts/setup.sh` to automate setup
- Include database seeding script

---

### Story 1.6: Monitoring & Logging Foundation

**As a** ops engineer  
**I want** basic logging and health monitoring in place  
**So that** I can identify and debug issues quickly in dev and prod

**Acceptance Criteria:**
- Given: All services running
- When: Services log to stdout
- Then: `docker compose logs` shows all service logs aggregated
- And: Each service includes request/error logs with timestamps
- And: Health check endpoints (`/health`) return JSON status
- And: Prometheus metrics endpoint available at `/metrics` (optional for MVP)

**Prerequisites:** Story 1.1

**Technical Notes:**
- Configure JSON logging for all services
- Use structured logging (Winston for Node, Python logging for Onyx)
- Set up basic health check endpoints
- Document logging format and where to find logs

---

## Epic 2: Chat Interface & Core Intelligence

**Goal:** Enable strategic founder conversations with system intelligence and source transparency

**Scope:** Suna UI deployment, LiteLLM proxy setup, message streaming, system prompt integration, response citation

**Success Criteria:**
- Founder can ask questions and receive streamed responses with sources
- Chat persists across sessions
- System prompt ensures strategic advisor tone
- <1.5s response latency (avg)
- <500ms first token latency (streaming start)

---

### Story 2.1: Suna UI Deployment with Manus Theme

**As a** frontend engineer  
**I want** Suna deployed with Manus dark theme (Inter font, blue accents, minimalist)  
**So that** the UI feels cohesive, branded, and optimized for strategic work

**Acceptance Criteria:**
- Given: Suna running on :3000
- When: User navigates to http://localhost:3000
- Then: Chat interface loads in <2s
- And: Dark theme with blue accents (Manus color palette) is applied
- And: Inter font is used for all text
- And: Layout is single-column, minimalist (focus on conversation)
- And: Mobile responsive (tablet + phone supported)

**Prerequisites:** Story 1.1

**Technical Notes:**
- Fork or use Suna as base (Next.js 14)
- Customize CSS/Tailwind for Manus theme
- Create custom color tokens (primary: #2563EB, background: #0F172A)
- Ensure accessibility (WCAG AA contrast)
- Test on Chrome, Safari, Firefox

---

### Story 2.2: LiteLLM Proxy Setup & Model Routing

**As a** backend engineer  
**I want** LiteLLM proxy routing requests to DeepSeek (Together AI) with Ollama fallback  
**So that** we have a single interface for LLM requests and can switch models without code changes

**Acceptance Criteria:**
- Given: LiteLLM proxy running on separate port
- When: POST `/chat/completions` with model="gpt-4-like"
- Then: Request routes to DeepSeek via Together AI API
- And: If Together AI is down, fallback to Ollama locally
- And: Response is streamed back to client
- And: Rate limiting enforced (100 req/min per user)
- And: Logs include model, tokens used, latency

**Prerequisites:** Stories 1.1, 1.3

**Technical Notes:**
- Deploy LiteLLM in Docker container
- Configure models in config.yaml (primary: deepseek, fallback: ollama)
- Implement circuit breaker for fallback switching
- Use OpenAI-compatible API format
- Log costs and model performance

---

### Story 2.3: Message History & Persistence

**As a** user  
**I want** all my chat messages saved and retrievable across sessions  
**So that** I can review past conversations and continue where I left off

**Acceptance Criteria:**
- Given: User sends message in chat
- When: Message submitted
- Then: Message saved to Supabase with timestamp, user_id, session_id
- And: User can load last 100 messages in current session
- And: Infinite scroll loads older messages (paginated)
- And: Search across all messages by keyword works
- And: Old messages don't slow down current chat (pagination)

**Prerequisites:** Stories 1.1, 2.1, 1.3

**Technical Notes:**
- Create `chats` table in Supabase (id, user_id, session_id, role, content, created_at)
- Add indexes on (user_id, session_id, created_at)
- Implement pagination (limit 50 per request)
- Add search functionality via full-text search or algolia
- Soft-delete messages (don't hard delete)

---

### Story 2.4: Message Streaming & Real-Time Response Display

**As a** user  
**I want** to see LLM responses stream in real-time, character by character  
**So that** I feel engaged and don't wait for the entire response before reading starts

**Acceptance Criteria:**
- Given: User submits question
- When: LLM begins responding
- Then: First token arrives within 500ms
- And: Tokens stream to UI continuously (no batching)
- And: User sees "typing" indicator until streaming complete
- And: Copy button available on complete response
- And: Latency visible in UI (e.g., "Response in 1.2s")

**Prerequisites:** Stories 2.1, 2.2

**Technical Notes:**
- Use SSE (Server-Sent Events) or WebSocket for streaming
- LiteLLM proxy handles streaming from DeepSeek
- Frontend uses EventSource or fetch with ReadableStream
- Show token count + estimated cost for transparency

---

### Story 2.5: System Prompt & Strategic Advisor Tone

**As a** product manager  
**I want** system prompts baked into all LLM responses  
**So that** Manus consistently responds as a strategic advisor (cite sources, think step-by-step, context-aware)

**Acceptance Criteria:**
- Given: User asks question
- When: LiteLLM sends request to DeepSeek
- Then: System prompt prepended to request
- And: Response includes:
  - Step-by-step reasoning (show work)
  - Source citations for claims
  - Strategic implications, not just facts
  - Actionable recommendations
- And: Tone is professional, direct, no fluff

**Prerequisites:** Story 2.2

**Technical Notes:**
- Define system prompt in config (or load from file)
- Prompt should include:
  - Role: "You are Manus, M3rcury's strategic intelligence advisor..."
  - Instructions: "Think step-by-step. Cite all sources. Be concise. Focus on strategic impact."
  - Constraints: "No speculation without data. Disclose uncertainty."
- Test on 10 sample questions to ensure tone

---

### Story 2.6: Response Citation & Source Attribution

**As a** user  
**I want** to see where each fact/claim comes from (source document, timestamp)  
**So that** I can verify information and drill deeper into source material

**Acceptance Criteria:**
- Given: LLM response with citations
- When: Response rendered
- Then: Each claim has superscript citation number [1], [2]
- And: Citation key appears at end: "[1] 2025-11-10 Google Drive: Q3 Metrics"
- And: Citations are clickable links to source (Drive doc, Slack thread, etc.)
- And: If no source, claim marked as "reasoning" (not data-backed)

**Prerequisites:** Stories 2.4, 3.1 (RAG integration)

**Technical Notes:**
- LiteLLM/prompt engineering: instruct model to cite sources
- Frontend: parse citations from response text
- Store citation metadata: source_type, source_id, file_name, url, timestamp
- Support Drive docs, Slack messages, local files

---

## Epic 3: Knowledge Retrieval (RAG)

**Goal:** Unified access to all company knowledge with high relevance, enabling grounded strategic advice

**Scope:** Google Drive sync, Slack sync, local file uploads, Qdrant vector DB, hybrid search, inline citations

**Success Criteria:**
- >95% RAG relevance on 50 internal test queries
- <200ms retrieval latency
- All company data (Drive, Slack, local) indexed and searchable
- Support for multiple file types (Markdown, PDF, CSV, JSON, images)

---

### Story 3.1: Qdrant Vector Database Setup

**As a** backend engineer  
**I want** Qdrant vector database running and configured  
**So that** we have fast semantic search for RAG

**Acceptance Criteria:**
- Given: Qdrant running on :6333
- When: Create collection via API
- Then: Collection created with embedding dimension 1536 (OpenAI model)
- And: API endpoints respond (<100ms)
- And: Can upsert vectors and search
- And: Persistence enabled (data survives container restart)
- And: Health check passes

**Prerequisites:** Story 1.1

**Technical Notes:**
- Deploy Qdrant in Docker (qdrant/qdrant image)
- Create collection with:
  - name: "documents"
  - vector_size: 1536
  - distance: "Cosine"
  - payload_indexing: enabled
- Mount volume for persistence: `/qdrant/storage`
- Document API: create collection, upsert, search endpoints

---

### Story 3.2: Google Drive Connector & Auto-Sync

**As a** user  
**I want** all my Google Drive documents automatically indexed every 10 minutes  
**So that** Manus always has current knowledge without manual uploads

**Acceptance Criteria:**
- Given: User authenticates with Google OAuth
- When: Sync job runs every 10 min
- Then: All Drive files accessible to user are listed
- And: New/modified files detected and indexed
- And: File metadata stored: name, id, modified_at, owner, sharing_status
- And: Respects file permissions (don't index files user can't read)
- And: Sync status visible on dashboard ("Last sync: 2 min ago")
- And: <2% error rate on sync jobs (retry failed files)

**Prerequisites:** Stories 1.1, 1.3, 3.1, 2.1

**Technical Notes:**
- Use google-api-node-js-client with OAuth2
- Sync job: list files from Drive → check if new/modified → index new files
- Store sync metadata in Supabase: file_id, name, mime_type, modified_at, indexed_at
- Support file types: Google Docs (export as Markdown), Sheets (export as CSV), PDFs, images
- Error handling: log failures, alert user if sync breaks

---

### Story 3.3: Slack Connector & Message Indexing

**As a** user  
**I want** all Slack messages and files from channels I'm in indexed every 10 minutes  
**So that** Manus can search company discussions and decisions

**Acceptance Criteria:**
- Given: Slack API token configured
- When: Sync job runs
- Then: Messages from last 10 min retrieved from all accessible channels
- And: Parse threads (include thread replies)
- And: Extract files shared in messages
- And: Index reactions/context (who reacted, how important)
- And: Respect channel privacy (don't index private channels without access)
- And: Metadata stored: channel_id, user_id, timestamp, text, files, thread_id
- And: <2% error rate on sync

**Prerequisites:** Stories 1.1, 1.3, 3.1

**Technical Notes:**
- Use Slack SDK (python-slack-sdk or node slack-sdk)
- Sync: list channels → get history (since last sync) → parse → index
- Support: text, threads, files, emoji reactions
- Store in Supabase: slack_messages table
- Handle rate limits (Slack API has limits per workspace)

---

### Story 3.4: Local File Upload & Parsing

**As a** user  
**I want** to upload files directly (Markdown, PDF, CSV, JSON)  
**So that** I can add custom context not in Drive or Slack

**Acceptance Criteria:**
- Given: User uploads file via Suna UI
- When: File selected (supported type: .md, .pdf, .csv, .json, .txt, .png, .jpg)
- Then: File stored in `/uploads/{user_id}/*`
- And: Parsed into text content
- And: Indexed into Qdrant with metadata
- And: Appears in search results
- And: File size limit: 50MB
- And: Unsupported types show error message

**Prerequisites:** Stories 2.1, 3.1

**Technical Notes:**
- Frontend: file input, validate type/size, show progress
- Backend: save to filesystem or S3, parse content
- Parsing libraries:
  - PDF: pdf-parse (Node) or PyPDF2 (Python)
  - CSV: csv-parser (Node) or pandas (Python)
  - JSON: native parsing
  - Images: OCR via Tesseract or cloud API (optional for MVP)
- Index with metadata: filename, upload_date, user_id, file_type

---

### Story 3.5: Hybrid Search (Semantic + Keyword)

**As a** user  
**I want** search combining semantic meaning (vector) and keyword matching  
**So that** I find relevant documents even if wording differs

**Acceptance Criteria:**
- Given: User asks question
- When: RAG search triggered
- Then: Semantic search in Qdrant returns top-10 candidates (vector similarity)
- And: Keyword search (BM25 or ES) returns top-10 candidates
- And: Results merged and ranked by combined score
- And: Top-5 final results passed to LLM
- And: Retrieval completes in <200ms

**Prerequisites:** Stories 3.1, 3.2, 3.3, 3.4

**Technical Notes:**
- Use Qdrant's built-in search + separate BM25 index (or Elasticsearch)
- Scoring: 70% vector similarity + 30% keyword score
- Re-rank by recency (boost recent documents 10%)
- Filter by source type if needed (Drive only, Slack only)
- Return metadata: filename, snippet (100 chars), source, timestamp

---

### Story 3.6: Citation & Source Link Generation

**As a** user  
**I want** each claim in LLM response linked to original source  
**So that** I can verify info and drill into detail

**Acceptance Criteria:**
- Given: RAG search returns top-5 documents
- When: LLM generates response
- Then: Model instructed to cite sources
- And: Response includes [1], [2] references
- And: Citation key shows: "[1] 2025-11-10 | Google Drive | Q3 Board Deck"
- And: Click citation → opens source (Drive doc, Slack thread in sidebar)
- And: If no relevant source found, response says "No data found"

**Prerequisites:** Stories 3.5, 2.6

**Technical Notes:**
- Prompt engineering: instruct LLM to cite [N] in response
- RAG context includes source metadata in JSON
- Frontend: parse citations, create clickable links
- Support source types: Google Drive, Slack, uploaded files
- Fallback: if source link fails, show text snippet

---

## Epic 4: Persistent Memory & Learning

**Goal:** Manus learns from interactions, recalls standing instructions, and improves over time

**Scope:** Supabase memory schema, memory injection at chat start, standing instructions UI, auto-summarization pipeline

**Success Criteria:**
- 98% memory recall across 5+ sessions
- User can set/edit standing instructions
- Auto-summarization runs every 10 messages
- Memory UI intuitive and fast

---

### Story 4.1: User Memory Schema & Storage

**As a** backend engineer  
**I want** a Supabase schema for storing persistent facts about the user  
**So that** Manus learns and recalls context across sessions

**Acceptance Criteria:**
- Given: Supabase running
- When: Create `user_memories` table
- Then: Table has columns: id, user_id, fact, source_message_id, created_at, expires_at, confidence
- And: Indexes on (user_id, created_at) for fast queries
- And: Support soft-delete (is_deleted flag)
- And: Maximum 1,000 facts per user (auto-prune oldest if exceeded)
- And: Storage query <50ms

**Prerequisites:** Stories 1.1, 1.3

**Technical Notes:**
- Table schema:
  ```sql
  CREATE TABLE user_memories (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    fact TEXT NOT NULL,
    category TEXT (e.g., 'priority', 'decision', 'context'),
    source_message_id UUID,
    created_at TIMESTAMP,
    expires_at TIMESTAMP (optional, for temporary facts),
    confidence FLOAT (0-1, for ranking),
    is_deleted BOOLEAN DEFAULT FALSE
  );
  ```
- Create indexes for performance
- Add RLS policies for user data isolation

---

### Story 4.2: Memory Injection at Chat Start

**As a** user  
**I want** my standing instructions and top-5 memories auto-injected at start of each chat  
**So that** Manus remembers context without me repeating

**Acceptance Criteria:**
- Given: User starts new chat
- When: Chat initialized
- Then: Query `user_memories` for top-5 (ordered by confidence + recency)
- And: Query `standing_instructions` table
- And: Inject into LLM context before first message
- And: Injection shows in system message (optional: "Remembering: [facts]")
- And: <50ms to fetch and inject memories

**Prerequisites:** Stories 4.1, 2.1

**Technical Notes:**
- On new chat session, fetch memories
- Include in LLM system prompt: "User context: [facts]. Standing instructions: [instructions]"
- Show user what was injected (optional UI: "Recalling 5 facts...")
- Soft-fail if memory fetch is slow (show chat without memories, load async)

---

### Story 4.3: Standing Instructions UI & Management

**As a** user  
**I want** to set and edit permanent directives (e.g., "Always prioritize defense contracts")  
**So that** Manus automatically follows my preferences in all conversations

**Acceptance Criteria:**
- Given: User in Manus UI
- When: Click "Standing Instructions" (settings)
- Then: Modal opens showing current instructions (list view)
- And: Can add new instruction (textarea)
- And: Can edit existing instruction
- And: Can delete instruction (confirm first)
- And: Can enable/disable individual instructions
- And: Instructions saved to Supabase immediately
- And: Applied to all future chats

**Prerequisites:** Stories 2.1, 4.1

**Technical Notes:**
- Create UI in Suna (React component)
- Instructions stored in `standing_instructions` table (user_id, instruction_text, enabled, created_at)
- Show preview of how instruction will be injected
- Optional: add priority ranking (reorder instructions)

---

### Story 4.4: Auto-Summarization Pipeline

**As a** backend engineer  
**I want** LLM to summarize every 10 messages and store summary as memory  
**So that** context from long conversations is retained concisely

**Acceptance Criteria:**
- Given: Chat ongoing, 10 messages exchanged
- When: 10th message marked as processed
- Then: Trigger summarization job
- And: LLM reads last 10 messages, generates 2-3 sentence summary
- And: Summary stored in `user_memories` with source_message_id pointing to 10th message
- And: Confidence set to 0.9 (high confidence)
- And: Next memory injection includes new summary
- And: Job completes without user noticing (<2s, async)

**Prerequisites:** Stories 4.1, 2.4

**Technical Notes:**
- Use job queue (Bull for Node, Celery for Python)
- Trigger: on message #10, #20, #30, etc. in a session
- Prompt: "Summarize the following conversation in 2-3 sentences for future recall: [messages]"
- Store summary as memory fact
- Error handling: log failure, don't block chat

---

### Story 4.5: Memory UI & Search

**As a** user  
**I want** to see, edit, and search my stored memories  
**So that** I can manage context and recall what Manus learned about me

**Acceptance Criteria:**
- Given: User in Manus UI
- When: Click "My Memories" (settings)
- Then: List view shows all current memories (paginated)
- And: Search box filters memories by keyword
- And: Can edit memory (update fact text)
- And: Can delete memory
- And: Can set expiration date (fact expires after date)
- And: Shows metadata: created_at, source_message, confidence
- And: Sorting options: recency, confidence, category

**Prerequisites:** Stories 2.1, 4.1

**Technical Notes:**
- Frontend: React component with list, search, edit modal
- Backend: GET /memories, PATCH /memories/{id}, DELETE /memories/{id}
- Search: full-text search in fact column
- Show count: "You have 47 memories"

---

## Epic 5: Agent Mode & Task Execution

**Goal:** Transform Manus from advisor to autonomous executor, enabling multi-step strategic workflows

**Scope:** Agent mode toggle, tool selection logic, approval gates, task history, concurrent execution limits

**Success Criteria:**
- >93% agent task completion rate
- All sensitive actions require approval
- Task history clear and auditable
- Max 3 concurrent tasks without bottlenecks

---

### Story 5.1: Agent Mode Toggle & UI

**As a** user  
**I want** to switch between Chat Mode (advisory) and Agent Mode (execution)  
**So that** I can choose when to give Manus autonomy

**Acceptance Criteria:**
- Given: User in Suna UI
- When: Toggle "Agent Mode" switch (top-right)
- Then: Switch changes state (Chat ↔ Agent)
- And: Agent Mode shows warning: "Agent will execute actions. Review approval gates."
- And: In Agent Mode, "Execute Task" button shown instead of "Send"
- And: In Chat Mode, only "Send" button shown
- And: Mode preference saved to user settings

**Prerequisites:** Stories 2.1

**Technical Notes:**
- Add toggle switch to Suna header
- Store mode in localStorage + Supabase user_settings
- Show different UI/buttons based on mode
- Include help text explaining Agent Mode

---

### Story 5.2: Tool Selection & Routing Logic

**As a** backend engineer  
**I want** agent to autonomously select appropriate tools for tasks  
**So that** complex queries are handled without user specifying each step

**Acceptance Criteria:**
- Given: User submits task in Agent Mode
- When: Agent analyzes task
- Then: Agent selects appropriate tool(s):
  - "search_web" for external research
  - "search_internal" for company data
  - "create_doc" for document generation
  - "scrape_url" for web content
  - "code_execute" for analysis
- And: Tool selection logic logged with reasoning
- And: Wrong tool selection caught (< 5% misclassification)

**Prerequisites:** Stories 2.2, 3.5

**Technical Notes:**
- Use LLM with tool description + examples
- Prompt: "Given task: {task}, select tool and explain why: [tools list]"
- Define tools with descriptions, parameters, constraints
- Log selection for monitoring
- Implement fallback: if tool not available, suggest alternative

---

### Story 5.3: Approval Gates for Sensitive Actions

**As a** security engineer  
**I want** agent to request approval before executing sensitive actions  
**So that** user maintains control and nothing critical executes unintentionally

**Acceptance Criteria:**
- Given: Agent planning sensitive action
- When: Action category is sensitive (create/delete file, execute code, post to Slack)
- Then: Agent pauses and requests approval from user
- And: Approval request shows: action, reason, preview of result
- And: User can approve, reject, or modify
- And: Timeout after 5 min (auto-reject if no response)
- And: Approval recorded in audit log

**Prerequisites:** Stories 5.1, 5.2

**Technical Notes:**
- Define sensitive actions:
  - File operations: create, delete, modify (allow read/search)
  - Code execution: any code_execute tool
  - External posts: create Slack message, create Drive doc with sharing
  - Deletions: any delete operation
- Approval flow: agent pauses → send approval request to UI → user responds → continue or abort
- Store approvals in audit log with user_id, action, timestamp, result

---

### Story 5.4: Multi-Step Task Planning

**As a** user  
**I want** agent to break complex tasks into steps and show plan before executing  
**So that** I understand the approach and can adjust if needed

**Acceptance Criteria:**
- Given: User submits complex task
- When: Agent analyzes task
- Then: Agent creates plan: "Step 1: [action], Step 2: [action]..."
- And: Plan shown to user with option to approve/modify
- And: User can remove/reorder steps
- And: Once approved, agent executes plan step-by-step
- And: Each step can fail independently (show error, skip, retry)

**Prerequisites:** Stories 5.2, 5.3

**Technical Notes:**
- Prompt engineering: "Break down task into steps: [steps]"
- Plan shown as numbered list with descriptions
- User can edit plan (remove steps, reorder) before execution
- Implement step-by-step execution with logging

---

### Story 5.5: Task History & Status Tracking

**As a** user  
**I want** to see all executed tasks with status (pending, running, success, failed)  
**So that** I understand what Manus has done and can troubleshoot failures

**Acceptance Criteria:**
- Given: Agent executes tasks
- When: Task completes or fails
- Then: Task recorded in history with:
  - Title, description
  - Status (pending/running/success/failed)
  - Execution time
  - Result (output, files created, etc.)
  - Error message (if failed)
- And: User can view task history (UI shows last 20)
- And: Can filter by status or date
- And: Can click task to see details, logs, outputs

**Prerequisites:** Stories 5.1, 5.2

**Technical Notes:**
- Create `agent_tasks` table (user_id, title, status, started_at, completed_at, result, error)
- Show task history in UI (sidebar or modal)
- Pagination for large history
- Archive old tasks (keep 100 most recent)

---

### Story 5.6: Task Execution Logs & Debugging

**As a** developer  
**I want** detailed logs for each agent task execution  
**So that** I can debug failures and understand agent reasoning

**Acceptance Criteria:**
- Given: Agent executes task
- When: Task runs
- Then: Logs captured for:
  - Tool selection reasoning
  - Step-by-step execution
  - Tool output (requests/responses)
  - Errors and retries
  - Final result
- And: Logs queryable by task_id in UI
- And: Logs contain timestamps, LLM tokens, latency
- And: User can view logs in task detail view (optional: JSON export)

**Prerequisites:** Stories 5.5, 1.6

**Technical Notes:**
- Log to Supabase or external logging (Sentry)
- Fields: task_id, step_number, action, input, output, error, timestamp, duration
- Show logs in UI as expandable tree
- Highlight errors in red, successes in green

---

### Story 5.7: Task Rollback & Undo

**As a** user  
**I want** to undo the last agent action (delete file, revert sheet edit)  
**So that** I can recover from mistakes

**Acceptance Criteria:**
- Given: Agent creates or modifies resource
- When: Task completes
- Then: "Undo" button available for 5 minutes
- And: Click undo → agent reverts action (delete created file, etc.)
- And: Undo also appears in task history view
- And: Can't undo destructive operations (deletion of irreplaceable files)

**Prerequisites:** Stories 5.5, 5.6

**Technical Notes:**
- Track reversible actions: file create, sheet edit
- Store "undo" command in task record
- Implement: delete created doc, revert sheet to previous version
- Time limit: 5 min after task completion
- Not supported for: deletions, code execution outputs

---

### Story 5.8: Concurrent Task Limits & Queueing

**As a** ops engineer  
**I want** max 3 concurrent agent tasks to prevent VPS overload  
**So that** system remains responsive under load

**Acceptance Criteria:**
- Given: User submits task while 3 tasks running
- When: New task submitted
- Then: New task enters queue (status: "queued")
- And: UI shows "Queued" status with position
- And: Task auto-starts when slot available
- And: Notification sent when task moves to running
- And: User can reorder queue or cancel tasks

**Prerequisites:** Stories 5.5, 1.1

**Technical Notes:**
- Use job queue (Bull for Node, Celery for Python)
- Max concurrent: 3 (configurable based on VPS capacity)
- Store queue in Redis for fast lookup
- Show queue position in UI with estimated wait time

---

## Epic 6: Google Workspace Integration

**Goal:** Enable agent to create, edit, and manage Google Docs/Sheets, expanding autonomous capabilities

**Scope:** Google OAuth setup, Doc/Sheet create/edit, Drive file listing, permission-aware operations

**Success Criteria:**
- Secure OAuth flow with token refresh
- All Google Workspace tools working end-to-end
- Permission awareness prevents unauthorized access
- <2s latency for file operations

---

### Story 6.1: Google OAuth2 Setup & Token Management

**As a** backend engineer  
**I want** secure Google OAuth2 authentication with token refresh  
**So that** Manus can safely access user's Google Workspace without storing passwords

**Acceptance Criteria:**
- Given: User logs in
- When: First use of Google tools
- Then: Redirected to Google login (OAuth2 flow)
- And: User grants Manus permission to access Drive, Docs, Sheets
- And: Token stored encrypted in Supabase (AES-256)
- And: Refresh token auto-refreshed before expiry (<1s overhead)
- And: No credentials visible in logs or error messages

**Prerequisites:** Stories 1.3, 4.1

**Technical Notes:**
- Use google-auth-library-nodejs (Node) or google-auth-httplib2 (Python)
- Store tokens in encrypted column in Supabase
- Scopes: drive, drive.file, spreadsheets
- Refresh token before 1 hour of expiry
- Error handling: if token expired, show "Reconnect Google" UI

---

### Story 6.2: Create Google Doc Tool

**As a** user  
**I want** agent to create new Google Docs with content  
**So that** agent can generate documents (strategies, reports, etc.)

**Acceptance Criteria:**
- Given: Agent invokes create_doc tool
- When: Tool called with title and content
- Then: New Google Doc created in Drive
- And: Document accessible at provided share link
- And: Content formatted with headings, lists, etc.
- And: Returns shareable URL to user
- And: Document created in user's folder (permission-aware)
- And: Execution time <2s

**Prerequisites:** Stories 6.1, 5.2

**Technical Notes:**
- API: POST /tools/create_doc with {title, content, folder_id (optional)}
- Use Google Docs API to create and format document
- Support Markdown → Google Docs conversion
- Return: doc_id, share_link
- Error handling: permission denied, quota exceeded

---

### Story 6.3: Edit Google Doc Tool

**As a** user  
**I want** agent to edit existing Google Docs  
**So that** agent can append to, update, or refine documents

**Acceptance Criteria:**
- Given: Agent invokes edit_doc tool
- When: Tool called with doc_id and action (insert, replace, append)
- Then: Document updated as specified
- And: Change tracked (Google Docs version history)
- And: Confirmation returned to user
- And: User can view changes in Google Docs
- And: Execution time <2s

**Prerequisites:** Stories 6.2

**Technical Notes:**
- API: PATCH /tools/edit_doc with {doc_id, action, content, location (optional)}
- Actions: insert (at position), replace (range), append (end)
- Use Google Docs API batchUpdate
- Return: confirmation, new version URL
- Support Markdown input

---

### Story 6.4: Create Google Sheet Tool

**As a** user  
**I want** agent to create new Google Sheets with data  
**So that** agent can generate tables, dashboards, data analyses

**Acceptance Criteria:**
- Given: Agent invokes create_sheet tool
- When: Tool called with title, headers, and data rows
- Then: New Google Sheet created in Drive
- And: Headers formatted (bold, color)
- And: Data inserted in rows (support 2D array)
- And: Sheet accessible via shareable link
- And: Returns sheet ID and share link
- And: Execution time <2s

**Prerequisites:** Stories 6.1, 5.2

**Technical Notes:**
- API: POST /tools/create_sheet with {title, headers: [], data: [[...]]}
- Use Google Sheets API (sheets.spreadsheets.create)
- Format headers (bold, light background)
- Support CSV/JSON data import
- Return: sheet_id, share_link, worksheet_id

---

### Story 6.5: Edit Google Sheet Tool

**As a** user  
**I want** agent to edit Google Sheets (update cells, add rows/columns)  
**So that** agent can maintain live data, dashboards, and analyses

**Acceptance Criteria:**
- Given: Agent invokes edit_sheet tool
- When: Tool called with sheet_id, range, data
- Then: Specified range updated
- And: Support multiple updates in batch
- And: Confirmation returned
- And: User sees live updates in Google Sheets
- And: Execution time <2s for batch updates

**Prerequisites:** Stories 6.4

**Technical Notes:**
- API: PATCH /tools/edit_sheet with {sheet_id, range, data}
- Range format: "Sheet1!A1:C5"
- Use batchUpdate for multiple changes
- Return: confirmation, affected_range
- Support formulas and formatting

---

### Story 6.6: List Drive Files Tool

**As a** user  
**I want** agent to list files from Drive (with filters)  
**So that** agent can find and reference relevant documents

**Acceptance Criteria:**
- Given: Agent invokes list_drive_files tool
- When: Tool called with optional filters (folder_id, type, name_contains)
- Then: Returns list of files accessible to user
- And: Metadata: file_id, name, type, modified_date, owner
- And: Results limited to 50 (paginated)
- And: Respects folder permissions
- And: Execution time <1s

**Prerequisites:** Stories 6.1

**Technical Notes:**
- API: GET /tools/list_drive_files with query params
- Filters: folder_id, mimeType (document, spreadsheet, pdf), name_contains
- Use Google Drive API files.list with query
- Return: file_id, name, mimeType, modifiedTime, owners
- Pagination support (pageToken)

---

### Story 6.7: Summarize Drive Link Tool

**As a** user  
**I want** agent to read and summarize Google Docs  
**So that** agent can extract key info without opening UI

**Acceptance Criteria:**
- Given: Agent invokes summarize_drive_link tool
- When: Tool called with Drive document URL or doc_id
- Then: Document content fetched and summarized
- And: Summary is 3-5 sentences covering key points
- And: Citations included (sections referenced)
- And: Execution time <3s
- And: Supports Google Docs, Sheets (as table summary)

**Prerequisites:** Stories 6.1

**Technical Notes:**
- API: GET /tools/summarize_drive_link with {url or doc_id}
- Fetch doc content via Google Docs API
- Use LLM to summarize
- Return: summary, key_sections, document_link

---

## Epic 7: Web Automation & Search

**Goal:** Enable agent to research markets, analyze competitors, and execute web tasks

**Scope:** Playwright browser automation, web search (SerpAPI/Exa), URL scraping, form filling

**Success Criteria:**
- Web search returns top-5 results in <3s
- URL scraping extracts clean text content
- Form filling handles common patterns
- <5s latency for web operations

---

### Story 7.1: Playwright Browser Setup & Headless Automation

**As a** backend engineer  
**I want** Playwright headless browser running in Docker  
**So that** agent can automate web tasks (search, scrape, fill forms)

**Acceptance Criteria:**
- Given: Playwright running in container
- When: Agent submits web automation task
- Then: Browser starts without GUI
- And: Can navigate to URLs, interact with pages
- And: Supports screenshots, data extraction
- And: Performance: page load <3s, interaction <1s
- And: Max 1 browser instance active (serial execution)

**Prerequisites:** Story 1.1

**Technical Notes:**
- Deploy playwright in Docker (with Chrome/Firefox)
- Use Playwright Node.js library
- Headless mode by default
- Error handling: timeouts, network failures
- Screenshot support for debugging

---

### Story 7.2: Web Search Tool (SerpAPI or Exa)

**As a** user  
**I want** agent to search the web for information  
**So that** agent can research markets, competitors, trends

**Acceptance Criteria:**
- Given: Agent invokes search_web tool
- When: Tool called with query
- Then: Top-5 results returned with:
  - Title, URL, snippet (100 chars)
  - Source domain
  - Result rank
- And: Results from Google/Bing (via SerpAPI) or Exa
- And: Latency <3s
- And: Supports filtering by time (past week/month/year)

**Prerequisites:** Stories 1.3, 5.2

**Technical Notes:**
- Use SerpAPI (google search) or Exa (AI-powered search)
- API: GET /tools/search_web with {query, time_range (optional)}
- Return: title, url, snippet, position
- Cache results for identical queries (24h TTL)
- Rate limiting: 100 searches/day per user

---

### Story 7.3: URL Scraping & Content Extraction

**As a** user  
**I want** agent to scrape web pages and extract clean text  
**So that** agent can read and analyze web content

**Acceptance Criteria:**
- Given: Agent invokes scrape_url tool
- When: Tool called with URL
- Then: Page loaded and rendered
- And: HTML cleaned (remove ads, scripts, navigation)
- And: Main content extracted (article, page text)
- And: Markdown formatted for readability
- And: Execution time <5s
- And: Returns text_content, metadata (title, author, date)

**Prerequisites:** Stories 7.1

**Technical Notes:**
- Use Playwright to load page (handle JS rendering)
- Extract main content with readability library (readability-node)
- Convert to Markdown
- Metadata: title, author (if present), publish_date
- Error handling: 404, timeout, blocked sites

---

### Story 7.4: Form Filling & Web Interaction

**As a** user  
**I want** agent to fill web forms and interact with pages  
**So that** agent can submit surveys, sign up, interact with web apps

**Acceptance Criteria:**
- Given: Agent invokes fill_form tool
- When: Tool called with URL and field values
- Then: Browser navigates to page
- And: Finds form fields and fills them
- And: Handles common field types (text, select, checkbox, radio)
- And: Can submit form or just fill (agent decides)
- And: Returns success/failure and result page
- And: Execution time <5s

**Prerequisites:** Stories 7.1

**Technical Notes:**
- API: POST /tools/fill_form with {url, fields: {name: value}, submit: boolean}
- Use Playwright's fill() and click() methods
- Support common input types
- Error handling: field not found, CAPTCHA (manual), blocked
- Return: success, result_page_content (optional)

---

### Story 7.5: Screenshot & Page Capture

**As a** user  
**I want** agent to take screenshots of web pages  
**So that** visual information can be analyzed and shared

**Acceptance Criteria:**
- Given: Agent invokes screenshot tool
- When: Tool called with URL
- Then: Browser navigates and waits for page load
- And: Full page screenshot captured
- And: Image returned as base64 or stored in Drive
- And: Resolution: 1920x1080
- And: Execution time <5s

**Prerequisites:** Stories 7.1

**Technical Notes:**
- API: GET /tools/screenshot with {url}
- Use Playwright's screenshot() method
- Full page screenshot (scrollHeight)
- Return: image_base64 or {image_url: Drive link}
- Support PDF export (optional)

---

## Epic 8: Live Workspace (noVNC)

**Goal:** Founder can see and intervene in real-time agent actions via live desktop control

**Scope:** noVNC embed in UI, WebSocket streaming, mouse/keyboard control, intervention workflow, audit trails

**Success Criteria:**
- VNC latency <500ms round-trip
- Streaming smooth at 30fps, 1920x1080
- Founder can pause/takeover/resume agent
- All actions logged for audit

---

### Story 8.1: noVNC Server Setup

**As a** ops engineer  
**I want** noVNC VNC server running on VPS  
**So that** founder can remotely view and control VPS desktop

**Acceptance Criteria:**
- Given: VPS running (Hostinger KVM 4)
- When: noVNC service started
- Then: VNC server listening on :6080 (WebSocket)
- And: Supports resolution 1920x1080
- And: Framerate 30fps target
- And: Compression enabled for lower bandwidth
- And: Security: VNC password set (stored encrypted)

**Prerequisites:** Story 1.1

**Technical Notes:**
- Deploy noVNC in Docker (novnc/novnc image)
- Connect to system VNC or dedicated display
- VNC password: generate and store in .env
- Port: 6080 (WebSocket, :5900 for native VNC)
- Configure compression and JPEG quality

---

### Story 8.2: VNC Embed in Suna UI

**As a** frontend engineer  
**I want** noVNC viewer embedded in Suna UI (right sidebar)  
**So that** founder can watch workspace while chatting

**Acceptance Criteria:**
- Given: User viewing Suna chat
- When: Click "Show Workspace" or toggle workspace panel
- Then: VNC viewer appears in right sidebar (30% width)
- And: VNC connects to noVNC server
- And: Live desktop displayed in real-time
- And: Responsive: works on tablets (landscape)
- And: Can maximize/fullscreen workspace
- And: Can disconnect from workspace (pause watching)

**Prerequisites:** Stories 2.1, 8.1

**Technical Notes:**
- Use noVNC JavaScript client (noVNC/noVNC repo)
- Embed in React component
- WebSocket connection to :6080
- Handle connection errors gracefully
- Optional: show connection status indicator

---

### Story 8.3: Mouse & Keyboard Input Handling

**As a** user  
**I want** to control VPS desktop via mouse and keyboard in workspace panel  
**So that** I can intervene, take over, or adjust agent actions

**Acceptance Criteria:**
- Given: VNC viewer embedded and connected
- When: User moves mouse or types in panel
- Then: Input forwarded to VPC desktop
- And: Cursor visible on remote desktop
- And: Mouse clicks execute on remote
- And: Keyboard input sent (Cmd/Ctrl+C, etc.)
- And: Latency <500ms round-trip (browser → VNC → VPS → browser)
- And: Can hold Cmd and click to interact with UI elements

**Prerequisites:** Stories 8.2

**Technical Notes:**
- noVNC handles input automatically
- Ensure low-latency connection (VPC on same network as browser)
- Test: measure RTT for click-response
- Handle special keys (Cmd, Alt, Ctrl)
- Support mobile input (touch/keyboard on tablet)

---

### Story 8.4: Intervention Workflow (Pause/Takeover/Resume)

**As a** user  
**I want** to pause agent, take manual control, and resume agent  
**So that** I can fix mistakes or guide execution

**Acceptance Criteria:**
- Given: Agent executing task with workspace visible
- When: Click "Pause Agent" button
- Then: Agent pauses (stops executing next step)
- And: Workspace remains live for founder to control
- And: Founder can interact manually (click, type, etc.)
- And: Click "Resume Agent" to continue agent execution
- And: Agent resumes from paused state (no duplication)
- And: State preserved across pause/resume

**Prerequisites:** Stories 8.3, 5.4

**Technical Notes:**
- Add Pause/Resume buttons in workspace UI
- On pause: set agent status to "paused", don't execute next step
- Founder can interact freely while paused
- On resume: agent continues from last checkpoint
- Log: pause/resume events with timestamp

---

### Story 8.5: Audit Trail & Action Logging

**As a** security engineer  
**I want** all workspace actions logged (agent actions, founder interventions)  
**So that** we have audit trail for compliance and debugging

**Acceptance Criteria:**
- Given: Agent executing, founder intervening
- When: Actions occur
- Then: Log stored for:
  - Agent step execution (tool, input, output)
  - Founder mouse clicks (location, target element)
  - Founder keyboard input (what was typed, where)
  - Pause/resume events
  - Screenshots before/after interventions
- And: Logs stored in Supabase (queryable by task_id, user_id, timestamp)
- And: Sensitive inputs masked (passwords, API keys)

**Prerequisites:** Stories 8.1, 8.3, 5.6

**Technical Notes:**
- Log to audit_logs table: task_id, user_id, action_type, action_data, timestamp
- Action types: agent_step, mouse_click, keyboard_input, pause, resume, screenshot
- Mask sensitive fields (password, credit_card, api_key patterns)
- Compression: store action summaries, not verbose details
- Retention: 90 days (auto-prune)

---

## Epic 9: Monitoring, DevOps & Launch

**Goal:** Production-ready system with observability, resilience, and confident launch

**Scope:** Prometheus/Grafana monitoring, error tracking (Sentry), daily backups, incident playbooks, launch checklist

**Success Criteria:**
- 99.5% uptime (target)
- Alert on errors, latency spikes, failing syncs
- Daily backups, <1hr restore time
- Launch checklist completed by Dec 15

---

### Story 9.1: Prometheus Metrics & Grafana Dashboards

**As a** ops engineer  
**I want** Prometheus scraping metrics and Grafana displaying dashboards  
**So that** I can see system health, latency, and resource usage

**Acceptance Criteria:**
- Given: Prometheus and Grafana running in Docker
- When: Services running
- Then: Prometheus scrapes metrics from all services (15s interval)
- And: Grafana dashboards display:
  - CPU, memory, disk usage (all containers)
  - LLM latency (p50, p95, p99)
  - RAG retrieval latency
  - Chat message count (throughput)
  - Error rates (5xx, timeouts)
  - Task completion rate
- And: Dashboards update every 10s
- And: Accessible at http://localhost:3001 (Grafana)

**Prerequisites:** Story 1.1, 1.6

**Technical Notes:**
- Deploy Prometheus and Grafana in Docker
- Configure targets for each service (/metrics endpoint)
- Create dashboards with key metrics
- Set up data retention (7 days for dev, 30 days for prod)
- Alerts (optional for MVP): critical errors, >5s latency

---

### Story 9.2: Sentry Error Tracking & Alerts

**As a** engineer  
**I want** errors automatically reported to Sentry with context  
**So that** I discover bugs and user issues in real-time

**Acceptance Criteria:**
- Given: Sentry project created
- When: Error occurs in production
- Then: Error reported to Sentry with:
  - Stack trace, error message
  - User context (user_id, session_id)
  - Request context (URL, method, headers)
  - Breadcrumbs (recent events leading to error)
- And: Slack notification sent for critical errors
- And: Email digest sent daily
- And: Can group similar errors, assign to team, mark resolved

**Prerequisites:** Story 1.1

**Technical Notes:**
- Add Sentry SDK to Node.js (sentry/node) and Python services
- Configure DSN in .env
- Set error handler middleware
- Include request context in errors
- Ignore: 404s, rate limit errors (configurable)

---

### Story 9.3: Daily Backup Automation

**As a** ops engineer  
**I want** daily automated backups of all persistent data  
**So that** we can recover from data loss or corruption

**Acceptance Criteria:**
- Given: Supabase PostgreSQL and Qdrant vector DB running
- When: 2 AM UTC daily backup job runs
- Then: Snapshots created:
  - Supabase database dump (SQL)
  - Qdrant backup (vector data)
  - Docker volumes backed up
- And: Backups stored on S3 (or VPS secondary drive)
- And: Retention: keep 7 daily + 4 weekly + 12 monthly
- And: Backup logs written (success/failure)
- And: Slack notification on backup completion/failure

**Prerequisites:** Story 1.1

**Technical Notes:**
- Use pg_dump for Supabase backups
- Qdrant has built-in backup endpoint (GET /snapshots)
- Docker volume backups: tar + compress
- Store on S3 or secondary volume on VPS
- Implement retention policy (delete old backups)
- Test restore monthly (automated test)

---

### Story 9.4: Backup Restoration Procedures

**As a** ops engineer  
**I want** documented procedures to restore from backup  
**So that** in emergency, we can recover quickly

**Acceptance Criteria:**
- Given: Data loss or corruption occurs
- When: Follow restoration procedure
- Then: Documented steps to restore:
  - Stop services
  - Restore Supabase from backup
  - Restore Qdrant from backup
  - Restore Docker volumes
  - Start services
  - Verify data integrity
- And: Restoration completes in <1 hour
- And: Tested monthly (dry run)

**Prerequisites:** Story 9.3

**Technical Notes:**
- Create RESTORE.md with step-by-step procedures
- Include rollback steps if something goes wrong
- Automate where possible (script)
- Document: which backup to use, how to verify restore
- Schedule monthly dry-run tests

---

### Story 9.5: Incident Response Playbooks

**As a** ops engineer  
**I want** documented procedures for common incident scenarios  
**So that** we can respond quickly and minimize downtime

**Acceptance Criteria:**
- Given: Common incident occurs
- When: Team follows playbook
- Then: Procedures documented for:
  - LLM service down (fallback to Ollama)
  - Database connection failure (retry + alert)
  - High memory/CPU (restart container, investigate)
  - Qdrant vector DB corruption (restore from backup)
  - SSL cert expiry (auto-renew setup)
  - Sync job failure (alert, manual retry, investigate)
- And: Each playbook includes: symptoms, diagnosis, resolution, prevention
- And: Stored in INCIDENTS.md with decision tree

**Prerequisites:** Story 1.1, 1.6, 9.2

**Technical Notes:**
- Create INCIDENTS.md with playbook index
- Each incident type: symptoms, diagnosis steps, resolution, prevention
- Include escalation: who to contact, when
- Link to Grafana dashboards, logs, Sentry

---

### Story 9.6: Load Testing & Performance Baseline

**As a** engineer  
**I want** load tests to verify system handles expected traffic  
**So that** we launch confident and know bottlenecks

**Acceptance Criteria:**
- Given: System running
- When: Load test run (simulate 20 concurrent users)
- Then: Metrics measured:
  - Chat response latency (target: <1.5s p95)
  - RAG retrieval latency (target: <200ms)
  - Concurrent agent tasks (max 3)
  - Database connection pool (no exhaustion)
  - Memory usage (peak <12GB)
- And: Test results documented
- And: Bottlenecks identified (if any)
- And: Remediation plan created

**Prerequisites:** Story 1.1, 9.1

**Technical Notes:**
- Use k6 or Apache JMeter for load testing
- Scenario: 20 concurrent users, 100 messages total, 10 agent tasks
- Measure: latency, throughput, errors, resource usage
- Load test script in repository (runnable)
- Results baseline for monitoring

---

### Story 9.7: Launch Checklist & Go-Live Procedures

**As a** product manager  
**I want** comprehensive launch checklist to ensure nothing is missed  
**So that** go-live on Dec 15 is smooth and confident

**Acceptance Criteria:**
- Given: Dec 14, 2025 (day before launch)
- When: Launch checklist reviewed and executed
- Then: All items verified:
  - **Code:** All features merged, tests pass, no breaking changes
  - **Deployment:** Docker images built, pushed to registry
  - **Infrastructure:** VPS ready (KVM 4), DNS configured, SSL certs valid
  - **Data:** Backups configured, restore procedure tested
  - **Monitoring:** Sentry set up, Grafana dashboards created, alerts configured
  - **Security:** Google OAuth tokens refreshable, credentials encrypted, no secrets in logs
  - **Documentation:** README, DEVELOPMENT.md, INCIDENTS.md, runbooks complete
  - **Testing:** Load test passed, all features verified in staging
  - **User onboarding:** Founder trained, standing instructions set, initial memories loaded
  - **Launch comms:** Team notified, stakeholders ready
- And: Launch coordinator confirms all items
- And: Go-live proceeds with confidence

**Prerequisites:** All prior stories

**Technical Notes:**
- Create LAUNCH.md with full checklist
- Owner assigned to each section
- Sign-off required from: engineering, ops, PM
- Scheduled for Dec 14 afternoon (give 24h before go-live)

---

## Epic Summary & Dependency Map

### Sequential Dependencies:

1. **Epic 1** → All others (foundation blocker)
2. **Epics 2, 3** → Parallel (Week 1)
3. **Epics 4, 5, 6, 7** → Parallel (Week 2-3, depend on 1+2+3)
4. **Epic 8** → Depends on 5 (Agent Mode) + 2 (UI)
5. **Epic 9** → Ongoing, critical at launch (Week 4)

### Story Count by Epic:

| Epic | Title | Stories | Estimated Effort |
|------|-------|---------|------------------|
| 1 | Foundation | 6 | High |
| 2 | Chat | 6 | High |
| 3 | RAG | 6 | High |
| 4 | Memory | 5 | Medium |
| 5 | Agent | 8 | High |
| 6 | Google Tools | 7 | Medium |
| 7 | Web Automation | 5 | Medium |
| 8 | Workspace | 5 | Medium |
| 9 | DevOps | 7 | Medium |
| **Total** | | **58** | **4 weeks (1 FTE)** |

---

## Story Sizing & Velocity

**Estimated Story Points:**
- Small (1-3 points): Configuration, simple integrations, UI tweaks (20 stories)
- Medium (3-5 points): Feature implementation, complex integrations (28 stories)
- Large (5-8 points): Foundational components, multi-service systems (10 stories)

**Total Estimated Points:** ~180 points

**4-Week Velocity:** 45 points/week (team of 1-2 engineers)

**Risk:** Complex projects may uncover unknowns. Build 20% buffer into schedule.

---

## Next Steps

1. **Review & Approve** - Confirm epic structure and story breakdown with team
2. **Architecture Workflow** - Run `workflow create-architecture` for technical design
3. **Sprint Planning** - Break into 4 weekly sprints, assign stories to developers
4. **Development** - Execute stories in order, maintain velocity tracking

---

_Epic breakdown complete. Ready for architecture design and sprint execution._

_Created: 2025-11-10 | Approved by: (Pending user review)_

