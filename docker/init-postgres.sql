-- =============================================================================
-- ONYX Database Schema Initialization
-- =============================================================================
-- This script sets up the initial database schema for the ONYX platform
-- Run automatically when PostgreSQL container starts for the first time
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Try to enable pgvector, but don't fail if it's not available
-- This allows the database to start in development environments
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS "pgvector";
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'pgvector extension not available, vector features will be disabled';
    END;
END $$;

-- =============================================================================
-- Users Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    google_id TEXT UNIQUE,
    display_name TEXT,
    encrypted_google_token BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- =============================================================================
-- Conversations Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'Untitled',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- =============================================================================
-- Messages Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]'::jsonb,
    token_count INTEGER DEFAULT 0,
    model_used TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for messages
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- =============================================================================
-- Memories Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact TEXT NOT NULL,
    source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'extracted_from_chat', 'auto_generated')),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add embedding column only if pgvector is available
DO $$
BEGIN
    BEGIN
        ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);
        -- Create vector index only if pgvector is available
        CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Vector features disabled for memories table';
    END;
END $$;

-- Create indexes for memories
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at);

-- =============================================================================
-- Standing Instructions Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS standing_instructions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    instruction TEXT NOT NULL,
    priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 10),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for standing instructions
CREATE INDEX IF NOT EXISTS idx_standing_instructions_user_id ON standing_instructions(user_id);
CREATE INDEX IF NOT EXISTS idx_standing_instructions_priority ON standing_instructions(priority DESC);

-- =============================================================================
-- Tasks Table (Agent Execution)
-- =============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'queued', 'running', 'success', 'failed', 'cancelled')),
    steps JSONB DEFAULT '[]'::jsonb,
    result TEXT,
    error_message TEXT,
    approval_required BOOLEAN DEFAULT false,
    approved_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for tasks
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_conversation_id ON tasks(conversation_id);

-- =============================================================================
-- Documents Table (RAG Metadata)
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL CHECK (source_type IN ('google_drive', 'slack', 'upload', 'web')),
    source_id TEXT,
    title TEXT NOT NULL,
    content_hash TEXT UNIQUE,
    file_size BIGINT,
    mime_type TEXT,
    embedding_model TEXT DEFAULT 'text-embedding-3-small',
    chunk_count INTEGER DEFAULT 0,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_last_synced_at ON documents(last_synced_at DESC);

-- =============================================================================
-- API Keys Table (Encrypted)
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    encrypted_key BYTEA NOT NULL,
    key_type TEXT DEFAULT 'api_key' CHECK (key_type IN ('api_key', 'oauth_token', 'webhook_secret')),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, service_name)
);

-- Create indexes for api_keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_service_name ON api_keys(service_name);

-- =============================================================================
-- Audit Logs Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- =============================================================================
-- System Configuration Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default system configuration
INSERT INTO system_config (key, value, description, is_public) VALUES
('app_version', '"1.0.0"', 'Current application version', true),
('max_file_size_mb', '50', 'Maximum file upload size in MB', true),
('supported_file_types', '["pdf", "doc", "docx", "txt", "md"]', 'Supported file types for upload', true),
('rate_limit_rpm', '100', 'Rate limit requests per minute per user', false),
('session_timeout_ms', '1800000', 'Session timeout in milliseconds', false)
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- Triggers and Functions
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to log user actions
CREATE OR REPLACE FUNCTION log_user_action()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES (
            COALESCE(NEW.user_id, current_setting('app.current_user_id', true)::UUID),
            TG_TABLE_NAME || '_created',
            TG_TABLE_NAME,
            NEW.id,
            json_build_object('old_values', NULL, 'new_values', row_to_json(NEW))
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES (
            COALESCE(NEW.user_id, current_setting('app.current_user_id', true)::UUID),
            TG_TABLE_NAME || '_updated',
            TG_TABLE_NAME,
            NEW.id,
            json_build_object('old_values', row_to_json(OLD), 'new_values', row_to_json(NEW))
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
        VALUES (
            COALESCE(OLD.user_id, current_setting('app.current_user_id', true)::UUID),
            TG_TABLE_NAME || '_deleted',
            TG_TABLE_NAME,
            OLD.id,
            json_build_object('old_values', row_to_json(OLD), 'new_values', NULL)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create audit triggers (only on critical tables)
CREATE TRIGGER audit_conversations
    AFTER INSERT OR UPDATE OR DELETE ON conversations
    FOR EACH ROW EXECUTE FUNCTION log_user_action();

CREATE TRIGGER audit_memories
    AFTER INSERT OR UPDATE OR DELETE ON memories
    FOR EACH ROW EXECUTE FUNCTION log_user_action();

CREATE TRIGGER audit_tasks
    AFTER INSERT OR UPDATE OR DELETE ON tasks
    FOR EACH ROW EXECUTE FUNCTION log_user_action();

-- =============================================================================
-- Views
-- =============================================================================

-- View for active conversations with latest message
CREATE OR REPLACE VIEW active_conversations AS
SELECT 
    c.id,
    c.user_id,
    c.title,
    c.created_at,
    c.updated_at,
    (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message,
    (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message_at,
    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
FROM conversations c
ORDER BY c.updated_at DESC;

-- View for user statistics
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    u.id,
    u.email,
    u.display_name,
    u.created_at,
    (SELECT COUNT(*) FROM conversations WHERE user_id = u.id) as conversation_count,
    (SELECT COUNT(*) FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = u.id)) as message_count,
    (SELECT COUNT(*) FROM memories WHERE user_id = u.id AND (expires_at IS NULL OR expires_at > NOW())) as active_memories,
    (SELECT COUNT(*) FROM tasks WHERE user_id = u.id AND status = 'success') as completed_tasks
FROM users u;

-- =============================================================================
-- Initial Data
-- =============================================================================

-- Create a default system user for background tasks
INSERT INTO users (email, display_name, created_at)
VALUES ('system@onyx.local', 'System User', NOW())
ON CONFLICT (email) DO NOTHING;

-- =============================================================================
-- Performance Optimizations
-- =============================================================================

-- Set statement timeout for queries
SET statement_timeout = '30s';

-- Set work_mem for complex queries
SET work_mem = '16MB';

-- Set maintenance_work_mem for index creation
SET maintenance_work_mem = '128MB';

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE users IS 'User accounts and authentication information';
COMMENT ON TABLE conversations IS 'Chat sessions between users and AI';
COMMENT ON TABLE messages IS 'Individual messages within conversations';
COMMENT ON TABLE memories IS 'User facts and contextual information for personalization';
COMMENT ON TABLE standing_instructions IS 'Persistent user directives for AI behavior';
COMMENT ON TABLE tasks IS 'Agent execution history and status tracking';
COMMENT ON TABLE documents IS 'Metadata for RAG document indexing';
COMMENT ON TABLE api_keys IS 'Encrypted third-party service credentials';
COMMENT ON TABLE audit_logs IS 'Security and compliance audit trail';
COMMENT ON TABLE system_config IS 'Application configuration and settings';

-- =============================================================================
-- Schema Version
-- =============================================================================

INSERT INTO system_config (key, value, description, is_public) VALUES
('schema_version', '"1.0.0"', 'Database schema version', false)
ON CONFLICT (key) DO UPDATE SET value = '"1.0.0"', updated_at = NOW();