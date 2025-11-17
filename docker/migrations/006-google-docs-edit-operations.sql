-- Migration: Google Docs Edit Operations Table
-- Story: 6-3-google-docs-editing-capabilities
-- Purpose: Track all Google Docs edit operations for audit trail and compliance

CREATE TABLE IF NOT EXISTS google_docs_edit_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('insert', 'replace', 'format')),
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL CHECK (status IN ('pending', 'success', 'failed')),
    result JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes for efficient querying
    CONSTRAINT google_docs_edit_ops_user_doc CHECK (user_id IS NOT NULL AND document_id IS NOT NULL)
);

-- Indexes for common queries
CREATE INDEX idx_google_docs_edit_ops_user_id ON google_docs_edit_operations(user_id);
CREATE INDEX idx_google_docs_edit_ops_document_id ON google_docs_edit_operations(document_id);
CREATE INDEX idx_google_docs_edit_ops_timestamp ON google_docs_edit_operations(timestamp);
CREATE INDEX idx_google_docs_edit_ops_status ON google_docs_edit_operations(status);
CREATE INDEX idx_google_docs_edit_ops_operation_type ON google_docs_edit_operations(operation_type);

-- Composite index for common audit queries
CREATE INDEX idx_google_docs_edit_ops_user_timestamp ON google_docs_edit_operations(user_id, timestamp DESC);

-- Add column to documents table to link edit operations (optional, for referential integrity)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMP;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS edit_operation_count INTEGER DEFAULT 0;

-- Comment on table
COMMENT ON TABLE google_docs_edit_operations IS 'Audit trail for all Google Docs edit operations (inserts, replacements, formatting updates)';
COMMENT ON COLUMN google_docs_edit_operations.user_id IS 'User who performed the edit';
COMMENT ON COLUMN google_docs_edit_operations.document_id IS 'Google Docs document ID';
COMMENT ON COLUMN google_docs_edit_operations.operation_type IS 'Type: insert, replace, or format';
COMMENT ON COLUMN google_docs_edit_operations.details IS 'Operation-specific details (position, search_text, formatting properties, etc.)';
COMMENT ON COLUMN google_docs_edit_operations.status IS 'Operation status: pending, success, or failed';
COMMENT ON COLUMN google_docs_edit_operations.result IS 'Operation result data (character counts, replacements made, etc.)';
COMMENT ON COLUMN google_docs_edit_operations.error_message IS 'Error message if operation failed';
COMMENT ON COLUMN google_docs_edit_operations.timestamp IS 'Timestamp of operation execution';
