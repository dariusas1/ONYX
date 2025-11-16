-- Memory System Schema Migration
-- Story 4-1: Memory Schema & Storage System
-- Creating tables for user memories, categories, and related functionality

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core memories table
CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    fact TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('priority', 'decision', 'context', 'preference', 'relationship', 'goal', 'summary')),
    confidence FLOAT NOT NULL DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    source_type TEXT NOT NULL CHECK (source_type IN ('manual', 'extracted_from_chat', 'auto_summary', 'standing_instruction')),
    source_message_id UUID,
    conversation_id UUID,
    metadata JSONB DEFAULT '{}',
    expires_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Memory categories table for user-configurable categories
CREATE TABLE IF NOT EXISTS memory_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#6366f1',
    icon TEXT DEFAULT 'folder',
    is_system_category BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Memory injection logs for analytics
CREATE TABLE IF NOT EXISTS memory_injection_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    conversation_id UUID,
    memories_count INTEGER NOT NULL DEFAULT 0,
    injection_type TEXT NOT NULL,
    performance_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversation summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    summary TEXT NOT NULL,
    key_points TEXT[],
    action_items TEXT[],
    confidence FLOAT DEFAULT 0.8,
    generated_by TEXT DEFAULT 'auto_summary',
    metadata JSONB DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes for user_memories
CREATE INDEX IF NOT EXISTS idx_memories_user_category ON user_memories(user_id, category) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_memories_confidence ON user_memories(user_id, confidence DESC) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_memories_recency ON user_memories(user_id, created_at DESC) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_memories_search ON user_memories USING gin(to_tsvector('english', fact)) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_memories_source_type ON user_memories(user_id, source_type) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON user_memories(expires_at) WHERE is_deleted = FALSE AND expires_at IS NOT NULL;

-- Indexes for memory_categories
CREATE INDEX IF NOT EXISTS idx_categories_user_id ON memory_categories(user_id);
CREATE INDEX IF NOT EXISTS idx_categories_system ON memory_categories(is_system_category);

-- Indexes for memory_injection_logs
CREATE INDEX IF NOT EXISTS idx_injection_logs_user_id ON memory_injection_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_injection_logs_conversation ON memory_injection_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_injection_logs_created_at ON memory_injection_logs(created_at DESC);

-- Indexes for conversation_summaries
CREATE INDEX IF NOT EXISTS idx_summaries_user_id ON conversation_summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_summaries_conversation ON conversation_summaries(conversation_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_summaries_created_at ON conversation_summaries(created_at DESC) WHERE is_deleted = FALSE;

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to tables
CREATE TRIGGER update_user_memories_updated_at
    BEFORE UPDATE ON user_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memory_categories_updated_at
    BEFORE UPDATE ON memory_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_summaries_updated_at
    BEFORE UPDATE ON conversation_summaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to track memory access
CREATE OR REPLACE FUNCTION track_memory_access()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE user_memories
    SET access_count = access_count + 1,
        last_accessed_at = NOW()
    WHERE id = NEW.id;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to track access when memory is selected
CREATE TRIGGER track_memory_access_trigger
    AFTER SELECT ON user_memories
    FOR EACH ROW EXECUTE FUNCTION track_memory_access();

-- Function to cleanup expired memories
CREATE OR REPLACE FUNCTION cleanup_expired_memories()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_memories
    WHERE expires_at IS NOT NULL
    AND expires_at < NOW()
    AND is_deleted = FALSE;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Insert default system categories for new users
CREATE OR REPLACE FUNCTION insert_default_categories(p_user_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO memory_categories (user_id, name, description, color, icon, is_system_category)
    VALUES
        (p_user_id, 'priority', 'User priorities and important goals', '#ef4444', 'star', TRUE),
        (p_user_id, 'decision', 'Key decisions made and rationale', '#f59e0b', 'check-circle', TRUE),
        (p_user_id, 'context', 'Background information and situational context', '#10b981', 'info', TRUE),
        (p_user_id, 'preference', 'User preferences and communication style', '#8b5cf6', 'heart', TRUE),
        (p_user_id, 'relationship', 'Information about people and relationships', '#06b6d4', 'users', TRUE),
        (p_user_id, 'goal', 'User objectives and targets', '#f97316', 'target', TRUE),
        (p_user_id, 'summary', 'Auto-generated conversation summaries', '#6b7280', 'document-text', TRUE)
    ON CONFLICT (user_id, name) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust based on your database user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO manus;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO manus;

-- Add helpful comments
COMMENT ON TABLE user_memories IS 'Core table for storing user memories with full metadata and categorization';
COMMENT ON TABLE memory_categories IS 'User-configurable memory categories with system defaults';
COMMENT ON TABLE memory_injection_logs IS 'Analytics tracking for memory injection performance';
COMMENT ON TABLE conversation_summaries IS 'Auto-generated conversation summaries with key points';

-- Migration completed successfully
SELECT 'Memory system schema migration completed successfully' as status;