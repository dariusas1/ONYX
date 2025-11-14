# Epic 4: Persistent Memory & Learning - Technical Specification

**Project:** ONYX (Manus Internal)
**Epic ID:** epic-4
**Author:** Technical Architect
**Date:** 2025-11-14
**Version:** 1.0
**Status:** Ready for Implementation

---

## Executive Summary

Epic 4 delivers the persistent memory and learning capabilities that transform ONYX from a stateless chat tool into an intelligent strategic partner that remembers context across sessions, learns from every interaction, and builds compounding knowledge about the user and their business. This epic implements the memory layer that makes ONYX truly adaptive and personalized.

**Goal:** Enable ONYX to maintain persistent context, learn user preferences, and provide increasingly personalized strategic guidance over time.

**Success Criteria:**
- User memories persist across all chat sessions with 98% recall accuracy
- System automatically extracts and stores relevant facts from conversations
- Standing instructions are consistently applied to all future interactions
- Memory injection adds <50ms latency to chat initiation
- Memory UI allows users to view, edit, and manage their stored memories
- Cross-session context awareness improves conversation relevance by >40%

**Timeline:** Week 2-3 of development (following Epic 1-3 completion)

**Dependencies:**
- Epic 1 (Foundation & Infrastructure) must be complete
- Epic 2 (Chat Interface & Conversation Management) must be complete
- Epic 3 (RAG Integration & Knowledge Retrieval) must be complete
- PostgreSQL database running with schema initialized
- LiteLLM proxy operational for LLM integration

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Epic 4 Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Browser    │────────▶│  Suna (Next) │                 │
│  │   (User)     │◀────────│   Frontend   │                 │
│  └──────────────┘  HTTP   └──────┬───────┘                 │
│                            │ API                            │
│                            │                                │
│  ┌─────────────────────────▼────────────────┐               │
│  │            Memory Layer                 │               │
│  │  ┌─────────────┐  ┌─────────────────┐   │               │
│  │  │   Memory    │  │  Standing       │   │               │
│  │  │  Manager    │  │  Instructions   │   │               │
│  │  │             │  │                 │   │               │
│  │  │ • Extract   │  │ • System Prompt │   │               │
│  │  │ • Store     │  │   Injection     │   │               │
│  │  │ • Recall    │  │ • Validation    │   │               │
│  │  │ • Search    │  │ • Persistence   │   │               │
│  │  └─────────────┘  └─────────────────┘   │               │
│  └─────────────────────────────────────────┘               │
│                            │                                │
│                            ▼                                │
│  ┌─────────────────────────────────────────┐               │
│  │         PostgreSQL Database             │               │
│  │  ┌─────────────┐  ┌─────────────────┐   │               │
│  │  │   Memories  │  │  Standing       │   │               │
│  │  │   Table     │  │  Instructions   │   │               │
│  │  │             │  │                 │   │               │
│  │  │ • User Facts│  │ • Directives    │   │               │
│  │  │ • Context   │  │ • Persistence   │   │               │
│  │  │ • Metadata  │  │ • Versioning    │   │               │
│  │  └─────────────┘  └─────────────────┘   │               │
│  └─────────────────────────────────────────┘               │
│                                                              │
│  ┌─────────────────────────────────────────┐               │
│  │          Qdrant Vector DB               │               │
│  │                                         │               │
│  │  • Memory Embeddings for Similarity     │               │
│  │  • Semantic Memory Search              │               │
│  │  • Fast Retrieval (<10ms)              │               │
│  └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Memory Flow Architecture

```
Chat Start → Memory Injection → LLM Context → Response Generation → Memory Extraction → Storage

1. Chat Start
   └─ Load top-5 user memories (PostgreSQL)
   └─ Load standing instructions (PostgreSQL)
   └─ Inject into LLM system prompt

2. Response Generation
   └─ LLM uses memory context to personalize response
   └─ Citations link to both documents AND memories

3. Memory Extraction (Async)
   └─ Analyze conversation for new facts
   └─ Extract entities, preferences, decisions
   └─ Store in PostgreSQL + Qdrant

4. Memory Management
   └─ User can view/edit memories via UI
   └─ Set expiration dates for temporary facts
   └─ Search memories by keyword or semantic similarity
```

---

## Functional Requirements

### Memory Storage & Retrieval

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F4.1.1 | User memory storage | Store unlimited user facts with metadata (source, confidence, expiration) |
| F4.1.2 | Cross-session recall | Inject top-5 relevant memories at start of each chat session |
| F4.1.3 | Memory accuracy | 98% recall accuracy of stored facts across 5+ sessions |
| F4.1.4 | Memory search | Full-text search across all stored memories with relevance ranking |
| F4.1.5 | Semantic similarity | Find memories by meaning, not just exact keywords (via Qdrant embeddings) |
| F4.1.6 | Memory hierarchy | Prioritize memories by recency, frequency, and user confidence |
| F4.1.7 | Contextual relevance | Select memories based on current conversation topic |
| F4.1.8 | Memory persistence | Survive system restarts, database failures, version upgrades |

### Automatic Memory Extraction

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F4.2.1 | Conversation analysis | Automatically extract new facts from every conversation |
| F4.2.2 | Entity recognition | Identify people, companies, projects, preferences, decisions |
| F4.2.3 | Confidence scoring | Rate extracted facts by confidence (0.0-1.0) before storage |
| F4.2.4 | Source tracking | Track conversation source for each memory (chat ID, timestamp) |
| F4.2.5 | Fact validation | Avoid storing contradictory or outdated information |
| F4.2.6 | Batch processing | Process memory extraction asynchronously (not block chat) |
| F4.2.7 | User confirmation | Optional: Prompt user to confirm important extracted facts |

### Standing Instructions System

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F4.3.1 | Instruction storage | Store user-defined standing instructions with priority levels |
| F4.3.2 | System prompt injection | Automatically include standing instructions in LLM context |
| F4.3.3 | Instruction persistence | Apply instructions consistently across all future sessions |
| F4.3.4 | Priority handling | Higher priority instructions override lower priority ones |
| F4.3.5 | Conditional instructions | Support "if-then" conditional instructions |
| F4.3.6 | Time-based instructions | Support instructions that expire at specific times |
| F4.3.7 | Instruction validation | Parse and validate instruction syntax before storage |

### Memory Management Interface

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F4.4.1 | Memory viewing | Display all stored memories with search and filtering |
| F4.4.2 | Memory editing | Allow users to edit, delete, or modify stored memories |
| F4.4.3 | Memory categorization | Tag memories with categories (projects, people, decisions) |
| F4.4.4 | Memory export | Export all memories as JSON or CSV for backup |
| F4.4.5 | Memory import | Import memories from previous instances or backups |
| F4.4.6 | Privacy controls | Allow users to mark memories as private or sensitive |
| F4.4.7 | Memory analytics | Show memory growth trends and usage statistics |

### Context Integration

| Req ID | Requirement | Acceptance Criteria |
|--------|-------------|-------------------|
| F4.5.1 | LLM integration | Inject memories into LLM system prompt seamlessly |
| F4.5.2 | RAG integration | Combine memories with document retrieval for context |
| F4.5.3 | Citation linking | Cite memories alongside document sources in responses |
| F4.5.4 | Performance impact | Memory injection adds <50ms to chat response time |
| F4.5.5 | Context window management | Optimize memory selection to fit within LLM context limits |
| F4.5.6 | Memory relevance scoring | Rate memories by relevance to current conversation |
| F4.5.7 | Dynamic context updating | Update context during long conversations if needed |

---

## Data Architecture

### PostgreSQL Schema

```sql
-- User Memories Table
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  fact TEXT NOT NULL,
  fact_type TEXT NOT NULL CHECK (fact_type IN ('preference', 'decision', 'relationship', 'project', 'company', 'personal', 'strategic')),
  confidence DECIMAL(3,2) DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
  source_type TEXT NOT NULL CHECK (source_type IN ('manual', 'extracted_from_chat', 'extracted_from_document', 'api_import')),
  source_id TEXT, -- Reference to conversation, document, or import batch
  embedding VECTOR(1536), -- pgvector for semantic similarity
  category TEXT,
  tags TEXT[], -- Array of tags for categorization
  expires_at TIMESTAMP, -- NULL = permanent
  is_private BOOLEAN DEFAULT false,
  access_count INTEGER DEFAULT 0,
  last_accessed TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Standing Instructions Table
CREATE TABLE standing_instructions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  instruction TEXT NOT NULL,
  priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 10),
  condition_expression TEXT, -- Optional conditional logic (JSONPath or similar)
  expires_at TIMESTAMP, -- NULL = permanent
  is_active BOOLEAN DEFAULT true,
  usage_count INTEGER DEFAULT 0,
  last_used TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Memory Extraction Jobs (for async processing)
CREATE TABLE memory_extraction_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  conversation_id UUID REFERENCES conversations(id),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  extracted_facts JSONB DEFAULT '[]', -- Array of extracted facts waiting for confirmation
  processed_facts INTEGER DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);

-- Memory Access Logs (for analytics and privacy)
CREATE TABLE memory_access_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  memory_id UUID REFERENCES memories(id),
  access_type TEXT NOT NULL CHECK (access_type IN ('injected', 'cited', 'viewed', 'edited')),
  conversation_id UUID REFERENCES conversations(id),
  relevance_score DECIMAL(3,2), -- How relevant was this memory to the conversation
  created_at TIMESTAMP DEFAULT NOW()
);

-- Memory Categories (user-defined taxonomy)
CREATE TABLE memory_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  color TEXT DEFAULT '#3b82f6', -- Hex color for UI
  description TEXT,
  parent_category_id UUID REFERENCES memory_categories(id),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for Performance
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_fact_type ON memories(fact_type);
CREATE INDEX idx_memories_category ON memories(category);
CREATE INDEX idx_memories_expires_at ON memories(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_standing_instructions_user_active ON standing_instructions(user_id, is_active) WHERE is_active = true;
CREATE INDEX idx_standing_instructions_priority ON standing_instructions(user_id, priority DESC);

CREATE INDEX idx_memory_extraction_jobs_status ON memory_extraction_jobs(status);
CREATE INDEX idx_memory_access_logs_user_date ON memory_access_logs(user_id, created_at DESC);
```

### Qdrant Collection Configuration

```yaml
# memories collection for semantic search
memories_collection:
  vectors:
    size: 1536  # text-embedding-3-small dimensions
    distance: Cosine
    on_disk: true  # Persist vectors to disk

  payload_schema:
    memory_id: string  # PostgreSQL UUID
    user_id: string   # For multi-tenant isolation
    fact_type: string # Type of memory
    category: string  # User-defined category
    tags: array      # Array of string tags
    confidence: float # 0.0-1.0 confidence score
    created_at: string # ISO 8601 timestamp
    expires_at: string # NULL for permanent memories

  optimizers_config:
    default_segment_number: 2  # Start with 2 segments for good performance
    memmap_threshold: 50000    # Use memory mapping for larger collections
    indexing_threshold: 10000   # Build HNSW index after 10k vectors
    max_indexing_threads: 2    # Limit indexing threads for resource efficiency

  quantization_config:
    scalar:
      type: int8  # 8-bit scalar quantization for memory efficiency
```

---

## API Design

### Memory Management API

```typescript
// GET /api/memory - List user memories
interface GetMemoriesRequest {
  category?: string;
  fact_type?: MemoryType;
  search?: string;
  limit?: number; // default 50
  offset?: number; // default 0
  include_expired?: boolean; // default false
}

interface GetMemoriesResponse {
  success: boolean;
  data: {
    memories: Memory[];
    total: number;
    categories: MemoryCategory[];
  };
}

// POST /api/memory - Create new memory
interface CreateMemoryRequest {
  fact: string;
  fact_type: MemoryType;
  category?: string;
  tags?: string[];
  expires_at?: string; // ISO 8601
  is_private?: boolean;
  confidence?: number; // 0.0-1.0
}

interface CreateMemoryResponse {
  success: boolean;
  data: {
    memory: Memory;
  };
}

// PATCH /api/memory/:id - Update existing memory
interface UpdateMemoryRequest {
  fact?: string;
  fact_type?: MemoryType;
  category?: string;
  tags?: string[];
  expires_at?: string | null;
  is_private?: boolean;
  confidence?: number;
}

// DELETE /api/memory/:id - Delete memory
interface DeleteMemoryResponse {
  success: boolean;
  data: {
    deleted_id: string;
  };
}

// GET /api/memory/search - Search memories
interface SearchMemoriesRequest {
  query: string;
  search_type: 'text' | 'semantic' | 'hybrid';
  limit?: number; // default 10
  min_relevance?: number; // default 0.5
}

interface SearchMemoriesResponse {
  success: boolean;
  data: {
    results: Array<{
      memory: Memory;
      relevance_score: number;
      match_type: 'exact' | 'semantic' | 'hybrid';
    }>;
  };
}
```

### Standing Instructions API

```typescript
// GET /api/instructions - List standing instructions
interface GetInstructionsRequest {
  active_only?: boolean; // default true
  priority_min?: number; // default 1
  priority_max?: number; // default 10
}

interface GetInstructionsResponse {
  success: boolean;
  data: {
    instructions: StandingInstruction[];
  };
}

// POST /api/instructions - Create standing instruction
interface CreateInstructionRequest {
  instruction: string;
  priority?: number; // default 1
  condition_expression?: string; // Optional conditional logic
  expires_at?: string; // ISO 8601, null = permanent
}

interface CreateInstructionResponse {
  success: boolean;
  data: {
    instruction: StandingInstruction;
  };
}

// PATCH /api/instructions/:id - Update instruction
interface UpdateInstructionRequest {
  instruction?: string;
  priority?: number;
  condition_expression?: string;
  expires_at?: string | null;
  is_active?: boolean;
}
```

### Memory Categories API

```typescript
// GET /api/memory/categories - List memory categories
interface GetCategoriesResponse {
  success: boolean;
  data: {
    categories: MemoryCategory[];
    category_stats: Array<{
      category_id: string;
      memory_count: number;
      last_used: string;
    }>;
  };
}

// POST /api/memory/categories - Create category
interface CreateCategoryRequest {
  name: string;
  color?: string; // hex color
  description?: string;
  parent_category_id?: string;
}
```

### Memory Analytics API

```typescript
// GET /api/memory/analytics - Memory usage analytics
interface GetMemoryAnalyticsResponse {
  success: boolean;
  data: {
    summary: {
      total_memories: number;
      active_memories: number;
      expired_memories: number;
      memories_this_week: number;
      memories_this_month: number;
    };
    growth_trend: Array<{
      date: string;
      cumulative_count: number;
      new_memories: number;
    }>;
    category_distribution: Array<{
      category: string;
      count: number;
      percentage: number;
    }>;
    fact_type_distribution: Array<{
      fact_type: MemoryType;
      count: number;
      percentage: number;
    }>;
    usage_stats: {
      most_accessed_memories: Array<{
        memory_id: string;
        fact: string;
        access_count: number;
      }>;
      recently_accessed: Array<{
        memory_id: string;
        fact: string;
        last_accessed: string;
      }>;
    };
  };
}
```

---

## Implementation Patterns

### Memory Injection System

```typescript
// Memory injection at chat start
class MemoryInjector {
  async injectContext(userId: string, conversationTopic?: string): Promise<MemoryContext> {
    // 1. Load standing instructions (highest priority)
    const instructions = await this.getStandingInstructions(userId);

    // 2. Load relevant memories based on conversation topic
    const relevantMemories = await this.getRelevantMemories(userId, conversationTopic);

    // 3. Build memory context string
    const memoryContext = this.buildMemoryContext(instructions, relevantMemories);

    // 4. Log injection for analytics
    await this.logMemoryInjection(userId, relevantMemories.map(m => m.id));

    return memoryContext;
  }

  private async getRelevantMemories(userId: string, topic?: string): Promise<Memory[]> {
    if (!topic) {
      // If no topic, get most recent and frequently accessed memories
      return await this.getRecentMemories(userId, 5);
    }

    // Semantic search for topic-relevant memories
    const topicEmbedding = await this.generateEmbedding(topic);
    const similarMemories = await this.qdrantClient.search('memories', {
      query_vector: topicEmbedding,
      query_filter: {
        must: [
          { key: 'user_id', match: { value: userId } },
          {
            key: 'expires_at',
            match: { value: null }, // Only non-expired
            is_null: true
          }
        ]
      },
      limit: 10,
      score_threshold: 0.7
    });

    return similarMemories.map(result => this.mapQdrantPointToMemory(result));
  }

  private buildMemoryContext(instructions: StandingInstruction[], memories: Memory[]): string {
    const instructionText = instructions
      .sort((a, b) => b.priority - a.priority)
      .map(inst => `- ${inst.instruction}`)
      .join('\n');

    const memoryText = memories
      .map(mem => `- ${mem.fact} (${mem.source_type})`)
      .join('\n');

    let context = '';

    if (instructionText) {
      context += `## Standing Instructions:\n${instructionText}\n\n`;
    }

    if (memoryText) {
      context += `## Relevant Context:\n${memoryText}\n\n`;
    }

    context += `## Instructions:
Use the above context and memories to provide personalized, relevant responses.
When referencing memories, cite them as [Memory: fact description].`;

    return context;
  }
}
```

### Automatic Memory Extraction

```typescript
// Async memory extraction from conversations
class MemoryExtractor {
  async extractFromConversation(conversationId: string): Promise<void> {
    // Create extraction job
    const job = await this.createExtractionJob(conversationId);

    // Process asynchronously (don't block chat)
    setImmediate(() => this.processExtractionJob(job.id));
  }

  private async processExtractionJob(jobId: string): Promise<void> {
    const job = await this.getExtractionJob(jobId);

    try {
      await this.updateJobStatus(jobId, 'processing');

      // 1. Load conversation messages
      const conversation = await this.loadConversation(job.conversation_id);

      // 2. Extract facts using LLM
      const extractedFacts = await this.extractFactsWithLLM(conversation.messages);

      // 3. Validate and score facts
      const validatedFacts = await this.validateAndScoreFacts(extractedFacts, conversation);

      // 4. Store high-confidence facts automatically
      const autoStored = await this.storeFactsAutomatically(validatedFacts.filter(f => f.confidence >= 0.8));

      // 5. Queue lower-confidence facts for user confirmation
      const needsConfirmation = validatedFacts.filter(f => f.confidence < 0.8);
      if (needsConfirmation.length > 0) {
        await this.queueForConfirmation(jobId, needsConfirmation);
      }

      await this.updateJobStatus(jobId, 'completed', {
        processed_facts: autoStored.length + needsConfirmation.length,
        auto_stored: autoStored.length,
        needs_confirmation: needsConfirmation.length
      });

    } catch (error) {
      await this.updateJobStatus(jobId, 'failed', {
        error_message: error.message
      });
    }
  }

  private async extractFactsWithLLM(messages: Message[]): Promise<ExtractedFact[]> {
    const conversationText = messages
      .map(m => `${m.role}: ${m.content}`)
      .join('\n\n');

    const prompt = `
Analyze this conversation and extract important facts about the user. Focus on:

1. Personal preferences (e.g., "prefers morning meetings")
2. Business decisions (e.g., "decided to prioritize defense contracts")
3. Relationships (e.g., "works closely with Sarah on product")
4. Strategic priorities (e.g., "expanding into enterprise market")
5. Project information (e.g., "ONYX launch target is December 15")
6. Company information (e.g., "M3rcury has 12 employees")

For each fact, provide:
- The fact statement
- Type (preference/decision/relationship/project/company/personal/strategic)
- Confidence level (0.0-1.0)
- Source evidence from conversation

Conversation:
${conversationText}

Respond in JSON format:
{
  "extracted_facts": [
    {
      "fact": "fact statement",
      "type": "preference|decision|relationship|project|company|personal|strategic",
      "confidence": 0.9,
      "evidence": "quote from conversation supporting this fact",
      "suggested_category": "category name"
    }
  ]
}`;

    const response = await this.llmClient.generate(prompt);
    return JSON.parse(response.content).extracted_facts;
  }
}
```

### Memory Search & Ranking

```typescript
// Hybrid memory search (text + semantic)
class MemorySearch {
  async searchMemories(userId: string, query: string, options: SearchOptions = {}): Promise<SearchResult[]> {
    const {
      search_type = 'hybrid',
      limit = 10,
      min_relevance = 0.5,
      fact_types,
      categories
    } = options;

    let textResults: SearchResult[] = [];
    let semanticResults: SearchResult[] = [];

    // 1. Text search (PostgreSQL full-text search)
    if (search_type === 'text' || search_type === 'hybrid') {
      textResults = await this.textSearch(userId, query, { limit, fact_types, categories });
    }

    // 2. Semantic search (Qdrant vector search)
    if (search_type === 'semantic' || search_type === 'hybrid') {
      semanticResults = await this.semanticSearch(userId, query, { limit, fact_types, categories });
    }

    // 3. Combine and rank results
    if (search_type === 'hybrid') {
      return this.combineResults(textResults, semanticResults, min_relevance);
    }

    // 4. Return single-type results
    const results = search_type === 'text' ? textResults : semanticResults;
    return results.filter(r => r.relevance_score >= min_relevance);
  }

  private async textSearch(userId: string, query: string, options: SearchOptions): Promise<SearchResult[]> {
    const sql = `
      SELECT
        m.*,
        ts_rank(search_vector, plainto_tsquery($1)) as relevance_score
      FROM memories m
      WHERE m.user_id = $2
        AND ($3::text[] IS NULL OR m.fact_type = ANY($3))
        AND ($4::text[] IS NULL OR m.category = ANY($4))
        AND (m.expires_at IS NULL OR m.expires_at > NOW())
        AND search_vector @@ plainto_tsquery($1)
      ORDER BY relevance_score DESC, m.created_at DESC
      LIMIT $5
    `;

    const results = await this.db.query(sql, [query, userId, options.fact_types, options.categories, options.limit]);

    return results.map(row => ({
      memory: this.mapRowToMemory(row),
      relevance_score: row.relevance_score,
      match_type: 'exact' as const
    }));
  }

  private async semanticSearch(userId: string, query: string, options: SearchOptions): Promise<SearchResult[]> {
    const queryEmbedding = await this.generateEmbedding(query);

    const filter: any = {
      must: [
        { key: 'user_id', match: { value: userId } },
        {
          key: 'expires_at',
          is_null: true // Non-expired memories only
        }
      ]
    };

    if (options.fact_types) {
      filter.must.push({
        key: 'fact_type',
        match: { any: options.fact_types }
      });
    }

    if (options.categories) {
      filter.must.push({
        key: 'category',
        match: { any: options.categories }
      });
    }

    const searchResults = await this.qdrantClient.search('memories', {
      query_vector: queryEmbedding,
      query_filter: filter,
      limit: options.limit,
      with_payload: true,
      score_threshold: 0.3
    });

    return searchResults.map(result => ({
      memory: this.mapQdrantPointToMemory(result),
      relevance_score: result.score,
      match_type: 'semantic' as const
    }));
  }

  private combineResults(textResults: SearchResult[], semanticResults: SearchResult[], minRelevance: number): SearchResult[] {
    const combinedResults = new Map<string, SearchResult>();

    // Add text results
    textResults.forEach(result => {
      combinedResults.set(result.memory.id, {
        ...result,
        relevance_score: result.relevance_score * 0.7 // Weight text search lower
      });
    });

    // Add or combine with semantic results
    semanticResults.forEach(result => {
      const existing = combinedResults.get(result.memory.id);
      if (existing) {
        // Combine scores - semantic search gets higher weight
        existing.relevance_score = Math.max(
          existing.relevance_score,
          result.relevance_score * 0.9 + existing.relevance_score * 0.1
        );
        existing.match_type = 'hybrid';
      } else {
        combinedResults.set(result.memory.id, {
          ...result,
          relevance_score: result.relevance_score * 0.9 // Weight semantic search higher
        });
      }
    });

    // Convert to array and sort by relevance
    return Array.from(combinedResults.values())
      .filter(r => r.relevance_score >= minRelevance)
      .sort((a, b) => b.relevance_score - a.relevance_score);
  }
}
```

---

## User Interface Design

### Memory Management Dashboard

```typescript
// Memory management interface components
interface MemoryManagerProps {
  userId: string;
}

const MemoryManager: React.FC<MemoryManagerProps> = ({ userId }) => {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [categories, setCategories] = useState<MemoryCategory[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  return (
    <div className="memory-manager">
      {/* Header with stats */}
      <MemoryStats userId={userId} />

      {/* Search and filters */}
      <div className="memory-filters">
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search memories..."
        />
        <CategoryFilter
          categories={categories}
          selected={selectedCategory}
          onChange={setSelectedCategory}
        />
        <ViewModeToggle
          mode={viewMode}
          onChange={setViewMode}
        />
      </div>

      {/* Memory list/grid */}
      <MemoryList
        memories={memories}
        viewMode={viewMode}
        onEdit={handleEditMemory}
        onDelete={handleDeleteMemory}
      />

      {/* Add new memory */}
      <AddMemoryButton onClick={handleAddMemory} />
    </div>
  );
};

// Individual memory card component
interface MemoryCardProps {
  memory: Memory;
  onEdit: (memory: Memory) => void;
  onDelete: (memoryId: string) => void;
}

const MemoryCard: React.FC<MemoryCardProps> = ({ memory, onEdit, onDelete }) => {
  return (
    <div className="memory-card">
      <div className="memory-header">
        <CategoryBadge category={memory.category} />
        <FactTypeBadge type={memory.fact_type} />
        <ConfidenceScore confidence={memory.confidence} />
      </div>

      <div className="memory-content">
        <p className="memory-fact">{memory.fact}</p>
        <div className="memory-metadata">
          <span className="source">Source: {memory.source_type}</span>
          <span className="created">Created: {formatDate(memory.created_at)}</span>
          {memory.expires_at && (
            <span className="expires">Expires: {formatDate(memory.expires_at)}</span>
          )}
        </div>
      </div>

      <div className="memory-actions">
        <EditButton onClick={() => onEdit(memory)} />
        <DeleteButton onClick={() => onDelete(memory.id)} />
        <ViewSourceButton sourceId={memory.source_id} />
      </div>

      {memory.tags.length > 0 && (
        <div className="memory-tags">
          {memory.tags.map(tag => (
            <Tag key={tag} label={tag} />
          ))}
        </div>
      )}
    </div>
  );
};
```

### Standing Instructions Interface

```typescript
// Standing instructions management
interface StandingInstructionsProps {
  userId: string;
}

const StandingInstructions: React.FC<StandingInstructionsProps> = ({ userId }) => {
  const [instructions, setInstructions] = useState<StandingInstruction[]>([]);
  const [isAdding, setIsAdding] = useState(false);

  return (
    <div className="standing-instructions">
      <div className="instructions-header">
        <h2>Standing Instructions</h2>
        <AddInstructionButton onClick={() => setIsAdding(true)} />
      </div>

      <div className="instructions-list">
        {instructions
          .sort((a, b) => b.priority - a.priority)
          .map(instruction => (
            <InstructionCard
              key={instruction.id}
              instruction={instruction}
              onEdit={handleEditInstruction}
              onDelete={handleDeleteInstruction}
              onToggleActive={handleToggleActive}
            />
          ))}
      </div>

      {isAdding && (
        <AddInstructionModal
          userId={userId}
          onSave={handleSaveInstruction}
          onCancel={() => setIsAdding(false)}
        />
      )}
    </div>
  );
};

interface InstructionCardProps {
  instruction: StandingInstruction;
  onEdit: (instruction: StandingInstruction) => void;
  onDelete: (instructionId: string) => void;
  onToggleActive: (instructionId: string, active: boolean) => void;
}

const InstructionCard: React.FC<InstructionCardProps> = ({
  instruction,
  onEdit,
  onDelete,
  onToggleActive
}) => {
  return (
    <div className={`instruction-card ${!instruction.is_active ? 'inactive' : ''}`}>
      <div className="instruction-header">
        <PriorityBadge priority={instruction.priority} />
        <ActiveToggle
          active={instruction.is_active}
          onChange={(active) => onToggleActive(instruction.id, active)}
        />
      </div>

      <div className="instruction-content">
        <p className="instruction-text">{instruction.instruction}</p>
        {instruction.condition_expression && (
          <div className="condition-badge">
            Conditional: {instruction.condition_expression}
          </div>
        )}
      </div>

      <div className="instruction-metadata">
        <span>Priority: {instruction.priority}</span>
        <span>Used {instruction.usage_count} times</span>
        {instruction.expires_at && (
          <span>Expires: {formatDate(instruction.expires_at)}</span>
        )}
      </div>

      <div className="instruction-actions">
        <EditButton onClick={() => onEdit(instruction)} />
        <DeleteButton onClick={() => onDelete(instruction.id)} />
      </div>
    </div>
  );
};
```

---

## Performance Optimizations

### Memory Retrieval Optimizations

```typescript
// Memory caching and performance optimizations
class MemoryCache {
  private redis: Redis;
  private cacheConfig = {
    recentMemories: { ttl: 300, key: 'memories:recent:{userId}' }, // 5 min
    instructions: { ttl: 600, key: 'instructions:{userId}' }, // 10 min
    searchResults: { ttl: 180, key: 'search:{userId}:{queryHash}' }, // 3 min
  };

  async getRecentMemories(userId: string, limit: number = 10): Promise<Memory[]> {
    const cacheKey = this.cacheConfig.recentMemories.key.replace('{userId}', userId);

    // Try cache first
    const cached = await this.redis.get(cacheKey);
    if (cached) {
      return JSON.parse(cached);
    }

    // Cache miss - fetch from database
    const memories = await this.fetchRecentMemoriesFromDB(userId, limit);

    // Cache for 5 minutes
    await this.redis.setex(cacheKey, this.cacheConfig.recentMemories.ttl, JSON.stringify(memories));

    return memories;
  }

  async getStandingInstructions(userId: string): Promise<StandingInstruction[]> {
    const cacheKey = this.cacheConfig.instructions.key.replace('{userId}', userId);

    const cached = await this.redis.get(cacheKey);
    if (cached) {
      return JSON.parse(cached);
    }

    const instructions = await this.fetchInstructionsFromDB(userId);

    await this.redis.setex(cacheKey, this.cacheConfig.instructions.ttl, JSON.stringify(instructions));

    return instructions;
  }

  async invalidateUserCache(userId: string): Promise<void> {
    const patterns = [
      this.cacheConfig.recentMemories.key.replace('{userId}', userId),
      this.cacheConfig.instructions.key.replace('{userId}', userId),
      `search:${userId}:*` // All search results for this user
    ];

    for (const pattern of patterns) {
      const keys = await this.redis.keys(pattern);
      if (keys.length > 0) {
        await this.redis.del(...keys);
      }
    }
  }
}

// Batch memory operations for efficiency
class MemoryBatchProcessor {
  async batchStoreMemories(memories: CreateMemoryRequest[]): Promise<Memory[]> {
    // Use PostgreSQL COPY for bulk inserts
    const sql = `
      INSERT INTO memories (user_id, fact, fact_type, confidence, source_type, source_id, category, tags, is_private)
      VALUES ${memories.map((_, i) => `($${i * 9 + 1}, $${i * 9 + 2}, $${i * 9 + 3}, $${i * 9 + 4}, $${i * 9 + 5}, $${i * 9 + 6}, $${i * 9 + 7}, $${i * 9 + 8}, $${i * 9 + 9})`).join(', ')}
      RETURNING *
    `;

    const values = memories.flatMap(m => [
      m.user_id,
      m.fact,
      m.fact_type,
      m.confidence || 1.0,
      m.source_type || 'manual',
      m.source_id,
      m.category,
      m.tags || [],
      m.is_private || false
    ]);

    const result = await this.db.query(sql, values);

    // Batch generate embeddings and store in Qdrant
    const embeddings = await this.batchGenerateEmbeddings(result.rows);
    await this.batchStoreEmbeddings(embeddings);

    return result.rows;
  }

  private async batchGenerateEmbeddings(memories: Memory[]): Promise<Array<{memory: Memory, embedding: number[]}>> {
    // Process in batches of 10 to avoid overwhelming the embedding API
    const batchSize = 10;
    const results = [];

    for (let i = 0; i < memories.length; i += batchSize) {
      const batch = memories.slice(i, i + batchSize);
      const texts = batch.map(m => m.fact);

      // Generate embeddings for the batch
      const embeddings = await this.embeddingClient.embedBatch(texts);

      results.push(...batch.map((memory, index) => ({
        memory,
        embedding: embeddings[index]
      })));
    }

    return results;
  }
}
```

### Database Performance Optimizations

```sql
-- Optimized indexes for memory queries
CREATE INDEX CONCURRENTLY idx_memories_user_recent ON memories(user_id, created_at DESC)
WHERE expires_at IS NULL OR expires_at > NOW();

CREATE INDEX CONCURRENTLY idx_memories_user_type ON memories(user_id, fact_type)
WHERE expires_at IS NULL OR expires_at > NOW();

CREATE INDEX CONCURRENTLY idx_memories_user_category ON memories(user_id, category)
WHERE expires_at IS NULL OR expires_at > NOW();

-- Partial index for active standing instructions
CREATE INDEX CONCURRENTLY idx_instructions_active ON standing_instructions(user_id, priority DESC)
WHERE is_active = true AND (expires_at IS NULL OR expires_at > NOW());

-- Text search index with GIN for fast full-text search
ALTER TABLE memories ADD COLUMN search_vector tsvector;
CREATE INDEX CONCURRENTLY idx_memories_search ON memories USING GIN(search_vector);

-- Trigger to automatically update search vector
CREATE OR REPLACE FUNCTION update_memory_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    COALESCE(NEW.fact, '') || ' ' ||
    COALESCE(NEW.category, '') || ' ' ||
    COALESCE(array_to_string(NEW.tags, ' '), '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_memory_search_vector
  BEFORE INSERT OR UPDATE ON memories
  FOR EACH ROW EXECUTE FUNCTION update_memory_search_vector();

-- Partitioning for large memory tables (future optimization)
CREATE TABLE memories_partitioned (
  LIKE memories INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE memories_2025_11 PARTITION OF memories_partitioned
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE memories_2025_12 PARTITION OF memories_partitioned
FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
```

---

## Security & Privacy

### Memory Privacy Controls

```typescript
// Privacy controls for sensitive memories
class MemoryPrivacyController {
  async storePrivateMemory(userId: string, memory: CreateMemoryRequest): Promise<Memory> {
    // Encrypt sensitive memories
    if (memory.is_private || this.containsSensitiveData(memory.fact)) {
      memory.fact = await this.encryptMemoryContent(memory.fact, userId);
      memory.is_encrypted = true;
    }

    const storedMemory = await this.memoryStore.create(memory);

    // Log access for compliance
    await this.auditLogger.log({
      user_id: userId,
      action: 'create_private_memory',
      resource_id: storedMemory.id,
      details: { fact_type: memory.fact_type, category: memory.category }
    });

    return storedMemory;
  }

  async accessPrivateMemory(userId: string, memoryId: string): Promise<Memory> {
    // Verify user has access to this memory
    const memory = await this.memoryStore.findById(memoryId);

    if (!memory || memory.user_id !== userId) {
      throw new UnauthorizedError('Access denied to memory');
    }

    // Decrypt if needed
    if (memory.is_encrypted) {
      memory.fact = await this.decryptMemoryContent(memory.fact, userId);
    }

    // Log access
    await this.auditLogger.log({
      user_id: userId,
      action: 'access_private_memory',
      resource_id: memoryId,
      details: { fact_type: memory.fact_type }
    });

    return memory;
  }

  private containsSensitiveData(fact: string): boolean {
    const sensitivePatterns = [
      /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/, // Credit card numbers
      /\b\d{3}-\d{2}-\d{4}\b/, // SSN
      /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email addresses
      /\b(?:\d{1,3}\.){3}\d{1,3}\b/, // IP addresses
      /password|secret|token|key|credential/i // Sensitive keywords
    ];

    return sensitivePatterns.some(pattern => pattern.test(fact));
  }
}

// Memory retention and expiration policies
class MemoryRetentionManager {
  async cleanupExpiredMemories(): Promise<void> {
    // Soft delete expired memories (keep for audit)
    const expiredMemories = await this.db.query(`
      UPDATE memories
      SET is_expired = true, expired_at = NOW()
      WHERE expires_at <= NOW() AND is_expired = false
      RETURNING id, user_id, fact
    `);

    // Log expiration for compliance
    for (const memory of expiredMemories.rows) {
      await this.auditLogger.log({
        user_id: memory.user_id,
        action: 'memory_expired',
        resource_id: memory.id,
        details: { fact_preview: memory.fact.substring(0, 100) }
      });
    }

    // Hard delete memories older than 1 year after expiration
    await this.db.query(`
      DELETE FROM memories
      WHERE expired_at <= NOW() - INTERVAL '1 year'
    `);
  }

  async applyMemoryLimits(userId: string): Promise<void> {
    // Check if user exceeds memory limits
    const memoryCount = await this.db.queryOne(`
      SELECT COUNT(*) as count FROM memories
      WHERE user_id = $1 AND is_expired = false
    `, [userId]);

    if (memoryCount.count > 10000) { // Configurable limit
      // Archive oldest memories
      await this.db.query(`
        UPDATE memories
        SET is_archived = true, archived_at = NOW()
        WHERE user_id = $1
          AND is_expired = false
          AND is_archived = false
        ORDER BY created_at ASC
        LIMIT ${memoryCount.count - 10000}
      `, [userId]);
    }
  }
}
```

### Consent and Data Management

```typescript
// User consent for memory storage
class MemoryConsentManager {
  async checkMemoryConsent(userId: string, fact: string, factType: MemoryType): Promise<boolean> {
    const consentSettings = await this.getUserConsentSettings(userId);

    // Check if user has opted out of this type of memory storage
    if (!consentSettings.allow_memory_extraction) {
      return false;
    }

    // Check fact-specific consent requirements
    if (factType === 'personal' && !consentSettings.allow_personal_memories) {
      return false;
    }

    // Check for sensitive content that requires explicit consent
    if (this.containsSensitiveContent(fact) && !consentSettings.allow_sensitive_memories) {
      return await this.requestExplicitConsent(userId, fact, factType);
    }

    return true;
  }

  async getUserMemoryRights(userId: string): Promise<MemoryRights> {
    return {
      can_export: true,
      can_delete: true,
      can_correct: true,
      can_limit_processing: await this.hasProcessingLimits(userId),
      data_retention_days: 365, // Configurable
      right_to_be_forgotten: true
    };
  }

  async exportUserData(userId: string): Promise<MemoryExport> {
    // Export all user memories in portable format
    const memories = await this.memoryStore.getAllByUser(userId);
    const instructions = await this.instructionStore.getAllByUser(userId);
    const categories = await this.categoryStore.getAllByUser(userId);

    return {
      export_date: new Date().toISOString(),
      user_id: userId,
      memories: memories.map(m => this.sanitizeMemoryForExport(m)),
      standing_instructions: instructions,
      categories: categories,
      format_version: '1.0'
    };
  }

  async deleteUserData(userId: string): Promise<void> {
    // GDPR "right to be forgotten" implementation
    await this.db.transaction(async (trx) => {
      // Soft delete first (for recovery)
      await trx('memories').where({ user_id: userId }).update({
        is_deleted: true,
        deleted_at: new Date()
      });

      await trx('standing_instructions').where({ user_id: userId }).update({
        is_deleted: true,
        deleted_at: new Date()
      });

      // Schedule hard deletion after 30 days
      await this.scheduleHardDeletion(userId, new Date(Date.now() + 30 * 24 * 60 * 60 * 1000));
    });

    // Remove from vector database
    await this.qdrantClient.delete('memories', {
      filter: {
        must: [
          { key: 'user_id', match: { value: userId } }
        ]
      }
    });
  }
}
```

---

## Testing Strategy

### Unit Tests

```typescript
// Memory extraction tests
describe('MemoryExtractor', () => {
  let extractor: MemoryExtractor;
  let mockLLMClient: jest.Mocked<LLMClient>;

  beforeEach(() => {
    mockLLMClient = createMockLLMClient();
    extractor = new MemoryExtractor(mockLLMClient);
  });

  describe('extractFactsWithLLM', () => {
    it('should extract facts from conversation correctly', async () => {
      const messages: Message[] = [
        { role: 'user', content: 'I need to prioritize defense contracts for Q4' },
        { role: 'assistant', content: 'I\'ll note that defense contracts are your priority for Q4.' }
      ];

      mockLLMClient.generate.mockResolvedValue({
        content: JSON.stringify({
          extracted_facts: [
            {
              fact: 'User prioritizes defense contracts for Q4',
              type: 'strategic',
              confidence: 0.9,
              evidence: 'I need to prioritize defense contracts for Q4',
              suggested_category: 'strategic-priorities'
            }
          ]
        })
      });

      const facts = await extractor.extractFactsWithLLM(messages);

      expect(facts).toHaveLength(1);
      expect(facts[0].fact).toBe('User prioritizes defense contracts for Q4');
      expect(facts[0].type).toBe('strategic');
      expect(facts[0].confidence).toBe(0.9);
    });

    it('should handle ambiguous facts with lower confidence', async () => {
      const messages: Message[] = [
        { role: 'user', content: 'Maybe we should think about expanding' }
      ];

      mockLLMClient.generate.mockResolvedValue({
        content: JSON.stringify({
          extracted_facts: [
            {
              fact: 'User considering expansion',
              type: 'strategic',
              confidence: 0.4,
              evidence: 'Maybe we should think about expanding',
              suggested_category: 'growth-strategy'
            }
          ]
        })
      });

      const facts = await extractor.extractFactsWithLLM(messages);

      expect(facts[0].confidence).toBe(0.4);
    });
  });
});

// Memory search tests
describe('MemorySearch', () => {
  let search: MemorySearch;
  let mockDB: jest.Mocked<Database>;
  let mockQdrant: jest.Mocked<QdrantClient>;

  beforeEach(() => {
    mockDB = createMockDatabase();
    mockQdrant = createMockQdrantClient();
    search = new MemorySearch(mockDB, mockQdrant);
  });

  describe('searchMemories', () => {
    it('should combine text and semantic search results', async () => {
      const userId = 'user-123';
      const query = 'defense contracts';

      // Mock text search results
      mockDB.query.mockResolvedValue({
        rows: [
          {
            id: 'mem-1',
            fact: 'Prioritize defense contracts',
            relevance_score: 0.8
          }
        ]
      });

      // Mock semantic search results
      mockQdrant.search.mockResolvedValue([
        {
          id: 'mem-2',
          payload: { fact: 'Government contract opportunities' },
          score: 0.7
        }
      ]);

      const results = await search.searchMemories(userId, query, { search_type: 'hybrid' });

      expect(results).toHaveLength(2);
      expect(results[0].match_type).toBe('exact');
      expect(results[1].match_type).toBe('semantic');
    });
  });
});
```

### Integration Tests

```typescript
// Memory injection integration tests
describe('Memory Injection Integration', () => {
  let app: Application;
  let testDB: TestDatabase;
  let testUser: User;

  beforeAll(async () => {
    testDB = await setupTestDatabase();
    app = await createTestApp({ database: testDB });
    testUser = await createTestUser(testDB);
  });

  afterAll(async () => {
    await testDB.cleanup();
  });

  describe('Chat with Memory Injection', () => {
    it('should inject memories into chat context', async () => {
      // Create test memories
      await testDB.query(`
        INSERT INTO memories (user_id, fact, fact_type, category) VALUES
        ($1, 'User prioritizes defense contracts', 'strategic', 'priorities'),
        ($1, 'Q4 target is December 15', 'project', 'deadlines')
      `, [testUser.id]);

      // Create standing instruction
      await testDB.query(`
        INSERT INTO standing_instructions (user_id, instruction, priority) VALUES
        ($1, 'Always cite sources for strategic decisions', 1)
      `, [testUser.id]);

      // Start chat with memory injection
      const response = await app.inject({
        method: 'POST',
        url: '/api/chat',
        payload: {
          message: 'What should I focus on for Q4?',
          inject_memory: true
        },
        headers: { authorization: `Bearer ${testUser.token}` }
      });

      const chatResponse = response.json();

      // Verify memories were injected
      expect(chatResponse.context.memories).toContain('User prioritizes defense contracts');
      expect(chatResponse.context.memories).toContain('Q4 target is December 15');
      expect(chatResponse.context.instructions).toContain('Always cite sources for strategic decisions');

      // Verify response uses memory context
      expect(chatResponse.response).toContain('defense contracts');
    });
  });
});

// Memory extraction integration tests
describe('Memory Extraction Integration', () => {
  let app: Application;
  let testDB: TestDatabase;
  let testUser: User;

  beforeAll(async () => {
    testDB = await setupTestDatabase();
    app = await createTestApp({ database: testDB });
    testUser = await createTestUser(testDB);
  });

  describe('Automatic Memory Extraction', () => {
    it('should extract and store facts from conversation', async () => {
      // Simulate conversation
      const conversationId = 'conv-123';
      await testDB.query(`
        INSERT INTO conversations (id, user_id, title) VALUES
        ($1, $2, 'Test Conversation')
      `, [conversationId, testUser.id]);

      await testDB.query(`
        INSERT INTO messages (conversation_id, role, content) VALUES
        ($1, 'user', 'I''ve decided to focus on enterprise clients going forward'),
        ($1, 'assistant', 'I''ll note that you''re focusing on enterprise clients.'),
        ($1, 'user', 'Yes, and our target is 10 enterprise deals by EOY')
      `, [conversationId]);

      // Trigger memory extraction
      await app.inject({
        method: 'POST',
        url: '/api/memory/extract',
        payload: { conversation_id: conversationId },
        headers: { authorization: `Bearer ${testUser.token}` }
      });

      // Wait for async processing
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Verify memories were extracted
      const memories = await testDB.query(`
        SELECT fact, fact_type, confidence FROM memories
        WHERE user_id = $1 AND source_type = 'extracted_from_chat'
      `, [testUser.id]);

      expect(memories.rows).toHaveLength(2);
      expect(memories.rows.some(m => m.fact.includes('enterprise clients'))).toBe(true);
      expect(memories.rows.some(m => m.fact.includes('10 enterprise deals'))).toBe(true);
    });
  });
});
```

### Performance Tests

```typescript
// Memory injection performance tests
describe('Memory Injection Performance', () => {
  let app: Application;
  let testDB: TestDatabase;
  let testUser: User;

  beforeAll(async () => {
    testDB = await setupTestDatabase();
    app = await createTestApp({ database: testDB });
    testUser = await createTestUser(testDB);

    // Create test data set
    await createTestMemorySet(testDB, testUser.id, 1000); // 1000 memories
    await createTestInstructions(testDB, testUser.id, 50); // 50 instructions
  });

  it('should inject memories within performance target', async () => {
    const startTime = Date.now();

    const response = await app.inject({
      method: 'POST',
      url: '/api/chat',
      payload: {
        message: 'What are my current priorities?',
        inject_memory: true
      },
      headers: { authorization: `Bearer ${testUser.token}` }
    });

    const injectionTime = Date.now() - startTime;

    // Performance target: <50ms for memory injection
    expect(injectionTime).toBeLessThan(50);

    const chatResponse = response.json();
    expect(chatResponse.context.memories).toBeDefined();
    expect(chatResponse.context.instructions).toBeDefined();
  });

  it('should handle concurrent memory requests', async () => {
    const concurrentRequests = 100;
    const startTime = Date.now();

    const promises = Array.from({ length: concurrentRequests }, () =>
      app.inject({
        method: 'GET',
        url: '/api/memory',
        headers: { authorization: `Bearer ${testUser.token}` }
      })
    );

    const responses = await Promise.all(promises);
    const totalTime = Date.now() - startTime;

    // All requests should succeed
    expect(responses.every(r => r.statusCode === 200)).toBe(true);

    // Average time per request should be reasonable
    const avgTime = totalTime / concurrentRequests;
    expect(avgTime).toBeLessThan(100); // 100ms average target
  });
});
```

---

## Monitoring & Analytics

### Memory Usage Metrics

```typescript
// Memory analytics and monitoring
class MemoryAnalytics {
  async generateMemoryReport(userId: string, timeframe: 'week' | 'month' | 'quarter'): Promise<MemoryReport> {
    const timeFilter = this.getTimeFilter(timeframe);

    const [
      summaryStats,
      growthTrend,
      categoryDistribution,
      usagePatterns,
      extractionAccuracy
    ] = await Promise.all([
      this.getSummaryStats(userId, timeFilter),
      this.getGrowthTrend(userId, timeFilter),
      this.getCategoryDistribution(userId, timeFilter),
      this.getUsagePatterns(userId, timeFilter),
      this.getExtractionAccuracy(userId, timeFilter)
    ]);

    return {
      user_id: userId,
      timeframe,
      generated_at: new Date().toISOString(),
      summary: summaryStats,
      growth: growthTrend,
      categories: categoryDistribution,
      usage: usagePatterns,
      accuracy: extractionAccuracy
    };
  }

  private async getSummaryStats(userId: string, timeFilter: TimeFilter): Promise<SummaryStats> {
    const sql = `
      SELECT
        COUNT(*) as total_memories,
        COUNT(CASE WHEN confidence >= 0.8 THEN 1 END) as high_confidence,
        COUNT(CASE WHEN fact_type = 'strategic' THEN 1 END) as strategic_memories,
        COUNT(CASE WHEN is_private = true THEN 1 END) as private_memories,
        AVG(confidence) as avg_confidence,
        COUNT(DISTINCT category) as unique_categories
      FROM memories
      WHERE user_id = $1
        AND created_at >= $2
        AND is_expired = false
    `;

    const result = await this.db.queryOne(sql, [userId, timeFilter.startDate]);
    return result;
  }

  private async getGrowthTrend(userId: string, timeFilter: TimeFilter): Promise<GrowthTrend> {
    const sql = `
      SELECT
        DATE_TRUNC('day', created_at) as date,
        COUNT(*) as new_memories,
        COUNT(CASE WHEN source_type = 'extracted_from_chat' THEN 1 END) as auto_extracted,
        COUNT(CASE WHEN source_type = 'manual' THEN 1 END) as manual_added
      FROM memories
      WHERE user_id = $1
        AND created_at >= $2
        AND created_at <= $3
        AND is_expired = false
      GROUP BY DATE_TRUNC('day', created_at)
      ORDER BY date ASC
    `;

    const results = await this.db.query(sql, [userId, timeFilter.startDate, timeFilter.endDate]);

    return {
      daily_growth: results.rows,
      total_growth: results.rows.reduce((sum, row) => sum + parseInt(row.new_memories), 0),
      auto_extraction_rate: results.rows.reduce((sum, row) => sum + parseInt(row.auto_extracted), 0) / results.rows.reduce((sum, row) => sum + parseInt(row.new_memories), 0)
    };
  }

  async trackMemoryEffectiveness(userId: string, memoryId: string, context: string): Promise<void> {
    // Track how well memories perform in different contexts
    const relevanceScore = await this.calculateMemoryRelevance(memoryId, context);

    await this.db.query(`
      INSERT INTO memory_effectiveness_logs (user_id, memory_id, context, relevance_score, created_at)
      VALUES ($1, $2, $3, $4, NOW())
    `, [userId, memoryId, context, relevanceScore]);
  }

  private async calculateMemoryRelevance(memoryId: string, context: string): Promise<number> {
    // Use semantic similarity to calculate relevance
    const memory = await this.memoryStore.findById(memoryId);
    const memoryEmbedding = await this.generateEmbedding(memory.fact);
    const contextEmbedding = await this.generateEmbedding(context);

    // Cosine similarity
    const similarity = this.cosineSimilarity(memoryEmbedding, contextEmbedding);
    return similarity;
  }
}

// Performance monitoring for memory operations
class MemoryPerformanceMonitor {
  async trackOperation(operation: string, userId: string, duration: number, success: boolean): Promise<void> {
    // Log performance metrics
    await this.metricsClient.record('memory_operation_duration', duration, {
      operation,
      success: success.toString(),
      user_id: userId
    });

    // Alert on performance issues
    if (duration > this.getPerformanceThreshold(operation)) {
      await this.alertManager.sendAlert({
        type: 'performance',
        operation,
        duration,
        user_id: userId,
        threshold: this.getPerformanceThreshold(operation)
      });
    }
  }

  private getPerformanceThreshold(operation: string): number {
    const thresholds = {
      'memory_injection': 50, // ms
      'memory_search': 200,   // ms
      'memory_extraction': 5000, // ms (async)
      'memory_store': 100     // ms
    };

    return thresholds[operation] || 1000;
  }

  async generatePerformanceReport(timeframe: 'hour' | 'day' | 'week'): Promise<PerformanceReport> {
    const metrics = await this.metricsClient.query(`
      SELECT
        operation,
        AVG(duration) as avg_duration,
        P95(duration) as p95_duration,
        COUNT(*) as total_operations,
        SUM(CASE WHEN success = 'true' THEN 1 ELSE 0 END)::float / COUNT(*) as success_rate
      FROM memory_metrics
      WHERE timestamp >= NOW() - INTERVAL '${timeframe}'
      GROUP BY operation
    `);

    return {
      timeframe,
      generated_at: new Date().toISOString(),
      operations: metrics,
      overall_health: this.calculateOverallHealth(metrics)
    };
  }
}
```

---

## Story Definitions

Based on the technical specification, Epic 4 is broken down into the following stories:

### Story 4-1: Memory Storage & Schema Implementation
**Story ID:** 4-1-memory-storage-schema
**Title:** Memory Storage & Schema Implementation
**Priority:** P0 (Foundation)
**Estimated Points:** 8
**Description:** Implement the database schema and basic storage functionality for user memories and standing instructions.
**Acceptance Criteria:**
- AC4.1.1: PostgreSQL tables created with proper indexes and constraints
- AC4.1.2: Memory model with fields for fact, type, confidence, source, expiration
- AC4.1.3: Standing instructions table with priority and conditional logic support
- AC4.1.4: Basic CRUD operations working for memories and instructions
- AC4.1.5: Database migrations implemented and tested
- AC4.1.6: Connection pooling and query optimization configured

### Story 4-2: Memory Injection System
**Story ID:** 4-2-memory-injection-system
**Title:** Memory Injection System
**Priority:** P0 (Core Feature)
**Estimated Points:** 13
**Description:** Build the memory injection system that loads relevant memories and standing instructions into LLM context at chat start.
**Acceptance Criteria:**
- AC4.2.1: Memory injector loads top-5 relevant memories based on conversation context
- AC4.2.2: Standing instructions automatically included in LLM system prompt
- AC4.2.3: Memory injection completes within 50ms performance target
- AC4.2.4: Memory relevance scoring algorithm implemented
- AC4.2.5: Integration with chat API working end-to-end
- AC4.2.6: Memory access logging for analytics

### Story 4-3: Qdrant Vector Integration
**Story ID:** 4-3-qdrant-vector-integration
**Title:** Qdrant Vector Integration
**Priority:** P1 (Enhancement)
**Estimated Points:** 8
**Description:** Integrate Qdrant vector database for semantic memory search and similarity-based retrieval.
**Acceptance Criteria:**
- AC4.3.1: Qdrant collection configured for memory embeddings
- AC4.3.2: Embedding generation service integrated with text-embedding-3-small
- AC4.3.3: Semantic search functionality working with cosine similarity
- AC4.3.4: Vector storage and retrieval operations optimized for performance
- AC4.3.5: Hybrid search (text + semantic) implemented
- AC4.3.6: Vector indexing and quantization configured for memory efficiency

### Story 4-4: Automatic Memory Extraction
**Story ID:** 4-4-automatic-memory-extraction
**Title:** Automatic Memory Extraction
**Priority:** P1 (Core Feature)
**Estimated Points:** 13
**Description:** Implement automatic fact extraction from conversations using LLM analysis with confidence scoring.
**Acceptance Criteria:**
- AC4.4.1: Async memory extraction jobs processed after each conversation
- AC4.4.2: LLM-based fact extraction with entity recognition
- AC4.4.3: Confidence scoring system (0.0-1.0) for extracted facts
- AC4.4.4: Automatic storage of high-confidence facts (≥0.8)
- AC4.4.5: User confirmation workflow for lower-confidence facts
- AC4.4.6: Fact validation to prevent contradictions and outdated information

### Story 4-5: Memory Management UI
**Story ID:** 4-5-memory-management-ui
**Title:** Memory Management UI
**Priority:** P1 (User Interface)
**Estimated Points:** 10
**Description:** Build the user interface for viewing, editing, and managing stored memories and standing instructions.
**Acceptance Criteria:**
- AC4.5.1: Memory dashboard with search, filtering, and categorization
- AC4.5.2: Memory editing interface with fact modification and deletion
- AC4.5.3: Standing instructions management with priority controls
- AC4.5.4: Memory category system with color coding and organization
- AC4.5.5: Memory analytics showing usage patterns and growth trends
- AC4.5.6: Responsive design working on desktop and tablet

### Story 4-6: Memory Search & Ranking
**Story ID:** 4-6-memory-search-ranking
**Title:** Memory Search & Ranking
**Priority:** P2 (Enhancement)
**Estimated Points:** 8
**Description:** Implement advanced memory search capabilities with relevance ranking and result filtering.
**Acceptance Criteria:**
- AC4.6.1: Full-text search across memory content and metadata
- AC4.6.2: Semantic similarity search using vector embeddings
- AC4.6.3: Hybrid search combining text and semantic results
- AC4.6.4: Search result relevance scoring and ranking
- AC4.6.5: Advanced filtering by type, category, date range
- AC4.6.6: Search performance optimized with caching and indexing

### Story 4-7: Memory Privacy & Security
**Story ID:** 4-7-memory-privacy-security
**Title:** Memory Privacy & Security
**Priority:** P1 (Security)
**Estimated Points:** 10
**Description:** Implement privacy controls, encryption, and user consent mechanisms for sensitive memory data.
**Acceptance Criteria:**
- AC4.7.1: Encryption for sensitive memories and private data
- AC4.7.2: User consent system for memory extraction and storage
- AC4.7.3: Memory access controls and permission checking
- AC4.7.4: Data retention policies and automatic expiration
- AC4.7.5: GDPR compliance with right to deletion and data export
- AC4.7.6: Audit logging for memory access and modifications

### Story 4-8: Memory Analytics & Insights
**Story ID:** 4-8-memory-analytics-insights
**Title:** Memory Analytics & Insights
**Priority:** P2 (Analytics)
**Estimated Points:** 5
**Description:** Build analytics system to track memory usage patterns, extraction accuracy, and system performance.
**Acceptance Criteria:**
- AC4.8.1: Memory growth trends and usage statistics dashboard
- AC4.8.2: Category distribution and fact type analytics
- AC4.8.3: Memory extraction accuracy tracking and reporting
- AC4.8.4: Performance metrics for memory operations
- AC4.8.5: Memory effectiveness tracking and optimization recommendations
- AC4.8.6: Export capabilities for analytics data

### Story 4-9: Memory Performance Optimization
**Story ID:** 4-9-memory-performance-optimization
**Title:** Memory Performance Optimization
**Priority:** P2 (Performance)
**Estimated Points:** 8
**Description:** Optimize memory system performance with caching, batch operations, and database tuning.
**Acceptance Criteria:**
- AC4.9.1: Redis caching layer for frequent memory access
- AC4.9.2: Batch memory operations for improved efficiency
- AC4.9.3: Database query optimization and indexing strategy
- AC4.9.4: Memory retrieval latency under 50ms for cached data
- AC4.9.5: Concurrent request handling and rate limiting
- AC4.9.6: Memory usage monitoring and alerting system

### Story 4-10: Memory Testing & Validation
**Story ID:** 4-10-memory-testing-validation
**Title:** Memory Testing & Validation
**Priority:** P2 (Quality)
**Estimated Points:** 5
**Description:** Comprehensive testing suite for memory functionality including unit, integration, and performance tests.
**Acceptance Criteria:**
- AC4.10.1: Unit tests for all memory extraction and storage logic
- AC4.10.2: Integration tests for memory injection and search
- AC4.10.3: Performance tests meeting all latency targets
- AC4.10.4: Security tests for privacy controls and data protection
- AC4.10.5: Load testing for concurrent memory operations
- AC4.10.6: Test coverage >90% for memory system code

---

## Dependencies & Integration Points

### Technical Dependencies

**Epic 1 (Foundation & Infrastructure)** - Must be complete
- PostgreSQL database with proper configuration
- Redis caching system operational
- Docker Compose orchestration working
- CI/CD pipeline for deployments

**Epic 2 (Chat Interface & Conversation Management)** - Must be complete
- Chat API endpoints implemented
- Message history and persistence working
- LLM integration via LiteLLM proxy
- Conversation management system

**Epic 3 (RAG Integration & Knowledge Retrieval)** - Must be complete
- Qdrant vector database operational
- Document search and retrieval working
- Citation system implemented
- Hybrid search functionality

### Integration Points

**LLM Integration**
- Memory injection into system prompts
- Conversation analysis for fact extraction
- Context window management for memory limits

**Database Integration**
- PostgreSQL for structured memory data
- Qdrant for semantic search and embeddings
- Redis for caching and session management

**API Integration**
- Memory management endpoints (/api/memory/*)
- Standing instructions endpoints (/api/instructions/*)
- Analytics and reporting endpoints

**Frontend Integration**
- Memory management UI components
- Search and filtering interfaces
- Analytics dashboards and reporting

---

## Risk Assessment & Mitigation

### Technical Risks

| Risk | Severity | Impact | Mitigation Strategy |
|------|----------|--------|-------------------|
| **Memory extraction accuracy** | High | Poor user experience if irrelevant facts extracted | Implement confidence scoring, user confirmation workflow, continuous model fine-tuning |
| **Performance degradation** | Medium | Slow chat responses if memory injection is slow | Implement caching, database optimization, performance monitoring |
| **Privacy concerns** | High | User data protection and regulatory compliance | Implement encryption, consent mechanisms, GDPR compliance features |
| **Storage costs growth** | Medium | Increasing database costs as memories accumulate | Implement retention policies, data archiving, efficient compression |
| **Qdrant vector scaling** | Medium | Performance issues with large vector collections | Implement vector quantization, proper indexing, monitoring |

### Operational Risks

| Risk | Severity | Impact | Mitigation Strategy |
|------|----------|--------|-------------------|
| **Memory corruption** | High | Loss of user data and trust | Implement regular backups, data validation, recovery procedures |
| **Context window overflow** | Medium | LLM context limits exceeded | Implement intelligent memory selection, context compression |
| **User memory overload** | Low | Too many memories reducing relevance | Implement memory limits, automatic archiving, relevance filtering |
| **Embedding model changes** | Low | Inconsistent semantic search | Version embeddings, migration strategies, model locking |

---

## Success Metrics & KPIs

### Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Memory injection latency** | <50ms | System monitoring, response time tracking |
| **Memory extraction accuracy** | >85% user approval | User feedback surveys, confirmation rates |
| **Memory recall accuracy** | 98% across sessions | Cross-session testing, automated validation |
| **Search response time** | <200ms | Performance monitoring, query analysis |
| **System uptime** | 99.5% | Infrastructure monitoring, alerting |

### User Experience Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Memory usage adoption** | >80% of active users | Analytics tracking, feature usage monitoring |
| **User satisfaction with memories** | >4.5/5 rating | User surveys, feedback collection |
| **Manual memory addition rate** | >5 memories per user per week | Analytics tracking, user behavior analysis |
| **Memory editing rate** | <20% of stored memories | Analytics tracking, correction monitoring |
| **Search success rate** | >90% of queries find relevant results | Search analytics, user satisfaction |

### Business Impact Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Conversation relevance improvement** | >40% more relevant responses | A/B testing, user feedback analysis |
| **User time savings** | >30 minutes per week | User surveys, time tracking studies |
| **Strategic decision quality** | Improved decision confidence | User feedback, outcome tracking |
| **Knowledge retention** | 90% of important facts retained | Memory analytics, usage pattern analysis |
| **User retention** | >95% monthly retention | User analytics, churn analysis |

---

## Implementation Timeline

### Sprint Planning

**Sprint 4-1: Foundation (Week 1)**
- Story 4-1: Memory Storage & Schema Implementation (8 points)
- Story 4-2: Memory Injection System (13 points)
- **Total:** 21 points

**Sprint 4-2: Core Features (Week 2)**
- Story 4-3: Qdrant Vector Integration (8 points)
- Story 4-4: Automatic Memory Extraction (13 points)
- Story 4-5: Memory Management UI (10 points)
- **Total:** 31 points

**Sprint 4-3: Enhancement & Polish (Week 3)**
- Story 4-6: Memory Search & Ranking (8 points)
- Story 4-7: Memory Privacy & Security (10 points)
- Story 4-8: Memory Analytics & Insights (5 points)
- **Total:** 23 points

**Sprint 4-4: Optimization & Testing (Week 4)**
- Story 4-9: Memory Performance Optimization (8 points)
- Story 4-10: Memory Testing & Validation (5 points)
- **Total:** 13 points

### Critical Path

1. **Database Schema** (Story 4-1) → Blocks all memory storage
2. **Memory Injection** (Story 4-2) → Blocks chat integration
3. **Vector Integration** (Story 4-3) → Blocks semantic search
4. **UI Implementation** (Story 4-5) → Blocks user interaction
5. **Testing & Validation** (Story 4-10) → Blocks release

### Milestone Targets

- **Week 1:** Basic memory storage and injection working
- **Week 2:** Complete memory pipeline with extraction and UI
- **Week 3:** Full feature set with privacy and analytics
- **Week 4:** Performance optimization and production readiness

---

## Conclusion

Epic 4 delivers the foundational memory and learning capabilities that make ONYX a truly intelligent and adaptive strategic partner. By implementing persistent memory, automatic learning, and context-aware responses, this epic transforms ONYX from a simple chat tool into a compounding knowledge asset that becomes more valuable with every interaction.

The technical specification provides a comprehensive roadmap for building a scalable, secure, and performant memory system that respects user privacy while delivering powerful personalization capabilities. With proper implementation of the defined stories, ONYX will be able to maintain context across sessions, learn user preferences, and provide increasingly relevant and insightful strategic guidance.

The success of Epic 4 is critical for the overall ONYX vision, as it enables the system to build lasting relationships with users and provide the persistent intelligence that differentiates it from generic AI assistants.

---

**Technical Specification Status:** ✅ **READY FOR IMPLEMENTATION**

**Estimated Implementation Time:** 4 weeks
**Total Story Points:** 90 points
**Critical Dependencies:** Epic 1, 2, 3 must be complete
**Risk Level:** Medium (mitigated with comprehensive testing and performance optimization)

---

*This technical specification provides the complete implementation guidance for Epic 4: Persistent Memory & Learning. All components are designed to work together seamlessly within the broader ONYX architecture while maintaining high standards for performance, security, and user experience.*