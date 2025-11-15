-- =============================================================================
-- ONYX Migration 002: Standing Instructions Table
-- =============================================================================
-- Creates user_standing_instructions table with Row Level Security
-- Supports persistent system prompt customization per user
-- =============================================================================

-- Create UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop table if it exists (for clean migration)
DROP TABLE IF EXISTS user_standing_instructions CASCADE;

-- Create standing instructions table
CREATE TABLE user_standing_instructions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    enabled BOOLEAN DEFAULT true,
    category VARCHAR(50) DEFAULT 'general',
    conditions JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_standing_instructions_user_enabled ON user_standing_instructions(user_id, enabled);
CREATE INDEX idx_standing_instructions_priority ON user_standing_instructions(priority DESC);
CREATE INDEX idx_standing_instructions_category ON user_standing_instructions(category);
CREATE INDEX idx_standing_instructions_user_category ON user_standing_instructions(user_id, category);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_standing_instructions_updated_at
    BEFORE UPDATE ON user_standing_instructions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE user_standing_instructions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Users can only access their own standing instructions
CREATE POLICY "Users can view own standing instructions" ON user_standing_instructions
    FOR SELECT USING (
        auth.uid() = user_id
    );

CREATE POLICY "Users can insert own standing instructions" ON user_standing_instructions
    FOR INSERT WITH CHECK (
        auth.uid() = user_id
    );

CREATE POLICY "Users can update own standing instructions" ON user_standing_instructions
    FOR UPDATE USING (
        auth.uid() = user_id
    );

CREATE POLICY "Users can delete own standing instructions" ON user_standing_instructions
    FOR DELETE USING (
        auth.uid() = user_id
    );

-- Create function for getting user's active standing instructions
CREATE OR REPLACE FUNCTION get_user_standing_instructions(
    p_user_id UUID,
    p_enabled_only BOOLEAN DEFAULT true
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    priority INTEGER,
    category VARCHAR(50),
    conditions JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        si.id,
        si.content,
        si.priority,
        si.category,
        si.conditions,
        si.created_at,
        si.updated_at
    FROM user_standing_instructions si
    WHERE si.user_id = p_user_id
        AND (NOT p_enabled_only OR si.enabled = true)
    ORDER BY si.priority DESC, si.created_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function for upserting standing instructions
CREATE OR REPLACE FUNCTION upsert_standing_instruction(
    p_user_id UUID,
    p_content TEXT,
    p_priority INTEGER DEFAULT 5,
    p_enabled BOOLEAN DEFAULT true,
    p_category VARCHAR(50) DEFAULT 'general',
    p_conditions JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    instruction_id UUID;
BEGIN
    -- Check if instruction with same content and user already exists
    SELECT id INTO instruction_id
    FROM user_standing_instructions
    WHERE user_id = p_user_id AND content = p_content;

    IF instruction_id IS NOT NULL THEN
        -- Update existing instruction
        UPDATE user_standing_instructions
        SET
            priority = p_priority,
            enabled = p_enabled,
            category = p_category,
            conditions = p_conditions,
            updated_at = NOW()
        WHERE id = instruction_id;

        RETURN instruction_id;
    ELSE
        -- Insert new instruction
        INSERT INTO user_standing_instructions (
            user_id, content, priority, enabled, category, conditions
        ) VALUES (
            p_user_id, p_content, p_priority, p_enabled, p_category, p_conditions
        ) RETURNING id INTO instruction_id;

        RETURN instruction_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_standing_instructions TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_standing_instructions TO authenticated;
GRANT EXECUTE ON FUNCTION upsert_standing_instruction TO authenticated;

-- Add validation constraints
ALTER TABLE user_standing_instructions
    ADD CONSTRAINT valid_category
    CHECK (category IN ('general', 'tone', 'reasoning', 'citations', 'recommendations', 'professional', 'custom'));

-- Add comments for documentation
COMMENT ON TABLE user_standing_instructions IS 'User-specific standing instructions for system prompt customization';
COMMENT ON COLUMN user_standing_instructions.content IS 'Instruction text that will be injected into system prompts';
COMMENT ON COLUMN user_standing_instructions.priority IS 'Priority level (1-10, higher = more important)';
COMMENT ON COLUMN user_standing_instructions.enabled IS 'Whether this instruction is currently active';
COMMENT ON COLUMN user_standing_instructions.category IS 'Type of instruction for organization';
COMMENT ON COLUMN user_standing_instructions.conditions IS 'JSON conditions for when this instruction applies';