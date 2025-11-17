-- Migration: Google Docs Creation Metadata
-- Description: Create table to track documents created by agents
-- Timestamp: 2025-11-16

-- Create google_docs_created table for document metadata tracking
CREATE TABLE IF NOT EXISTS google_docs_created (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    doc_id VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(1024) NOT NULL,
    folder_id VARCHAR(255),
    url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    agent_context JSONB,
    stored_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes for common queries
    INDEX idx_google_docs_user_id (user_id),
    INDEX idx_google_docs_doc_id (doc_id),
    INDEX idx_google_docs_created_at (created_at)
);

-- Add comment
COMMENT ON TABLE google_docs_created IS 'Tracks all Google Docs created by agents for audit and recovery';
COMMENT ON COLUMN google_docs_created.user_id IS 'User ID who authorized the document creation';
COMMENT ON COLUMN google_docs_created.doc_id IS 'Google Docs document ID';
COMMENT ON COLUMN google_docs_created.agent_context IS 'JSON context with agent name, task ID, and other metadata';
COMMENT ON COLUMN google_docs_created.stored_at IS 'When this metadata was stored in ONYX database';
