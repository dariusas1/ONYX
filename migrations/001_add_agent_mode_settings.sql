-- Migration: Add Agent Mode Settings to Users Table
-- Description: Adds agent mode functionality with audit trail and compliance tracking
-- Version: 1.0
-- Created: 2025-11-15

-- ==========================================
-- SECTION 1: Add Agent Mode Columns to Users Table
-- ==========================================

-- Add agent mode related columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS agent_mode VARCHAR(10) DEFAULT 'chat' CHECK (agent_mode IN ('chat', 'agent')),
ADD COLUMN IF NOT EXISTS agent_mode_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS agent_mode_warning_accepted BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS agent_mode_consent_timestamp TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS agent_mode_ip_address INET,
ADD COLUMN IF NOT EXISTS agent_mode_user_agent TEXT,
ADD COLUMN IF NOT EXISTS agent_mode_last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add comments for documentation
COMMENT ON COLUMN users.agent_mode IS 'Current agent mode: chat or agent';
COMMENT ON COLUMN users.agent_mode_enabled IS 'Whether agent mode is enabled for the user';
COMMENT ON COLUMN users.agent_mode_warning_accepted IS 'Whether user has accepted the agent mode warning';
COMMENT ON COLUMN users.agent_mode_consent_timestamp IS 'Timestamp when user accepted agent mode warning';
COMMENT ON COLUMN users.agent_mode_ip_address IS 'IP address when agent mode was last enabled';
COMMENT ON COLUMN users.agent_mode_user_agent IS 'User agent string when agent mode was last enabled';
COMMENT ON COLUMN users.agent_mode_last_activity IS 'Last activity timestamp for agent mode usage';

-- ==========================================
-- SECTION 2: Create Agent Mode Audit Logs Table
-- ==========================================

-- Create audit log table for agent mode changes
CREATE TABLE IF NOT EXISTS agent_mode_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_mode_audit_logs_user_id ON agent_mode_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_mode_audit_logs_action ON agent_mode_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_agent_mode_audit_logs_created_at ON agent_mode_audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_mode_audit_logs_session_id ON agent_mode_audit_logs(session_id);

-- Add comments
COMMENT ON TABLE agent_mode_audit_logs IS 'Audit trail for agent mode changes and consent tracking';
COMMENT ON COLUMN agent_mode_audit_logs.action IS 'Type of action: mode_change, warning_accepted, agent_enabled, etc.';
COMMENT ON COLUMN agent_mode_audit_logs.details IS 'Additional details about the action in JSON format';
COMMENT ON COLUMN agent_mode_audit_logs.ip_address IS 'Client IP address for security tracking';
COMMENT ON COLUMN agent_mode_audit_logs.user_agent IS 'Client user agent string';
COMMENT ON COLUMN agent_mode_audit_logs.session_id IS 'Session identifier for tracking user sessions';

-- ==========================================
-- SECTION 3: Create Agent Mode Usage Statistics Table
-- ==========================================

-- Create table for tracking agent mode usage statistics
CREATE TABLE IF NOT EXISTS agent_mode_usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    agent_mode_requests INTEGER DEFAULT 0,
    agent_mode_requests_successful INTEGER DEFAULT 0,
    agent_mode_requests_failed INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    session_duration_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, date)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_agent_mode_usage_stats_user_id ON agent_mode_usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_mode_usage_stats_date ON agent_mode_usage_stats(date DESC);

-- Add comments
COMMENT ON TABLE agent_mode_usage_stats IS 'Daily usage statistics for agent mode';
COMMENT ON COLUMN agent_mode_usage_stats.agent_mode_requests IS 'Total number of agent mode requests';
COMMENT ON COLUMN agent_mode_usage_stats.agent_mode_requests_successful IS 'Number of successful agent mode requests';
COMMENT ON COLUMN agent_mode_usage_stats.agent_mode_requests_failed IS 'Number of failed agent mode requests';
COMMENT ON COLUMN agent_mode_usage_stats.total_tokens_used IS 'Total tokens consumed in agent mode';
COMMENT ON COLUMN agent_mode_usage_stats.session_duration_seconds IS 'Total time spent in agent mode';

-- ==========================================
-- SECTION 4: Row Level Security (RLS) Policies
-- ==========================================

-- Enable RLS on audit logs
ALTER TABLE agent_mode_audit_logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own audit logs
CREATE POLICY "Users can view own agent mode audit logs" ON agent_mode_audit_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Users can only insert their own audit logs
CREATE POLICY "Users can insert own agent mode audit logs" ON agent_mode_audit_logs
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Enable RLS on usage stats
ALTER TABLE agent_mode_usage_stats ENABLE ROW LEVEL SECURITY;

-- Users can only view their own usage stats
CREATE POLICY "Users can view own agent mode usage stats" ON agent_mode_usage_stats
    FOR SELECT USING (auth.uid() = user_id);

-- Users can only insert their own usage stats (handled by upsert)
CREATE POLICY "Users can upsert own agent mode usage stats" ON agent_mode_usage_stats
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can only update their own usage stats
CREATE POLICY "Users can update own agent mode usage stats" ON agent_mode_usage_stats
    FOR UPDATE USING (auth.uid() = user_id);

-- ==========================================
-- SECTION 5: Triggers and Functions
-- ==========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_agent_mode_audit_logs_updated_at
    BEFORE UPDATE ON agent_mode_audit_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_mode_usage_stats_updated_at
    BEFORE UPDATE ON agent_mode_usage_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to log agent mode changes
CREATE OR REPLACE FUNCTION log_agent_mode_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Log the change to audit table
    INSERT INTO agent_mode_audit_logs (
        user_id,
        action,
        details,
        ip_address,
        user_agent,
        session_id
    ) VALUES (
        OLD.id,
        'mode_change',
        jsonb_build_object(
            'previous_mode', OLD.agent_mode,
            'new_mode', NEW.agent_mode,
            'previous_enabled', OLD.agent_mode_enabled,
            'new_enabled', NEW.agent_mode_enabled,
            'previous_warning_accepted', OLD.agent_mode_warning_accepted,
            'new_warning_accepted', NEW.agent_mode_warning_accepted,
            'consent_timestamp', NEW.agent_mode_consent_timestamp,
            'change_reason', 'database_trigger'
        ),
        NEW.agent_mode_ip_address,
        NEW.agent_mode_user_agent,
        NULL -- session_id should be provided by application
    );

    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for agent mode changes
CREATE TRIGGER trigger_agent_mode_change_audit
    AFTER UPDATE OF agent_mode, agent_mode_enabled, agent_mode_warning_accepted, agent_mode_consent_timestamp
    ON users
    FOR EACH ROW
    WHEN (
        OLD.agent_mode IS DISTINCT FROM NEW.agent_mode OR
        OLD.agent_mode_enabled IS DISTINCT FROM NEW.agent_mode_enabled OR
        OLD.agent_mode_warning_accepted IS DISTINCT FROM NEW.agent_mode_warning_accepted OR
        OLD.agent_mode_consent_timestamp IS DISTINCT FROM NEW.agent_mode_consent_timestamp
    )
    EXECUTE FUNCTION log_agent_mode_change();

-- ==========================================
-- SECTION 6: Helper Functions
-- ==========================================

-- Function to get user's current agent mode settings
CREATE OR REPLACE FUNCTION get_user_agent_mode_settings(p_user_id UUID)
RETURNS TABLE (
    agent_mode VARCHAR(10),
    enabled BOOLEAN,
    warning_accepted BOOLEAN,
    consent_timestamp TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    user_agent TEXT,
    last_activity TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.agent_mode,
        u.agent_mode_enabled,
        u.agent_mode_warning_accepted,
        u.agent_mode_consent_timestamp,
        u.agent_mode_ip_address,
        u.agent_mode_user_agent,
        u.agent_mode_last_activity
    FROM users u
    WHERE u.id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user can use agent mode
CREATE OR REPLACE FUNCTION can_user_use_agent_mode(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_can_use BOOLEAN := false;
    v_warning_accepted BOOLEAN;
    v_enabled BOOLEAN;
BEGIN
    -- Check if user has enabled agent mode and accepted warning
    SELECT
        agent_mode_enabled,
        agent_mode_warning_accepted
    INTO v_enabled, v_warning_accepted
    FROM users
    WHERE id = p_user_id;

    v_can_use := v_enabled AND v_warning_accepted;

    RETURN v_can_use;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN false;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update agent mode usage stats
CREATE OR REPLACE FUNCTION update_agent_mode_usage_stats(
    p_user_id UUID,
    p_date DATE DEFAULT CURRENT_DATE,
    p_requests_increment INTEGER DEFAULT 0,
    p_successful_increment INTEGER DEFAULT 0,
    p_failed_increment INTEGER DEFAULT 0,
    p_tokens_increment INTEGER DEFAULT 0,
    p_session_duration_increment INTEGER DEFAULT 0
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO agent_mode_usage_stats (
        user_id,
        date,
        agent_mode_requests,
        agent_mode_requests_successful,
        agent_mode_requests_failed,
        total_tokens_used,
        session_duration_seconds
    ) VALUES (
        p_user_id,
        p_date,
        p_requests_increment,
        p_successful_increment,
        p_failed_increment,
        p_tokens_increment,
        p_session_duration_increment
    )
    ON CONFLICT (user_id, date) DO UPDATE SET
        agent_mode_requests = agent_mode_usage_stats.agent_mode_requests + p_requests_increment,
        agent_mode_requests_successful = agent_mode_usage_stats.agent_mode_requests_successful + p_successful_increment,
        agent_mode_requests_failed = agent_mode_usage_stats.agent_mode_requests_failed + p_failed_increment,
        total_tokens_used = agent_mode_usage_stats.total_tokens_used + p_tokens_increment,
        session_duration_seconds = agent_mode_usage_stats.session_duration_seconds + p_session_duration_increment,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- SECTION 7: Constraints and Validation
-- ==========================================

-- Add constraints to ensure data integrity
ALTER TABLE users
ADD CONSTRAINT IF NOT EXISTS chk_agent_mode_enabled_requires_warning
    CHECK (agent_mode_enabled = false OR agent_mode_warning_accepted = true),
ADD CONSTRAINT IF NOT EXISTS chk_agent_mode_consent_requires_warning
    CHECK (agent_mode_consent_timestamp IS NULL OR agent_mode_warning_accepted = true);

-- Add constraints to audit logs
ALTER TABLE agent_mode_audit_logs
ADD CONSTRAINT IF NOT EXISTS chk_agent_mode_audit_action
    CHECK (action IN (
        'mode_change',
        'warning_shown',
        'warning_accepted',
        'warning_rejected',
        'agent_enabled',
        'agent_disabled',
        'consent_revoked',
        'session_start',
        'session_end',
        'request_executed',
        'request_completed',
        'request_failed'
    ));

-- ==========================================
-- SECTION 8: Views for Reporting
-- ==========================================

-- Create view for agent mode activity summary
CREATE OR REPLACE VIEW agent_mode_activity_summary AS
SELECT
    u.id as user_id,
    u.email,
    u.agent_mode,
    u.agent_mode_enabled,
    u.agent_mode_warning_accepted,
    u.agent_mode_consent_timestamp,
    u.agent_mode_last_activity,
    COALESCE(stats.total_requests, 0) as total_requests,
    COALESCE(stats.total_successful, 0) as total_successful,
    COALESCE(stats.total_failed, 0) as total_failed,
    COALESCE(stats.total_tokens, 0) as total_tokens,
    COALESCE(stats.total_session_time, 0) as total_session_time,
    COALESCE(audit_logs.total_actions, 0) as total_audit_actions
FROM users u
LEFT JOIN (
    SELECT
        user_id,
        SUM(agent_mode_requests) as total_requests,
        SUM(agent_mode_requests_successful) as total_successful,
        SUM(agent_mode_requests_failed) as total_failed,
        SUM(total_tokens_used) as total_tokens,
        SUM(session_duration_seconds) as total_session_time
    FROM agent_mode_usage_stats
    GROUP BY user_id
) stats ON u.id = stats.user_id
LEFT JOIN (
    SELECT
        user_id,
        COUNT(*) as total_actions
    FROM agent_mode_audit_logs
    GROUP BY user_id
) audit_logs ON u.id = audit_logs.user_id;

-- ==========================================
-- SECTION 9: Migration Verification
-- ==========================================

-- Verify the migration was successful
DO $$
DECLARE
    v_users_columns INTEGER;
    v_audit_table_exists BOOLEAN;
    v_stats_table_exists BOOLEAN;
    v_agent_mode_policy_exists BOOLEAN;
BEGIN
    -- Check if columns were added to users table
    SELECT COUNT(*) INTO v_users_columns
    FROM information_schema.columns
    WHERE table_name = 'users'
    AND column_name IN ('agent_mode', 'agent_mode_enabled', 'agent_mode_warning_accepted');

    -- Check if audit table exists
    SELECT EXISTS(
        SELECT FROM information_schema.tables
        WHERE table_name = 'agent_mode_audit_logs'
    ) INTO v_audit_table_exists;

    -- Check if stats table exists
    SELECT EXISTS(
        SELECT FROM information_schema.tables
        WHERE table_name = 'agent_mode_usage_stats'
    ) INTO v_stats_table_exists;

    -- Check if RLS policy exists
    SELECT EXISTS(
        SELECT FROM pg_policies
        WHERE tablename = 'agent_mode_audit_logs'
    ) INTO v_agent_mode_policy_exists;

    -- Raise exception if migration failed
    IF v_users_columns < 3 OR NOT v_audit_table_exists OR NOT v_stats_table_exists OR NOT v_agent_mode_policy_exists THEN
        RAISE EXCEPTION 'Migration verification failed. Expected components not found.';
    END IF;

    RAISE NOTICE 'Agent mode migration completed successfully.';
END $$;