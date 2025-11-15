# Story 3-5: Hybrid Search (Semantic + Keyword)

**Story ID:** 3-5-hybrid-search-semantic-keyword
**Epic:** Epic 3 - Knowledge Retrieval (RAG)
**Status:** drafted
**Created:** 2025-11-15
**Story Points:** 13 (High complexity)
**Priority:** P0 (Critical for search quality)

---

## User Story

**As a** user of Manus Internal
**I want** hybrid search that combines semantic vector search with keyword BM25 search
**So that** I get the most relevant results from all company knowledge sources with optimal precision and recall

---

## Business Context

Hybrid search is a critical component of Manus Internal's RAG system that combines the strengths of two complementary search approaches:

1. **Semantic Vector Search (70% weight)**: Understands meaning, concepts, and context using embeddings
2. **Keyword BM25 Search (30% weight)**: Finds exact terms, names, and technical specifications

This hybrid approach delivers >95% relevance across diverse query types:
- **Semantic queries**: "What are our Q3 revenue targets?" → Finds related concepts even without exact keywords
- **Keyword queries**: "project-unicorn launch date" → Finds exact document references
- **Mixed queries**: "customer feedback on AI features" → Combines semantic understanding with keyword matching

The search system processes queries across all indexed knowledge sources:
- Google Drive documents (Story 3-2)
- Slack messages (Story 3-3)
- Local file uploads (Story 3-4)
- Qdrant vector database (Story 3-1)

**Performance Requirements:**
- Sub-200ms total retrieval latency (95th percentile)
- Parallel processing of semantic and keyword searches
- Intelligent result fusion and ranking
- Recency boosting for timely information

---

## Acceptance Criteria

### AC3.5.1: User Query Triggers Both Semantic and Keyword Search
- **Given:** User submits a search query via RAG service
- **When:** The search request is processed
- **Then:** Both semantic vector search AND keyword BM25 search are executed in parallel
- **And:** Query processing starts within 10ms of request receipt
- **And:** No sequential blocking between search approaches

### AC3.5.2: Semantic Search Returns Top-10 Candidates from Qdrant
- **Given:** User query is processed for semantic search
- **When:** Vector similarity search is executed against Qdrant
- **Then:** Returns top-10 most semantically similar documents
- **And:** Each result includes similarity score (0.0-1.0)
- **And:** Results sorted by semantic similarity in descending order
- **And:** Includes document metadata (title, source, created_date, permissions)

### AC3.5.3: Keyword Search Returns Top-10 Candidates from PostgreSQL/Elasticsearch
- **Given:** User query is processed for keyword search
- **When:** BM25 text search is executed against the keyword index
- **Then:** Returns top-10 most relevant documents by keyword matching
- **And:** Each result includes BM25 score
- **And:** Results sorted by BM25 score in descending order
- **And:** Includes document metadata (title, source, created_date, permissions)
- **And:** Supports phrase matching, stemming, and term frequency analysis

### AC3.5.4: Results Merged and Ranked by Combined Score (70% Semantic + 30% Keyword)
- **Given:** Top-10 results from both semantic and keyword searches are available
- **When:** Result fusion and ranking algorithm processes both result sets
- **Then:** Results are merged and re-ranked using weighted scoring:
  - Combined Score = (Semantic Score × 0.7) + (BM25 Score × 0.3)
- **And:** Duplicate results are intelligently merged (highest score kept)
- **And:** Final result set contains unique documents with combined scores
- **And:** Results sorted by combined score in descending order

### AC3.5.5: Top-5 Final Results Passed to LLM Context
- **Given:** Merged and ranked results are available
- **When:** Results are prepared for LLM context injection
- **Then:** Top-5 highest-scoring documents are selected
- **And:** Each document includes full text content and metadata
- **And:** Results are formatted for LLM consumption with source attribution
- **And:** Context includes relevance scores for transparency

### AC3.5.6: Total Retrieval Latency <200ms (95th Percentile)
- **Given:** User search query is submitted to RAG service
- **When:** Complete hybrid search pipeline executes
- **Then:** Total time from query receipt to final results is <200ms (95th percentile)
- **And:** Average latency <150ms across 1000 test queries
- **And:** Parallel processing reduces total time compared to sequential execution
- **And:** Performance monitoring tracks latency percentiles

### AC3.5.7: Recent Documents Boosted by 10% in Ranking
- **Given:** Documents have creation/update timestamps
- **When:** Results are ranked by combined scores
- **Then:** Documents created/updated within last 30 days receive 10% score boost
- **And:** Recency boost is applied after semantic/keyword fusion
- **And:** Boost factor is configurable (default: 1.10× for recent documents)
- **And:** Ensures timely information appears higher in results

---

## Technical Context

### Architecture Overview

```
User Query → RAG Service Hybrid Search Engine
                                      ↓
                    ┌─────────────────────────┬─────────────────────────┐
                    │                         │                         │
            Semantic Search        Keyword Search        Query Preprocessing
                    │                         │                         │
            Qdrant Vector DB      PostgreSQL/Elasticsearch      Tokenization
            (1536-dim vectors)           (BM25 Index)              Stemming
                    │                         │                         │
            Top-10 Results         Top-10 Results            Stop Words
                    │                         │                         │
                    └─────────────────────────┴─────────────────────────┘
                                      ↓
                              Result Fusion Engine
                                      ↓
                            Score: (Semantic × 0.7) + (BM25 × 0.3)
                                      ↓
                             Recency Boost (+10% for 30d)
                                      ↓
                              Top-5 Results → LLM Context
```

### Hybrid Search Algorithm

**Phase 1: Query Preprocessing**
```python
def preprocess_query(query: str) -> Dict:
    return {
        "original_query": query,
        "semantic_query": query,  # Direct use for embedding
        "keyword_query": preprocess_text(query),  # Tokenized, stemmed
        "query_length": len(query.split()),
        "query_type": classify_query_type(query)  # semantic, keyword, mixed
    }
```

**Phase 2: Parallel Search Execution**
```python
async def hybrid_search(query: str, limit: int = 10) -> Dict:
    # Execute both searches in parallel
    semantic_task = asyncio.create_task(semantic_search(query, limit))
    keyword_task = asyncio.create_task(keyword_search(query, limit))

    # Wait for both to complete
    semantic_results, keyword_results = await asyncio.gather(
        semantic_task, keyword_task
    )

    return fuse_results(semantic_results, keyword_results)
```

**Phase 3: Result Fusion**
```python
def fuse_results(semantic_results: List[Dict], keyword_results: List[Dict]) -> List[Dict]:
    merged = {}

    # Merge semantic results
    for result in semantic_results:
        doc_id = result["doc_id"]
        merged[doc_id] = {
            **result,
            "semantic_score": result["score"],
            "bm25_score": 0.0,
            "combined_score": result["score"] * 0.7
        }

    # Merge keyword results
    for result in keyword_results:
        doc_id = result["doc_id"]
        if doc_id in merged:
            # Update existing document
            merged[doc_id]["bm25_score"] = result["score"]
            merged[doc_id]["combined_score"] = (
                merged[doc_id]["semantic_score"] * 0.7 + result["score"] * 0.3
            )
        else:
            # Add new document
            merged[doc_id] = {
                **result,
                "semantic_score": 0.0,
                "bm25_score": result["score"],
                "combined_score": result["score"] * 0.3
            }

    # Apply recency boost
    results = apply_recency_boost(list(merged.values()))

    # Sort by combined score
    results.sort(key=lambda x: x["combined_score"], reverse=True)

    return results[:5]  # Return top 5 for LLM context
```

### Search Index Configuration

**Semantic Search (Qdrant)**
- Vector Size: 1536 dimensions (OpenAI text-embedding-3-small)
- Distance Metric: Cosine similarity
- Index Type: HNSW (Hierarchical Navigable Small World)
- Payload Filters: source_type, created_at, permissions

**Keyword Search (PostgreSQL/Elasticsearch)**
- Index Type: BM25 (Best Match 25)
- Text Fields: title, content, metadata
- Analyzer: English with stemming, stop words
- Phrase Matching: Enabled for exact phrases
- Boosting: Title field boosted 2×, recent documents 1.1×

### Performance Optimization

**Parallel Processing**
- Semantic and keyword searches execute concurrently
- Async/await pattern for non-blocking I/O
- Connection pooling for database queries
- Vector search optimized with HNSW indexing

**Latency Targets**
- Query preprocessing: <5ms
- Semantic search: <100ms (Qdrant)
- Keyword search: <50ms (PostgreSQL/Elasticsearch)
- Result fusion: <20ms
- **Total target: <200ms (95th percentile)**

**Caching Strategy**
- Vector embeddings cached for frequent queries
- Search results cached for 5 minutes
- BM25 index cached in memory
- Connection pools maintained for low-latency access

---

## Implementation Notes

### Prerequisites

**Required Components:**
1. **Qdrant Vector Database** (Story 3-1) - Operational with documents collection
2. **PostgreSQL/Elasticsearch** - Configured for full-text search with BM25
3. **Document Indexing** - All documents indexed in both systems:
   - Vectors in Qdrant (1536-dimensional embeddings)
   - Full-text in PostgreSQL/Elasticsearch with BM25 analysis

**Dependencies Status:**
- ✅ **Story 3-1**: Qdrant Vector Database Setup (Complete)
- ✅ **Story 3-2**: Google Drive Connector Auto-Sync (Complete)
- ✅ **Story 3-3**: Slack Connector Message Indexing (Complete)
- ✅ **Story 3-4**: Local File Upload & Parsing (Complete)

### Setup Steps

**1. Install Search Dependencies**
```bash
# Add to onyx-core/requirements.txt
asyncpg>=0.28.0           # PostgreSQL async driver
elasticsearch-async>=8.0.0 # Elasticsearch async client
scikit-learn>=1.3.0       # For BM25 implementation if needed
rank-bm25>=0.2.2          # Alternative BM25 library
```

**2. Configure Search Engines**
```python
# onyx-core/config/search_config.py
SEARCH_CONFIG = {
    "semantic": {
        "weight": 0.7,
        "vector_size": 1536,
        "top_k": 10,
        "timeout": 100  # ms
    },
    "keyword": {
        "weight": 0.3,
        "top_k": 10,
        "timeout": 50   # ms
    },
    "fusion": {
        "final_results": 5,
        "recency_days": 30,
        "recency_boost": 1.10
    }
}
```

**3. Implement Hybrid Search Service**
```python
# onyx-core/hybrid_search_service.py
class HybridSearchService:
    def __init__(self):
        self.qdrant_client = get_qdrant_client()
        self.keyword_client = get_keyword_client()  # PostgreSQL/Elasticsearch
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def search(self, query: str, user_permissions: List[str]) -> List[Dict]:
        """Execute hybrid search with result fusion."""
        start_time = time.time()

        # Preprocess query
        processed_query = self.preprocess_query(query)

        # Execute parallel searches
        semantic_results, keyword_results = await asyncio.gather(
            self.semantic_search(processed_query, user_permissions),
            self.keyword_search(processed_query, user_permissions)
        )

        # Fuse and rank results
        fused_results = self.fuse_results(semantic_results, keyword_results)

        # Log performance metrics
        latency = (time.time() - start_time) * 1000  # ms
        logger.info(f"Hybrid search completed in {latency:.2f}ms")

        return fused_results
```

### Database Schema Updates

**PostgreSQL Full-Text Search Setup**
```sql
-- Add full-text search capability
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create documents search index
CREATE TABLE documents_search (
    doc_id VARCHAR(255) PRIMARY KEY,
    title TEXT,
    content TEXT,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    permissions TEXT[]
);

-- Create GIN index for full-text search
CREATE INDEX documents_search_content_idx
ON documents_search USING gin(to_tsvector('english', content));

CREATE INDEX documents_search_title_idx
ON documents_search USING gin(to_tsvector('english', title));

-- BM25 function (if using pg_bm25 extension)
CREATE EXTENSION IF NOT EXISTS pg_bm25;
```

**Elasticsearch Alternative Setup**
```json
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "english",
        "boost": 2.0
      },
      "content": {
        "type": "text",
        "analyzer": "english"
      },
      "source_type": {
        "type": "keyword"
      },
      "created_at": {
        "type": "date"
      },
      "permissions": {
        "type": "keyword"
      }
    }
  },
  "settings": {
    "analysis": {
      "analyzer": {
        "english": {
          "type": "english",
          "stemmer": "english",
          "stopwords": "_english_"
        }
      }
    }
  }
}
```

---

## Testing Requirements

### Unit Tests

**Test: Hybrid Search Integration**
```python
async def test_hybrid_search_integration():
    """Verify both search engines are called and results fused correctly."""
    service = HybridSearchService()

    # Mock search engines
    with patch.object(service, 'semantic_search') as mock_semantic, \
         patch.object(service, 'keyword_search') as mock_keyword:

        # Configure mock returns
        mock_semantic.return_value = [
            {"doc_id": "doc1", "score": 0.9, "title": "AI Strategy"},
            {"doc_id": "doc2", "score": 0.8, "title": "Product Roadmap"}
        ]

        mock_keyword.return_value = [
            {"doc_id": "doc1", "score": 0.7, "title": "AI Strategy"},  # Duplicate
            {"doc_id": "doc3", "score": 0.6, "title": "Technical Specs"}
        ]

        # Execute search
        results = await service.search("AI product features", ["read"])

        # Verify parallel execution
        assert mock_semantic.called
        assert mock_keyword.called

        # Verify result fusion
        assert len(results) == 3  # doc1 (fused), doc2, doc3

        # Verify combined scores
        doc1_result = next(r for r in results if r["doc_id"] == "doc1")
        expected_score = (0.9 * 0.7) + (0.7 * 0.3)  # 0.84
        assert abs(doc1_result["combined_score"] - expected_score) < 0.01
```

**Test: Recency Boost**
```python
def test_recency_boost():
    """Verify recent documents receive 10% boost."""
    recent_date = datetime.now() - timedelta(days=15)  # Within 30 days
    old_date = datetime.now() - timedelta(days=60)     # Outside 30 days

    documents = [
        {"doc_id": "recent", "combined_score": 0.5, "created_at": recent_date},
        {"doc_id": "old", "combined_score": 0.6, "created_at": old_date}
    ]

    boosted = apply_recency_boost(documents)

    # Verify recent document boosted by 10%
    recent_doc = next(d for d in boosted if d["doc_id"] == "recent")
    assert recent_doc["combined_score"] == 0.55  # 0.5 * 1.10

    # Verify old document not boosted
    old_doc = next(d for d in boosted if d["doc_id"] == "old")
    assert old_doc["combined_score"] == 0.6     # No change
```

**Test: Latency Performance**
```python
async def test_search_latency():
    """Verify search completes within 200ms."""
    service = HybridSearchService()

    start_time = time.time()
    results = await service.search("test query", ["read"])
    latency = (time.time() - start_time) * 1000

    assert latency < 200, f"Search took {latency:.2f}ms, expected <200ms"
    assert len(results) <= 5, "Should return maximum 5 results"
```

### Integration Tests

**Test: End-to-End Search Pipeline**
```bash
#!/bin/bash
# tests/integration/test-hybrid-search.sh

echo "Testing Hybrid Search Integration..."

# 1. Verify Qdrant has vectors
curl -s "http://localhost:6333/collections/documents/points/count" \
  | jq '.result.count' > /tmp/vector_count

# 2. Verify PostgreSQL has documents
psql -h localhost -U postgres -d onyx -c "
  SELECT COUNT(*) FROM documents_search;" > /tmp/doc_count

# 3. Test search performance
START_TIME=$(date +%s%N)
curl -s -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "AI strategy", "permissions": ["read"]}' \
  > /tmp/search_result.json
END_TIME=$(date +%s%N)

LATENCY_MS=$(( (END_TIME - START_TIME) / 1000000 ))
echo "Search latency: ${LATENCY_MS}ms"

# 4. Verify result format
RESULT_COUNT=$(cat /tmp/search_result.json | jq '.results | length')
if [ "$RESULT_COUNT" -le 5 ]; then
    echo "✅ Result count correct: $RESULT_COUNT"
else
    echo "❌ Too many results: $RESULT_COUNT"
fi

# 5. Verify result has required fields
HAS_SCORES=$(cat /tmp/search_result.json | jq '.results[0] | has("combined_score")')
if [ "$HAS_SCORES" = "true" ]; then
    echo "✅ Results have combined scores"
else
    echo "❌ Results missing combined scores"
fi

echo "Integration test completed"
```

### Performance Benchmarks

**Benchmark: Hybrid Search Throughput**
```python
# scripts/benchmark-hybrid-search.py
async def benchmark_search_performance():
    """Measure search latency and throughput."""
    queries = generate_test_queries(1000)  # 1000 diverse queries

    latencies = []
    start_time = time.time()

    for query in queries:
        query_start = time.time()
        results = await search_service.search(query["text"], query["permissions"])
        latency = (time.time() - query_start) * 1000
        latencies.append(latency)

    total_time = time.time() - start_time

    # Calculate metrics
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    avg = np.mean(latencies)
    throughput = len(queries) / total_time

    print(f"Search Performance Results:")
    print(f"  Latency P50: {p50:.2f}ms")
    print(f"  Latency P95: {p95:.2f}ms")
    print(f"  Latency P99: {p99:.2f}ms")
    print(f"  Average Latency: {avg:.2f}ms")
    print(f"  Throughput: {throughput:.2f} queries/second")

    # Verify performance targets
    assert p95 < 200, f"P95 latency {p95:.2f}ms exceeds 200ms target"
    assert throughput > 5, f"Throughput {throughput:.2f} QPS below target"
```

---

## Dependencies

### Prerequisites
- **Story 3-1**: Qdrant Vector Database Setup (COMPLETED)
  - Vectors stored for all documents
  - Collection configured with 1536-dimensional vectors
- **Story 3-2**: Google Drive Connector Auto-Sync (COMPLETED)
  - All Google Drive documents indexed
  - Embeddings generated and stored
- **Story 3-3**: Slack Connector Message Indexing (COMPLETED)
  - All Slack messages indexed and embedded
- **Story 3-4**: Local File Upload & Parsing (COMPLETED)
  - Uploaded files processed and embedded

### External Dependencies
- **OpenAI API**: text-embedding-3-small for query embedding generation
- **PostgreSQL**: Full-text search with pg_trgm extension
  - Alternative: Elasticsearch with BM25 analyzer
- **Qdrant**: Vector search for semantic similarity
- **AsyncIO**: Python async framework for parallel execution

### Python Dependencies
```txt
# Add to onyx-core/requirements.txt
asyncpg>=0.28.0           # PostgreSQL async driver
elasticsearch-async>=8.0.0 # Elasticsearch async client (alternative)
rank-bm25>=0.2.2          # BM25 implementation
scikit-learn>=1.3.0       # Text preprocessing utilities
aiofiles>=23.0.0          # Async file operations
```

### Environment Variables Required
```bash
# .env
OPENAI_API_KEY=your-openai-api-key-here
POSTGRES_URL=postgresql://user:pass@localhost/onyx
ELASTICSEARCH_URL=http://localhost:9200  # Alternative to PostgreSQL
SEARCH_TIMEOUT_MS=200                     # Maximum search latency
SEMANTIC_WEIGHT=0.7                       # Semantic search weight
KEYWORD_WEIGHT=0.3                        # Keyword search weight
RECENCY_BOOST_DAYS=30                     # Days to consider as recent
RECENCY_BOOST_FACTOR=1.10                 # Boost factor for recent docs
```

### Database Schema Requirements
```sql
-- PostgreSQL documents_search table must exist
CREATE TABLE documents_search (
    doc_id VARCHAR(255) PRIMARY KEY,
    title TEXT,
    content TEXT,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    permissions TEXT[]
);

-- Full-text search indexes
CREATE INDEX documents_search_fts_idx
ON documents_search USING gin(to_tsvector('english', title || ' ' || content));
```

### Blocked By
None - All dependencies are completed

### Blocks
- **Story 3-6**: RAG Pipeline Integration (depends on hybrid search)
- **Future Stories**: All search-dependent features rely on hybrid search foundation

---

## Development Summary

**Implementation Date:** 2025-11-15
**Developer:** Claude Code (BMAD Orchestration)
**Status:** Drafted - Ready for Implementation

### Key Architectural Decisions

**1. Search Engine Selection: Qdrant + PostgreSQL**
- **Decision**: Use Qdrant for semantic search, PostgreSQL for keyword search
- **Rationale**:
  - Qdrant already operational from Story 3-1
  - PostgreSQL provides excellent BM25 implementation
  - Single database reduces operational complexity
  - Full-text search capabilities built-in with pg_trgm

**2. Weight Fusion: 70% Semantic + 30% Keyword**
- **Decision**: Prioritize semantic understanding while maintaining keyword precision
- **Rationale**:
  - Semantic search provides better understanding of user intent
  - Keyword search excels at exact matches (names, IDs, technical terms)
  - 70/30 balance based on industry best practices
  - Weighted by search type importance for business context

**3. Parallel Processing Architecture**
- **Decision**: Execute semantic and keyword searches concurrently using asyncio
- **Rationale**:
  - Reduces total latency compared to sequential execution
  - Both searches are independent and can run simultaneously
  - Async/await pattern efficient for I/O-bound operations
  - Scales well with increased query volume

**4. Recency Boosting Strategy**
- **Decision**: 10% boost for documents updated within last 30 days
- **Rationale**:
  - Recent information often more relevant for business decisions
  - 30-day window balances freshness with result stability
  - 10% boost improves ranking without overwhelming relevance signals
  - Configurable for different business contexts

### Implementation Components

#### 1. Hybrid Search Service (`onyx-core/hybrid_search_service.py`)
**Core Features:**
- Parallel execution of semantic and keyword searches
- Query preprocessing for optimal search performance
- Result fusion with weighted scoring
- Recency boosting for recent documents
- Permission-based filtering
- Performance monitoring and logging

#### 2. Search Configuration (`onyx-core/config/search_config.py`)
**Configuration:**
- Search weights and parameters
- Timeout settings for performance targets
- Recency boost configuration
- Index-specific settings
- Performance tuning parameters

#### 3. Database Schema Updates (`scripts/setup-hybrid-search.sql`)
**Schema:**
- PostgreSQL full-text search indexes
- Document search table setup
- BM25 analysis configuration
- Performance optimization indexes
- Permission filtering indexes

#### 4. Integration Tests (`tests/integration/test-hybrid-search.sh`)
**Test Coverage:**
- End-to-end search pipeline
- Performance latency validation
- Result format verification
- Permission-based filtering
- Error handling scenarios

#### 5. Performance Benchmarks (`scripts/benchmark-hybrid-search.py`)
**Metrics:**
- Search latency percentiles (P50, P95, P99)
- Query throughput (queries/second)
- Resource utilization monitoring
- Scalability testing with concurrent queries

### Performance Targets

**Latency Requirements:**
- Query preprocessing: <5ms
- Semantic search: <100ms (Qdrant)
- Keyword search: <50ms (PostgreSQL)
- Result fusion: <20ms
- **Total target: <200ms (95th percentile)**

**Throughput Requirements:**
- Single instance: 10+ queries/second
- Concurrent queries: 5 parallel searches
- Memory usage: <500MB per search service instance
- CPU usage: <50% average, <80% peak

**Quality Metrics:**
- Search relevance: >95% user satisfaction
- Result diversity: Covers multiple document types
- Recency boost effectiveness: Recent documents rank higher
- Permission filtering: 100% access control compliance

### Integration Points

**RAG Service Integration:**
- `rag_service.py` updated to use `HybridSearchService`
- Existing semantic search maintained as fallback
- Backward compatibility for current API
- Performance metrics integrated

**Document Pipeline Integration:**
- All indexing pipelines update both Qdrant and PostgreSQL
- Synchronization between vector and text indexes
- Consistent document IDs across search engines
- Real-time updates for new/modified documents

**API Layer Integration:**
- `/search` endpoint uses hybrid search by default
- Optional semantic-only or keyword-only search modes
- Search performance metrics exposed via `/health` endpoint
- Search debugging endpoints for development

---

## Definition of Done

- [ ] Hybrid search service implemented with parallel processing
- [ ] Semantic search integration with Qdrant operational
- [ ] Keyword search integration with PostgreSQL/Elasticsearch operational
- [ ] Result fusion algorithm implemented with 70/30 weighting
- [ ] Recency boosting (10% for 30-day window) implemented
- [ ] All acceptance criteria verified (AC3.5.1 - AC3.5.7)
- [ ] Performance benchmark confirms <200ms latency (95th percentile)
- [ ] Unit tests pass for search fusion and ranking logic
- [ ] Integration tests pass for end-to-end search pipeline
- [ ] Documentation updated:
  - [ ] README.md updated with hybrid search configuration
  - [ ] Environment variables documented in .env.example
  - [ ] API usage examples and search query formats
- [ ] Code reviewed and merged to main branch
- [ ] Manual verification checklist completed
- [ ] Sprint status updated to "done"

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Search latency exceeds 200ms** | Medium | Implement connection pooling, caching, and query optimization. Monitor performance metrics. |
| **Result fusion produces poor rankings** | Medium | A/B test different weight combinations, implement relevance scoring, gather user feedback. |
| **Index synchronization issues** | High | Implement transaction-based updates, consistency checks, and automated repair processes. |
| **Memory usage exceeds limits** | Medium | Optimize result processing, implement streaming for large result sets, monitor resource usage. |
| **Permission filtering bypassed** | High | Implement defense-in-depth with filters at both search and result levels, audit access logs. |

---

## Additional Notes

### Search Quality Considerations

**Query Type Classification:**
- Implement automatic classification of queries as semantic-dominant, keyword-dominant, or mixed
- Adjust search weights based on query type for better relevance
- Learn from user interactions to improve classification accuracy

**Relevance Scoring Enhancement:**
- Consider user engagement signals (clicks, time-on-page)
- Implement learning-to-rank for result optimization
- Add domain-specific boosting rules (e.g., prioritize source types)

**Performance Optimization:**
- Implement query result caching with LRU eviction
- Use connection pooling for database efficiency
- Consider search result pagination for large datasets
- Implement rate limiting for API protection

### Future Enhancements (Out of Scope for MVP)
- Advanced query expansion with synonyms
- Machine learning-based relevance ranking
- Multi-language search support
- Real-time search result streaming
- Search analytics and user behavior tracking
- Personalized search based on user history

### References
- [BM25 Algorithm Documentation](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Qdrant Search Documentation](https://qdrant.tech/documentation/)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [Elasticsearch BM25](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity-bm25.html)
- [Information Retrieval Best Practices](https://nlp.stanford.edu/IR-book/)

### Related Files
- `onyx-core/hybrid_search_service.py` - Main hybrid search implementation
- `onyx-core/config/search_config.py` - Search configuration and weights
- `onyx-core/rag_service.py` - RAG service integration
- `scripts/setup-hybrid-search.sql` - Database schema setup
- `tests/unit/test_hybrid_search.py` - Unit tests
- `tests/integration/test-hybrid-search.sh` - Integration tests
- `scripts/benchmark-hybrid-search.py` - Performance benchmarks

---

**Story Created:** 2025-11-15
**Last Updated:** 2025-11-15
**Author:** System Architect
**Reviewer:** TBD
**Status:** Drafted - Ready for Implementation