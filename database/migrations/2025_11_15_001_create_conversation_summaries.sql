-- Migration: Create conversation_summaries table
-- Story: 4-4 Auto-Summarization Pipeline
-- Purpose: Store auto-generated conversation summaries with metadata

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    message_range_start INTEGER NOT NULL,
    message_range_end INTEGER NOT NULL,
    key_topics JSONB,
    sentiment_score DECIMAL(3,2) CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    confidence_score DECIMAL(3,2) DEFAULT 0.9 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    processing_time_ms INTEGER,
    model_used VARCHAR(100) DEFAULT 'deepseek-main',
    prompt_version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_conversation_summaries_conversation_id
    ON conversation_summaries(conversation_id);

CREATE INDEX idx_conversation_summaries_user_id
    ON conversation_summaries(user_id);

CREATE INDEX idx_conversation_summaries_created_at
    ON conversation_summaries(created_at DESC);

CREATE INDEX idx_conversation_summaries_message_range
    ON conversation_summaries(conversation_id, message_range_start, message_range_end);

-- Partial index for recent summaries (used in memory injection)
CREATE INDEX idx_conversation_summaries_recent_high_confidence
    ON conversation_summaries(conversation_id, created_at DESC)
    WHERE confidence_score >= 0.8
    AND created_at > NOW() - INTERVAL '30 days';

-- GIN index for topic searching
CREATE INDEX idx_conversation_summaries_topics_gin
    ON conversation_summaries USING GIN(key_topics);

-- RLS (Row Level Security) policies
ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;

-- Users can only access their own conversation summaries
CREATE POLICY "Users can view own conversation summaries" ON conversation_summaries
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversation summaries" ON conversation_summaries
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversation summaries" ON conversation_summaries
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversation summaries" ON conversation_summaries
    FOR DELETE USING (auth.uid() = user_id);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversation_summaries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversation_summaries_updated_at_trigger
    BEFORE UPDATE ON conversation_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_summaries_updated_at();

-- Function to prevent duplicate summaries (similarity check)
CREATE OR REPLACE FUNCTION prevent_duplicate_summaries()
RETURNS TRIGGER AS $$
BEGIN
    -- Check for similar summary in the same conversation within the last hour
    IF EXISTS (
        SELECT 1 FROM conversation_summaries
        WHERE conversation_id = NEW.conversation_id
        AND user_id = NEW.user_id
        AND created_at > NOW() - INTERVAL '1 hour'
        AND similarity(summary_text, NEW.summary_text) > 0.8
        LIMIT 1
    ) THEN
        RAISE EXCEPTION 'Duplicate summary detected for conversation %', NEW.conversation_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to prevent duplicate summaries
CREATE TRIGGER conversation_summaries_prevent_duplicates
    BEFORE INSERT ON conversation_summaries
    FOR EACH ROW
    EXECUTE FUNCTION prevent_duplicate_summaries();

-- View for recent high-quality summaries (used by memory injection)
CREATE OR REPLACE VIEW recent_high_quality_summaries AS
SELECT
    cs.id,
    cs.conversation_id,
    cs.user_id,
    cs.summary_text,
    cs.key_topics,
    cs.sentiment_score,
    cs.confidence_score,
    cs.created_at,
    cs.processing_time_ms
FROM conversation_summaries cs
WHERE cs.confidence_score >= 0.8
    AND cs.created_at > NOW() - INTERVAL '30 days'
ORDER BY cs.confidence_score DESC, cs.created_at DESC;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON conversation_summaries TO authenticated;
GRANT SELECT ON recent_high_quality_summaries TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;