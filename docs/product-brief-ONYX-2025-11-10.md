# Product Brief: ONYX – Manus Internal

**Date:** 2025-11-10
**Author:** darius
**Context:** Enterprise internal tool – Strategic AI advisor

---

## Executive Summary

**Manus Internal** is M3rcury's private, self-hosted strategic intelligence system. It combines Suna-powered chat, full RAG over internal data (Google Drive, Slack, local files), persistent memory, and advanced agentic tools to serve as the company's second brain and strategic advisor.

Instead of fragmented data and manual synthesis, Manus knows everything about M3rcury, remembers everything across conversations, and can execute complex tasks (create docs, analyze data, browse web, generate assets) autonomously with founder oversight via live workspace.

**Goal:** Reduce founder cognitive load by >7 hours/week, generate weekly strategic insights, and build a compounding intelligence asset worth $1M+ over 2 years.

---

## Core Vision

### Problem Statement

M3rcury's internal knowledge is fragmented across Google Drive, Slack, and local systems with no unified intelligence layer. Current tools (Onyx 1.0) provide search but lack execution, reasoning, and memory. This forces the founder to spend 10+ hours/week manually synthesizing insights, and external AI tools (ChatGPT, Grok) present security and context limitations.

### Problem Impact

- **10+ founder hours/week** spent on manual data synthesis and decision-making
- **Fragmented knowledge** reduces decision quality and increases errors
- **Security/compliance risk** from using external AI tools with sensitive data
- **Opportunity cost** of not leveraging the company's full internal knowledge base
- **Lack of persistence** means insights are forgotten between conversations

### Why Existing Solutions Fall Short

- **ChatGPT/Claude:** No internal data access, not self-hosted, monthly SaaS costs, general-purpose (not strategic)
- **Onyx 1.0:** Search-only, no reasoning, no memory across sessions, no execution
- **Manus (commercial):** Closed-source, expensive, vendor lock-in, not customizable
- **Standard agents:** No persistent memory, no workspace oversight, limited tool integration

### Proposed Solution

A private, self-hosted strategic agent that:

1. **Knows everything** – Full RAG over Google Drive, Slack, and local uploads with hybrid search (semantic + keyword)
2. **Remembers everything** – Persistent cross-session memory via Supabase, auto-summarization, standing instructions
3. **Does everything** – File I/O (Docs, Sheets, Forms), web automation (Playwright), image/video generation, code execution, live workspace control
4. **Thinks deeply** – 128k context window (DeepSeek), chain-of-thought reasoning, multi-step planning
5. **Acts in real-time** – Live noVNC workspace with founder intervention, approval gates for sensitive actions

### Key Differentiators

- **Self-hosted** on existing VPS ($25/month) – no SaaS lock-in, full data control
- **Unlimited usage** – no token quotas or rate limits
- **Manus-branded UI** – purpose-built for strategic advising, not generic chat
- **Persistent memory** – learns from every interaction, recalls context across chats
- **Live workspace** – founder can see and intervene in agent actions in real-time
- **Modular tool architecture** – easy to add new capabilities (Slack bot, Notion sync, etc.)
- **Open-source foundation** (Suna + Onyx) – customizable, no black boxes

---

## Target Users

### Primary Users

**Darius Tabatabai (Founder)**
- Makes strategic decisions involving M3rcury's direction, partnerships, hiring
- Needs fast, accurate synthesis of market trends, competitive data, internal insights
- Currently spends 10+ hours/week on manual research and synthesis
- Would use Manus daily for: strategic planning, quick research, document generation, market analysis
- Workflow: Ask Manus a question → see sources → review live actions → get actionable insights

### Secondary Users

**M3rcury Core Team** (3-5 engineers + strategists)
- Execute on strategic plans, build products, manage operations
- Use Manus for: quick answers, code insights, data analysis, document generation
- Workflow: @Manus in team chat → Manus responds with sources → optional live workspace for complex tasks

### User Journey

```
1. Founder asks Manus: "What's the competitive landscape for AI agents?"
   → Manus searches RAG + web, recalls relevant M3rcury context
   → Cites sources (Drive docs, past Slack discussions, articles)
   → Presents analysis with key differentiators

2. Founder asks: "Draft a strategy doc for defense contracts"
   → Manus recalls standing instructions: "Prioritize defense contracts"
   → Creates Google Doc, auto-syncs with team folder
   → Founder reviews live (VNC), asks for edits
   → Manus updates doc, presents final version

3. Founder asks: "Show me product-market fit signals from user interviews"
   → Manus runs Python analysis on drive data
   → Generates charts, CSV with insights
   → Presents findings with confidence levels

4. Founder at 11pm: "I need a slide deck for tomorrow's pitch"
   → Manus generates from standing context + recent updates
   → Includes charts, market data, strategic talking points
   → Founder approves, Manus deploys to Vercel
```

---

## Success Metrics

### Key Metrics

- **Founder Time Saved:** >7 hours/week (measured via Toggl time logs)
- **Task Completion Rate:** >93% (agent logs, error tracking)
- **Daily Active Users:** 100% of core team (Suna analytics)
- **Strategic Insights:** 1+ per week (proactive reports)
- **Net Promoter Score (NPS):** >9/10 (quarterly survey)
- **System Uptime:** 99.5% (Prometheus monitoring)
- **Response Latency:** <1.5s avg (95th percentile)
- **VNC Latency:** <500ms (live workspace overlay)

### Business Objectives

- **Compound intelligence asset** – Persistent memory grows weekly, creating moat
- **Reduce founder bottleneck** – Enable delegation of strategic research
- **Accelerate decision velocity** – Sub-2-minute turnaround on strategic queries
- **Improve decision quality** – All decisions backed by full internal context
- **Support growth** – Easily add new data sources (Notion, GitHub, email) as company scales

---

## MVP Scope

### Core Features (Phases 1-2)

**Phase 1 (Week 1):**
- Suna UI with Manus dark theme (Inter font, blue accents, minimalist)
- Single-page chat interface (unlimited conversations, no quotas)
- LiteLLM proxy → DeepSeek via Together AI
- Google Drive, Slack, local file connectors (auto-sync every 10 min)
- Hybrid RAG (semantic + keyword search) powered by Onyx Core + Qdrant
- Inline citations (file name, link, timestamp)
- System prompt: _"You are Manus, M3rcury's strategic advisor. Be concise, proactive, cite sources, think step-by-step."_

**Phase 2 (Weeks 2-3):**
- Supabase + Redis for persistent memory
- Cross-chat recall (top-5 memories injected per session)
- Standing instructions (e.g., "Prioritize defense contracts")
- Agent Mode toggle (Chat vs execution)
- Approval gates for sensitive actions
- Google Workspace tools (create_doc, edit_sheet, summarize_drive_link)
- Playwright web automation (search_web, scrape_url, fill_form)
- Task history with status, logs, outputs

### Out of Scope for MVP

- Slack bot integration (Phase 3)
- Notion/GitHub sync (Phase 3)
- Voice input (future)
- Mobile app (use responsive web)
- Advanced fine-tuning (use base DeepSeek model)

### MVP Success Criteria

- >95% relevance on 50 internal queries (RAG accuracy)
- 98% recall of 10 stored facts across sessions (memory)
- >93% task completion in Agent Mode
- <1.5s avg response time, <500ms VNC latency
- All Phase 1-2 features working end-to-end

### Future Vision

- **Phase 3:** Live workspace (noVNC), image/video gen, code interpreter, team workspace
- **Phase 4:** Slack bot (@manus commands), Notion sync, email parsing, GitHub issues
- **Year 2:** Autonomous strategic workflows, predictive insights, custom fine-tuning on M3rcury data

---

## Technical Architecture

### Core Stack

- **Frontend:** Suna (Next.js 14, Tailwind, Manus theme)
- **Backend:** Node.js (Suna), Python (Onyx Core), LiteLLM
- **LLM:** DeepSeek (Together AI), Ollama 7B fallback
- **RAG:** Onyx Core (stripped), Qdrant (vector DB), Redis (session cache)
- **Memory:** Supabase (PostgreSQL), Redis
- **Tools:** Playwright, Google APIs, FFmpeg, Stable Diffusion
- **Infra:** Docker Compose, Hostinger KVM 4 VPS (4 vCPU, 16 GB RAM, 200 GB SSD), Nginx reverse proxy

### Data Flow

1. User → Suna UI (Next.js)
2. Suna → LiteLLM proxy (route to DeepSeek or Ollama)
3. LiteLLM ↔ RAG Engine (search internal data via Onyx Core + Qdrant)
4. RAG Engine ↔ Connectors (Google Drive, Slack, local files)
5. LLM response ↔ Memory Layer (Supabase + Redis)
6. Agent Mode ↔ Tools (Playwright, Google APIs, FFmpeg, noVNC)
7. Response → User with citations

---

## Implementation Timeline

| Phase | Duration | Goal |
|-------|----------|------|
| **Phase 1: Foundation** | Week 1 (Nov 2025) | Deploy Suna + Onyx Core, enable RAG, apply Manus theme |
| **Phase 2: Core Features** | Weeks 2-3 | Add memory layer, Agent Mode, Google tools, web automation |
| **Phase 3: Advanced** | Weeks 4-5 | Deploy noVNC workspace, add multimedia gen, code interpreter |
| **Phase 4: Launch** | Dec 15, 2025 | Beta with founders, iterate, full team rollout |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|----------|
| VPS overload (RAM/CPU) | Docker resource caps, monitoring, auto-kill idle agents, scale to larger VPS if needed |
| LLM cost spike | $100/month alert, auto-fallback to Ollama 7B |
| Data sync bugs | 2-week PoC per connector, modular tool testing |
| Security breach | Pen test before launch, encrypted volume, 2FA, IP whitelist |
| Low team adoption | Manus-themed demos, weekly wins, integrate with daily workflows |
| Context window limits | 128k context (DeepSeek), summarization strategy, sliding window |

---

## Budget & Resources

| Item | Cost | Notes |
|------|------|-------|
| **VPS (KVM 4)** | $25/month | Already approved, deployed by Nov 26 |
| **Together AI (DeepSeek)** | $80–150/month | Moderate use (~100 queries/day) |
| **APIs (Google, SerpAPI, etc.)** | <$50/month | Search, auth, file operations |
| **Dev Time** | 4 weeks (1 FTE) | One engineer, full-time for MVP |
| **Supabase (optional, if heavy use)** | $25–100/month | Free tier sufficient initially |
| **Domain/monitoring** | <$20/month | Datadog, SSL cert |
| **Total First Year** | ~$1,800 | Annualized ($150/month base + dev) |

**ROI:** 7 hrs/week saved × 52 weeks × $500/hr (founder rate) = **$182,000/year in founder time**.

---

## Appendix

### Manus System Prompt (Default)

```
You are Manus, M3rcury Ventures' strategic intelligence partner.

Core directives:
- Use internal data first. Always cite sources (file name, link, timestamp).
- Be concise, proactive, and action-oriented.
- For complex tasks: Plan → Execute → Report.
- Never hallucinate. If uncertain, search RAG or web first.
- Think step-by-step. Show reasoning in Agent Mode.
- Default to strategic impact. Ask clarifying questions if ambiguous.
- Adapt tone to context (founder = strategic, team = operational).
- Prioritize defense contracts in strategic discussions.

Memory & learning:
- Recall relevant facts from conversation history.
- Learn from founder feedback. Update standing instructions.
- Proactively flag patterns and opportunities.

Response style:
- Founder queries: 2-3 paragraph strategic insights + 3-5 action items.
- Team queries: Quick answers with sources, offer deep dive.
- Document creation: Professional, M3rcury-branded, citation-rich.
```

---

_This Product Brief captures the vision and strategic fit for **Manus Internal**._

_It was co-created between darius and discovery process, informed by the approved PRD and reflects M3rcury's unique needs for a self-hosted, unlimited-use strategic AI advisor._

_Next: **PRD Workflow** will transform this brief into detailed epic/story breakdowns for implementation starting Nov 2025._
