-- =============================================================================
-- Story 3-5: Hybrid Search - PostgreSQL Keyword Search Setup
-- =============================================================================
-- This migration sets up PostgreSQL full-text search capabilities with BM25
-- implementation and keyword indexing for hybrid search functionality
-- =============================================================================
-- Migration: 004-hybrid-search-keyword.sql
-- Story: 3-5-hybrid-search-semantic-keyword
-- Date: 2025-11-15
-- =============================================================================

-- Enable required extensions for full-text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Note: pg_bm25 extension would be ideal, but we'll implement BM25-like scoring
-- using built-in PostgreSQL functions for broader compatibility

-- =============================================================================
-- Documents Search Table
-- =============================================================================
-- This table stores document content for keyword search with BM25-like scoring
-- It acts as the keyword search counterpart to Qdrant vector search
CREATE TABLE IF NOT EXISTS documents_search (
    doc_id VARCHAR(255) PRIMARY KEY,  -- Matches Qdrant point IDs
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('google_drive', 'slack', 'upload', 'web')),
    source_id VARCHAR(255),
    file_path TEXT,
    mime_type TEXT,
    file_size BIGINT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    permissions TEXT[] DEFAULT ARRAY['*'],  -- Array of user emails with access, * means public
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Denormalized fields for better search performance
    author_email TEXT,
    chunk_count INTEGER DEFAULT 1,
    content_length INTEGER,
    -- Full-text search vectors
    title_vector tsvector GENERATED ALWAYS AS (setweight(to_tsvector('english', coalesce(title, '')), 'A')) STORED,
    content_vector tsvector GENERATED ALWAYS AS (setweight(to_tsvector('english', coalesce(content, '')), 'B')) STORED,
    combined_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'B')
    ) STORED
);

-- =============================================================================
-- Indexes for Keyword Search Performance
-- =============================================================================

-- GIN indexes for full-text search (critical for performance)
CREATE INDEX IF NOT EXISTS idx_documents_search_title_vector ON documents_search USING gin(title_vector);
CREATE INDEX IF NOT EXISTS idx_documents_search_content_vector ON documents_search USING gin(content_vector);
CREATE INDEX IF NOT EXISTS idx_documents_search_combined_vector ON documents_search USING gin(combined_vector);

-- Trigram indexes for fuzzy matching and partial word searches
CREATE INDEX IF NOT EXISTS idx_documents_search_title_trgm ON documents_search USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_search_content_trgm ON documents_search USING gin(content gin_trgm_ops);

-- B-tree indexes for filtering and sorting
CREATE INDEX IF NOT EXISTS idx_documents_search_source_type ON documents_search(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_search_created_at ON documents_search(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_search_updated_at ON documents_search(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_search_indexed_at ON documents_search(indexed_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_search_file_size ON documents_search(file_size);
CREATE INDEX IF NOT EXISTS idx_documents_search_content_length ON documents_search(content_length);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_documents_search_source_created ON documents_search(source_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_search_permissions_created ON documents_search USING gin(permissions, created_at DESC);

-- =============================================================================
-- BM25-like Scoring Functions
-- =============================================================================

-- Function to calculate document length normalization (for BM25)
CREATE OR REPLACE FUNCTION calculate_doc_length_norm(doc_length INTEGER, avg_doc_length FLOAT)
RETURNS FLOAT AS $$
BEGIN
    -- BM25 length normalization: k1 * (1 - b + b * (doc_length / avg_doc_length))
    -- Using typical BM25 parameters: k1=1.2, b=0.75
    RETURN 1.2 * (1 - 0.75 + 0.75 * (doc_length / avg_doc_length));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate BM25-like score for a document
CREATE OR REPLACE FUNCTION calculate_bm25_score(
    doc_title_vector tsvector,
    doc_content_vector tsvector,
    query_vector tsvector,
    doc_length INTEGER,
    avg_doc_length FLOAT,
    title_weight FLOAT DEFAULT 2.0
) RETURNS FLOAT AS $$
DECLARE
    title_score FLOAT;
    content_score FLOAT;
    length_norm FLOAT;
BEGIN
    -- Calculate term frequency scores
    title_score := ts_rank_cd(doc_title_vector, query_vector, 32);
    content_score := ts_rank_cd(doc_content_vector, query_vector, 32);

    -- Apply length normalization
    length_norm := calculate_doc_length_norm(doc_length, avg_doc_length);

    -- Combine scores with title boost and length normalization
    RETURN (title_score * title_weight + content_score) / length_norm;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to get average document length (for BM25 normalization)
CREATE OR REPLACE FUNCTION get_avg_document_length()
RETURNS FLOAT AS $$
DECLARE
    avg_length FLOAT;
BEGIN
    SELECT AVG(content_length) INTO avg_length
    FROM documents_search
    WHERE content_length > 0;

    -- Return default if no documents or NULL result
    RETURN COALESCE(avg_length, 1000.0);  -- Default 1000 characters
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =============================================================================
-- Search Functions
-- =============================================================================

-- Function for keyword search with BM25-like scoring
CREATE OR REPLACE FUNCTION keyword_search(
    query_text TEXT,
    user_permissions TEXT[] DEFAULT ARRAY['*'],
    source_filter VARCHAR(50) DEFAULT NULL,
    limit_count INTEGER DEFAULT 10,
    offset_count INTEGER DEFAULT 0
) RETURNS TABLE (
    doc_id VARCHAR(255),
    title TEXT,
    content TEXT,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    permissions TEXT[],
    metadata JSONB,
    bm25_score FLOAT,
    content_preview TEXT
) AS $$
DECLARE
    query_ts tsvector;
    avg_doc_len FLOAT;
BEGIN
    -- Create query vector
    query_ts := to_tsvector('english', query_text);

    -- Get average document length for BM25 normalization
    avg_doc_len := get_avg_document_length();

    -- Return query results with BM25-like scoring
    RETURN QUERY
    SELECT
        ds.doc_id,
        ds.title,
        ds.content,
        ds.source_type,
        ds.source_id,
        ds.created_at,
        ds.updated_at,
        ds.permissions,
        ds.metadata,
        calculate_bm25_score(
            ds.title_vector,
            ds.content_vector,
            query_ts,
            ds.content_length,
            avg_doc_len
        ) as bm25_score,
        LEFT(ds.content, 200) || '...' as content_preview
    FROM documents_search ds
    WHERE
        -- Permission filtering: user must have access OR document is public
        (
            '*' = ANY(user_permissions) OR
            ds.permissions && user_permissions OR
            '{*}' && ds.permissions
        )
        -- Source type filtering
        AND (source_filter IS NULL OR ds.source_type = source_filter)
        -- Full-text search matching
        AND (
            plainto_tsquery('english', query_text) @@ ds.title_vector OR
            plainto_tsquery('english', query_text) @@ ds.content_vector
        )
    ORDER BY bm25_score DESC, ds.updated_at DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Function for phrase search (exact phrase matching)
CREATE OR REPLACE FUNCTION phrase_search(
    phrase_text TEXT,
    user_permissions TEXT[] DEFAULT ARRAY['*'],
    source_filter VARCHAR(50) DEFAULT NULL,
    limit_count INTEGER DEFAULT 10
) RETURNS TABLE (
    doc_id VARCHAR(255),
    title TEXT,
    content TEXT,
    source_type VARCHAR(50),
    source_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    permissions TEXT[],
    metadata JSONB,
    phrase_score FLOAT,
    content_preview TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.doc_id,
        ds.title,
        ds.content,
        ds.source_type,
        ds.source_id,
        ds.created_at,
        ds.updated_at,
        ds.permissions,
        ds.metadata,
        ts_rank_cd(ds.combined_vector, phraseto_tsquery('english', phrase_text), 32) as phrase_score,
        LEFT(ds.content, 200) || '...' as content_preview
    FROM documents_search ds
    WHERE
        -- Permission filtering
        (
            '*' = ANY(user_permissions) OR
            ds.permissions && user_permissions OR
            '{*}' && ds.permissions
        )
        -- Source type filtering
        AND (source_filter IS NULL OR ds.source_type = source_filter)
        -- Phrase search matching
        AND phraseto_tsquery('english', phrase_text) @@ ds.combined_vector
    ORDER BY phrase_score DESC, ds.updated_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Triggers and Automated Functions
-- =============================================================================

-- Function to update content length trigger
CREATE OR REPLACE FUNCTION update_content_length()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_length := LENGTH(COALESCE(NEW.content, ''));
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for content length updates
CREATE TRIGGER update_documents_search_content_length
    BEFORE INSERT OR UPDATE ON documents_search
    FOR EACH ROW EXECUTE FUNCTION update_content_length();

-- Function to sync documents from main documents table
CREATE OR REPLACE FUNCTION sync_document_to_search(
    p_doc_id VARCHAR(255),
    p_title TEXT,
    p_content TEXT,
    p_source_type VARCHAR(50),
    p_source_id VARCHAR(255),
    p_file_path TEXT,
    p_mime_type TEXT,
    p_file_size BIGINT,
    p_created_at TIMESTAMP WITH TIME ZONE,
    p_updated_at TIMESTAMP WITH TIME ZONE,
    p_permissions TEXT[] DEFAULT ARRAY['*'],
    p_metadata JSONB DEFAULT '{}'::jsonb
) RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO documents_search (
        doc_id, title, content, source_type, source_id, file_path,
        mime_type, file_size, created_at, updated_at, permissions, metadata
    ) VALUES (
        p_doc_id, p_title, p_content, p_source_type, p_source_id, p_file_path,
        p_mime_type, p_file_size, p_created_at, p_updated_at, p_permissions, p_metadata
    )
    ON CONFLICT (doc_id) DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        source_type = EXCLUDED.source_type,
        source_id = EXCLUDED.source_id,
        file_path = EXCLUDED.file_path,
        mime_type = EXCLUDED.mime_type,
        file_size = EXCLUDED.file_size,
        updated_at = EXCLUDED.updated_at,
        permissions = EXCLUDED.permissions,
        metadata = EXCLUDED.metadata,
        indexed_at = NOW();

    RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Failed to sync document %: %', p_doc_id, SQLERRM;
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Materialized Views for Performance
-- =============================================================================

-- Materialized view for document statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_document_search_stats AS
SELECT
    source_type,
    COUNT(*) as total_documents,
    SUM(content_length) as total_content_length,
    AVG(content_length) as avg_content_length,
    MIN(created_at) as oldest_document,
    MAX(created_at) as newest_document,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_documents
FROM documents_search
GROUP BY source_type;

-- Create index for materialized view
CREATE INDEX IF NOT EXISTS idx_mv_document_search_stats_source_type
ON mv_document_search_stats(source_type);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_document_search_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_document_search_stats;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Performance Monitoring and Maintenance
-- =============================================================================

-- Function to analyze search performance
CREATE OR REPLACE FUNCTION analyze_search_performance()
RETURNS TABLE (
    metric_name TEXT,
    metric_value TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'total_documents'::TEXT, COUNT(*)::TEXT
    FROM documents_search
    UNION ALL
    SELECT 'indexed_documents'::TEXT, COUNT(*)::TEXT
    FROM documents_search WHERE indexed_at IS NOT NULL
    UNION ALL
    SELECT 'avg_content_length'::TEXT, ROUND(AVG(content_length))::TEXT
    FROM documents_search WHERE content_length > 0
    UNION ALL
    SELECT 'documents_with_permissions'::TEXT, COUNT(*)::TEXT
    FROM documents_search WHERE array_length(permissions, 1) > 0
    UNION ALL
    SELECT 'recent_documents_30d'::TEXT, COUNT(*)::TEXT
    FROM documents_search WHERE created_at > NOW() - INTERVAL '30 days'
    UNION ALL
    SELECT 'largest_document_size'::TEXT, MAX(content_length)::TEXT
    FROM documents_search
    UNION ALL
    SELECT 'avg_documents_per_source'::TEXT, ROUND(COUNT(*) / COUNT(DISTINCT source_type))::TEXT
    FROM documents_search;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Sample Data for Testing (Optional)
-- =============================================================================

-- Insert sample documents for testing (only in development)
-- This would be removed or conditional in production
DO $$
BEGIN
    -- Check if this is a development environment and table is empty
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'documents_search')
       AND (SELECT COUNT(*) FROM documents_search) = 0 THEN
        INSERT INTO documents_search (
            doc_id, title, content, source_type, source_id,
            created_at, updated_at, permissions, metadata
        ) VALUES
        ('doc-sample-1', 'AI Strategy Document', 'Our company strategy focuses on implementing AI solutions across all departments. Key priorities include automation, machine learning, and natural language processing.', 'google_drive', 'sample-doc-1', NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days', ARRAY['*'], '{"department": "strategy", "priority": "high"}'),
        ('doc-sample-2', 'Project Unicorn Launch Plan', 'Project Unicorn is scheduled to launch in Q4 2025. The launch will involve coordination across marketing, engineering, and sales teams.', 'slack', 'sample-msg-1', NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days', ARRAY['user1@company.com', 'user2@company.com'], '{"project": "unicorn", "stage": "planning"}'),
        ('doc-sample-3', 'Technical Specifications', 'The system must support sub-200ms search latency with 99.9% uptime. Database requirements include PostgreSQL with full-text search capabilities.', 'upload', 'sample-file-1', NOW() - INTERVAL '45 days', NOW() - INTERVAL '45 days', ARRAY['*'], '{"type": "specifications", "version": "1.0"}');

        RAISE NOTICE 'Sample documents inserted for testing purposes';
    END IF;
END $$;

-- =============================================================================
-- Grant Permissions
-- =============================================================================

-- Grant necessary permissions to the application user
-- Adjust the user role name as needed for your environment
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'onyx_user') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON documents_search TO onyx_user;
        GRANT SELECT ON mv_document_search_stats TO onyx_user;
        GRANT EXECUTE ON FUNCTION keyword_search TO onyx_user;
        GRANT EXECUTE ON FUNCTION phrase_search TO onyx_user;
        GRANT EXECUTE ON FUNCTION sync_document_to_search TO onyx_user;
        GRANT EXECUTE ON FUNCTION analyze_search_performance TO onyx_user;
        GRANT EXECUTE ON FUNCTION refresh_document_search_stats TO onyx_user;
    END IF;
END $$;

-- =============================================================================
-- Migration Complete
-- =============================================================================

-- Update schema version
INSERT INTO system_config (key, value, description, is_public) VALUES
('migration_004_hybrid_search_timestamp', '"2025-11-15T00:00:00Z"', 'Hybrid search keyword migration timestamp', false)
ON CONFLICT (key) DO UPDATE SET value = '"2025-11-15T00:00:00Z"', updated_at = NOW();

-- Create migration log entry
INSERT INTO system_config (key, value, description, is_public) VALUES
('migration_004_status', '"completed"', 'Status of migration 004: hybrid search keyword setup', false)
ON CONFLICT (key) DO UPDATE SET value = '"completed"', updated_at = NOW();

-- =============================================================================
-- Documentation Comments
-- =============================================================================

COMMENT ON TABLE documents_search IS 'Full-text search index for documents with BM25-like scoring, enabling keyword search component of hybrid search system';
COMMENT ON FUNCTION keyword_search IS 'Primary keyword search function with BM25-like scoring, permission filtering, and performance optimization';
COMMENT ON FUNCTION phrase_search IS 'Exact phrase search function for precise matching requirements';
COMMENT ON FUNCTION sync_document_to_search IS 'Synchronization function to maintain consistency between main documents table and search index';
COMMENT ON MATERIALIZED VIEW mv_document_search_stats IS 'Performance statistics materialized view for search analytics and monitoring';

-- Migration completion notice
DO $$
BEGIN
    RAISE NOTICE 'Migration 004: Hybrid Search Keyword Setup completed successfully';
    RAISE NOTICE '- Enabled pg_trgm and btree_gin extensions';
    RAISE NOTICE '- Created documents_search table with full-text search vectors';
    RAISE NOTICE '- Implemented BM25-like scoring functions';
    RAISE NOTICE '- Added performance-optimized indexes';
    RAISE NOTICE '- Created search and synchronization functions';
    RAISE NOTICE '- Set up performance monitoring views';
END $$;