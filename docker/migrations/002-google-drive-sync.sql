-- =============================================================================
-- Google Drive Sync Migration
-- =============================================================================
-- Story 3-2: Google Drive Connector & Auto-Sync
-- This migration adds tables and columns for Google Drive integration
-- =============================================================================

-- =============================================================================
-- Extend documents table with Drive-specific fields
-- =============================================================================
ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_email TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS sharing_status TEXT CHECK (sharing_status IN ('private', 'shared', 'public'));
ALTER TABLE documents ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '[]'::jsonb;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS web_view_link TEXT;

-- Create indexes for new document fields
CREATE INDEX IF NOT EXISTS idx_documents_owner_email ON documents(owner_email);
CREATE INDEX IF NOT EXISTS idx_documents_sharing_status ON documents(sharing_status);
CREATE INDEX IF NOT EXISTS idx_documents_modified_at ON documents(modified_at DESC);

-- Add comments
COMMENT ON COLUMN documents.owner_email IS 'File owner email address (from Google Drive)';
COMMENT ON COLUMN documents.sharing_status IS 'File sharing status: private, shared, or public';
COMMENT ON COLUMN documents.permissions IS 'JSON array of user emails with access to this document';
COMMENT ON COLUMN documents.modified_at IS 'Last modified timestamp from source (Google Drive)';
COMMENT ON COLUMN documents.web_view_link IS 'URL to view file in Google Drive';

-- =============================================================================
-- OAuth Tokens Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('google_drive', 'google_workspace', 'slack', 'github')),
    encrypted_access_token BYTEA NOT NULL,
    encrypted_refresh_token BYTEA NOT NULL,
    token_expiry TIMESTAMP WITH TIME ZONE NOT NULL,
    scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, provider)
);

-- Create indexes for oauth_tokens
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_id ON oauth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_provider ON oauth_tokens(provider);
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expiry ON oauth_tokens(token_expiry);

-- Add comments
COMMENT ON TABLE oauth_tokens IS 'Encrypted OAuth credentials for third-party services';
COMMENT ON COLUMN oauth_tokens.encrypted_access_token IS 'AES-256 encrypted OAuth access token';
COMMENT ON COLUMN oauth_tokens.encrypted_refresh_token IS 'AES-256 encrypted OAuth refresh token';
COMMENT ON COLUMN oauth_tokens.token_expiry IS 'Access token expiry timestamp';
COMMENT ON COLUMN oauth_tokens.scopes IS 'Array of OAuth scopes granted';

-- =============================================================================
-- Drive Sync State Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS drive_sync_state (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sync_token TEXT,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    files_synced INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    last_error TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for drive_sync_state
CREATE INDEX IF NOT EXISTS idx_drive_sync_state_last_sync ON drive_sync_state(last_sync_at DESC);

-- Add comments
COMMENT ON TABLE drive_sync_state IS 'Google Drive incremental sync state per user';
COMMENT ON COLUMN drive_sync_state.sync_token IS 'Google Drive API sync token for incremental changes';
COMMENT ON COLUMN drive_sync_state.last_sync_at IS 'Timestamp of last successful sync';
COMMENT ON COLUMN drive_sync_state.files_synced IS 'Count of files successfully synced in last run';
COMMENT ON COLUMN drive_sync_state.files_failed IS 'Count of files that failed in last sync';
COMMENT ON COLUMN drive_sync_state.last_error IS 'Last sync error message (if any)';

-- =============================================================================
-- Sync Jobs Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS sync_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL DEFAULT 'google_drive' CHECK (source_type IN ('google_drive', 'slack', 'dropbox')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    documents_synced INTEGER DEFAULT 0,
    documents_failed INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for sync_jobs
CREATE INDEX IF NOT EXISTS idx_sync_jobs_user_id ON sync_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_user_started ON sync_jobs(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_source_type ON sync_jobs(source_type);

-- Add comments
COMMENT ON TABLE sync_jobs IS 'History of sync job executions';
COMMENT ON COLUMN sync_jobs.status IS 'Job status: pending, running, success, failed, cancelled';
COMMENT ON COLUMN sync_jobs.documents_synced IS 'Number of documents successfully synced';
COMMENT ON COLUMN sync_jobs.documents_failed IS 'Number of documents that failed to sync';
COMMENT ON COLUMN sync_jobs.error_details IS 'Detailed error information as JSON';

-- =============================================================================
-- Triggers
-- =============================================================================

-- Trigger for oauth_tokens updated_at
CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for drive_sync_state updated_at
CREATE TRIGGER update_drive_sync_state_updated_at BEFORE UPDATE ON drive_sync_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Views for Monitoring
-- =============================================================================

-- View for latest sync status per user
CREATE OR REPLACE VIEW drive_sync_status AS
SELECT
    u.id as user_id,
    u.email,
    dss.last_sync_at,
    dss.files_synced,
    dss.files_failed,
    dss.last_error,
    (
        SELECT COUNT(*)
        FROM documents d
        WHERE d.source_type = 'google_drive'
    ) as total_drive_documents,
    (
        SELECT status
        FROM sync_jobs
        WHERE user_id = u.id
        AND source_type = 'google_drive'
        ORDER BY started_at DESC
        LIMIT 1
    ) as last_job_status,
    (
        SELECT started_at
        FROM sync_jobs
        WHERE user_id = u.id
        AND source_type = 'google_drive'
        ORDER BY started_at DESC
        LIMIT 1
    ) as last_job_started
FROM users u
LEFT JOIN drive_sync_state dss ON u.id = dss.user_id;

COMMENT ON VIEW drive_sync_status IS 'Current Google Drive sync status for all users';

-- View for sync job statistics
CREATE OR REPLACE VIEW sync_job_statistics AS
SELECT
    user_id,
    source_type,
    COUNT(*) as total_jobs,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_jobs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
    SUM(documents_synced) as total_documents_synced,
    SUM(documents_failed) as total_documents_failed,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MAX(started_at) as last_sync_time
FROM sync_jobs
WHERE completed_at IS NOT NULL
GROUP BY user_id, source_type;

COMMENT ON VIEW sync_job_statistics IS 'Aggregate statistics for sync jobs';

-- =============================================================================
-- Default Data
-- =============================================================================

-- Insert default system configuration for Google Drive
INSERT INTO system_config (key, value, description, is_public) VALUES
('google_drive_sync_enabled', 'true', 'Enable Google Drive auto-sync', false),
('google_drive_sync_interval_minutes', '10', 'Google Drive sync interval in minutes', false),
('google_drive_max_file_size_mb', '50', 'Maximum Google Drive file size to sync (MB)', false),
('google_drive_supported_mime_types', '["application/vnd.google-apps.document", "application/vnd.google-apps.spreadsheet", "application/pdf", "text/plain"]', 'Supported Google Drive MIME types', false)
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- Schema Version Update
-- =============================================================================

INSERT INTO system_config (key, value, description, is_public) VALUES
('schema_version', '"1.1.0"', 'Database schema version', false)
ON CONFLICT (key) DO UPDATE SET value = '"1.1.0"', updated_at = NOW();

-- =============================================================================
-- End of Migration
-- =============================================================================
