# Story 3.5: Hybrid Search (Semantic + Keyword)

## Story Metadata

- **Story ID**: 3-5-hybrid-search-semantic-keyword
- **Title**: Hybrid Search (Semantic + Keyword)
- **Epic**: Epic 3 (RAG Integration & Knowledge Retrieval)
- **Priority**: P0 (Critical)
- **Estimated Points**: 13
- **Status**: drafted
- **Sprint**: Sprint 3-5
- **Assigned To**: TBD
- **Created Date**: 2025-11-14
- **Dependencies**: 3-1-qdrant-vector-database-setup, 3-2-google-drive-connector-auto-sync, 3-3-slack-connector-message-indexing, 3-4-local-file-upload-parsing

## Description

Implement hybrid search combining semantic vector search (70%) with keyword BM25 search (30%) for optimal relevance, with parallel processing, result fusion, recency boosting, and sub-200ms latency performance. This search system will provide users with the most relevant results from their entire knowledge base by leveraging both semantic understanding and exact keyword matching, ensuring comprehensive and accurate information retrieval.

## Acceptance Criteria

### AC3.5.1: Dual Search Execution
- **Requirement**: User query triggers both semantic (vector) and keyword (BM25) search
- **Evidence**: Query processing initiates parallel search threads
- **Test**: Verify both search engines are called for every query

### AC3.5.2: Semantic Search Results
- **Requirement**: Semantic search returns top-10 candidates from Qdrant
- **Evidence**: Qdrant search API returns ranked document list with similarity scores
- **Test**: Confirm vector search returns 10 results with cosine similarity scores

### AC3.5.3: Keyword Search Results
- **Requirement**: Keyword search returns top-10 candidates from PostgreSQL/Elasticsearch
- **Evidence**: BM25 search returns ranked document list with relevance scores
- **Test**: Confirm keyword search returns 10 results with BM25 scores

### AC3.5.4: Result Fusion and Ranking
- **Requirement**: Results merged and ranked by combined score (70% semantic + 30% keyword)
- **Evidence**: Final ranking uses weighted scoring algorithm
- **Test**: Verify score calculation and final ranking order

### AC3.5.5: Top-K Selection
- **Requirement**: Top-5 final results passed to LLM context
- **Evidence**: Search API response contains exactly 5 ranked documents
- **Test**: Confirm result limiting and content selection

### AC3.5.6: Performance Requirements
- **Requirement**: Total retrieval latency <200ms (95th percentile)
- **Evidence**: Performance monitoring shows p95 latency under 200ms
- **Test**: Load testing with 100+ concurrent queries

### AC3.5.7: Recency Boosting
- **Requirement**: Recent documents boosted by 10% in ranking
- **Evidence**: Documents <7 days old receive score bonus
- **Test**: Verify recency boosting algorithm application

## Technical Requirements

### Search Architecture
- **Parallel Processing**: Semantic and keyword searches execute concurrently
- **Vector Embeddings**: OpenAI text-embedding-3-small model (1536 dimensions)
- **Keyword Search**: BM25 algorithm using PostgreSQL full-text search
- **Score Fusion**: Configurable weighting (70% semantic, 30% keyword)

### Performance Targets
- **Embedding Generation**: <100ms
- **Vector Search**: <50ms
- **Keyword Search**: <30ms
- **Result Fusion**: <20ms
- **Total Latency**: <200ms (95th percentile)

### Query Processing
- **Preprocessing**: Query normalization and keyword extraction
- **Permission Filtering**: Results filtered by user access permissions
- **Caching**: Search results cached for 5 minutes (TTL)
- **Monitoring**: Comprehensive latency and performance metrics

### Ranking Algorithm
- **Base Score**: `(semantic_score * 0.7) + (keyword_score * 0.3)`
- **Recency Boost**: Documents <7 days: +10%, <30 days: +5%
- **Deduplication**: Remove duplicate documents by ID
- **Final Sort**: By boosted score descending

## Technical Implementation

### Core Components

#### 1. Hybrid Search Service
```typescript
class HybridSearchService {
  private vectorSearch: VectorSearchService;
  private keywordSearch: KeywordSearchService;
  private resultFusion: ResultFusionService;

  async search(query: SearchQuery): Promise<SearchResults>;
  async parallelSearch(query: string): Promise<ParallelResults>;
  async fuseResults(results: ParallelResults): Promise<FusedResults>;
}
```

#### 2. Vector Search Service
```typescript
class VectorSearchService {
  async generateEmbedding(query: string): Promise<VectorEmbedding>;
  async searchVectors(embedding: VectorEmbedding): Promise<VectorResults>;
  async filterByPermissions(results: VectorResults, user: User): Promise<VectorResults>;
}
```

#### 3. Keyword Search Service
```typescript
class KeywordSearchService {
  async extractKeywords(query: string): Promise<string[]>;
  async bm25Search(keywords: string[]): Promise<KeywordResults>;
  async filterByPermissions(results: KeywordResults, user: User): Promise<KeywordResults>;
}
```

#### 4. Result Fusion Service
```typescript
class ResultFusionService {
  async deduplicateResults(vectorResults: VectorResults, keywordResults: KeywordResults): Promise<DeduplicatedResults>;
  async calculateScores(results: DeduplicatedResults): Promise<ScoredResults>;
  async applyRecencyBoost(results: ScoredResults): Promise<BoostedResults>;
  async selectTopK(results: BoostedResults, k: number): Promise<FinalResults>;
}
```

### Search Flow Algorithm

#### 1. Query Processing
```typescript
async function processQuery(query: string, user: User): Promise<ProcessedQuery> {
  // Normalize query
  const normalizedQuery = normalizeQuery(query);

  // Generate embedding for semantic search
  const embedding = await generateEmbedding(normalizedQuery);

  // Extract keywords for BM25 search
  const keywords = await extractKeywords(normalizedQuery);

  return {
    original: query,
    normalized: normalizedQuery,
    embedding: embedding,
    keywords: keywords,
    user: user
  };
}
```

#### 2. Parallel Search Execution
```typescript
async function executeParallelSearch(processedQuery: ProcessedQuery): Promise<ParallelResults> {
  // Execute searches in parallel
  const [vectorResults, keywordResults] = await Promise.all([
    vectorSearch(processedQuery.embedding, processedQuery.user),
    keywordSearch(processedQuery.keywords, processedQuery.user)
  ]);

  return {
    vectorResults: vectorResults,
    keywordResults: keywordResults
  };
}
```

#### 3. Result Fusion Algorithm
```typescript
async function fuseResults(parallelResults: ParallelResults): Promise<FusedResults> {
  // Step 1: Deduplicate by document ID
  const deduplicated = deduplicateByDocumentId(parallelResults);

  // Step 2: Calculate combined scores
  const scored = deduplicated.map(doc => ({
    ...doc,
    combinedScore: (doc.semanticScore * 0.7) + (doc.keywordScore * 0.3)
  }));

  // Step 3: Apply recency boosting
  const boosted = applyRecencyBoost(scored);

  // Step 4: Sort by final score
  const sorted = boosted.sort((a, b) => b.finalScore - a.finalScore);

  // Step 5: Select top-k results
  return sorted.slice(0, 5);
}

function applyRecencyBoost(documents: ScoredDocument[]): ScoredDocument[] {
  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  return documents.map(doc => {
    let boost = 0;
    if (doc.createdAt >= sevenDaysAgo) {
      boost = 0.10; // +10%
    } else if (doc.createdAt >= thirtyDaysAgo) {
      boost = 0.05; // +5%
    }

    return {
      ...doc,
      finalScore: doc.combinedScore * (1 + boost)
    };
  });
}
```

### Database Schema

#### Search Query Logs
```sql
CREATE TABLE search_query_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  query_text TEXT NOT NULL,
  embedding_vector VECTOR(1536),
  keywords TEXT[],
  vector_latency_ms INTEGER,
  keyword_latency_ms INTEGER,
  fusion_latency_ms INTEGER,
  total_latency_ms INTEGER,
  results_count INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  INDEX idx_search_logs_user_timestamp (user_id, created_at),
  INDEX idx_search_logs_latency (total_latency_ms)
);
```

#### Search Results Cache
```sql
CREATE TABLE search_results_cache (
  query_hash TEXT PRIMARY KEY,
  query_text TEXT NOT NULL,
  user_id UUID REFERENCES users(id),
  results JSONB NOT NULL,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  hit_count INTEGER DEFAULT 0,

  INDEX idx_cache_expires (expires_at),
  INDEX idx_cache_user (user_id)
);
```

### API Endpoints

#### Search API
```typescript
// POST /api/search
interface SearchRequest {
  query: string;
  top_k?: number; // default: 5
  filters?: {
    source_types?: string[]; // ['google_drive', 'slack', 'upload']
    date_range?: {
      start: string;
      end: string;
    };
    file_types?: string[];
  };
  include_citations?: boolean; // default: true
}

interface SearchResponse {
  results: SearchResult[];
  query_id: string;
  latency_ms: number;
  cached: boolean;
  total_available: number;
}

interface SearchResult {
  doc_id: string;
  title: string;
  content_snippet: string;
  source_type: string;
  source_url: string;
  relevance_score: number;
  created_at: string;
  citation?: {
    text: string;
    link: string;
  };
}
```

#### Configuration API
```typescript
// GET /api/search/config
interface SearchConfig {
  weights: {
    semantic: number; // default: 0.7
    keyword: number; // default: 0.3
  };
  recency_boosts: {
    seven_days: number; // default: 0.10
    thirty_days: number; // default: 0.05
  };
  limits: {
    max_results: number; // default: 5
    cache_ttl_minutes: number; // default: 5
  };
  performance_targets: {
    max_latency_ms: number; // default: 200
    embedding_timeout_ms: number; // default: 100
  };
}
```

### Performance Optimization

#### Caching Strategy
```typescript
class SearchCache {
  async get(queryHash: string): Promise<CachedResults | null>;
  async set(queryHash: string, results: SearchResults, ttl: number): Promise<void>;
  async invalidate(pattern: string): Promise<void>;
  async getMetrics(): Promise<CacheMetrics>;
}

// Cache key generation
function generateCacheKey(query: string, filters: SearchFilters, userId: string): string {
  const keyData = { query, filters, userId };
  return crypto.createHash('md5').update(JSON.stringify(keyData)).digest('hex');
}
```

#### Performance Monitoring
```typescript
class SearchMetrics {
  async recordLatency(operation: string, duration: number): Promise<void>;
  async recordCacheHit(hit: boolean): Promise<void>;
  async recordResultsCount(count: number): Promise<void>;
  async getPerformanceReport(timeRange: TimeRange): Promise<PerformanceReport>;
}
```

### Configuration

#### Environment Variables
```env
# Search Configuration
SEARCH_SEMANTIC_WEIGHT=0.7
SEARCH_KEYWORD_WEIGHT=0.3
SEARCH_MAX_RESULTS=5
SEARCH_CACHE_TTL=300000  # 5 minutes in milliseconds

# Performance Targets
SEARCH_MAX_LATENCY_MS=200
SEARCH_EMBEDDING_TIMEOUT_MS=100
SEARCH_VECTOR_TIMEOUT_MS=50
SEARCH_KEYWORD_TIMEOUT_MS=30

# OpenAI Configuration
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MAX_RETRIES=3

# Qdrant Configuration
QDRANT_COLLECTION_NAME=documents
QDRANT_SEARCH_LIMIT=10
QDRANT_SIMILARITY_THRESHOLD=0.1

# PostgreSQL Configuration
POSTGRES_FULLTEXT_SEARCH=enabled
POSTGRES_SEARCH_LIMIT=10
POSTGRES_MIN_WORD_LENGTH=3
```

## Implementation Tasks

### Phase 1: Foundation Services (4 points)
- [ ] Implement HybridSearchService with query processing
- [ ] Create VectorSearchService with OpenAI embedding integration
- [ ] Build KeywordSearchService with PostgreSQL BM25
- [ ] Set up performance monitoring and caching infrastructure

### Phase 2: Parallel Search & Fusion (4 points)
- [ ] Implement parallel search execution with async/await
- [ ] Create result deduplication and score fusion algorithms
- [ ] Build recency boosting system with configurable weights
- [ ] Add permission-based result filtering

### Phase 3: API & Performance (3 points)
- [ ] Implement REST API endpoints with request/response models
- [ ] Add comprehensive error handling and validation
- [ ] Create search result caching with TTL management
- [ ] Implement performance optimization and monitoring

### Phase 4: Testing & Integration (2 points)
- [ ] Create unit tests for all search components
- [ ] Build integration tests with real data scenarios
- [ ] Add performance benchmarks and load testing
- [ ] Implement end-to-end testing with citation generation

## Dependencies

### Internal Dependencies
- **3-1-qdrant-vector-database-setup**: Vector database for semantic search (completed)
- **3-2-google-drive-connector-auto-sync**: Document source for search (completed)
- **3-3-slack-connector-message-indexing**: Message source for search (drafted)
- **3-4-local-file-upload-parsing**: File upload source for search (drafted)
- **Epic 1**: Foundation infrastructure (PostgreSQL, caching, monitoring)

### External Dependencies
- **OpenAI API**: Embedding generation for semantic search
- **Qdrant**: Vector database for similarity search
- **PostgreSQL**: Full-text search for keyword matching
- **Redis**: Search result caching (optional)

## Risk Assessment

### Technical Risks
- **Latency Degradation**: Complex fusion algorithm may impact performance
- **Score Tuning**: 70/30 weighting may not produce optimal relevance
- **Vector Database Performance**: Qdrant performance at scale
- **Cache Invalidation**: Stale cached results for updated documents

### Mitigation Strategies
- **Performance Monitoring**: Real-time latency tracking and alerting
- **Configurable Weights**: Allow runtime adjustment of search parameters
- **Query Optimization**: Efficient database queries and indexing
- **Smart Caching**: Cache invalidation on document updates

## Success Metrics

### Functional Metrics
- **Search Relevance**: >95% user satisfaction with result quality
- **Result Coverage**: Search across all indexed document sources
- **Permission Accuracy**: 0% unauthorized document access
- **Citation Quality**: 100% of results include accurate source citations

### Performance Metrics
- **Search Latency**: p95 <200ms, p50 <100ms
- **Throughput**: 100+ concurrent search queries
- **Cache Hit Rate**: >30% for repeated queries
- **Index Freshness**: New documents searchable within 5 minutes

### Quality Metrics
- **Result Accuracy**: >90% relevant results in top-5
- **Duplicate Elimination**: 0% duplicate documents in results
- **Recency Boosting**: Recent documents appropriately promoted
- **Error Rate**: <1% failed search requests

## Testing Strategy

### Unit Tests
- **Search Services**: Individual component logic and algorithms
- **Score Calculation**: Fusion algorithm and recency boosting
- **Query Processing**: Normalization and keyword extraction
- **Cache Management**: Cache hit/miss and TTL handling

### Integration Tests
- **End-to-End Search**: Complete search workflow with real data
- **Vector Database**: Qdrant integration and performance
- **Full-Text Search**: PostgreSQL BM25 search functionality
- **API Endpoints**: Request/response handling and validation

### Performance Tests
- **Latency Benchmarks**: Search latency under various loads
- **Concurrent Queries**: 100+ simultaneous search requests
- **Cache Performance**: Hit rates and cache invalidation
- **Stress Testing**: System behavior under peak load

### Quality Tests
- **Relevance Evaluation**: Manual assessment of search result quality
- **Permission Testing**: Access control and privacy enforcement
- **Citation Accuracy**: Source attribution and link validation
- **Result Ranking**: Score calculation and ordering correctness

## Monitoring & Observability

### Key Metrics
- **Search Latency**: p50, p95, p99 response times
- **Query Volume**: Search requests per minute/hour
- **Cache Performance**: Hit rates and cache miss latency
- **Result Quality**: User feedback and relevance scores

### Alerting
- **High Latency**: Alert if p95 latency >300ms
- **Search Failures**: Alert if error rate >1%
- **Cache Issues**: Alert if cache hit rate <20%
- **Vector Database**: Alert if Qdrant performance degrades

### Logging
- **Search Queries**: Query text, user, and results
- **Performance Metrics**: Component-level latency breakdown
- **Cache Operations**: Cache hits, misses, and invalidations
- **Error Details**: Comprehensive error information

## Rollout Plan

### Phase 1: Development (Week 1-2)
- Implement core search services and algorithms
- Create unit tests and development environment
- Set up performance monitoring infrastructure

### Phase 2: Testing (Week 3)
- Integration testing with real document corpus
- Performance optimization and benchmarking
- Quality assessment with test queries

### Phase 3: Deployment (Week 4)
- Deploy to staging environment
- Production configuration and monitoring setup
- Gradual rollout with feature flags

### Phase 4: Production (Week 5)
- Full production deployment
- Monitor performance and user feedback
- Optimize weights and algorithms based on usage

## Definition of Done

### Code Requirements
- [ ] All acceptance criteria met and tested
- [ ] Code review completed and approved
- [ ] Documentation updated and complete
- [ ] Security review passed

### Testing Requirements
- [ ] Unit test coverage >90%
- [ ] Integration tests covering all search workflows
- [ ] Performance tests meeting latency targets
- [ ] Quality tests confirming result relevance

### Operational Requirements
- [ ] Monitoring and alerting configured
- [ ] Performance baseline established
- [ ] Cache management procedures documented
- [ ] Search tuning guidelines created

### Deployment Requirements
- [ ] Production deployment successful
- [ ] Health checks passing
- [ ] Performance targets validated
- [ ] User acceptance testing passed

## Notes

### Important Considerations
- **Performance First**: Sub-200ms latency is critical for user experience
- **Relevance Quality**: Continuous monitoring and tuning of search weights
- **Privacy Enforcement**: Strict permission filtering for all search results
- **Scalability**: Design for growth in document volume and query load

### Future Enhancements
- **Advanced Ranking**: Machine learning reranking models
- **Query Expansion**: Automatic query enhancement and synonyms
- **Personalization**: User-specific search result ranking
- **Analytics**: Search behavior analysis and optimization insights

### Dependencies
This story is part of Epic 3 (RAG Integration & Knowledge Retrieval) and depends on:
- **3-1-qdrant-vector-database-setup** (completed)
- **3-2-google-drive-connector-auto-sync** (completed)
- **3-3-slack-connector-message-indexing** (drafted)
- **3-4-local-file-upload-parsing** (drafted)

The hybrid search system will provide users with the most relevant results from their entire knowledge base, combining the strengths of semantic understanding and exact keyword matching to deliver comprehensive and accurate information retrieval.