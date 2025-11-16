-- Auto-Summarization Pipeline Schema Migration
-- Story 4-4: Auto-Summarization Pipeline
-- Adding tables and indexes for summarization pipeline functionality

-- Summarization metrics table for performance tracking
CREATE TABLE IF NOT EXISTS summarization_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL,
    processing_time INTEGER NOT NULL, -- in milliseconds
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    message_range_start INTEGER NOT NULL,
    message_range_end INTEGER NOT NULL,
    summary_length INTEGER,
    topics_count INTEGER,
    sentiment_score FLOAT,
    model_version TEXT DEFAULT 'deepseek-main',
    prompt_version TEXT DEFAULT 'v1.0',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Update conversation_summaries table to match documentation requirements
ALTER TABLE conversation_summaries
ADD COLUMN IF NOT EXISTS message_range_start INTEGER,
ADD COLUMN IF NOT EXISTS message_range_end INTEGER,
ADD COLUMN IF NOT EXISTS key_topics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
ADD COLUMN IF NOT EXISTS processing_time INTEGER, -- in milliseconds
ADD COLUMN IF NOT EXISTS generated_by TEXT DEFAULT 'auto_summary' CHECK (generated_by IN ('auto_summary', 'manual', 'extracted')),
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Drop existing columns if they conflict with new structure
DO $$
BEGIN
    -- Drop columns that are being replaced
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversation_summaries' AND column_name = 'key_points') THEN
        ALTER TABLE conversation_summaries DROP COLUMN key_points;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversation_summaries' AND column_name = 'action_items') THEN
        ALTER TABLE conversation_summaries DROP COLUMN action_items;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversation_summaries' AND column_name = 'confidence') THEN
        ALTER TABLE conversation_summaries DROP COLUMN confidence;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversation_summaries' AND column_name = 'metadata') THEN
        ALTER TABLE conversation_summaries DROP COLUMN metadata;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conversation_summaries' AND column_name = 'generated_by') THEN
        ALTER TABLE conversation_summaries DROP COLUMN generated_by;
    END IF;
END $$;

-- Add the columns again to ensure correct structure
ALTER TABLE conversation_summaries
ADD COLUMN IF NOT EXISTS key_topics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
ADD COLUMN IF NOT EXISTS processing_time INTEGER,
ADD COLUMN IF NOT EXISTS generated_by TEXT DEFAULT 'auto_summary',
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Summarization job queue tracking table
CREATE TABLE IF NOT EXISTS summarization_job_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL,
    message_id UUID,
    message_count INTEGER NOT NULL,
    message_range_start INTEGER NOT NULL,
    message_range_end INTEGER NOT NULL,
    job_id TEXT NOT NULL, -- BullMQ job ID
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    queued_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for summarization_metrics
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_conversation ON summarization_metrics(conversation_id);
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_user_id ON summarization_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_created_at ON summarization_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_success ON summarization_metrics(success);
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_processing_time ON summarization_metrics(processing_time);

-- Indexes for conversation_summaries (updated)
CREATE INDEX IF NOT EXISTS idx_summaries_topics ON conversation_summaries USING gin(key_topics) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_summaries_sentiment ON conversation_summaries(sentiment_score) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_summaries_message_range ON conversation_summaries(conversation_id, message_range_start, message_range_end) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_summaries_processing_time ON conversation_summaries(processing_time) WHERE is_deleted = FALSE;

-- Indexes for summarization_job_tracking
CREATE INDEX IF NOT EXISTS idx_job_tracking_conversation ON summarization_job_tracking(conversation_id);
CREATE INDEX IF NOT EXISTS idx_job_tracking_user_id ON summarization_job_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_job_tracking_status ON summarization_job_tracking(status);
CREATE INDEX IF NOT EXISTS idx_job_tracking_job_id ON summarization_job_tracking(job_id);
CREATE INDEX IF NOT EXISTS idx_job_tracking_created_at ON summarization_job_tracking(created_at DESC);

-- Add trigger for updated_at on summarization_job_tracking
CREATE TRIGGER update_summarization_job_tracking_updated_at
    BEFORE UPDATE ON summarization_job_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate summarization success rate
CREATE OR REPLACE FUNCTION get_summarization_success_rate(
    p_user_id UUID,
    p_time_range INTERVAL DEFAULT '24 hours'
) RETURNS FLOAT AS $$
DECLARE
    total_jobs INTEGER;
    successful_jobs INTEGER;
    success_rate FLOAT;
BEGIN
    SELECT COUNT(*) INTO total_jobs
    FROM summarization_metrics
    WHERE user_id = p_user_id
    AND created_at >= NOW() - p_time_range;

    IF total_jobs = 0 THEN
        RETURN 0.0;
    END IF;

    SELECT COUNT(*) INTO successful_jobs
    FROM summarization_metrics
    WHERE user_id = p_user_id
    AND created_at >= NOW() - p_time_range
    AND success = TRUE;

    success_rate := (successful_jobs::FLOAT / total_jobs::FLOAT) * 100;

    RETURN ROUND(success_rate, 2);
END;
$$ LANGUAGE plpgsql;

-- Function to get average processing time
CREATE OR REPLACE FUNCTION get_avg_summarization_processing_time(
    p_user_id UUID,
    p_time_range INTERVAL DEFAULT '24 hours'
) RETURNS INTEGER AS $$
DECLARE
    avg_time INTEGER;
BEGIN
    SELECT COALESCE(AVG(processing_time), 0)::INTEGER INTO avg_time
    FROM summarization_metrics
    WHERE user_id = p_user_id
    AND created_at >= NOW() - p_time_range
    AND success = TRUE;

    RETURN avg_time;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old summarization metrics
CREATE OR REPLACE FUNCTION cleanup_old_summarization_metrics(
    p_days_to_keep INTEGER DEFAULT 30
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM summarization_metrics
    WHERE created_at < NOW() - INTERVAL '1 day' * p_days_to_keep;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add helpful comments
COMMENT ON TABLE summarization_metrics IS 'Performance tracking and analytics for auto-summarization pipeline';
COMMENT ON TABLE summarization_job_tracking IS 'Job queue tracking for summarization background processing';
COMMENT ON COLUMN summarization_metrics.processing_time IS 'Processing time in milliseconds';
COMMENT ON COLUMN summarization_metrics.sentiment_score IS 'Sentiment score ranging from -1 (negative) to 1 (positive)';
COMMENT ON COLUMN conversation_summaries.key_topics IS 'JSON array of extracted key topics from summary';
COMMENT ON COLUMN conversation_summaries.sentiment_score IS 'Overall sentiment of summarized conversation segment';

-- Migration completed successfully
SELECT 'Auto-summarization pipeline schema migration completed successfully' as status;