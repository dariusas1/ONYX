-- Standing Instructions Schema Migration
-- Story 4-2: Standing Instructions Management
-- Creating standing_instructions table with proper indexing and constraints

-- Standing instructions table for user behavioral directives
CREATE TABLE IF NOT EXISTS standing_instructions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    instruction_text TEXT NOT NULL CHECK (length(instruction_text) BETWEEN 1 AND 500),
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    category TEXT CHECK (category IN ('behavior', 'communication', 'decision', 'security', 'workflow')),
    enabled BOOLEAN DEFAULT TRUE,
    context_hints JSONB DEFAULT '{}',
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key constraints (will be enabled after users table exists)
    -- CONSTRAINT fk_instructions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Performance indexes for standing_instructions
CREATE INDEX IF NOT EXISTS idx_instructions_user_enabled ON standing_instructions(user_id, enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_instructions_priority ON standing_instructions(user_id, priority DESC);
CREATE INDEX IF NOT EXISTS idx_instructions_category ON standing_instructions(user_id, category);
CREATE INDEX IF NOT EXISTS idx_instructions_usage ON standing_instructions(user_id, usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_instructions_last_used ON standing_instructions(user_id, last_used_at DESC NULLS LAST);

-- Index for context hints queries
CREATE INDEX IF NOT EXISTS idx_instructions_context_hints ON standing_instructions USING gin(context_hints);

-- Apply updated_at trigger to standing_instructions table
CREATE TRIGGER update_standing_instructions_updated_at
    BEFORE UPDATE ON standing_instructions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to track instruction usage
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

-- Trigger to automatically update usage statistics when instruction is applied
-- Note: This would be triggered by application logic, not database selects

-- Function to get active instructions for a user with context filtering
CREATE OR REPLACE FUNCTION get_active_instructions(
    p_user_id UUID,
    p_enabled_only BOOLEAN DEFAULT TRUE,
    p_category_filter TEXT DEFAULT NULL,
    p_min_priority INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    instruction_text TEXT,
    priority INTEGER,
    category TEXT,
    enabled BOOLEAN,
    context_hints JSONB,
    usage_count INTEGER,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    relevance_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        si.id,
        si.instruction_text,
        si.priority,
        si.category,
        si.enabled,
        si.context_hints,
        si.usage_count,
        si.last_used_at,
        si.created_at,
        si.updated_at,
        -- Calculate relevance score based on priority, usage, and recency
        (si.priority * 0.6 +
         LEAST(si.usage_count::FLOAT / 10.0, 1.0) * 0.3 +
         CASE
             WHEN si.last_used_at IS NOT NULL
             THEN LEAST(EXTRACT(EPOCH FROM (NOW() - si.last_used_at)) / (7 * 24 * 3600.0), 1.0) * 0.1
             ELSE 0.0
         END) as relevance_score
    FROM standing_instructions si
    WHERE si.user_id = p_user_id
    AND (p_enabled_only IS FALSE OR si.enabled = TRUE)
    AND (p_category_filter IS NULL OR si.category = p_category_filter)
    AND (p_min_priority IS NULL OR si.priority >= p_min_priority)
    ORDER BY
        si.priority DESC,
        si.usage_count DESC,
        si.last_used_at DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- Function to detect instruction conflicts
CREATE OR REPLACE FUNCTION detect_instruction_conflicts(p_user_id UUID)
RETURNS TABLE (
    instruction_1_id UUID,
    instruction_1_text TEXT,
    instruction_2_id UUID,
    instruction_2_text TEXT,
    conflict_type TEXT,
    severity TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH instruction_pairs AS (
        SELECT
            si1.id as id1,
            si1.instruction_text as text1,
            si1.category as cat1,
            si2.id as id2,
            si2.instruction_text as text2,
            si2.category as cat2
        FROM standing_instructions si1
        CROSS JOIN standing_instructions si2
        WHERE si1.user_id = p_user_id
        AND si2.user_id = p_user_id
        AND si1.enabled = TRUE
        AND si2.enabled = TRUE
        AND si1.id < si2.id  -- Avoid duplicate pairs and self-comparison
    ),
    conflict_detection AS (
        SELECT
            id1,
            text1,
            cat1,
            id2,
            text2,
            cat2,
            CASE
                -- Direct contradictions
                WHEN (
                    (LOWER(text1) LIKE '%always%' AND LOWER(text2) LIKE '%never%') OR
                    (LOWER(text1) LIKE '%never%' AND LOWER(text2) LIKE '%always%') OR
                    (LOWER(text1) LIKE '%do%' AND LOWER(text2) LIKE '%don''t%') OR
                    (LOWER(text1) LIKE '%don''t%' AND LOWER(text2) LIKE '%do%')
                ) THEN 'direct_contradiction'

                -- Priority conflicts (different priorities for similar instructions)
                WHEN (cat1 = cat2 AND ABS(
                    (SELECT priority FROM standing_instructions WHERE id = id1) -
                    (SELECT priority FROM standing_instructions WHERE id = id2)
                ) > 3) THEN 'priority_conflict'

                -- Category conflicts
                WHEN (cat1 = 'security' AND cat2 = 'workflow') OR
                     (cat2 = 'security' AND cat1 = 'workflow') THEN 'security_workflow_conflict'

                -- Communication style conflicts
                WHEN (cat1 = 'communication' AND cat2 = 'communication' AND
                      (
                          (LOWER(text1) LIKE '%formal%' AND LOWER(text2) LIKE '%casual%') OR
                          (LOWER(text1) LIKE '%casual%' AND LOWER(text2) LIKE '%formal%') OR
                          (LOWER(text1) LIKE '%brief%' AND LOWER(text2) LIKE '%detailed%') OR
                          (LOWER(text1) LIKE '%detailed%' AND LOWER(text2) LIKE '%brief%')
                      )) THEN 'communication_style_conflict'

                ELSE 'no_conflict'
            END as conflict_type,
            CASE
                WHEN conflict_type = 'direct_contradiction' THEN 'high'
                WHEN conflict_type IN ('priority_conflict', 'security_workflow_conflict') THEN 'medium'
                WHEN conflict_type = 'communication_style_conflict' THEN 'low'
                ELSE 'none'
            END as severity
        FROM instruction_pairs
    )
    SELECT
        id1::UUID as instruction_1_id,
        text1 as instruction_1_text,
        id2::UUID as instruction_2_id,
        text2 as instruction_2_text,
        conflict_type,
        severity
    FROM conflict_detection
    WHERE conflict_type != 'no_conflict'
    ORDER BY
        CASE severity
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
        END;
END;
$$ LANGUAGE plpgsql;

-- View for instruction analytics
CREATE OR REPLACE VIEW instruction_analytics AS
SELECT
    user_id,
    category,
    COUNT(*) as total_instructions,
    COUNT(*) FILTER (WHERE enabled = TRUE) as active_instructions,
    AVG(priority) as avg_priority,
    SUM(usage_count) as total_usage,
    AVG(usage_count) as avg_usage,
    MAX(last_used_at) as last_activity,
    COUNT(*) FILTER (WHERE usage_count = 0) as unused_instructions
FROM standing_instructions
GROUP BY user_id, category;

-- Add helpful comments
COMMENT ON TABLE standing_instructions IS 'User-defined behavioral directives that guide Manus responses across conversations';
COMMENT ON COLUMN standing_instructions.instruction_text IS 'The directive text (1-500 characters)';
COMMENT ON COLUMN standing_instructions.priority IS 'Importance level (1-10, higher = more important)';
COMMENT ON COLUMN standing_instructions.category IS 'Type of instruction (behavior, communication, decision, security, workflow)';
COMMENT ON COLUMN standing_instructions.context_hints IS 'JSON metadata for when to apply the instruction';
COMMENT ON COLUMN standing_instructions.usage_count IS 'Track how often instruction is applied';
COMMENT ON COLUMN standing_instructions.last_used_at IS 'Timestamp of last application';

-- Migration completed successfully
SELECT 'Standing instructions schema migration completed successfully' as status;