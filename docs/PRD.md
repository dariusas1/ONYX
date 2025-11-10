# ONYX - Product Requirements Document

**Author:** darius
**Date:** 2025-11-10
**Version:** 1.0 (Final, Approved)

---

## Executive Summary

**Manus Internal** is M3rcury's private, self-hosted strategic intelligence system—a unified platform combining Suna-powered chat, full company-wide RAG, persistent memory, and advanced agentic capabilities.

**Core Value Proposition:**
- **One place** for strategic knowledge (Google Drive, Slack, local context all unified)
- **Persistent intelligence** that learns from every interaction
- **Autonomous execution** (document creation, web research, data analysis, live workspace)
- **Zero lock-in** (self-hosted, unlimited use, full data control)

**Business Impact:**
- Reduce founder cognitive load by >7 hours/week
- Enable strategic decision-making in <2 minutes per query
- Generate weekly strategic insights proactively
- Build a compounding intelligence asset worth $1M+ over 2 years

**Target Release:** Q4 2025 (December 15, 2025)

### What Makes This Special

**The Magic: A strategic advisor that knows everything, remembers everything, and can act on anything.**

Unlike ChatGPT (generic, external), Slack (fragmented), or Onyx 1.0 (search-only), Manus Internal is purpose-built for strategic leadership:

1. **Complete Context** – Full RAG over all M3rcury data (not just search, but synthesis)
2. **Persistent Memory** – Learns standing instructions, recalls context across chats
3. **Real Execution** – Creates documents, analyzes data, researches markets, not just talks
4. **Live Oversight** – Founder can see and intervene in agent actions in real-time via VNC
5. **Deep Reasoning** – 128k context + chain-of-thought for complex strategic problems
6. **Strategic Tone** – Built specifically for executive decision-making, not general chat

**The Moment:** A founder asks Manus a hard strategic question at 11pm. Within 2 minutes, Manus synthesizes internal context (past decisions, current metrics, team insights), searches the web (market trends, competitor moves), creates a draft strategy doc, and presents it for review—all backed by sources, all editable live.

---

## Project Classification

**Technical Type:** Full-Stack SaaS Application (Enterprise Internal Tool)
- **Frontend:** Next.js 14 + TypeScript (Suna-based, Manus theme)
- **Backend:** Node.js (Suna) + Python (Onyx Core)
- **Infrastructure:** Docker Compose, Hostinger KVM 4 VPS, Nginx reverse proxy
- **Key Services:** LiteLLM proxy, Qdrant vector DB, Supabase PostgreSQL, Redis cache, Playwright browser, noVNC workspace

**Domain:** Enterprise AI Operations / Strategic Intelligence
- **Sensitivity:** Medium-High (internal company data, RAG over sensitive docs)
- **Regulatory:** Minimal (internal use, no customer PII)
- **Special Requirements:** Data access control, OAuth credential management, real-time performance

**Complexity:** High
- Multi-service orchestration (6+ Docker containers)
- Advanced LLM routing (DeepSeek primary, Ollama fallback)
- Complex data integration (Google Drive, Slack, local files with permission awareness)
- Real-time browser control (noVNC) with <500ms latency requirement
- Persistent memory with cross-session context injection

**Project Type Requirements:**
- **SaaS Architecture:** Multi-feature backend, persistent data, user sessions
- **Real-Time Performance:** <1.5s response for chat, <500ms for workspace
- **Complex Integrations:** 4+ external APIs (Google, SerpAPI, Together AI, etc.)
- **Agentic Orchestration:** Tool selection, approval gates, multi-step planning
- **Security:** OAuth2, encrypted credentials, RBAC, IP whitelist, no external telemetry

---

## Success Criteria

### Quantitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|------------------|
| **Founder Time Saved** | >7 hrs/week | Toggl time logs, founder estimation |
| **Response Latency** | <1.5s avg (95th %ile) | Suna analytics, CloudWatch logs |
| **Task Completion Rate** | >93% in Agent Mode | Agent execution logs |
| **Daily Active Users** | 100% of core team | Suna analytics |
| **System Uptime** | 99.5% | Prometheus monitoring |
| **VNC Latency** | <500ms live workspace | WebRTC performance metrics |
| **Chat Context Retrieval Accuracy** | >95% on 50 internal queries | RAG evaluation, human assessment |

### Qualitative Metrics

- **NPS (Net Promoter Score):** >9/10 (quarterly survey)
- **Adoption:** Used daily by 100% of core team within 2 weeks of launch
- **Strategic Impact:** 1+ strategic insights/week generated proactively
- **User Satisfaction:** "Manus is indispensable to how I work" (founder quote)

### Business Objectives

1. **Reduce Founder Bottleneck** – Enable delegation of strategic research
2. **Accelerate Decision Velocity** – Strategic decisions in minutes, not hours
3. **Improve Decision Quality** – All decisions backed by full internal context
4. **Build Moat** – Persistent memory creates compounding advantage
5. **Support Team Growth** – Scale decision support without proportional time investment

---

## Product Scope

### MVP (Phases 1-2, Weeks 1-3)

**Phase 1: Foundation (Week 1)**
- ✅ Suna UI with Manus dark theme (Inter font, blue accents, minimalist design)
- ✅ Single-page chat interface (unlimited conversations, no quotas)
- ✅ LiteLLM proxy routing to DeepSeek (Together AI), Ollama fallback
- ✅ System prompt baked in: strategic advisor tone, cite sources, think step-by-step
- ✅ Google Drive + Slack + local file connectors (auto-sync every 10 min)
- ✅ Hybrid RAG (semantic + keyword search) via Onyx Core + Qdrant
- ✅ Inline citations (file name, link, timestamp)
- ✅ Dashboard showing data freshness, sync status

**Phase 2: Core Features (Weeks 2-3)**
- ✅ Supabase + Redis memory layer
- ✅ Persistent cross-session memory (top-5 facts injected per chat)
- ✅ Standing instructions (e.g., "Prioritize defense contracts")
- ✅ Agent Mode toggle (Chat vs execution)
- ✅ Approval gates for sensitive actions
- ✅ Google Workspace tools (create_doc, edit_sheet, summarize_drive_link)
- ✅ Playwright web automation (search_web, scrape_url, fill_form)
- ✅ Task history with status, logs, outputs

**MVP Success Criteria:**
- >95% RAG relevance on 50 internal test queries
- 98% memory recall across 5+ sessions
- >93% agent task completion
- <1.5s avg response, <500ms VNC latency
- All Phase 1-2 features working end-to-end

### Growth Features (Phase 3, Weeks 4-5)

- **Live Workspace (noVNC):** Real-time VPS desktop overlay, founder mouse/keyboard takeover
- **Multimedia Generation:** Stable Diffusion (images), Reveal.js (slides), RunwayML (video)
- **Code Interpreter:** Python sandbox, pandas/matplotlib/plotly analysis, output graphs
- **Advanced Analytics:** Custom dashboards, prediction models
- **Slack Integration:** @manus bot in team chat, context awareness

### Vision Features (Post-Launch)

- **Autonomous Workflows:** Multi-day strategic tasks (market analysis → report → presentation)
- **Predictive Insights:** Identify trends, flag risks before they materialize
- **Team Workspace:** Multi-user collaboration on Manus tasks
- **Custom Fine-Tuning:** Train on M3rcury-specific patterns for better accuracy
- **Notion / GitHub / Email Sync:** Expand data sources beyond Drive/Slack

---

## Functional Requirements

### F1: Chat Interface & Conversation Management

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F1.1 | Single-page chat UI | No page navigation; minimal chrome; focus on conversation |
| F1.2 | Message history | Load last 100 messages per session; infinite scroll |
| F1.3 | Conversation persistence | Save all chats to Supabase; allow search by topic/date |
| F1.4 | Multi-turn context | Maintain conversation context across 50+ exchanges |
| F1.5 | System prompt application | All responses follow strategic advisor tone; cite sources |
| F1.6 | Response streaming | Show LLM response character-by-character as it arrives |
| F1.7 | Copy/share responses | Copy button for each response; shareable links (optional) |
| F1.8 | Keyboard shortcuts | Cmd+K for search, Cmd+N for new chat, Cmd+Enter to send |

### F2: RAG & Knowledge Retrieval

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F2.1 | Google Drive sync | Auto-sync every 10 min; track file version; permission-aware |
| F2.2 | Slack sync | Every 10 min; parse threads, files, reactions; respect channel access |
| F2.3 | Local file uploads | `/uploads` folder; support Markdown, PDF, CSV, JSON, images |
| F2.4 | Hybrid search | Semantic search (vector) + keyword search (BM25); combine scores |
| F2.5 | Relevance ranking | Top-5 results per query; re-rank by recency + match quality |
| F2.6 | Inline citations | For each fact, cite source (file name, link, timestamp) |
| F2.7 | Source links | Clickable links to original Google Drive doc/Slack message |
| F2.8 | RAG accuracy | >95% relevance on 50 test queries (manual evaluation) |
| F2.9 | Search latency | Retrieval + ranking in <200ms |

### F3: Persistent Memory & Learning

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F3.1 | User memory | Store facts learned about user (role, priorities, past decisions) |
| F3.2 | Cross-session recall | Inject top-5 memories at start of each chat |
| F3.3 | Standing instructions | User can set permanent instructions (e.g., "Prioritize X") |
| F3.4 | Auto-summarization | Summarize every 10 messages; store in Supabase |
| F3.5 | Memory accuracy | 98% recall of 10 stored facts across 5+ sessions |
| F3.6 | Memory UI | Show current memories, allow edit/delete, set expiration |
| F3.7 | Memory search | Search across all memories by keyword |

### F4: Agent Mode & Task Execution

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F4.1 | Agent Mode toggle | UI switch: Chat vs Agent Mode |
| F4.2 | Tool selection | Agent autonomously selects appropriate tools (search, file ops, code, etc.) |
| F4.3 | Approval gates | For sensitive actions (create/delete files, execute code), ask approval |
| F4.4 | Multi-step planning | Agent breaks complex tasks into steps: Plan → Execute → Report |
| F4.5 | Task history | Show all executed tasks with status (pending/running/success/fail) |
| F4.6 | Task logs | Detailed logs for each step (LLM reasoning, tool output, errors) |
| F4.7 | Task rollback | Undo last action (delete created file, revert sheet edit) |
| F4.8 | Concurrent tasks | Support max 3 concurrent agent tasks (prevent VPS overload) |

### F5: Google Workspace Tools

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F5.1 | Create Google Doc | Tool: `create_doc(title, content)` → returns shareable link |
| F5.2 | Edit Google Doc | Tool: `edit_doc(doc_id, action: insert/replace/append)` |
| F5.3 | Create Google Sheet | Tool: `create_sheet(title, headers, data)` → returns link |
| F5.4 | Edit Google Sheet | Tool: `edit_sheet(sheet_id, range, data)` |
| F5.5 | Summarize Drive link | Tool: `summarize_drive_link(url)` → extract key points |
| F5.6 | List Drive files | Tool: `list_drive_files(folder, filter)` → show matching files |
| F5.7 | File permissions | Respect user's Drive access; don't create in inaccessible folders |
| F5.8 | OAuth flow | Secure Google OAuth2; store credentials encrypted; refresh tokens |

### F6: Web Automation & Search

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F6.1 | Web search | Tool: `search_web(query)` → top-5 results from SerpAPI or Exa |
| F6.2 | URL scraping | Tool: `scrape_url(url)` → extract text content, clean HTML |
| F6.3 | Form filling | Tool: `fill_form(url, fields)` → fill form fields, handle captchas (manual) |
| F6.4 | Screenshot | Tool: `screenshot(url)` → capture full page screenshot as image |
| F6.5 | Multi-step flows | Agent can chain multiple web actions (search → scrape → extract) |
| F6.6 | Headless browser | Use Playwright in headless + headed mode for debugging |
| F6.7 | Search latency | Web operations complete in <5s per action |

### F7: Live Workspace (noVNC)

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F7.1 | VNC embed | Embed noVNC viewer in Suna UI (right sidebar or overlay) |
| F7.2 | Real-time control | Mouse/keyboard input → VPS desktop (streaming) |
| F7.3 | Desktop access | View and control VPS desktop or dedicated Manus PC |
| F7.4 | Latency | <500ms round-trip latency for input/output |
| F7.5 | Resolution | Support 1920x1080 at 30fps |
| F7.6 | Intervention | Founder can pause agent, take over, resume |
| F7.7 | Audit trail | Log all workspace actions (who did what, when) |

### F8: Memory Configuration & Standing Instructions

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F8.1 | Edit standing instructions | UI to set/edit permanent directives (e.g., "Always cite sources") |
| F8.2 | Instruction persistence | Standing instructions applied to all future chats |
| F8.3 | Memory limits | Store up to 1,000 user facts; auto-prune oldest if exceeded |
| F8.4 | Memory export | Download all memories as JSON |
| F8.5 | Memory import | Upload memories from previous instance |

---

## Non-Functional Requirements

### Performance Requirements

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| P1.1 | Chat response latency | <1.5s avg response time (95th percentile) |
| P1.2 | Streaming latency | Start streaming response within 500ms |
| P1.3 | RAG retrieval | <200ms to return top-5 relevant documents |
| P1.4 | UI responsiveness | <100ms for all UI interactions |
| P1.5 | VNC latency | <500ms round-trip for workspace control |
| P1.6 | Tool execution | Most tools complete in <5s (web search <3s, file ops <2s) |
| P1.7 | Memory injection | Inject top-5 memories in <50ms |
| P1.8 | Page load | SPA load in <2s on 4G connection |

### Security Requirements

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| S1.1 | OAuth2 authentication | Secure Google/Slack OAuth flow; no password storage |
| S1.2 | Credential encryption | All API keys, tokens encrypted at rest (AES-256) |
| S1.3 | RBAC | Users can only access data they have permission to (Drive, Slack) |
| S1.4 | Session management | Secure session cookies; auto-logout after 30 min inactivity |
| S1.5 | API rate limiting | 100 requests/min per user; 1000 req/min per IP |
| S1.6 | Input validation | Sanitize all user inputs; prevent SQL injection, XSS |
| S1.7 | Data isolation | No data leakage between users (single-user for MVP) |
| S1.8 | IP whitelist | Optional: restrict access to M3rcury office IPs |
| S1.9 | Audit logging | Log all sensitive actions (file creation, code execution) |
| S1.10 | No external telemetry | Disable all analytics, telemetry, external calls except APIs |
| S1.11 | Credential scope | LLM sees only necessary context (not credentials) |

### Scalability Requirements

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| Sc1.1 | Concurrent users | Handle 50 concurrent users on KVM 4 (4 vCPU, 16GB RAM) |
| Sc1.2 | Memory efficiency | Peak RAM usage <12GB under full load |
| Sc1.3 | Concurrent agent tasks | Support max 3 parallel agent executions; queue others |
| Sc1.4 | Data volume | Support 10TB in Qdrant vector DB |
| Sc1.5 | Chat history | Efficiently load/search 100k+ messages |
| Sc1.6 | Connection pooling | Reuse DB connections; max 20 connections to Supabase |

### Reliability & Uptime

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| R1.1 | System uptime | 99.5% uptime (target <3.6 hrs downtime/month) |
| R1.2 | Auto-recovery | Service crashes automatically restart (Docker healthchecks) |
| R1.3 | Data backups | Daily backups of Supabase + Qdrant volumes |
| R1.4 | Backup restoration | Restore from backup in <1 hour |
| R1.5 | Error handling | Graceful degradation; inform user of partial failures |
| R1.6 | Retry logic | Automatic retry for transient failures (API calls, DB) |
| R1.7 | Circuit breakers | Fallback to Ollama if DeepSeek unavailable |
| R1.8 | Monitoring | Real-time alerts for errors, latency spikes, failed tasks |

### Accessibility & UX

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| A1.1 | Responsive design | Works on desktop, tablet, mobile (>80% features) |
| A1.2 | Dark mode | Manus dark theme (no light mode toggle initially) |
| A1.3 | Keyboard navigation | Tab through all interactive elements; Escape to close |
| A1.4 | Contrast | WCAG AA contrast ratios (4.5:1 for text) |
| A1.5 | Help text | Tooltips for all tools, standing instructions UI |
| A1.6 | Error messages | Clear, actionable error messages (not generic "Error") |
| A1.7 | Loading indicators | Show progress during long operations (RAG search, web scrape) |

### Integration Requirements

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| I1.1 | Google Drive API | Full read/write access; support sharing + permissions |
| I1.2 | Slack API | Read messages, channels, files; post updates |
| I1.3 | LiteLLM API | Route to DeepSeek (Together AI), Ollama fallback |
| I1.4 | Together AI | Stable connection; handle rate limits gracefully |
| I1.5 | Google OAuth | Smooth auth flow; handle token refresh |
| I1.6 | Qdrant API | Vector DB operations via SDK; handle connection resets |
| I1.7 | Supabase API | PostgreSQL read/write; handle constraints |
| I1.8 | Redis API | Session cache + rate limiting; handle evictions |

---

## Architecture & Technical Decisions

### Technology Stack (Rationale)

**Frontend: Next.js 14 + Suna**
- Why: Suna provides pre-built agent UI; Next.js enables fast SSR + streaming
- Trade-off: Coupled to Suna's architecture (acceptable for MVP)

**Backend: Node.js (Suna) + Python (Onyx Core)**
- Why: Suna runs Node.js; Onyx Core is Python-native for RAG/ML
- Trade-off: Multi-language complexity (mitigated by Docker isolation)

**LLM Orchestration: LiteLLM Proxy**
- Why: Single interface for multiple model providers; easy fallback switching
- Trade-off: One more service to manage (outweighed by flexibility)

**Primary LLM: DeepSeek (via Together AI)**
- Why: Best cost/performance for 128k context; good reasoning; available via API
- Trade-off: Less established than OpenAI (mitigated by Ollama fallback)

**Vector DB: Qdrant**
- Why: Open-source, fast, supports semantic search + keyword hybrid search
- Trade-off: More ops overhead than managed service (acceptable for self-hosted)

**Memory: Supabase + Redis**
- Why: Supabase = managed PostgreSQL (easy); Redis = fast session cache
- Trade-off: Two DBs instead of one (justified by use-case fit)

**Browser Automation: Playwright + headless Chrome**
- Why: Mature, fast, supports multi-browser; good DevTools integration
- Trade-off: Requires Docker + resources (acceptable on KVM 4)

**Workspace: noVNC**
- Why: Open-source, VNC-based, embeds in browser; real-time control
- Trade-off: VNC latency (mitigated by deployment on same VPS)

### Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│  Hostinger KVM 4 VPS (4 vCPU, 16GB RAM, 200GB SSD) │
├──────────┬──────────┬──────────┬──────────┬─────────┤
│  Suna    │  Onyx   │ Qdrant   │ Supabase │ Redis   │
│  (Next)  │  Core   │ (Vector) │ (DB)     │ (Cache) │
│  :3000   │  :8080  │  :6333   │ :5432   │ :6379   │
└──────────┴──────────┴──────────┴──────────┴─────────┘
         ↓
    Nginx Reverse Proxy (:80, :443)
         ↓
    LiteLLM Proxy → DeepSeek (Together AI) or Ollama (:11434)
    Playwright Browser (headless, :3002)
    noVNC Server (VNC-over-websocket, :6080)
```

### Data Flow (Typical Query)

1. **User asks question** → Suna UI
2. **Suna routes** to LiteLLM proxy with RAG context
3. **LiteLLM calls** DeepSeek (or Ollama fallback)
4. **Onyx Core RAG** searches Qdrant + connectors in parallel
5. **Top-5 results** injected into LLM context
6. **Memory layer** injects top-5 facts from Supabase
7. **LLM responds** with citations + reasoning
8. **Response streamed** to UI + saved to chat history
9. **Memory auto-summary** updates Supabase

### Agent Task Execution Flow

1. User toggles Agent Mode, asks complex task
2. Agent breaks into sub-tasks (Plan step)
3. For each sub-task:
   - Selects appropriate tool (search, file, code, web)
   - Checks approval gates (sensitive actions)
   - Executes tool, logs output
   - Evaluates result, decides next step
4. Compiles final report with sources
5. Saves task history to Supabase

---

## Implementation Timeline

| Phase | Duration | Goal | Deliverable |
|-------|----------|------|-------------|
| **1: Foundation** | Week 1 | Deploy Suna + Onyx Core RAG | Suna UI with chat, Drive/Slack sync, DeepSeek routing |
| **2: Core Features** | Weeks 2-3 | Add memory, Agent Mode, Google tools | Persistent memory, approval gates, workspace tools |
| **3: Advanced** | Weeks 4-5 | Deploy noVNC, multimedia, code interpreter | Live workspace, image/video gen, Python sandbox |
| **4: Launch** | Dec 15, 2025 | Beta → production | Full team rollout, monitoring setup |

**Critical Path:**
- Week 0 (before start): VPS upgrade to KVM 4 (Hostinger)
- Week 1-2: Docker setup + Suna + Onyx Core (blocker: Google OAuth config)
- Week 2-3: Memory layer + Agent Mode (blocker: approval gate UI)
- Week 3-4: noVNC workspace (blocker: latency optimization)
- Week 4-5: Polish + monitoring + launch prep

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|----------|
| VPS overload under load | High | Resource caps on containers; auto-scale to larger VPS if needed |
| DeepSeek API outage | Medium | Ollama 7B fallback (slower but functional) |
| RAG accuracy issues | Medium | Start with Drive/Slack only; add more sources post-launch |
| Google OAuth complexity | Medium | Use google-auth library; test OAuth flow extensively pre-launch |
| noVNC latency >500ms | Medium | Optimize VNC compression; if needed, use higher-tier VPS |
| Data sync (Drive/Slack) race conditions | Low | Use job queue (Bull) to serialize sync tasks |
| Qdrant vector DB corruption | Low | Daily backups; test restore procedure monthly |
| Security: credential exposure | High | Encrypt all creds; audit all LLM context; no credentials in logs |
| Low team adoption | Medium | Weekly demos of time-saving features; integrate with daily workflows |

---

## Budget & Resources

| Item | Cost | Duration |
|------|------|----------|
| **VPS (KVM 4)** | $25/month | Ongoing |
| **Together AI (DeepSeek)** | $80–150/month | Ongoing (~100 queries/day) |
| **APIs (Google, SerpAPI, Stable Diffusion)** | <$50/month | Ongoing |
| **Supabase (managed DB)** | $25–100/month | Ongoing (optional if heavy use) |
| **Monitoring & logging** | <$20/month | Ongoing |
| **Dev Time** | 4 weeks (1 FTE) | Nov 2025 |
| **First Year Total** | ~$1,800 | Annualized (~$150/month) |

**ROI:** 7 hrs/week saved × 52 weeks × $500/hr (founder rate) = **$182,000/year**.

---

## Epic Breakdown (High Level)

*Detailed epic/story decomposition in next workflow (create-epics-and-stories)*

### Epic 1: Chat Foundation (Phase 1)
- E1.1: Suna UI deployment with Manus theme
- E1.2: LiteLLM proxy setup + DeepSeek routing
- E1.3: Message history & persistence
- E1.4: System prompt + response streaming

### Epic 2: RAG Integration (Phase 1)
- E2.1: Google Drive connector + auto-sync
- E2.2: Slack connector + message indexing
- E2.3: Local file uploads & parsing
- E2.4: Qdrant vector DB + hybrid search
- E2.5: Citation generation

### Epic 3: Memory Layer (Phase 2)
- E3.1: Supabase user memory schema
- E3.2: Memory injection at chat start
- E3.3: Standing instructions UI
- E3.4: Auto-summarization pipeline

### Epic 4: Agent Mode (Phase 2)
- E4.1: Agent Mode toggle + UI
- E4.2: Tool selection logic
- E4.3: Approval gates framework
- E4.4: Task history tracking

### Epic 5: Google Workspace Tools (Phase 2)
- E5.1: Google API integration + OAuth
- E5.2: Doc create/edit tools
- E5.3: Sheet create/edit tools
- E5.4: Drive querying tools

### Epic 6: Web Automation (Phase 2)
- E6.1: Playwright setup + headless browser
- E6.2: Web search tool (SerpAPI/Exa)
- E6.3: URL scraping tool
- E6.4: Form filling tool

### Epic 7: Live Workspace (Phase 3)
- E7.1: noVNC server setup
- E7.2: VNC embed + WebSocket streaming
- E7.3: Mouse/keyboard input handling
- E7.4: Intervention workflow

### Epic 8: Monitoring & DevOps (Ongoing)
- E8.1: Prometheus + Grafana setup
- E8.2: Error tracking (Sentry)
- E8.3: Daily backup automation
- E8.4: Incident response playbooks

---

## References

- **Product Brief:** docs/product-brief-ONYX-2025-11-10.md
- **Approved PRD:** (this document)
- **Tech Stack:** Docker Compose, Next.js 14, DeepSeek, Qdrant, Supabase

---

## Next Steps

1. **Create Epics & Stories** – Run: `workflow create-epics-and-stories`
   - Decompose requirements into 50-60 stories
   - Estimate story points
   - Plan 4-week sprint roadmap

2. **Create Architecture** – Run: `workflow create-architecture`
   - Detail data models (Supabase schema)
   - API design (Suna ↔ backend)
   - Tool architecture (LiteLLM, Qdrant, Playwright)

3. **UX Design** (Optional) – Run: `workflow create-design`
   - Detailed Figma designs for Manus theme
   - Component library
   - Interaction flows

4. **Begin Dev Sprints** – Run: `workflow sprint-planning`
   - Week 1-2: Foundation (Suna + RAG)
   - Week 2-3: Core features (Memory + Agent Mode)
   - Week 3-5: Advanced + launch

---

_This PRD captures the complete vision for **Manus Internal** – M3rcury's strategic intelligence partner._

_Approved by Darius Tabatabai. Ready for architecture design and implementation._

_Created through collaborative discovery; informed by approved product strategy and technical feasibility assessment._
