-- Standing Instructions Schema Migration
-- Story 4-2: Standing Instructions Management
-- Adding standing instructions table to support memory injection

-- Standing instructions table for user-defined standing instructions
CREATE TABLE IF NOT EXISTS standing_instructions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    instruction_text TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('workflow', 'decision', 'communication', 'security', 'general')),
    priority INTEGER NOT NULL DEFAULT 1 CHECK (priority >= 1 AND priority <= 10),
    context_hints TEXT[],
    enabled BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes for standing_instructions
CREATE INDEX IF NOT EXISTS idx_standing_instructions_user_enabled ON standing_instructions(user_id, enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_standing_instructions_priority ON standing_instructions(user_id, priority DESC) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_standing_instructions_category ON standing_instructions(user_id, category) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_standing_instructions_usage ON standing_instructions(user_id, usage_count DESC) WHERE enabled = TRUE;

-- Trigger to automatically update updated_at timestamp
CREATE TRIGGER update_standing_instructions_updated_at
    BEFORE UPDATE ON standing_instructions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to track standing instruction usage
CREATE OR REPLACE FUNCTION track_instruction_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE standing_instructions
    SET usage_count = usage_count + 1,
        last_used_at = NOW()
    WHERE id = NEW.id;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to get top standing instructions for injection
CREATE OR REPLACE FUNCTION get_top_standing_instructions(
    p_user_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    instruction_text TEXT,
    category TEXT,
    priority INTEGER,
    context_hints TEXT[],
    usage_count INTEGER,
    last_used_at TIMESTAMP,
    priority_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        si.id,
        si.instruction_text,
        si.category,
        si.priority,
        si.context_hints,
        si.usage_count,
        si.last_used_at,
        -- Calculate priority score for ranking
        (si.priority * 0.6 +
         COALESCE(si.usage_count * 0.01, 0) * 0.3 +
         CASE WHEN si.last_used_at > NOW() - INTERVAL '7 days' THEN 0.1 ELSE 0 END
        ) as priority_score
    FROM standing_instructions si
    WHERE si.user_id = p_user_id
        AND si.enabled = TRUE
    ORDER BY priority_score DESC, si.priority DESC, si.usage_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get memory injection analytics
CREATE OR REPLACE FUNCTION log_memory_injection(
    p_user_id UUID,
    p_conversation_id UUID,
    p_memories_count INTEGER,
    p_instructions_count INTEGER,
    p_injection_type TEXT,
    p_performance_ms INTEGER,
    p_success BOOLEAN DEFAULT TRUE,
    p_error_message TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    log_id UUID;
BEGIN
    INSERT INTO memory_injection_logs (
        user_id, conversation_id, memories_count, injection_type,
        performance_ms, success, error_message
    ) VALUES (
        p_user_id, p_conversation_id, p_memories_count + p_instructions_count,
        p_injection_type, p_performance_ms, p_success, p_error_message
    )
    RETURNING id INTO log_id;

    RETURN log_id;
END;
$$ LANGUAGE plpgsql;

-- Add helpful comments
COMMENT ON TABLE standing_instructions IS 'User-defined standing instructions for personalized behavior';
COMMENT ON FUNCTION get_top_standing_instructions IS 'Retrieve top ranked standing instructions for memory injection';
COMMENT ON FUNCTION log_memory_injection IS 'Log memory injection events for analytics and performance tracking';

-- Migration completed successfully
SELECT 'Standing instructions schema migration completed successfully' as status;