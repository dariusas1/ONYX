# Epic 4 Technical Specification: Persistent Memory & Learning

**Project:** ONYX - Manus Internal
**Epic ID:** epic-4
**Epic Name:** Persistent Memory & Learning
**Status:** 75% Complete (Core memory schema and standing instructions implemented)
**Missing Component:** Auto-summarization pipeline (Story 4.4)
**Author:** Claude Code (Technical Specification)
**Date:** 2025-11-15
**Version:** 1.0

---

## Executive Summary

Epic 4 enables Manus to learn from interactions, recall standing instructions, and improve over time through a sophisticated persistent memory system. The implementation provides cross-session context retention, automated knowledge extraction, and user-configurable behavioral directives.

**Current State:** Core memory schema and standing instructions system are operational. The auto-summarization pipeline (Story 4.4) represents the final 25% needed for completion.

**Technical Goal:** Achieve 98% memory recall accuracy across 5+ sessions with <50ms injection latency and seamless user experience.

---

## System Architecture Overview

### Memory System Components

```mermaid
graph TB
    A[Chat Session Start] --> B[Memory Injection Service]
    B --> C[Standing Instructions Query]
    B --> D[Top Memories Query]
    C --> E[LLM Context Assembly]
    D --> E
    E --> F[Chat Execution]
    F --> G[Message Processing]
    G --> H[Memory Extraction Service]
    H --> I[Store New Memory]
    G --> J[Auto-Summarization Trigger]
    J --> K[Every 10 Messages]
    K --> L[Summarization Pipeline]
    L --> M[Store Summary as Memory]

    N[Memory Management UI] --> O[CRUD Operations]
    O --> P[PostgreSQL Memory Tables]

    Q[Standing Instructions UI] --> R[Instruction CRUD]
    R --> S[Standing Instructions Table]
```

### Data Flow Architecture

1. **Injection Flow** (Pre-chat): Standing Instructions + Top-5 Memories → LLM Context
2. **Extraction Flow** (Post-message): Message Analysis → Memory Storage
3. **Summarization Flow** (Every 10 messages): Recent Messages → LLM Summary → Memory Storage
4. **Management Flow** (UI): Memory CRUD → PostgreSQL → Real-time Updates

---

## Database Schema Design

### Memory Tables (PostgreSQL)

```sql
-- User Memories (Extended from Story 4.1)
CREATE TABLE user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('priority', 'decision', 'context', 'preference', 'relationship', 'goal', 'summary')),
    confidence FLOAT NOT NULL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    source_type TEXT NOT NULL CHECK (source_type IN ('manual', 'extracted_from_chat', 'auto_summary', 'standing_instruction')),
    source_message_id UUID REFERENCES messages(id),
    conversation_id UUID REFERENCES conversations(id),
    metadata JSONB DEFAULT '{}',  -- Flexible storage for additional context
    expires_at TIMESTAMP,  -- NULL = permanent
    access_count INTEGER DEFAULT 0,  -- Track usage for pruning
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX idx_memories_user_category ON user_memories(user_id, category);
CREATE INDEX idx_memories_confidence ON user_memories(user_id, confidence DESC);
CREATE INDEX idx_memories_recency ON user_memories(user_id, created_at DESC);
CREATE INDEX idx_memories_expires ON user_memories(user_id, expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_memories_active ON user_memories(user_id, is_deleted) WHERE is_deleted = FALSE;

-- Standing Instructions (Enhanced from Story 4.3)
CREATE TABLE standing_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    instruction_text TEXT NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    category TEXT CHECK (category IN ('behavior', 'communication', 'decision', 'security', 'workflow')),
    enabled BOOLEAN DEFAULT TRUE,
    context_hints JSONB DEFAULT '{}',  -- When to apply this instruction
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_instructions_user_enabled ON standing_instructions(user_id, enabled);
CREATE INDEX idx_instructions_priority ON standing_instructions(user_id, priority DESC);

-- Memory Categories for UI Organization
CREATE TABLE memory_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_name TEXT NOT NULL,
    color_hex TEXT DEFAULT '#3b82f6',  -- UI display color
    icon TEXT DEFAULT 'brain',  -- Icon identifier
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, category_name)
);

-- Conversation Summaries (Auto-generated memories)
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    message_range_start INTEGER NOT NULL,
    message_range_end INTEGER NOT NULL,
    key_topics JSONB DEFAULT '[]',  -- Extracted topics
    sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_summaries_conversation ON conversation_summaries(conversation_id);
CREATE INDEX idx_summaries_user ON conversation_summaries(user_id, created_at DESC);
```

### Memory Injection Query Performance

```sql
-- Optimized query for top-5 memories (Stories 4.2 injection)
WITH ranked_memories AS (
    SELECT
        fact,
        category,
        confidence,
        source_type,
        created_at,
        -- Scoring algorithm combines confidence, recency, and usage
        (confidence * 0.5 +
         EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 * -0.001 +  -- Decay over time
         access_count * 0.01 +  -- Boost frequently accessed
         CASE WHEN source_type = 'auto_summary' THEN 0.2 ELSE 0 END  -- Boost summaries
        ) as memory_score
    FROM user_memories
    WHERE user_id = $1
        AND is_deleted = FALSE
        AND (expires_at IS NULL OR expires_at > NOW())
)
SELECT fact, category, confidence, source_type, created_at
FROM ranked_memories
ORDER BY memory_score DESC
LIMIT 5;

-- Standing instructions query (ordered by priority and recent usage)
SELECT instruction_text, priority, category, context_hints
FROM standing_instructions
WHERE user_id = $1 AND enabled = TRUE
ORDER BY
    priority DESC,
    CASE WHEN last_used_at > NOW() - INTERVAL '7 days' THEN 0 ELSE 1 END,
    created_at DESC;
```

---

## Auto-Summarization Pipeline (Story 4.4)

### Pipeline Architecture

```mermaid
graph LR
    A[Message #10/#20/etc] --> B[Summarization Trigger]
    B --> C[Conversation Context Fetch]
    C --> D[LLM Summarization Service]
    D --> E[Summary Processing]
    E --> F[Memory Storage]
    F --> G[Memory Score Calculation]
    G --> H[Background Job Queue]

    I[Error Handling] --> J[Retry Logic]
    J --> K[Dead Letter Queue]
```

### Implementation Specification

#### 1. Trigger Detection Service

```typescript
// services/summarization/trigger.ts
interface SummarizationTrigger {
    conversationId: string;
    messageId: string;
    messageCount: number;
    userId: string;
}

class SummarizationTriggerService {
    // Trigger every 10 messages
    private readonly TRIGGER_INTERVAL = 10;

    async shouldTrigger(conversationId: string): Promise<SummarizationTrigger | null> {
        const messageCount = await this.getMessageCount(conversationId);

        if (messageCount > 0 && messageCount % this.TRIGGER_INTERVAL === 0) {
            const latestMessage = await this.getLatestMessage(conversationId);
            return {
                conversationId,
                messageId: latestMessage.id,
                messageCount,
                userId: latestMessage.userId
            };
        }

        return null;
    }

    async processTrigger(trigger: SummarizationTrigger): Promise<void> {
        // Queue background job
        await bullQueue.add('summarize-conversation', trigger, {
            attempts: 3,
            backoff: 'exponential',
            delay: 1000 // 1 second delay to ensure message is fully processed
        });
    }
}
```

#### 2. Summarization Service

```typescript
// services/summarization/summarizer.ts
interface SummarizationRequest {
    conversationId: string;
    messageRange: {
        start: number;
        end: number;
    };
    userId: string;
}

interface SummarizationResult {
    summary: string;
    keyTopics: string[];
    sentiment: number;
    confidence: number;
    processingTime: number;
}

class ConversationSummarizer {
    async generateSummary(request: SummarizationRequest): Promise<SummarizationResult> {
        const startTime = Date.now();

        // Fetch conversation context
        const messages = await this.getMessagesInRange(
            request.conversationId,
            request.messageRange
        );

        if (messages.length === 0) {
            throw new Error('No messages found for summarization');
        }

        // Prepare context for LLM
        const conversationText = this.formatConversation(messages);

        // Generate summary using DeepSeek
        const summaryResult = await this.callLLMSummarization(conversationText);

        // Extract topics and sentiment
        const keyTopics = await this.extractTopics(summaryResult.summary);
        const sentiment = await this.analyzeSentiment(messages);

        const processingTime = Date.now() - startTime;

        return {
            summary: summaryResult.summary,
            keyTopics,
            sentiment,
            confidence: summaryResult.confidence,
            processingTime
        };
    }

    private async callLLMSummarization(conversationText: string): Promise<{
        summary: string;
        confidence: number;
    }> {
        const prompt = `
Summarize the following conversation in 2-3 sentences for future recall. Focus on:
1. Key decisions made
2. Important information shared
3. Action items or next steps
4. User preferences or context revealed

Conversation:
${conversationText}

Provide only the summary, no explanation.`;

        const response = await fetch('http://litellm-proxy:4000/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'deepseek-main',
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.3,  // Lower temperature for consistency
                max_tokens: 150    // Concise summaries
            })
        });

        const result = await response.json();
        const summary = result.choices[0].message.content.trim();

        return {
            summary,
            confidence: 0.9  // High confidence for auto-generated summaries
        };
    }

    private async extractTopics(summary: string): Promise<string[]> {
        // Use LLM to extract key topics
        const prompt = `Extract 3-5 key topics from this summary. Return as JSON array: ["topic1", "topic2", ...]\n\nSummary: ${summary}`;

        const response = await fetch('http://litellm-proxy:4000/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'deepseek-main',
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.1,
                max_tokens: 100
            })
        });

        const result = await response.json();
        try {
            return JSON.parse(result.choices[0].message.content);
        } catch {
            // Fallback: simple keyword extraction
            return this.simpleKeywordExtraction(summary);
        }
    }
}
```

#### 3. Memory Storage Service

```typescript
// services/summarization/storage.ts
class SummaryMemoryStorage {
    async storeSummary(
        userId: string,
        conversationId: string,
        summaryResult: SummarizationResult,
        messageRange: { start: number; end: number }
    ): Promise<string> {
        // Store in conversation_summaries table
        const summaryRecord = await db.query(`
            INSERT INTO conversation_summaries
            (conversation_id, user_id, summary_text, message_range_start, message_range_end, key_topics, sentiment_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        `, [
            conversationId,
            userId,
            summaryResult.summary,
            messageRange.start,
            messageRange.end,
            JSON.stringify(summaryResult.keyTopics),
            summaryResult.sentiment
        ]);

        // Also store as a memory for injection
        const memoryId = await db.query(`
            INSERT INTO user_memories
            (user_id, fact, category, confidence, source_type, source_message_id, conversation_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        `, [
            userId,
            summaryResult.summary,
            'summary',
            summaryResult.confidence,
            'auto_summary',
            null,  // No specific source message
            conversationId,
            JSON.stringify({
                topics: summaryResult.keyTopics,
                sentiment: summaryResult.sentiment,
                messageRange,
                processingTime: summaryResult.processingTime
            })
        ]);

        return memoryRecord.rows[0].id;
    }
}
```

#### 4. Background Job Processing

```typescript
// workers/summarization-worker.ts
import Bull from 'bull';

const summarizationQueue = new Bull('summarization', {
    redis: {
        host: 'redis',
        port: 6379
    }
});

summarizationQueue.process('summarize-conversation', async (job) => {
    const { conversationId, messageId, messageCount, userId } = job.data;

    try {
        // Calculate message range for summarization
        const messageRange = {
            start: messageCount - 9,  // Last 10 messages
            end: messageCount
        };

        // Generate summary
        const summarizer = new ConversationSummarizer();
        const summaryResult = await summarizer.generateSummary({
            conversationId,
            messageRange,
            userId
        });

        // Store summary as memory
        const storage = new SummaryMemoryStorage();
        await storage.storeSummary(userId, conversationId, summaryResult, messageRange);

        // Log success
        console.log(JSON.stringify({
            timestamp: new Date().toISOString(),
            level: 'info',
            service: 'summarization-worker',
            action: 'summary_completed',
            details: {
                conversationId,
                messageCount,
                summaryLength: summaryResult.summary.length,
                processingTime: summaryResult.processingTime
            }
        }));

    } catch (error) {
        // Log error and allow Bull to retry
        console.error(JSON.stringify({
            timestamp: new Date().toISOString(),
            level: 'error',
            service: 'summarization-worker',
            action: 'summary_failed',
            error: error.message,
            details: {
                conversationId,
                messageId,
                messageCount
            }
        }));

        throw error;  // Let Bull handle retry logic
    }
});

// Error handling and monitoring
summarizationQueue.on('failed', (job, err) => {
    // Implement dead letter queue for failed jobs after max retries
    if (job.opts.attempts >= job.opts.attemptsMade) {
        // Move to dead letter queue for manual inspection
        deadLetterQueue.add('failed-summary', {
            conversationId: job.data.conversationId,
            error: err.message,
            failedAt: new Date().toISOString()
        });
    }
});
```

### Performance Requirements

| Metric | Target | Implementation |
|--------|--------|----------------|
| Summarization Latency | <2 seconds | Background processing + optimized prompts |
| Memory Injection Time | <50ms | Pre-computed scoring + efficient queries |
| Storage Overhead | <10% of total messages | Compression + topic extraction |
| Accuracy | >90% relevance rating | Confidence scoring + user feedback loop |

---

## Memory Injection System (Story 4.2)

### Injection Pipeline

```typescript
// services/memory/injection.ts
interface MemoryInjection {
    userId: string;
    conversationId: string;
    standingInstructions: StandingInstruction[];
    memories: Memory[];
    injectionText: string;
}

class MemoryInjectionService {
    async prepareInjection(userId: string, conversationId: string): Promise<MemoryInjection> {
        // Parallel fetch of instructions and memories
        const [instructions, memories] = await Promise.all([
            this.getStandingInstructions(userId),
            this.getTopMemories(userId)
        ]);

        // Format for LLM injection
        const injectionText = this.formatForLLM(instructions, memories);

        return {
            userId,
            conversationId,
            standingInstructions: instructions,
            memories,
            injectionText
        };
    }

    private formatForLLM(
        instructions: StandingInstruction[],
        memories: Memory[]
    ): string {
        let injection = '';

        if (instructions.length > 0) {
            injection += 'STANDING INSTRUCTIONS:\n';
            instructions.forEach((inst, index) => {
                injection += `${index + 1}. ${inst.instruction_text}\n`;
            });
            injection += '\n';
        }

        if (memories.length > 0) {
            injection += 'USER CONTEXT (Key memories):\n';
            memories.forEach((memory, index) => {
                injection += `${index + 1}. ${memory.fact} (${this.formatAge(memory.created_at)})\n`;
            });
            injection += '\n';
        }

        return injection;
    }

    private formatAge(createdAt: Date): string {
        const hours = Math.floor((Date.now() - createdAt.getTime()) / (1000 * 60 * 60));
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }
}
```

### LLM Context Integration

```typescript
// services/chat/context-builder.ts
class ChatContextBuilder {
    async buildContext(
        userId: string,
        conversationId: string,
        currentMessage: string
    ): Promise<string> {
        // Get memory injection
        const memoryInjection = await this.memoryInjectionService.prepareInjection(
            userId,
            conversationId
        );

        // Get recent conversation context
        const recentContext = await this.getRecentConversationContext(conversationId, 5);

        // Build complete system prompt
        const systemPrompt = `
You are Manus, M3rcury's strategic intelligence advisor.

${memoryInjection.injectionText}

RECENT CONVERSATION CONTEXT:
${recentContext}

RESPONSE GUIDELINES:
- Use the standing instructions and memories above to provide personalized advice
- Always cite sources when referencing specific documents or data
- Think step-by-step and show your reasoning
- Focus on strategic implications and actionable recommendations
- Be concise but thorough

Current conversation continues below:
`;

        return systemPrompt;
    }
}
```

---

## Standing Instructions System (Story 4.3)

### UI Component Architecture

```typescript
// components/Settings/StandingInstructionsManager.tsx
interface StandingInstruction {
    id: string;
    instructionText: string;
    priority: number;
    category: string;
    enabled: boolean;
    contextHints: Record<string, any>;
    usageCount: number;
    lastUsed: Date | null;
}

const StandingInstructionsManager: React.FC = () => {
    const [instructions, setInstructions] = useState<StandingInstruction[]>([]);
    const [isAdding, setIsAdding] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);

    const categories = [
        { value: 'behavior', label: 'Behavior & Tone', icon: '🗣️' },
        { value: 'communication', label: 'Communication Style', icon: '💬' },
        { value: 'decision', label: 'Decision Making', icon: '⚖️' },
        { value: 'security', label: 'Security & Privacy', icon: '🔒' },
        { value: 'workflow', label: 'Workflow Preferences', icon: '⚙️' }
    ];

    return (
        <div className="standing-instructions-manager">
            <div className="header">
                <h2>Standing Instructions</h2>
                <p className="description">
                    Permanent directives that guide Manus behavior in all conversations
                </p>
                <button
                    onClick={() => setIsAdding(true)}
                    className="add-button"
                >
                    + Add Instruction
                </button>
            </div>

            <div className="instructions-list">
                {instructions.map(instruction => (
                    <InstructionCard
                        key={instruction.id}
                        instruction={instruction}
                        onEdit={setEditingId}
                        onUpdate={handleUpdate}
                        onToggle={handleToggle}
                        onDelete={handleDelete}
                    />
                ))}
            </div>

            {(isAdding || editingId) && (
                <InstructionModal
                    instruction={editingId ? instructions.find(i => i.id === editingId) : null}
                    categories={categories}
                    onSave={handleSave}
                    onCancel={() => {
                        setIsAdding(false);
                        setEditingId(null);
                    }}
                />
            )}
        </div>
    );
};
```

### Instruction Processing Service

```typescript
// services/instructions/processor.ts
class InstructionProcessor {
    async evaluateInstructions(
        userId: string,
        conversationContext: ConversationContext
    ): Promise<ActiveInstruction[]> {
        // Get all enabled instructions
        const instructions = await this.getEnabledInstructions(userId);

        // Evaluate context hints and filter relevant instructions
        const activeInstructions = instructions.filter(instruction => {
            return this.isInstructionRelevant(instruction, conversationContext);
        });

        // Update usage statistics
        await this.updateUsageStats(activeInstructions.map(i => i.id));

        return activeInstructions;
    }

    private isInstructionRelevant(
        instruction: StandingInstruction,
        context: ConversationContext
    ): boolean {
        const hints = instruction.context_hints;

        // Check category-specific relevance
        if (instruction.category === 'security' && context.involvesSensitiveData) {
            return true;
        }

        if (instruction.category === 'workflow' && context.isAgentMode) {
            return true;
        }

        // Check custom context hints
        if (hints.topics && hints.topics.length > 0) {
            const hasMatchingTopic = hints.topics.some((topic: string) =>
                context.messageContent.toLowerCase().includes(topic.toLowerCase())
            );
            if (!hasMatchingTopic) return false;
        }

        if (hints.minConfidence && context.confidence < hints.minConfidence) {
            return false;
        }

        return true;
    }
}
```

---

## Memory Management UI (Story 4.5)

### Memory Search and Organization

```typescript
// components/Memory/MemoryManager.tsx
const MemoryManager: React.FC = () => {
    const [memories, setMemories] = useState<Memory[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [sortBy, setSortBy] = useState<'recency' | 'confidence' | 'category'>('recency');
    const [editingMemory, setEditingMemory] = useState<string | null>(null);

    // Filter and sort memories
    const filteredMemories = useMemo(() => {
        let filtered = memories;

        // Apply search filter
        if (searchTerm) {
            filtered = filtered.filter(memory =>
                memory.fact.toLowerCase().includes(searchTerm.toLowerCase()) ||
                memory.category.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        // Apply category filter
        if (selectedCategory !== 'all') {
            filtered = filtered.filter(memory => memory.category === selectedCategory);
        }

        // Apply sorting
        return filtered.sort((a, b) => {
            switch (sortBy) {
                case 'recency':
                    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
                case 'confidence':
                    return b.confidence - a.confidence;
                case 'category':
                    return a.category.localeCompare(b.category);
                default:
                    return 0;
            }
        });
    }, [memories, searchTerm, selectedCategory, sortBy]);

    return (
        <div className="memory-manager">
            <div className="memory-header">
                <h2>My Memories</h2>
                <div className="memory-stats">
                    <span className="count">{memories.length} total memories</span>
                    <span className="categories">
                        {Object.entries(
                            memories.reduce((acc, m) => {
                                acc[m.category] = (acc[m.category] || 0) + 1;
                                return acc;
                            }, {} as Record<string, number>)
                        ).map(([cat, count]) => (
                            <span key={cat} className="category-stat">
                                {cat}: {count}
                            </span>
                        ))}
                    </span>
                </div>
            </div>

            <div className="memory-controls">
                <div className="search-filters">
                    <input
                        type="text"
                        placeholder="Search memories..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="search-input"
                    />

                    <select
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        className="category-filter"
                    >
                        <option value="all">All Categories</option>
                        <option value="priority">Priorities</option>
                        <option value="decision">Decisions</option>
                        <option value="context">Context</option>
                        <option value="preference">Preferences</option>
                        <option value="relationship">Relationships</option>
                        <option value="goal">Goals</option>
                        <option value="summary">Summaries</option>
                    </select>

                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as any)}
                        className="sort-select"
                    >
                        <option value="recency">Most Recent</option>
                        <option value="confidence">Highest Confidence</option>
                        <option value="category">By Category</option>
                    </select>
                </div>
            </div>

            <div className="memory-list">
                {filteredMemories.map(memory => (
                    <MemoryCard
                        key={memory.id}
                        memory={memory}
                        onEdit={setEditingMemory}
                        onDelete={handleDelete}
                        onUpdate={handleUpdate}
                    />
                ))}
            </div>

            {editingMemory && (
                <MemoryEditModal
                    memory={memories.find(m => m.id === editingMemory)}
                    onSave={handleSave}
                    onCancel={() => setEditingMemory(null)}
                />
            )}
        </div>
    );
};
```

### Memory CRUD API

```typescript
// app/api/memory/route.ts
export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const category = searchParams.get('category');
        const search = searchParams.get('search');
        const sort = searchParams.get('sort') || 'recency';

        const userId = await getCurrentUserId(req);

        let query = `
            SELECT
                id, fact, category, confidence, source_type,
                created_at, updated_at, access_count, metadata,
                expires_at
            FROM user_memories
            WHERE user_id = $1 AND is_deleted = FALSE
        `;

        const params: any[] = [userId];
        let paramIndex = 2;

        if (category && category !== 'all') {
            query += ` AND category = $${paramIndex++}`;
            params.push(category);
        }

        if (search) {
            query += ` AND fact ILIKE $${paramIndex++}`;
            params.push(`%${search}%`);
        }

        // Add sorting
        const sortMap = {
            recency: 'created_at DESC',
            confidence: 'confidence DESC',
            category: 'category ASC'
        };
        query += ` ORDER BY ${sortMap[sort as keyof typeof sortMap] || sortMap.recency}`;

        query += ' LIMIT 100';  // Pagination

        const result = await db.query(query, params);

        return Response.json({
            success: true,
            data: result.rows
        });

    } catch (error) {
        return errorHandler('MEMORY_FETCH_FAILED', error);
    }
}

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { fact, category, expiresAt } = body;

        validateInput({ fact, category });

        const userId = await getCurrentUserId(req);

        const result = await db.query(`
            INSERT INTO user_memories
            (user_id, fact, category, confidence, source_type, expires_at)
            VALUES ($1, $2, $3, 0.8, 'manual', $4)
            RETURNING *
        `, [userId, fact, category, expiresAt || null]);

        return Response.json({
            success: true,
            data: result.rows[0]
        });

    } catch (error) {
        return errorHandler('MEMORY_CREATE_FAILED', error);
    }
}
```

---

## Integration with Agent Modes

### Memory-Aware Agent Execution

```typescript
// services/agent/memory-aware-agent.ts
class MemoryAwareAgent {
    async executeTask(task: AgentTask, userId: string): Promise<AgentResult> {
        // 1. Load relevant memories for task context
        const taskMemories = await this.getTaskRelevantMemories(task, userId);

        // 2. Load standing instructions for agent behavior
        const agentInstructions = await this.getAgentInstructions(userId);

        // 3. Build enhanced system prompt
        const enhancedPrompt = this.buildAgentPrompt(task, taskMemories, agentInstructions);

        // 4. Execute with memory context
        const result = await this.executeWithMemory(task, enhancedPrompt);

        // 5. Extract and store new memories from execution
        await this.extractMemoriesFromExecution(result, userId, task.conversationId);

        return result;
    }

    private async getTaskRelevantMemories(task: AgentTask, userId: string): Promise<Memory[]> {
        // Use semantic search to find memories relevant to the task
        const relevantMemories = await this.semanticMemorySearch(task.description, userId);

        // Also fetch category-specific memories
        const categoryMemories = await this.getCategoryMemories(userId, [
            'priority', 'decision', 'goal'  // Categories most relevant to tasks
        ]);

        // Merge and deduplicate
        return this.mergeMemories(relevantMemories, categoryMemories).slice(0, 5);
    }

    private async getAgentInstructions(userId: string): Promise<StandingInstruction[]> {
        return await db.query(`
            SELECT instruction_text, priority, context_hints
            FROM standing_instructions
            WHERE user_id = $1 AND enabled = TRUE
                AND (category = 'workflow' OR category = 'decision' OR category = 'security')
            ORDER BY priority DESC
        `, [userId]);
    }
}
```

### Memory Extraction from Agent Actions

```typescript
// services/agent/memory-extractor.ts
class AgentMemoryExtractor {
    async extractMemories(
        taskResult: AgentResult,
        userId: string,
        conversationId: string
    ): Promise<void> {
        const extractedMemories: MemoryExtraction[] = [];

        // Extract from task description and results
        if (taskResult.type === 'create_document') {
            extractedMemories.push({
                fact: `Created document: ${taskResult.result.documentTitle}`,
                category: 'decision',
                confidence: 0.9,
                metadata: {
                    taskType: 'create_document',
                    documentId: taskResult.result.documentId
                }
            });
        }

        if (taskResult.type === 'search_web') {
            // Extract key findings from web search
            const keyFindings = await this.extractKeyFindings(taskResult.result);
            keyFindings.forEach(finding => {
                extractedMemories.push({
                    fact: finding,
                    category: 'context',
                    confidence: 0.7,
                    metadata: {
                        source: 'web_search',
                        query: taskResult.task.query
                    }
                });
            });
        }

        // Store extracted memories
        for (const memory of extractedMemories) {
            await this.storeExtractedMemory(userId, memory, conversationId);
        }
    }

    private async extractKeyFindings(searchResult: any): Promise<string[]> {
        // Use LLM to extract key factual information from search results
        const prompt = `
Extract 3-5 key factual findings from these search results that would be worth remembering for future conversations:

${JSON.stringify(searchResult.results, null, 2)}

Return as JSON array of short factual statements.`;

        const response = await fetch('http://litellm-proxy:4000/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'deepseek-main',
                messages: [{ role: 'user', content: prompt }],
                temperature: 0.2,
                max_tokens: 200
            })
        });

        const result = await response.json();
        try {
            return JSON.parse(result.choices[0].message.content);
        } catch {
            return [];
        }
    }
}
```

---

## Performance Optimization

### Memory Caching Strategy

```typescript
// services/memory/cache.ts
class MemoryCache {
    private cache = new Map<string, CachedMemory[]>();
    private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes

    async getCachedTopMemories(userId: string): Promise<CachedMemory[] | null> {
        const cached = this.cache.get(userId);
        if (cached && Date.now() - cached[0].timestamp < this.CACHE_TTL) {
            return cached;
        }
        return null;
    }

    async cacheTopMemories(userId: string, memories: Memory[]): Promise<void> {
        const cachedMemories: CachedMemory[] = memories.map(memory => ({
            ...memory,
            timestamp: Date.now()
        }));

        this.cache.set(userId, cachedMemories);

        // Schedule cache cleanup
        setTimeout(() => {
            this.invalidateCache(userId);
        }, this.CACHE_TTL);
    }

    invalidateCache(userId: string): void {
        this.cache.delete(userId);
    }

    // Pre-warm cache for active users
    async preWarmCache(userId: string): Promise<void> {
        const topMemories = await this.fetchTopMemories(userId);
        await this.cacheTopMemories(userId, topMemories);
    }
}
```

### Database Query Optimization

```sql
-- Materialized view for memory scoring (updated every hour)
CREATE MATERIALIZED VIEW memory_scores AS
SELECT
    id,
    user_id,
    fact,
    category,
    confidence,
    created_at,
    access_count,
    -- Pre-calculated memory score for faster ranking
    (confidence * 0.5 +
     EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 * -0.001 +
     access_count * 0.01 +
     CASE WHEN source_type = 'auto_summary' THEN 0.2 ELSE 0 END +
     CASE WHEN category = 'priority' THEN 0.1 ELSE 0 END +
     CASE WHEN category = 'decision' THEN 0.05 ELSE 0 END
    ) as memory_score
FROM user_memories
WHERE is_deleted = FALSE
    AND (expires_at IS NULL OR expires_at > NOW());

-- Index for quick top-5 retrieval
CREATE INDEX idx_memory_scores_user_ranked ON memory_scores(user_id, memory_score DESC);

-- Refresh function (called every hour)
CREATE OR REPLACE FUNCTION refresh_memory_scores()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_scores;
END;
$$ LANGUAGE plpgsql;
```

---

## Monitoring and Analytics

### Memory System Metrics

```typescript
// services/memory/analytics.ts
class MemoryAnalytics {
    async generateMemoryReport(userId: string): Promise<MemoryReport> {
        const [
            totalMemories,
            memoriesByCategory,
            memoriesBySource,
            avgConfidence,
            retentionStats,
            usageStats
        ] = await Promise.all([
            this.getTotalMemories(userId),
            this.getMemoriesByCategory(userId),
            this.getMemoriesBySource(userId),
            this.getAverageConfidence(userId),
            this.getRetentionStats(userId),
            this.getUsageStats(userId)
        ]);

        return {
            totalMemories,
            memoriesByCategory,
            memoriesBySource,
            averageConfidence: avgConfidence,
            retentionRate: retentionStats.retentionRate,
            averageAge: retentionStats.averageAge,
            mostUsedMemories: usageStats.topMemories,
            injectionAccuracy: usageStats.injectionAccuracy,
            lastUpdated: new Date()
        };
    }

    async trackMemoryInjection(
        userId: string,
        injectedMemories: string[],
        conversationId: string
    ): Promise<void> {
        // Track which memories were injected and their effectiveness
        for (const memoryId of injectedMemories) {
            await db.query(`
                INSERT INTO memory_injection_logs
                (user_id, memory_id, conversation_id, injected_at)
                VALUES ($1, $2, $3, NOW())
            `, [userId, memoryId, conversationId]);

            // Update access count
            await db.query(`
                UPDATE user_memories
                SET access_count = access_count + 1,
                    last_accessed_at = NOW()
                WHERE id = $1
            `, [memoryId]);
        }
    }

    async getMemoryEffectiveness(userId: string): Promise<MemoryEffectiveness[]> {
        return await db.query(`
            SELECT
                m.fact,
                m.category,
                COUNT(mil.id) as injection_count,
                AVG(c.sentiment_score) as avg_conversation_sentiment,
                AVG(c.messages_count) as avg_conversation_length
            FROM memories m
            LEFT JOIN memory_injection_logs mil ON m.id = mil.memory_id
            LEFT JOIN conversations c ON mil.conversation_id = c.id
            WHERE m.user_id = $1
                AND mil.injected_at > NOW() - INTERVAL '30 days'
            GROUP BY m.id, m.fact, m.category
            ORDER BY injection_count DESC, avg_conversation_sentiment DESC
            LIMIT 20
        `, [userId]);
    }
}
```

---

## Security and Privacy

### Memory Access Control

```typescript
// services/memory/security.ts
class MemorySecurity {
    async validateMemoryAccess(userId: string, memoryId: string): Promise<boolean> {
        const result = await db.query(`
            SELECT id FROM user_memories
            WHERE id = $1 AND user_id = $2 AND is_deleted = FALSE
        `, [memoryId, userId]);

        return result.rows.length > 0;
    }

    async sanitizeMemoryForExport(memory: Memory): Promise<SanitizedMemory> {
        // Remove sensitive metadata for export
        const { id, user_id, source_message_id, ...safeMemory } = memory;
        return safeMemory;
    }

    async detectSensitiveContent(fact: string): Promise<SensitivityLevel> {
        // Check for PII, sensitive business information
        const sensitivePatterns = [
            /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/, // Credit card numbers
            /\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b/, // SSN patterns
            /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email addresses
            /\b(?:secret|confidential|internal|proprietary)\b/i // Sensitive keywords
        ];

        const hasSensitiveContent = sensitivePatterns.some(pattern =>
            pattern.test(fact)
        );

        if (hasSensitiveContent) {
            return 'high';
        }

        // Check for business-sensitive terms
        const businessTerms = ['acquisition', 'merger', 'layoff', 'revenue', 'profit'];
        const hasBusinessTerms = businessTerms.some(term =>
            fact.toLowerCase().includes(term)
        );

        return hasBusinessTerms ? 'medium' : 'low';
    }
}
```

### Memory Retention Policies

```typescript
// services/memory/retention.ts
class MemoryRetention {
    async applyRetentionPolicies(userId: string): Promise<RetentionReport> {
        const report: RetentionReport = {
            expiredMemories: 0,
            lowValueMemories: 0,
            totalCleaned: 0
        };

        // 1. Remove expired memories
        const expiredResult = await db.query(`
            UPDATE user_memories
            SET is_deleted = TRUE
            WHERE user_id = $1
                AND expires_at IS NOT NULL
                AND expires_at <= NOW()
            RETURNING id
        `, [userId]);

        report.expiredMemories = expiredResult.rows.length;

        // 2. Remove low-value memories (below confidence threshold, rarely accessed)
        const lowValueResult = await db.query(`
            UPDATE user_memories
            SET is_deleted = TRUE
            WHERE user_id = $1
                AND confidence < 0.3
                AND access_count < 2
                AND created_at < NOW() - INTERVAL '90 days'
            RETURNING id
        `, [userId]);

        report.lowValueMemories = lowValueResult.rows.length;

        // 3. If user has >1000 memories, keep top 1000 by score
        const totalMemories = await db.query(`
            SELECT COUNT(*) as count FROM user_memories
            WHERE user_id = $1 AND is_deleted = FALSE
        `, [userId]);

        if (totalMemories.rows[0].count > 1000) {
            const excessCount = totalMemories.rows[0].count - 1000;

            const pruneResult = await db.query(`
                UPDATE user_memories
                SET is_deleted = TRUE
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id FROM user_memories
                        WHERE user_id = $1 AND is_deleted = FALSE
                        ORDER BY
                            confidence ASC,
                            access_count ASC,
                            created_at DESC
                        LIMIT $2
                    ) AS to_delete
                )
                RETURNING id
            `, [userId, excessCount]);

            report.totalCleaned += pruneResult.rows.length;
        }

        report.totalCleaned = report.expiredMemories + report.lowValueMemories;

        return report;
    }
}
```

---

## Error Handling and Resilience

### Memory System Error Recovery

```typescript
// services/memory/error-handler.ts
class MemoryErrorHandler {
    async handleMemoryInjectionFailure(
        userId: string,
        conversationId: string,
        error: Error
    ): Promise<InjectionFallback> {
        // Log error with context
        console.error(JSON.stringify({
            timestamp: new Date().toISOString(),
            level: 'error',
            service: 'memory-injection',
            action: 'memory_injection_failed',
            error: error.message,
            details: {
                userId,
                conversationId,
                stack: error.stack
            }
        }));

        // Implement fallback strategies
        const fallback: InjectionFallback = {
            success: false,
            strategy: 'minimal_context',
            message: 'Memory temporarily unavailable. Using minimal context.',
            injectedMemories: 0,
            injectedInstructions: 0
        };

        // Try to inject only standing instructions (simpler query)
        try {
            const instructionsOnly = await this.getStandingInstructionsOnly(userId);
            if (instructionsOnly.length > 0) {
                fallback.strategy = 'instructions_only';
                fallback.injectedInstructions = instructionsOnly.length;
                fallback.success = true;
            }
        } catch (instructionError) {
            // Complete fallback - no memory injection
            fallback.strategy = 'no_memory';
        }

        // Queue memory system for health check
        await this.queueHealthCheck(userId);

        return fallback;
    }

    async handleSummarizationFailure(
        conversationId: string,
        error: Error
    ): Promise<void> {
        // Log failure and create alert
        console.error(JSON.stringify({
            timestamp: new Date().toISOString(),
            level: 'error',
            service: 'summarization',
            action: 'summarization_failed',
            error: error.message,
            details: {
                conversationId,
                retryCount: error.retryCount || 0
            }
        }));

        // Add to monitoring dashboard
        await this.addToAlertDashboard({
            type: 'summarization_failure',
            severity: 'medium',
            conversationId,
            error: error.message,
            timestamp: new Date()
        });

        // Don't block chat - summarization is optional
        // Will retry on next message threshold
    }
}
```

---

## Testing Strategy

### Memory System Tests

```typescript
// tests/memory/memory-injection.test.ts
describe('Memory Injection System', () => {
    let testUserId: string;
    let testConversationId: string;

    beforeEach(async () => {
        testUserId = await createTestUser();
        testConversationId = await createTestConversation(testUserId);

        // Create test memories
        await createTestMemories(testUserId, [
            { fact: 'User prefers defense contracts', category: 'priority', confidence: 0.9 },
            { fact: 'Focus on AI infrastructure', category: 'goal', confidence: 0.8 },
            { fact: 'Recent decision to prioritize Onyx', category: 'decision', confidence: 0.95 }
        ]);
    });

    afterEach(async () => {
        await cleanupTestData(testUserId);
    });

    it('should inject top memories and standing instructions', async () => {
        const injection = await memoryInjectionService.prepareInjection(
            testUserId,
            testConversationId
        );

        expect(injection.memories).toHaveLength(3);
        expect(injection.memories[0].confidence).toBeGreaterThanOrEqual(
            injection.memories[1].confidence
        );
        expect(injection.injectionText).toContain('User prefers defense contracts');
    });

    it('should complete injection within performance target', async () => {
        const startTime = Date.now();

        await memoryInjectionService.prepareInjection(testUserId, testConversationId);

        const duration = Date.now() - startTime;
        expect(duration).toBeLessThan(50); // 50ms target
    });

    it('should handle expired memories correctly', async () => {
        // Create expired memory
        await createTestMemory(testUserId, {
            fact: 'Expired preference',
            category: 'preference',
            confidence: 0.7,
            expiresAt: new Date(Date.now() - 24 * 60 * 60 * 1000) // Yesterday
        });

        const injection = await memoryInjectionService.prepareInjection(
            testUserId,
            testConversationId
        );

        // Should not include expired memory
        expect(injection.memories.some(m => m.fact === 'Expired preference')).toBe(false);
    });
});
```

### Auto-Summarization Tests

```typescript
// tests/memory/summarization.test.ts
describe('Auto-Summarization Pipeline', () => {
    let testConversationId: string;

    beforeEach(async () => {
        testConversationId = await createTestConversation();

        // Create 10 test messages
        for (let i = 1; i <= 10; i++) {
            await createTestMessage(testConversationId, {
                role: i % 2 === 1 ? 'user' : 'assistant',
                content: `Test message ${i} with some content about decisions and priorities.`
            });
        }
    });

    it('should trigger summarization on 10th message', async () => {
        const trigger = await summarizationTriggerService.shouldTrigger(testConversationId);

        expect(trigger).not.toBeNull();
        expect(trigger.messageCount).toBe(10);
    });

    it('should generate meaningful summary', async () => {
        const summarizer = new ConversationSummarizer();
        const summary = await summarizer.generateSummary({
            conversationId: testConversationId,
            messageRange: { start: 1, end: 10 },
            userId: 'test-user'
        });

        expect(summary.summary).toBeDefined();
        expect(summary.summary.length).toBeGreaterThan(20);
        expect(summary.summary.length).toBeLessThan(300);
        expect(summary.keyTopics).toBeDefined();
        expect(summary.confidence).toBeGreaterThan(0.8);
    });

    it('should store summary as memory', async () => {
        const pipeline = new SummarizationPipeline();
        await pipeline.processSummarization(testConversationId, 'test-user');

        // Verify summary was stored
        const memories = await getTestUserMemories('test-user');
        const summaryMemories = memories.filter(m => m.source_type === 'auto_summary');

        expect(summaryMemories).toHaveLength(1);
        expect(summaryMemories[0].category).toBe('summary');
        expect(summaryMemories[0].confidence).toBe(0.9);
    });
});
```

---

## Deployment and Configuration

### Environment Variables

```bash
# Memory System Configuration
MEMORY_INJECTION_CACHE_TTL=300000          # 5 minutes in milliseconds
MEMORY_MAX_COUNT_PER_USER=1000              # Auto-prune threshold
MEMORY_CONFIDENCE_THRESHOLD=0.3            # Minimum confidence for retention
MEMORY_RETENTION_CLEANUP_INTERVAL=3600000   # 1 hour in milliseconds

# Summarization Configuration
SUMMARIZATION_TRIGGER_INTERVAL=10           # Messages between summaries
SUMMARIZATION_MAX_TOKENS=150                # Max tokens for summary
SUMMARIZATION_TEMPERATURE=0.3               # Low temperature for consistency
SUMMARIZATION_RETRY_ATTEMPTS=3              # Max retry attempts
SUMMARIZATION_RETRY_DELAY=1000              # Initial retry delay in ms

# Background Job Configuration
BULLMQ_REDIS_URL=redis://redis:6379
SUMMARIZATION_JOB_CONCURRENCY=2              # Max concurrent summary jobs
MEMORY_CLEANUP_JOB_CRON=0 2 * * *          # Daily at 2 AM UTC

# Monitoring and Analytics
MEMORY_ANALYTICS_RETENTION_DAYS=90          # Keep analytics data for 90 days
MEMORY_PERFORMANCE_LOGGING=true             # Enable detailed performance logging
```

### Docker Compose Updates

```yaml
# Add to existing docker-compose.yaml
services:
  # Memory system health check service
  memory-health:
    image: manus/memory-health:latest
    environment:
      - DATABASE_URL=postgresql://manus:${POSTGRES_PASSWORD}@postgres:5432/manus
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    command: ["npm", "run", "health-check"]
    restart: unless-stopped

  # Memory cleanup job (cron)
  memory-cleanup:
    image: manus/memory-cleanup:latest
    environment:
      - DATABASE_URL=postgresql://manus:${POSTGRES_PASSWORD}@postgres:5432/manus
      - MEMORY_MAX_COUNT_PER_USER=${MEMORY_MAX_COUNT_PER_USER}
    depends_on:
      - postgres
    command: ["npm", "run", "cleanup-job"]
    restart: unless-stopped
```

---

## Success Metrics and KPIs

### Performance Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|---------|
| Memory Injection Latency | <50ms | TBD | 🔄 In Development |
| Memory Recall Accuracy | 98% | TBD | 🔄 In Development |
| Auto-Summarization Success Rate | 95% | TBD | ❌ Not Implemented |
| Memory Storage Query Time | <100ms | TBD | 🔄 In Development |
| Standing Instructions Application | 100% | TBD | 🔄 In Development |

### Quality Metrics

- **Memory Relevance Score**: User feedback on memory usefulness (target: >4.5/5)
- **Summary Accuracy**: LLM evaluation of summary quality (target: >90%)
- **Duplicate Detection**: Automatic duplicate memory prevention (target: 95% detection)
- **Privacy Compliance**: Zero PII in stored memories (target: 100% compliance)

### User Experience Metrics

- **Memory Management UI Usage**: Track how often users manage their memories
- **Search Effectiveness**: Success rate of memory searches
- **Instruction Effectiveness**: How often standing instructions are applied correctly
- **Overall Satisfaction**: User satisfaction with memory system

---

## Migration and Rollout Plan

### Phase 1: Complete Auto-Summarization (Story 4.4) - **CRITICAL PATH**

1. **Week 1**: Implement summarization pipeline and background jobs
2. **Week 1**: Test with existing conversation data
3. **Week 1**: Deploy to production with feature flag

### Phase 2: Enhanced Memory Management

1. **Week 2**: Implement advanced memory search and categorization
2. **Week 2**: Add memory analytics and reporting
3. **Week 2**: Deploy UI improvements

### Phase 3: Agent Integration

1. **Week 3**: Integrate memory system with Agent Mode
2. **Week 3**: Implement memory extraction from agent actions
3. **Week 3**: Add memory-aware task planning

### Phase 4: Optimization and Monitoring

1. **Week 4**: Implement performance optimizations
2. **Week 4**: Add comprehensive monitoring and alerting
3. **Week 4**: Complete system integration testing

---

## Conclusion

This technical specification provides a comprehensive blueprint for completing Epic 4's persistent memory and learning system. The auto-summarization pipeline (Story 4.4) represents the critical final component needed to achieve the 98% memory recall target.

**Key Success Factors:**
1. **Performance**: Sub-50ms injection latency through intelligent caching
2. **Accuracy**: High-quality summaries and memory extraction
3. **User Control**: Intuitive memory management UI with search and categorization
4. **Integration**: Seamless operation with Agent Mode and chat functionality
5. **Privacy**: Robust security and data retention policies

The system is designed to scale with user needs while maintaining performance and privacy standards. Upon implementation, this will provide Manus with true persistent learning capabilities, enabling increasingly personalized and effective strategic advisory services.

---

**Next Steps:**
1. Implement auto-summarization pipeline (Story 4.4)
2. Update sprint status to mark Epic 4 as 'contexted'
3. Begin Phase 1 development with prioritized focus on summarization
4. Set up monitoring and success metrics tracking

**Status:** Ready for implementation with comprehensive technical specification complete.