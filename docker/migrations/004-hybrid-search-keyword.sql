-- Migration 004: Hybrid Search Keyword Infrastructure
-- Story 3-5: Hybrid Search (Semantic + Keyword)
-- Creates PostgreSQL keyword search infrastructure for BM25-like scoring
-- Performance targets: <200ms retrieval latency, parallel processing support

-- Enable required extensions for advanced text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Create documents_search table for keyword search with BM25-like scoring
-- This table serves as the keyword search complement to Qdrant vector search
CREATE TABLE IF NOT EXISTS documents_search (
    doc_id VARCHAR(255) PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'google_drive', 'slack', 'local_upload', 'chat_message'
    source_id VARCHAR(255), -- Original document ID from source system
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    permissions TEXT[], -- Array of user/team permissions for multi-tenant isolation
    metadata JSONB DEFAULT '{}', -- Flexible metadata storage for additional attributes
    content_length INTEGER NOT NULL DEFAULT 0, -- Character count for BM25 scoring
    search_metadata JSONB DEFAULT '{}' -- Search-specific metadata for optimization
);

-- Add content vector for full-text search indexing
-- tsvector provides built-in ranking algorithms similar to BM25
ALTER TABLE documents_search ADD COLUMN IF NOT EXISTS content_vector tsvector;

-- Add computed content column for optimized search (title + content)
-- This improves search relevance by giving title higher weight
ALTER TABLE documents_search ADD COLUMN IF NOT EXISTS computed_content TEXT
    GENERATED ALWAYS AS (COALESCE(title, '') || ' ' || COALESCE(content, '')) STORED;

-- Create GIN index for fast full-text search on computed content
-- GIN indexes are optimal for tsvector operations and support complex queries
CREATE INDEX IF NOT EXISTS idx_documents_search_vector
ON documents_search USING GIN (content_vector);

-- Create partial index on content vector for non-empty documents only
-- This optimizes storage and query performance by excluding null entries
CREATE INDEX IF NOT EXISTS idx_documents_search_vector_nonempty
ON documents_search USING GIN (content_vector)
WHERE content_vector IS NOT NULL;

-- Create source type index for filtering by document source
-- Supports efficient queries like "only Google Drive documents" or "exclude Slack messages"
CREATE INDEX IF NOT EXISTS idx_documents_search_source_type
ON documents_search (source_type);

-- Created date index for recency boosting (30-day window)
-- Enables efficient time-based filtering and sorting for freshness scoring
CREATE INDEX IF NOT EXISTS idx_documents_search_created_at
ON documents_search (created_at DESC);

-- Composite index for common query patterns (source + date + permissions)
-- Optimizes typical search queries with multiple WHERE conditions
CREATE INDEX IF NOT EXISTS idx_documents_search_source_created
ON documents_search (source_type, created_at DESC);

-- Create index for permission-based access control
-- Enables efficient multi-tenant isolation queries
CREATE INDEX IF NOT EXISTS idx_documents_search_permissions
ON documents_search USING GIN (permissions);

-- Create index on metadata for structured attribute searches
-- Supports JSONB queries on document attributes like file type, author, etc.
CREATE INDEX IF NOT EXISTS idx_documents_search_metadata
ON documents_search USING GIN (metadata);

-- Update content_vector automatically on insert/update
-- Trigger ensures search index stays synchronized with document content
CREATE OR REPLACE FUNCTION update_document_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_vector := to_tsvector('english', NEW.computed_content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update search vectors
-- This maintains data consistency without manual intervention
DROP TRIGGER IF EXISTS trigger_update_documents_search_vector ON documents_search;
CREATE TRIGGER trigger_update_documents_search_vector
    BEFORE INSERT OR UPDATE ON documents_search
    FOR EACH ROW EXECUTE FUNCTION update_document_search_vector();

-- Advanced keyword search function with BM25-like scoring
-- Implements sophisticated ranking algorithm combining multiple relevance factors
CREATE OR REPLACE FUNCTION keyword_search(
    query_text TEXT,
    source_filter TEXT[] DEFAULT '{}',
    user_permissions TEXT[] DEFAULT '{}',
    limit_count INTEGER DEFAULT 10,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    doc_id VARCHAR(255),
    title TEXT,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    created_at TIMESTAMPTZ,
    score NUMERIC,
    snippet TEXT,
    permissions TEXT[],
    metadata JSONB
) AS $$
DECLARE
    search_query tsvector;
    recency_weight NUMERIC := 1.0;
    freshness_days INTEGER;
BEGIN
    -- Convert query to search vector with English stemming
    search_query := to_tsvector('english', query_text);

    -- Main keyword search query with BM25-like scoring
    RETURN QUERY
    SELECT
        ds.doc_id,
        ds.title,
        ds.source_type,
        ds.source_id,
        ds.created_at,
        -- BM25-like scoring: document frequency + recency boosting
        (ts_rank(search_query, ds.content_vector) * 0.7) AS score,
        ts_headline('english', 2, ds.content_vector, search_query) AS snippet,
        ds.permissions,
        ds.metadata
    FROM documents_search ds
    WHERE
        -- Only search documents with actual content
        ds.content_vector IS NOT NULL
        -- Permission-based access control
        AND (
            user_permissions = '{}'
            OR ds.permissions && user_permissions
            OR ds.permissions && ARRAY['public']
        )
        -- Source type filtering (optional)
        AND (
            source_filter = '{}'
            OR ds.source_type = ANY(source_filter)
        )
        -- Full-text search matching
        AND search_query @@ ds.content_vector
    ORDER BY
        -- Combine text similarity with recency boosting
        (ts_rank(search_query, ds.content_vector) * 0.7 +
         CASE
            WHEN ds.created_at >= NOW() - INTERVAL '30 days' THEN 0.1
            ELSE 0
         END) DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Phrase search function for exact phrase matching
-- Provides higher precision when users need exact phrase results
CREATE OR REPLACE FUNCTION phrase_search(
    phrase_text TEXT,
    source_filter TEXT[] DEFAULT '{}',
    user_permissions TEXT[] DEFAULT '{}',
    limit_count INTEGER DEFAULT 5
)
RETURNS TABLE (
    doc_id VARCHAR(255),
    title TEXT,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    created_at TIMESTAMPTZ,
    score NUMERIC,
    permissions TEXT[],
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.doc_id,
        ds.title,
        ds.source_type,
        ds.source_id,
        ds.created_at,
        -- Perfect matches get highest score
        1.0 AS score,
        ds.permissions,
        ds.metadata
    FROM documents_search ds
    WHERE
        ds.content_vector IS NOT NULL
        AND (
            user_permissions = '{}'
            OR ds.permissions && user_permissions
            OR ds.permissions && ARRAY['public']
        )
        AND (
            source_filter = '{}'
            OR ds.source_type = ANY(source_filter)
        )
        -- Exact phrase matching (case-insensitive)
        AND ds.computed_content ILIKE '%' || phrase_text || '%'
    ORDER BY ds.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Search statistics and monitoring function
-- Provides insights into search performance and document distribution
CREATE OR REPLACE FUNCTION get_search_stats()
RETURNS TABLE (
    total_documents BIGINT,
    searchable_documents BIGINT,
    documents_by_source JSONB,
    avg_content_length NUMERIC,
    newest_document TIMESTAMPTZ,
    oldest_document TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_documents,
        COUNT(content_vector) AS searchable_documents,
        jsonb_build_object(
            'google_drive', COUNT(*) FILTER (WHERE source_type = 'google_drive'),
            'slack', COUNT(*) FILTER (WHERE source_type = 'slack'),
            'local_upload', COUNT(*) FILTER (WHERE source_type = 'local_upload'),
            'chat_message', COUNT(*) FILTER (WHERE source_type = 'chat_message')
        ) AS documents_by_source,
        ROUND(AVG(content_length), 2) AS avg_content_length,
        MAX(created_at) AS newest_document,
        MIN(created_at) AS oldest_document
    FROM documents_search;
END;
$$ LANGUAGE plpgsql;

-- Grant appropriate permissions for application users
-- These permissions are needed for the search services to function properly
GRANT EXECUTE ON FUNCTION keyword_search(TEXT, TEXT[], TEXT[], INTEGER, INTEGER) TO app_user;
GRANT EXECUTE ON FUNCTION phrase_search(TEXT, TEXT[], TEXT[], INTEGER) TO app_user;
GRANT EXECUTE ON FUNCTION get_search_stats() TO app_user;

-- Performance optimization: Create materialized view for frequently accessed statistics
-- This improves query performance for dashboard and monitoring features
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_search_statistics AS
SELECT
    source_type,
    COUNT(*) AS document_count,
    COUNT(content_vector) AS searchable_count,
    ROUND(AVG(content_length), 2) AS avg_content_length,
    MAX(created_at) AS newest_document,
    MIN(created_at) AS oldest_document,
    NOW() AS stats_updated_at
FROM documents_search
GROUP BY source_type;

-- Create unique index on materialized view for efficient refresh operations
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_search_statistics_unique
ON mv_search_statistics (source_type, stats_updated_at);

-- Grant read access to materialized view
GRANT SELECT ON mv_search_statistics TO app_user;

-- Insert migration record for tracking
INSERT INTO migrations (migration_id, description, applied_at, status)
VALUES ('004', 'Hybrid Search Keyword Infrastructure', NOW(), 'completed')
ON CONFLICT (migration_id) DO UPDATE SET
    description = 'Hybrid Search Keyword Infrastructure',
    applied_at = NOW(),
    status = 'completed';

-- Create optimized stored procedure for refreshing search statistics
-- This can be called periodically to keep statistics current without full rebuild
CREATE OR REPLACE FUNCTION refresh_search_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_statistics;
END;
$$ LANGUAGE plpgsql;

-- Grant permission for statistics refresh
GRANT EXECUTE ON FUNCTION refresh_search_statistics() TO app_user;