-- Migration: Summarization Metrics Schema
-- Story: 4-4 Auto-Summarization Pipeline
-- Purpose: Add tables for tracking summarization performance and trigger events

-- Enable pg_similarity extension for text similarity checks
CREATE EXTENSION IF NOT EXISTS "pg_similarity";

-- Summarization metrics table for performance tracking
CREATE TABLE IF NOT EXISTS summarization_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    processing_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Summarization trigger logs for analytics
CREATE TABLE IF NOT EXISTS summarization_trigger_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_count INTEGER NOT NULL,
    trigger_interval INTEGER NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'trigger_detected', 'job_queued', 'job_queue_failed'
    priority INTEGER,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance indexes for summarization_metrics
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_conversation_id
    ON summarization_metrics(conversation_id);

CREATE INDEX IF NOT EXISTS idx_summarization_metrics_user_id
    ON summarization_metrics(user_id);

CREATE INDEX IF NOT EXISTS idx_summarization_metrics_created_at
    ON summarization_metrics(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_summarization_metrics_success_created
    ON summarization_metrics(success, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_summarization_metrics_processing_time
    ON summarization_metrics(processing_time_ms) WHERE processing_time_ms IS NOT NULL;

-- Performance indexes for summarization_trigger_logs
CREATE INDEX IF NOT EXISTS idx_summarization_trigger_logs_conversation_id
    ON summarization_trigger_logs(conversation_id);

CREATE INDEX IF NOT EXISTS idx_summarization_trigger_logs_user_id
    ON summarization_trigger_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_summarization_trigger_logs_created_at
    ON summarization_trigger_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_summarization_trigger_logs_event_type
    ON summarization_trigger_logs(event_type, created_at DESC);

-- Partial index for failed processing (for monitoring)
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_failures
    ON summarization_metrics(conversation_id, user_id, created_at DESC)
    WHERE success = FALSE;

-- Partial index for slow processing (performance monitoring)
CREATE INDEX IF NOT EXISTS idx_summarization_metrics_slow_processing
    ON summarization_metrics(created_at DESC, processing_time_ms DESC)
    WHERE processing_time_ms > 5000; -- > 5 seconds

-- RLS (Row Level Security) policies
ALTER TABLE summarization_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE summarization_trigger_logs ENABLE ROW LEVEL SECURITY;

-- Users can view their own summarization metrics
CREATE POLICY "Users can view own summarization metrics" ON summarization_metrics
    FOR SELECT USING (auth.uid() = user_id);

-- Users can view their own trigger logs
CREATE POLICY "Users can view own trigger logs" ON summarization_trigger_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Service/worker roles can insert metrics (adjust based on your auth setup)
CREATE POLICY "Service can insert summarization metrics" ON summarization_metrics
    FOR INSERT WITH CHECK (
        auth.uid() = user_id OR
        current_setting('app.is_service_worker', true) = 'true'
    );

CREATE POLICY "Service can insert trigger logs" ON summarization_trigger_logs
    FOR INSERT WITH CHECK (
        auth.uid() = user_id OR
        current_setting('app.is_service_worker', true) = 'true'
    );

-- Views for analytics and monitoring
CREATE OR REPLACE VIEW summarization_performance_summary AS
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN success = TRUE THEN 1 END) as successful_jobs,
    COUNT(CASE WHEN success = FALSE THEN 1 END) as failed_jobs,
    ROUND(AVG(processing_time_ms)) as avg_processing_time_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms)) as p95_processing_time_ms,
    ROUND(AVG(tokens_used)) as avg_tokens_used,
    COUNT(DISTINCT conversation_id) as unique_conversations,
    COUNT(DISTINCT user_id) as unique_users
FROM summarization_metrics
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

CREATE OR REPLACE VIEW recent_summarization_failures AS
SELECT
    sm.conversation_id,
    sm.user_id,
    sm.error_message,
    sm.processing_time_ms,
    sm.retry_count,
    sm.created_at,
    c.title as conversation_title
FROM summarization_metrics sm
LEFT JOIN conversations c ON sm.conversation_id = c.id
WHERE sm.success = FALSE
    AND sm.created_at > NOW() - INTERVAL '24 hours'
ORDER BY sm.created_at DESC;

CREATE OR REPLACE VIEW summarization_trigger_analytics AS
SELECT
    DATE_TRUNC('day', created_at) as day,
    COUNT(*) as total_triggers,
    COUNT(CASE WHEN event_type = 'job_queued' THEN 1 END) as jobs_queued,
    COUNT(CASE WHEN event_type = 'job_queue_failed' THEN 1 END) as jobs_failed,
    COUNT(CASE WHEN event_type = 'trigger_detected' THEN 1 END) as triggers_detected,
    COUNT(DISTINCT conversation_id) as unique_conversations,
    COUNT(DISTINCT user_id) as unique_users,
    ROUND(AVG(message_count)) as avg_message_count_at_trigger
FROM summarization_trigger_logs
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY day DESC;

-- Function to clean up old metrics data
CREATE OR REPLACE FUNCTION cleanup_summarization_metrics()
RETURNS INTEGER AS $$
DECLARE
    metrics_deleted INTEGER;
    logs_deleted INTEGER;
BEGIN
    -- Delete metrics older than 90 days
    DELETE FROM summarization_metrics
    WHERE created_at < NOW() - INTERVAL '90 days';

    GET DIAGNOSTICS metrics_deleted = ROW_COUNT;

    -- Delete trigger logs older than 30 days
    DELETE FROM summarization_trigger_logs
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS logs_deleted = ROW_COUNT;

    -- Log the cleanup
    RAISE NOTICE 'Cleanup completed: %d metrics records and %d trigger log records deleted',
                   metrics_deleted, logs_deleted;

    RETURN metrics_deleted + logs_deleted;
END;
$$ LANGUAGE plpgsql;

-- Function to get summarization performance stats
CREATE OR REPLACE FUNCTION get_summarization_performance_stats(
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    total_jobs BIGINT,
    successful_jobs BIGINT,
    failed_jobs BIGINT,
    success_rate DECIMAL(5,2),
    avg_processing_time_ms DECIMAL(10,2),
    p95_processing_time_ms DECIMAL(10,2),
    avg_tokens_used DECIMAL(10,2),
    unique_conversations BIGINT,
    unique_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) as total_jobs,
        COUNT(CASE WHEN success = TRUE THEN 1 END) as successful_jobs,
        COUNT(CASE WHEN success = FALSE THEN 1 END) as failed_jobs,
        ROUND(
            (COUNT(CASE WHEN success = TRUE THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2
        ) as success_rate,
        ROUND(AVG(processing_time_ms), 2) as avg_processing_time_ms,
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms), 2) as p95_processing_time_ms,
        ROUND(AVG(tokens_used), 2) as avg_tokens_used,
        COUNT(DISTINCT conversation_id) as unique_conversations,
        COUNT(DISTINCT user_id) as unique_users
    FROM summarization_metrics
    WHERE created_at > NOW() - INTERVAL '%s hours'
    FORMAT p_hours;
END;
$$ LANGUAGE plpgsql;

-- Function to get trigger analytics
CREATE OR REPLACE FUNCTION get_trigger_analytics(
    p_days INTEGER DEFAULT 7
)
RETURNS TABLE (
    total_triggers BIGINT,
    jobs_queued BIGINT,
    jobs_failed BIGINT,
    queue_success_rate DECIMAL(5,2),
    avg_message_count DECIMAL(10,2),
    unique_conversations BIGINT,
    unique_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH trigger_stats AS (
        SELECT
            COUNT(*) as total_triggers,
            COUNT(CASE WHEN event_type = 'job_queued' THEN 1 END) as jobs_queued,
            COUNT(CASE WHEN event_type = 'job_queue_failed' THEN 1 END) as jobs_failed,
            AVG(message_count) as avg_message_count,
            COUNT(DISTINCT conversation_id) as unique_conversations,
            COUNT(DISTINCT user_id) as unique_users
        FROM summarization_trigger_logs
        WHERE created_at > NOW() - INTERVAL '%s days'
        FORMAT p_days
    )
    SELECT
        total_triggers,
        jobs_queued,
        jobs_failed,
        ROUND(
            (jobs_queued * 100.0 / NULLIF(total_triggers, 0)), 2
        ) as queue_success_rate,
        ROUND(avg_message_count, 2) as avg_message_count,
        unique_conversations,
        unique_users
    FROM trigger_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON summarization_metrics TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON summarization_trigger_logs TO authenticated;
GRANT SELECT ON summarization_performance_summary TO authenticated;
GRANT SELECT ON recent_summarization_failures TO authenticated;
GRANT SELECT ON summarization_trigger_analytics TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_summarization_metrics() TO authenticated;
GRANT EXECUTE ON FUNCTION get_summarization_performance_stats(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_trigger_analytics(INTEGER) TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Add helpful comments
COMMENT ON TABLE summarization_metrics IS 'Performance metrics for auto-summarization jobs';
COMMENT ON TABLE summarization_trigger_logs IS 'Analytics tracking for summarization trigger events';
COMMENT ON VIEW summarization_performance_summary IS 'Hourly performance summary for monitoring';
COMMENT ON VIEW recent_summarization_failures IS 'Recent summarization failures for debugging';
COMMENT ON VIEW summarization_trigger_analytics IS 'Daily trigger analytics and success rates';

-- Migration completed successfully
SELECT 'Summarization metrics schema migration completed successfully' as status;