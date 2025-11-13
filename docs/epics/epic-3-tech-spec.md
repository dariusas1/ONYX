# Epic Technical Specification: Knowledge Retrieval (RAG)

Date: 2025-11-13
Author: System Architect
Epic ID: epic-3
Status: Draft

---

## Overview

Epic 3 establishes the Retrieval-Augmented Generation (RAG) system for Manus Internal, enabling unified access to all company knowledge with high relevance for grounded strategic advice. This epic implements the vector database infrastructure, multi-source data connectors (Google Drive, Slack, local files), hybrid search capabilities, and citation generation to ensure all LLM responses are backed by verifiable sources.

The RAG system serves as the knowledge foundation for Manus, transforming fragmented company data (Drive docs, Slack discussions, uploaded files) into a unified, searchable knowledge base that powers strategic decision-making with >95% relevance accuracy.

## Objectives and Scope

### In-Scope:
- Qdrant vector database setup and configuration with 1536-dimensional embeddings
- Google Drive connector with OAuth2 authentication and auto-sync (every 10 minutes)
- Slack connector with message/thread indexing and auto-sync (every 10 minutes)
- Local file upload supporting multiple formats (Markdown, PDF, CSV, JSON, images)
- Hybrid search combining semantic vector search (70%) + keyword BM25 search (30%)
- Citation generation with inline source attribution and clickable links
- Support for 10TB+ document corpus with <200ms retrieval latency
- Permission-aware indexing (only index files user can access)

### Out-of-Scope:
- Real-time indexing (batch sync every 10 minutes is sufficient)
- Multi-language document support (English only for MVP)
- Advanced document preprocessing (OCR for images deferred to future)
- Custom embedding model fine-tuning (use OpenAI text-embedding-3-small)
- Email connector (Gmail/Outlook sync - future epic)
- Notion/GitHub/Linear integrations (future epics)
- Advanced reranking models (use simple recency + score boosting)

## System Architecture Alignment

Epic 3 implements the RAG layer defined in the architecture document, sitting between the Suna frontend and the knowledge sources (Google Drive, Slack, local storage). The hybrid search pattern (semantic + keyword) aligns with ADR-006, and the permission-aware indexing ensures data access control requirements are met.

```
┌─────────────────────────────────────────────────────────────┐
│  RAG Architecture Flow                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Query → Suna Frontend → Onyx Core RAG Service        │
│       ↓                                                     │
│  1. Embedding Generation (OpenAI API)                       │
│       ↓                                                     │
│  2. Parallel Search:                                        │
│     - Qdrant Vector Search (semantic, top-10)              │
│     - BM25 Keyword Search (exact match, top-10)            │
│       ↓                                                     │
│  3. Result Fusion & Ranking:                               │
│     - Combine scores (70% semantic + 30% keyword)          │
│     - Boost recent docs (+10%)                             │
│     - Filter by permissions                                │
│       ↓                                                     │
│  4. Top-5 Results → LLM Context + Citations                │
│       ↓                                                     │
│  5. LLM Response with [1], [2] inline citations            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Service Integration Points:
- **Onyx Core**: Python FastAPI service handling RAG operations
- **Qdrant**: Vector database for semantic search
- **PostgreSQL**: Document metadata and sync status
- **Redis**: Search result caching (5-minute TTL)
- **Google Drive API**: Document sync and permission checks
- **Slack API**: Message/thread indexing
- **OpenAI API**: Embedding generation (text-embedding-3-small)

## Detailed Design

### Services and Modules

| Module | Purpose | Technology | Responsibilities |
|--------|---------|------------|------------------|
| **qdrant-service** | Vector database | Qdrant 1.7+ | Semantic search, vector storage, collection management |
| **google-sync** | Drive connector | Google Drive API v3 | File listing, change detection, content extraction, OAuth |
| **slack-sync** | Slack connector | Slack SDK | Channel history, thread parsing, file extraction |
| **file-parser** | Content extraction | PyPDF2, csv-parser, markdown-it | Multi-format parsing (PDF, CSV, MD, JSON) |
| **hybrid-search** | Search orchestration | Python async | Query embedding, parallel search, result fusion |
| **citation-generator** | Source attribution | Template engine | Citation formatting, link generation |

### Data Models and Contracts

#### Qdrant Vector Collection Schema:
```yaml
collection: "documents"
config:
  vectors:
    size: 1536  # text-embedding-3-small
    distance: "Cosine"
    on_disk: true  # Support large corpus
  payload_schema:
    doc_id: "string"  # UUID from PostgreSQL
    title: "string"
    source_type: "string"  # "google_drive", "slack", "upload"
    source_id: "string"  # Google file ID, Slack message ID, etc.
    chunk_index: "integer"  # For chunked documents
    chunk_text: "string"  # 500-char snippet
    created_at: "datetime"
    modified_at: "datetime"
    owner_email: "string"
    permissions: ["string"]  # User emails with access
```

#### PostgreSQL Document Metadata Schema:
```sql
-- Document registry
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT NOT NULL,  -- 'google_drive', 'slack', 'upload'
  source_id TEXT UNIQUE NOT NULL,  -- External ID
  title TEXT NOT NULL,
  content_hash TEXT,  -- SHA-256 for deduplication
  file_type TEXT,  -- 'pdf', 'doc', 'md', etc.
  file_size BIGINT,
  owner_id UUID REFERENCES users(id),
  permissions JSONB,  -- {emails: [], type: 'private'|'shared'}
  indexed_at TIMESTAMP,
  modified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX idx_source (source_type, source_id),
  INDEX idx_owner (owner_id),
  INDEX idx_modified (modified_at DESC)
);

-- Sync status tracking
CREATE TABLE sync_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT NOT NULL,
  status TEXT NOT NULL,  -- 'running', 'success', 'failed'
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  documents_synced INTEGER DEFAULT 0,
  documents_failed INTEGER DEFAULT 0,
  error_message TEXT,
  INDEX idx_status (source_type, status)
);

-- Search cache
CREATE TABLE search_cache (
  query_hash TEXT PRIMARY KEY,  -- MD5 of query
  query_text TEXT NOT NULL,
  results JSONB NOT NULL,  -- Top-5 results
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,  -- TTL: 5 minutes
  INDEX idx_expires (expires_at)
);
```

#### Google Drive Sync State:
```json
{
  "sync_token": "CAESEggCIAoQABiAgICAgICAgAEYAw==",
  "last_sync": "2025-11-13T10:30:00Z",
  "folders": [
    {
      "id": "1XyZ...",
      "name": "M3rcury Shared",
      "last_modified": "2025-11-13T09:00:00Z"
    }
  ],
  "files_indexed": 1247,
  "errors": []
}
```

#### Slack Sync State:
```json
{
  "channels": [
    {
      "id": "C01ABC123",
      "name": "general",
      "last_message_ts": "1699886400.000100",
      "messages_indexed": 5432
    }
  ],
  "last_sync": "2025-11-13T10:30:00Z",
  "total_messages": 12489,
  "errors": []
}
```

### APIs and Interfaces

#### RAG Search API:
```http
POST /api/rag/search
Content-Type: application/json

{
  "query": "What's our competitive positioning vs Anthropic?",
  "top_k": 5,
  "filters": {
    "source_types": ["google_drive", "slack"],  # Optional
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-12-31"
    }
  }
}

Response:
{
  "results": [
    {
      "doc_id": "550e8400-...",
      "title": "Q4 Strategy Doc",
      "source_type": "google_drive",
      "source_id": "1XyZ...",
      "chunk_text": "M3rcury focuses on defense contractors...",
      "relevance_score": 0.94,
      "created_at": "2025-11-10T15:30:00Z",
      "citation": {
        "text": "[1] Q4 Strategy Doc (Google Drive, Nov 10)",
        "link": "https://drive.google.com/file/d/1XyZ..."
      }
    }
  ],
  "query_id": "search-uuid",
  "latency_ms": 187
}
```

#### Document Sync API:
```http
POST /api/sync/google-drive
Content-Type: application/json

{
  "folder_ids": ["1XyZ...", "1AbC..."],  # Optional, defaults to all accessible
  "full_sync": false  # Incremental by default
}

Response:
{
  "job_id": "sync-uuid",
  "status": "running",
  "started_at": "2025-11-13T10:35:00Z"
}

GET /api/sync/status/{job_id}

Response:
{
  "job_id": "sync-uuid",
  "status": "success",
  "documents_synced": 47,
  "documents_failed": 2,
  "completed_at": "2025-11-13T10:37:00Z",
  "errors": [
    {
      "file_id": "1AbC...",
      "error": "Permission denied"
    }
  ]
}
```

#### File Upload API:
```http
POST /api/upload
Content-Type: multipart/form-data

file: [binary data]
metadata: {
  "title": "Custom Market Research",
  "description": "Uploaded by user"
}

Response:
{
  "doc_id": "upload-uuid",
  "status": "processing",
  "message": "File uploaded, indexing in progress"
}
```

#### Citation Generation API:
```http
POST /api/citations/format
Content-Type: application/json

{
  "doc_ids": ["550e8400-...", "660e9500-..."],
  "format": "inline"  # or "footnote", "endnote"
}

Response:
{
  "citations": [
    {
      "index": 1,
      "text": "[1] Q4 Strategy Doc (Google Drive, Nov 10)",
      "link": "https://drive.google.com/file/d/1XyZ...",
      "source_type": "google_drive"
    },
    {
      "index": 2,
      "text": "[2] #general thread (Slack, Nov 12)",
      "link": "https://workspace.slack.com/archives/C01ABC123/p1699886400000100",
      "source_type": "slack"
    }
  ]
}
```

### Workflows and Sequencing

#### Document Indexing Flow:
```
1. Source Detection
   - Google Drive: List files via API (with pageToken for pagination)
   - Slack: List channels, fetch history since last sync
   - Upload: Receive file via multipart upload

2. Change Detection
   - Google Drive: Compare modifiedTime with last_sync
   - Slack: Compare message timestamp with last sync
   - Upload: Always new

3. Permission Check
   - Google Drive: Check file.permissions (only index if user has access)
   - Slack: Check channel membership
   - Upload: Associate with uploader user_id

4. Content Extraction
   - PDF: PyPDF2 text extraction
   - Google Docs: Export as Markdown via Drive API
   - Sheets: Export as CSV
   - Markdown/Text: Direct parsing
   - Slack: Extract message text + thread replies

5. Chunking Strategy
   - Max chunk size: 500 tokens (~2000 chars)
   - Overlap: 50 tokens between chunks
   - Preserve sentence boundaries
   - Store chunk_index for reconstruction

6. Embedding Generation
   - Call OpenAI API: text-embedding-3-small
   - Batch size: 100 documents per request
   - Retry logic: 3 attempts with exponential backoff
   - Cache embeddings by content hash

7. Vector Storage
   - Upsert to Qdrant collection "documents"
   - Include payload: doc_id, title, source info, chunk_text
   - Set permissions in payload for filtering

8. Metadata Storage
   - Insert/update PostgreSQL documents table
   - Record indexed_at timestamp
   - Update sync_jobs status

9. Index Optimization
   - Qdrant: Rebuild index if >10k new documents
   - PostgreSQL: Vacuum and analyze tables weekly
```

#### Hybrid Search Flow:
```
User Query: "M3rcury competitive advantage vs Anthropic"

1. Query Preprocessing
   - Normalize: lowercase, remove stop words (optional)
   - Generate embedding via OpenAI API
   - Extract keywords: ["m3rcury", "competitive", "advantage", "anthropic"]

2. Parallel Search (async)
   Thread A: Qdrant Vector Search
     - Query: embedding vector
     - Collection: "documents"
     - Limit: 10
     - Filter: permissions include current_user.email
     - Distance metric: Cosine similarity
     - Returns: 10 results with scores 0.0-1.0

   Thread B: BM25 Keyword Search
     - Query: keywords
     - Index: PostgreSQL full-text search or Elasticsearch
     - Limit: 10
     - Filter: permissions
     - Returns: 10 results with scores 0.0-1.0

3. Result Fusion
   - Combine results from both threads
   - Deduplicate by doc_id
   - Calculate final score:
     final_score = (0.7 × semantic_score) + (0.3 × keyword_score)

4. Recency Boosting
   - Documents < 7 days old: +10% score
   - Documents < 30 days old: +5% score

5. Re-ranking
   - Sort by final_score DESC
   - Take top-5 results

6. Citation Formatting
   - For each result, generate citation:
     - Format: "[N] {title} ({source}, {date})"
     - Link: Google Drive URL or Slack permalink
   - Include 100-char snippet

7. Cache Results
   - Store in search_cache table
   - Key: MD5(query_text)
   - TTL: 5 minutes
   - Skip cache if filters applied

8. Return Results
   - JSON response with results array
   - Include query_id for debugging
   - Log latency for monitoring
```

#### Auto-Sync Schedule:
```
Every 10 Minutes:
  1. Check if previous sync completed
  2. If running, skip (prevent overlap)
  3. Create new sync_job record
  4. Execute sync:
     - Google Drive: Incremental sync using sync_token
     - Slack: Fetch messages since last_message_ts
  5. Update sync_job status
  6. Log metrics: documents_synced, latency, errors
  7. Alert if error rate > 5%
```

## Non-Functional Requirements

### Performance

#### Search Latency Targets:
- **Embedding generation**: <100ms (OpenAI API call)
- **Qdrant vector search**: <50ms (semantic search)
- **BM25 keyword search**: <30ms (PostgreSQL full-text)
- **Result fusion & ranking**: <20ms (Python computation)
- **Total search latency**: <200ms (95th percentile)

#### Sync Performance:
- **Google Drive sync**: <2 minutes for 1000 files (incremental)
- **Slack sync**: <1 minute for 10,000 messages (incremental)
- **Full sync**: <30 minutes for 50k documents (initial index)

#### Throughput:
- **Search queries**: 100 req/sec sustained
- **Indexing**: 500 documents/minute
- **Concurrent syncs**: 1 (serialized to avoid rate limits)

#### Resource Utilization:
- **Qdrant memory**: <4GB for 100k documents (1536-dim vectors)
- **Onyx Core CPU**: <1 vCPU during search, <2 vCPU during sync
- **PostgreSQL disk**: <10GB for metadata (100k documents)
- **Network**: <100MB/min during full sync

### Security

#### Permission-Aware Indexing:
- **Access Control**: Only index documents user can access
  - Google Drive: Check file.permissions before indexing
  - Slack: Verify channel membership before indexing messages
  - Uploads: Associate with uploader user_id
- **Search Filtering**: Filter search results by current_user.email
  - Qdrant payload: Include permissions array
  - Query filter: `permissions CONTAINS current_user.email`
- **Audit Logging**: Log all access to sensitive documents
  - Who accessed what document when
  - Search queries that returned sensitive results

#### Data Privacy:
- **Encryption at Rest**: Qdrant data encrypted (AES-256 if supported)
- **Credential Management**: Google/Slack tokens encrypted in PostgreSQL
- **Data Retention**: Deleted files removed from index within 24 hours
- **PII Handling**: Mask sensitive data in logs (emails, phone numbers)

#### API Security:
- **Rate Limiting**: 100 search queries/min per user
- **Input Validation**: Sanitize query strings to prevent injection
- **Authentication**: Require valid session for all RAG endpoints
- **HTTPS Only**: Enforce TLS for all external API calls

### Reliability/Availability

#### Fault Tolerance:
- **Sync Failures**: Retry failed files up to 3 times
  - Exponential backoff: 1s, 5s, 30s
  - Log failures for manual review
  - Alert if >10% failure rate
- **Search Degradation**: If Qdrant down, fall back to keyword-only search
  - Return BM25 results with warning
  - Alert ops team
- **Embedding API Failures**: Cache embeddings by content hash
  - Reuse cached embeddings on retry
  - Fall back to keyword search if API unavailable

#### Data Consistency:
- **Deduplication**: Use content_hash to detect duplicate files
  - Update existing record instead of creating new
  - Preserve earliest created_at timestamp
- **Sync Token Management**: Store Google Drive sync_token for incremental sync
  - Atomic updates to prevent token corruption
  - Full sync fallback if token invalid
- **Index Coherence**: Ensure Qdrant and PostgreSQL stay in sync
  - Transaction: Insert PostgreSQL first, then Qdrant
  - Reconciliation job: Detect orphaned records weekly

#### Monitoring:
- **Sync Health**: Track sync success rate, latency, errors
  - Alert if sync fails 3 times consecutively
  - Dashboard: Last sync time, documents indexed
- **Search Performance**: Monitor search latency, cache hit rate
  - Alert if p95 latency > 300ms
  - Dashboard: Query volume, top queries, error rate
- **Index Size**: Track Qdrant collection size, PostgreSQL table size
  - Alert if approaching capacity (80% of allocated)

### Observability

#### Logging Strategy:
```json
{
  "timestamp": "2025-11-13T10:35:42Z",
  "level": "info",
  "service": "onyx-core",
  "action": "hybrid_search",
  "details": {
    "query": "competitive advantage",
    "user_id": "user-uuid",
    "results_count": 5,
    "semantic_score": 0.94,
    "keyword_score": 0.87,
    "latency_ms": 187,
    "cache_hit": false
  }
}
```

#### Metrics Collection:
- **Search Metrics**:
  - `rag_search_latency_ms` (histogram)
  - `rag_search_results_count` (gauge)
  - `rag_cache_hit_rate` (gauge)
- **Sync Metrics**:
  - `sync_duration_seconds` (histogram)
  - `sync_documents_total` (counter)
  - `sync_errors_total` (counter)
- **Index Metrics**:
  - `qdrant_collection_size` (gauge)
  - `qdrant_vector_count` (gauge)
  - `postgres_documents_count` (gauge)

#### Tracing:
- **Search Flow**: Trace from query → embedding → search → fusion → results
  - Span: `generate_embedding` (OpenAI API call)
  - Span: `qdrant_search` (vector search)
  - Span: `bm25_search` (keyword search)
  - Span: `result_fusion` (ranking)
- **Sync Flow**: Trace from trigger → list → extract → index
  - Span: `list_files` (Google Drive API)
  - Span: `extract_content` (parsing)
  - Span: `generate_embeddings` (batch OpenAI API)
  - Span: `upsert_vectors` (Qdrant)

## Dependencies and Integrations

### External Dependencies:
| Service | Version | Purpose | Rate Limits | Cost |
|---------|---------|---------|-------------|------|
| **OpenAI API** | Latest | Embedding generation | 3M tokens/min | $0.02/1M tokens |
| **Google Drive API** | v3 | File listing, content export | 1000 req/100s/user | Free (OAuth) |
| **Slack API** | Latest | Message history, channels | 50+ req/min | Free (OAuth) |
| **Qdrant** | 1.7+ | Vector database | N/A (self-hosted) | Free |
| **PostgreSQL** | 15+ | Metadata storage | N/A (self-hosted) | Free |

### Internal Service Dependencies:
```
Epic 3 (RAG) depends on:
├── Epic 1 (Foundation): Docker Compose, PostgreSQL, Redis
├── Epic 2 (Chat): Suna UI for file uploads
└── Future Epics (consume RAG):
    ├── Epic 4 (Memory): Memory facts embedding
    ├── Epic 5 (Agent): Tool selection RAG context
    └── Epic 6 (Google Tools): Document summarization
```

### Integration Points:
- **Suna Frontend**: File upload widget, search UI
- **LiteLLM Proxy**: Inject RAG context into LLM system prompt
- **Memory Layer**: Embed user memories for similarity search
- **Agent Mode**: Provide context for tool selection decisions

### Version Constraints:
- **Qdrant**: >=1.7.0 (required for hybrid search support)
- **Python**: >=3.10 (async/await syntax)
- **google-api-python-client**: >=2.0.0
- **slack-sdk**: >=3.0.0
- **PyPDF2**: >=3.0.0
- **openai**: >=1.0.0

## Acceptance Criteria (Authoritative)

### Story 3.1: Qdrant Vector Database Setup
- AC3.1.1: Qdrant running on port 6333 with health check returning 200
- AC3.1.2: Collection "documents" created with 1536-dimensional vectors
- AC3.1.3: Can upsert vectors and search with <100ms latency
- AC3.1.4: Data persists across container restarts (volume mounted)
- AC3.1.5: API endpoints respond correctly for create, upsert, search operations

### Story 3.2: Google Drive Connector & Auto-Sync
- AC3.2.1: User authenticates with Google OAuth and grants Drive access
- AC3.2.2: Sync job runs every 10 minutes automatically
- AC3.2.3: All accessible Drive files listed and new/modified files detected
- AC3.2.4: File metadata stored: name, id, modified_at, owner, sharing_status
- AC3.2.5: Respects file permissions (only indexes accessible files)
- AC3.2.6: Sync status visible on dashboard ("Last sync: X min ago")
- AC3.2.7: Error rate <2% on sync jobs (retry logic handles transient failures)

### Story 3.3: Slack Connector & Message Indexing
- AC3.3.1: Slack API token configured and authenticated
- AC3.3.2: Sync job retrieves messages from last 10 minutes every 10 minutes
- AC3.3.3: Messages from all accessible channels retrieved
- AC3.3.4: Thread replies included (full conversation context)
- AC3.3.5: Files shared in messages extracted and indexed
- AC3.3.6: Respects channel privacy (no private channel indexing without access)
- AC3.3.7: Metadata stored: channel_id, user_id, timestamp, text, thread_id
- AC3.3.8: Error rate <2% on sync operations

### Story 3.4: Local File Upload & Parsing
- AC3.4.1: User can upload files via Suna UI (drag-drop or file picker)
- AC3.4.2: Supported formats: .md, .pdf, .csv, .json, .txt, .png, .jpg
- AC3.4.3: Files stored and parsed into text content automatically
- AC3.4.4: Parsed content indexed into Qdrant with metadata
- AC3.4.5: Uploaded files appear in search results immediately (<30s)
- AC3.4.6: File size limit enforced: 50MB maximum
- AC3.4.7: Unsupported file types show clear error message

### Story 3.5: Hybrid Search (Semantic + Keyword)
- AC3.5.1: User query triggers both semantic (vector) and keyword (BM25) search
- AC3.5.2: Semantic search returns top-10 candidates from Qdrant
- AC3.5.3: Keyword search returns top-10 candidates from PostgreSQL/Elasticsearch
- AC3.5.4: Results merged and ranked by combined score (70% semantic + 30% keyword)
- AC3.5.5: Top-5 final results passed to LLM context
- AC3.5.6: Total retrieval latency <200ms (95th percentile)
- AC3.5.7: Recent documents boosted by 10% in ranking

### Story 3.6: Citation & Source Link Generation
- AC3.6.1: RAG search returns top-5 documents with metadata
- AC3.6.2: LLM response includes inline citations [1], [2], etc.
- AC3.6.3: Citation key format: "[N] YYYY-MM-DD | Source Type | Title"
- AC3.6.4: Citations are clickable links to original source
- AC3.6.5: Clicking citation opens Drive doc or Slack thread in new tab/sidebar
- AC3.6.6: If no relevant source found, response states "No data found" clearly

## Traceability Mapping

| Acceptance Criteria | Spec Section | Component | Test Strategy |
|-------------------|--------------|-----------|---------------|
| AC3.1.1 | Services and Modules | qdrant-service | Integration: Health endpoint check |
| AC3.1.2 | Data Models | Qdrant collection | Integration: Collection creation API |
| AC3.1.3 | Performance | Search latency | Integration: Benchmark test |
| AC3.1.4 | Reliability | Data persistence | Integration: Container restart test |
| AC3.1.5 | APIs and Interfaces | Qdrant API | Unit: API endpoint tests |
| AC3.2.1 | Security | Google OAuth | Integration: OAuth flow test |
| AC3.2.2 | Workflows | Auto-sync schedule | Integration: Cron job verification |
| AC3.2.3 | Workflows | Document indexing | Integration: File detection test |
| AC3.2.4 | Data Models | PostgreSQL schema | Unit: Metadata storage test |
| AC3.2.5 | Security | Permission-aware indexing | Integration: Access control test |
| AC3.2.6 | Observability | Sync status UI | Manual: Dashboard verification |
| AC3.2.7 | Reliability | Fault tolerance | Integration: Error rate monitoring |
| AC3.3.1 | Security | Slack authentication | Integration: API token validation |
| AC3.3.2 | Workflows | Auto-sync schedule | Integration: Message retrieval test |
| AC3.3.3 | Workflows | Channel indexing | Integration: Multi-channel test |
| AC3.3.4 | Workflows | Thread parsing | Unit: Thread structure test |
| AC3.3.5 | Workflows | File extraction | Integration: Attachment handling |
| AC3.3.6 | Security | Channel privacy | Integration: Permission test |
| AC3.3.7 | Data Models | PostgreSQL schema | Unit: Metadata schema test |
| AC3.3.8 | Reliability | Fault tolerance | Integration: Error handling test |
| AC3.4.1 | APIs and Interfaces | Upload API | Integration: File upload flow |
| AC3.4.2 | Services and Modules | file-parser | Unit: Multi-format parsing |
| AC3.4.3 | Workflows | Document indexing | Integration: Parse → index flow |
| AC3.4.4 | Workflows | Vector storage | Integration: Qdrant upsert test |
| AC3.4.5 | Workflows | Search integration | Integration: Upload → search test |
| AC3.4.6 | Security | Input validation | Unit: File size check |
| AC3.4.7 | APIs and Interfaces | Error handling | Unit: Unsupported format test |
| AC3.5.1 | Workflows | Hybrid search flow | Integration: Parallel search test |
| AC3.5.2 | APIs and Interfaces | Qdrant search | Integration: Vector search test |
| AC3.5.3 | APIs and Interfaces | BM25 search | Integration: Keyword search test |
| AC3.5.4 | Workflows | Result fusion | Unit: Score combination test |
| AC3.5.5 | Workflows | Top-k selection | Integration: Ranking test |
| AC3.5.6 | Performance | Search latency | Integration: Latency benchmark |
| AC3.5.7 | Workflows | Recency boosting | Unit: Score adjustment test |
| AC3.6.1 | APIs and Interfaces | Search API response | Integration: Metadata inclusion |
| AC3.6.2 | Services and Modules | citation-generator | Integration: LLM prompt test |
| AC3.6.3 | APIs and Interfaces | Citation format | Unit: Format template test |
| AC3.6.4 | APIs and Interfaces | Link generation | Integration: URL construction |
| AC3.6.5 | APIs and Interfaces | Link behavior | Manual: Click-through test |
| AC3.6.6 | Workflows | Empty result handling | Integration: No-match scenario |

## Risks, Assumptions, Open Questions

### Risks:

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Google/Slack API rate limits** | High | Implement exponential backoff, batch requests, cache results, monitor rate limit headers |
| **Embedding API cost explosion** | Medium | Cache embeddings by content hash, batch requests (100 docs), monitor monthly spend, set budget alerts |
| **Qdrant performance degradation at scale** | Medium | Enable on-disk vectors, use scalar quantization, optimize indexing parameters, monitor latency |
| **Permission sync lag (security risk)** | High | Verify permissions on every sync, log permission changes, alert on access control failures |
| **Search relevance below 95% target** | Medium | Tune hybrid search weights, add reranking, collect user feedback, A/B test parameters |
| **Large file indexing timeouts** | Low | Stream content extraction, chunk files >10MB, set timeout limits (30s), retry failed chunks |
| **Slack thread depth causing memory issues** | Low | Limit thread depth to 100 messages, paginate deep threads, warn on large threads |

### Assumptions:

- Google Drive and Slack APIs remain stable and backward-compatible
- OpenAI embedding API maintains <100ms latency and 99.9% availability
- Users have necessary OAuth permissions to access Drive/Slack data
- Qdrant can handle 100k+ documents on KVM 4 VPS (4 vCPU, 16GB RAM)
- 1536-dimensional embeddings sufficient for semantic search quality
- English-only documents (no multi-language support needed for MVP)
- 10-minute sync frequency acceptable (not real-time indexing)
- 50MB file size limit covers 99% of uploaded documents

### Open Questions:

1. **Embedding Model Selection**: Should we use OpenAI text-embedding-3-small or fine-tune a custom model?
   - Recommendation: Start with OpenAI (proven quality), evaluate custom later

2. **BM25 Implementation**: Use PostgreSQL full-text search or deploy Elasticsearch?
   - Recommendation: PostgreSQL for MVP (simpler), Elasticsearch if performance issues

3. **Document Chunking**: Fixed 500-token chunks or semantic chunking?
   - Recommendation: Fixed chunks for MVP, semantic chunking in future iteration

4. **OCR for Images**: Should we OCR uploaded images or defer to future epic?
   - Recommendation: Defer to Epic 7 (Web Automation) with Tesseract integration

5. **Reranking Strategy**: Add reranking model (e.g., cross-encoder) or simple score boosting?
   - Recommendation: Simple boosting for MVP, evaluate reranking if relevance <95%

6. **Sync Conflict Resolution**: How to handle simultaneous edits to same document?
   - Recommendation: Last-write-wins based on modified_at timestamp

7. **Privacy Compliance**: Do we need to implement right-to-be-forgotten (GDPR)?
   - Recommendation: Not required for internal MVP, plan for future if expanding users

### Next Steps for Risk Mitigation:

1. Set up Google/Slack API monitoring with rate limit tracking
2. Implement embedding cost tracking dashboard (tokens used, estimated monthly cost)
3. Load test Qdrant with 100k+ documents to validate performance assumptions
4. Create permission audit log and automated permission verification
5. Design relevance evaluation framework (50 test queries, manual assessment)
6. Implement file size validation and streaming for large files
7. Add Slack thread depth limits to prevent memory exhaustion

## Test Strategy Summary

### Testing Levels:

1. **Unit Tests**: Individual parsers, score calculation, citation formatting
   - Test: PDF parsing, CSV parsing, Markdown parsing
   - Test: Hybrid score calculation (70/30 weighting)
   - Test: Citation template rendering
   - Coverage: >80% for core modules

2. **Integration Tests**: API endpoints, sync flows, search pipelines
   - Test: Google Drive OAuth flow → file listing → indexing
   - Test: Slack message sync → thread parsing → storage
   - Test: File upload → parsing → embedding → Qdrant upsert
   - Test: Search query → embedding → parallel search → result fusion
   - Coverage: All API endpoints, all sync workflows

3. **Performance Tests**: Latency benchmarks, throughput testing
   - Benchmark: Search latency with 10k, 50k, 100k documents
   - Benchmark: Sync throughput (docs/minute)
   - Benchmark: Concurrent search queries (100 req/sec)
   - Baseline: Establish p50, p95, p99 latency targets

4. **End-to-End Tests**: User workflows from upload/sync to search to citation
   - Scenario: Upload PDF → search finds it → citation links work
   - Scenario: Google Drive sync → new file indexed → appears in search
   - Scenario: Slack message → indexed → search → citation with permalink
   - Validation: All user journeys complete successfully

5. **Security Tests**: Permission enforcement, data privacy, access control
   - Test: User A cannot search User B's private documents
   - Test: Google Drive file permissions respected in search results
   - Test: Slack private channel messages excluded from search
   - Validation: Zero permission leakage incidents

### Test Environment:

- **Local**: Docker Compose with mock APIs (Google/Slack) for development
- **Staging**: Real APIs with test accounts, subset of production data
- **Production**: Real data, real APIs, full monitoring

### Key Test Scenarios:

```python
# 1. Qdrant Setup Test
def test_qdrant_setup():
    assert qdrant.health_check() == 200
    collection = qdrant.get_collection("documents")
    assert collection.vector_size == 1536
    assert collection.distance == "Cosine"

# 2. Google Drive Sync Test
def test_google_drive_sync():
    job = sync_google_drive(folder_id="test-folder")
    assert job.status == "success"
    assert job.documents_synced > 0
    assert job.documents_failed < job.documents_synced * 0.02  # <2% error rate

# 3. Hybrid Search Test
def test_hybrid_search():
    results = hybrid_search(query="competitive advantage", top_k=5)
    assert len(results) == 5
    assert results[0].relevance_score > 0.9
    assert results[0].citation is not None
    assert search_latency < 200  # ms

# 4. Permission Enforcement Test
def test_permission_filtering():
    # User A searches for document owned by User B (private)
    results = hybrid_search(query="confidential doc", user=user_a)
    assert all(user_a.email in doc.permissions for doc in results)

# 5. Citation Generation Test
def test_citation_generation():
    citations = generate_citations(doc_ids=[doc1.id, doc2.id])
    assert citations[0].text == "[1] Q4 Strategy Doc (Google Drive, Nov 10)"
    assert citations[0].link.startswith("https://drive.google.com")
```

### Test Coverage Requirements:

- **Unit Tests**: >80% code coverage for parsers, search, citation modules
- **Integration Tests**: 100% of API endpoints, sync workflows, search pipelines
- **Performance Tests**: All latency targets validated (p95 < 200ms)
- **Security Tests**: All permission scenarios covered
- **E2E Tests**: 5 critical user journeys validated

### Success Criteria:

- All acceptance criteria pass for all 6 stories
- Search latency p95 <200ms with 100k documents
- Sync success rate >98% (error rate <2%)
- Search relevance >95% on 50 test queries (manual evaluation)
- Zero permission leakage incidents in security testing
- All performance benchmarks meet targets

### Test Automation:

- **CI Pipeline**: Run unit + integration tests on every PR
- **Nightly Tests**: Run full test suite including performance benchmarks
- **Weekly**: Run security tests, permission audits
- **Monthly**: Relevance evaluation on production data

### Monitoring Post-Deployment:

- **Search Latency**: Alert if p95 > 300ms
- **Sync Success Rate**: Alert if <95% success
- **Relevance**: Monthly manual evaluation (50 queries)
- **Permissions**: Automated weekly audit, alert on discrepancies

---

**Epic 3 Technical Specification Complete**

This specification provides comprehensive guidance for implementing the RAG system for Manus Internal. All implementation teams should reference this document for technical decisions, API contracts, and acceptance criteria validation.

**Next Steps:**
1. Review and approve this specification
2. Begin Story 3.1 (Qdrant setup) - foundation blocker
3. Parallelize Stories 3.2 (Drive), 3.3 (Slack), 3.4 (Uploads) once Qdrant ready
4. Implement Story 3.5 (Hybrid Search) after data sources operational
5. Finalize Story 3.6 (Citations) to complete RAG integration

**Document Status:** Draft - Pending Review
**Approver:** darius (Product Owner)
**Technical Reviewer:** System Architect
**Date:** 2025-11-13
