-- =============================================================================
-- ONYX Slack Connector Database Schema
-- =============================================================================
-- Schema for storing Slack messages, attachments, and sync state for RAG integration

-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Extension for text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- SLACK MESSAGES TABLE
-- =============================================================================
-- Core table for storing Slack messages with metadata

CREATE TABLE IF NOT EXISTS slack_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slack_message_id VARCHAR(50) UNIQUE NOT NULL,
  channel_id VARCHAR(50) NOT NULL,
  user_id VARCHAR(50) NOT NULL,
  thread_id VARCHAR(50),
  parent_message_id VARCHAR(50),
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  text TEXT,
  message_type VARCHAR(20) DEFAULT 'message',
  subtype VARCHAR(50),
  team_id VARCHAR(50),

  -- Search and indexing fields
  search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', COALESCE(text, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(subtype, '')), 'B')
  ) STORED,

  -- Metadata and tracking
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  indexed_at TIMESTAMP WITH TIME ZONE,
  sync_batch_id UUID,

  -- Constraints
  CONSTRAINT slack_messages_check CHECK (
    slack_message_id IS NOT NULL AND
    channel_id IS NOT NULL AND
    user_id IS NOT NULL
  )
);

-- =============================================================================
-- SLACK ATTACHMENTS TABLE
-- =============================================================================
-- Table for storing file attachment metadata

CREATE TABLE IF NOT EXISTS slack_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID REFERENCES slack_messages(id) ON DELETE CASCADE,
  slack_file_id VARCHAR(50) UNIQUE NOT NULL,
  filename VARCHAR(255) NOT NULL,
  file_type VARCHAR(50),
  mimetype VARCHAR(100),
  size_bytes INTEGER,
  url TEXT,
  permalink_url TEXT,
  local_path VARCHAR(500),

  -- Content extraction
  content_extracted BOOLEAN DEFAULT FALSE,
  extracted_content TEXT,
  extracted_at TIMESTAMP WITH TIME ZONE,
  extraction_error TEXT,

  -- Metadata
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Constraints
  CONSTRAINT slack_attachments_check CHECK (
    slack_file_id IS NOT NULL AND
    filename IS NOT NULL
  )
);

-- =============================================================================
-- SLACK SYNC STATE TABLE
-- =============================================================================
-- Table for tracking sync state per channel

CREATE TABLE IF NOT EXISTS slack_sync_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id VARCHAR(50) UNIQUE NOT NULL,
  workspace_id VARCHAR(50),

  -- Sync tracking
  last_sync_timestamp TIMESTAMP WITH TIME ZONE,
  last_message_timestamp TIMESTAMP WITH TIME ZONE,
  oldest_message_timestamp TIMESTAMP WITH TIME ZONE,
  message_count INTEGER DEFAULT 0,
  attachment_count INTEGER DEFAULT 0,

  -- Error tracking
  error_count INTEGER DEFAULT 0,
  last_error TEXT,
  last_error_at TIMESTAMP WITH TIME ZONE,
  consecutive_errors INTEGER DEFAULT 0,

  -- Status
  sync_status VARCHAR(20) DEFAULT 'pending'
    CHECK (sync_status IN ('pending', 'running', 'success', 'error', 'disabled')),
  is_active BOOLEAN DEFAULT TRUE,

  -- Configuration
  sync_interval_seconds INTEGER DEFAULT 600, -- 10 minutes
  batch_size INTEGER DEFAULT 200,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_success_at TIMESTAMP WITH TIME ZONE
);

-- =============================================================================
-- SLACK CHANNELS TABLE
-- =============================================================================
-- Table for caching channel information

CREATE TABLE IF NOT EXISTS slack_channels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id VARCHAR(50) UNIQUE NOT NULL,
  workspace_id VARCHAR(50),
  name VARCHAR(100) NOT NULL,
  display_name VARCHAR(100),
  purpose TEXT,
  topic TEXT,
  channel_type VARCHAR(20) NOT NULL
    CHECK (channel_type IN ('public_channel', 'private_channel', 'mpim', 'im')),
  is_member BOOLEAN DEFAULT FALSE,
  is_archived BOOLEAN DEFAULT FALSE,
  created_by VARCHAR(50),
  created_at INTEGER, -- Slack timestamp
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- SLACK USERS TABLE
-- =============================================================================
-- Table for caching user information

CREATE TABLE IF NOT EXISTS slack_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(50) UNIQUE NOT NULL,
  workspace_id VARCHAR(50),
  name VARCHAR(100) NOT NULL,
  display_name VARCHAR(100),
  real_name VARCHAR(100),
  email VARCHAR(255),
  avatar_url TEXT,
  is_bot BOOLEAN DEFAULT FALSE,
  is_app_user BOOLEAN DEFAULT FALSE,
  is_admin BOOLEAN DEFAULT FALSE,
  is_owner BOOLEAN DEFAULT FALSE,
  profile JSONB DEFAULT '{}',
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Slack messages indexes
CREATE INDEX IF NOT EXISTS idx_slack_messages_slack_id ON slack_messages(slack_message_id);
CREATE INDEX IF NOT EXISTS idx_slack_messages_channel_timestamp ON slack_messages(channel_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_slack_messages_thread ON slack_messages(thread_id) WHERE thread_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_slack_messages_user ON slack_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_slack_messages_timestamp ON slack_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_slack_messages_workspace ON slack_messages(team_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_slack_messages_search ON slack_messages USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_slack_messages_sync_batch ON slack_messages(sync_batch_id);

-- Slack attachments indexes
CREATE INDEX IF NOT EXISTS idx_slack_attachments_message ON slack_attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_slack_attachments_slack_id ON slack_attachments(slack_file_id);
CREATE INDEX IF NOT EXISTS idx_slack_attachments_file_type ON slack_attachments(file_type);
CREATE INDEX IF NOT EXISTS idx_slack_attachments_extracted ON slack_attachments(content_extracted) WHERE content_extracted = TRUE;

-- Slack sync state indexes
CREATE INDEX IF NOT EXISTS idx_slack_sync_state_channel ON slack_sync_state(channel_id);
CREATE INDEX IF NOT EXISTS idx_slack_sync_state_status ON slack_sync_state(sync_status);
CREATE INDEX IF NOT EXISTS idx_slack_sync_state_active ON slack_sync_state(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_slack_sync_state_last_sync ON slack_sync_state(last_sync_timestamp DESC);

-- Slack channels indexes
CREATE INDEX IF NOT EXISTS idx_slack_channels_channel_id ON slack_channels(channel_id);
CREATE INDEX IF NOT EXISTS idx_slack_channels_workspace ON slack_channels(workspace_id);
CREATE INDEX IF NOT EXISTS idx_slack_channels_type ON slack_channels(channel_type);
CREATE INDEX IF NOT EXISTS idx_slack_channels_member ON slack_channels(is_member) WHERE is_member = TRUE;

-- Slack users indexes
CREATE INDEX IF NOT EXISTS idx_slack_users_user_id ON slack_users(user_id);
CREATE INDEX IF NOT EXISTS idx_slack_users_workspace ON slack_users(workspace_id);
CREATE INDEX IF NOT EXISTS idx_slack_users_bot ON slack_users(is_bot) WHERE is_bot = TRUE;

-- =============================================================================
-- TRIGGERS AND FUNCTIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_slack_messages_updated_at
  BEFORE UPDATE ON slack_messages
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_slack_attachments_updated_at
  BEFORE UPDATE ON slack_attachments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_slack_sync_state_updated_at
  BEFORE UPDATE ON slack_sync_state
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SEARCH FUNCTIONS
-- =============================================================================

-- Function to search Slack messages
CREATE OR REPLACE FUNCTION search_slack_messages(
  search_query TEXT,
  workspace_id_param VARCHAR(50) DEFAULT NULL,
  channel_id_param VARCHAR(50) DEFAULT NULL,
  user_id_param VARCHAR(50) DEFAULT NULL,
  limit_param INTEGER DEFAULT 20,
  offset_param INTEGER DEFAULT 0
)
RETURNS TABLE(
  message_id UUID,
  slack_message_id VARCHAR(50),
  channel_id VARCHAR(50),
  user_id VARCHAR(50),
  thread_id VARCHAR(50),
  timestamp TIMESTAMP WITH TIME ZONE,
  text TEXT,
  rank REAL,
  snippet TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    sm.id as message_id,
    sm.slack_message_id,
    sm.channel_id,
    sm.user_id,
    sm.thread_id,
    sm.timestamp,
    sm.text,
    ts_rank(sm.search_vector, plainto_tsquery('english', search_query)) as rank,
    ts_headline('english', sm.text, plainto_tsquery('english', search_query)) as snippet
  FROM slack_messages sm
  WHERE
    sm.search_vector @@ plainto_tsquery('english', search_query)
    AND (workspace_id_param IS NULL OR sm.team_id = workspace_id_param)
    AND (channel_id_param IS NULL OR sm.channel_id = channel_id_param)
    AND (user_id_param IS NULL OR sm.user_id = user_id_param)
  ORDER BY rank DESC, sm.timestamp DESC
  LIMIT limit_param OFFSET offset_param;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VIEWS
-- =============================================================================

-- View for sync status overview
CREATE OR REPLACE VIEW slack_sync_overview AS
SELECT
  sss.channel_id,
  sc.name as channel_name,
  sc.display_name,
  sc.channel_type,
  sss.sync_status,
  sss.last_sync_timestamp,
  sss.last_message_timestamp,
  sss.message_count,
  sss.attachment_count,
  sss.error_count,
  sss.consecutive_errors,
  sss.is_active,
  CASE
    WHEN sss.consecutive_errors >= 3 THEN 'critical'
    WHEN sss.error_count > 0 THEN 'warning'
    WHEN sss.last_sync_timestamp > NOW() - INTERVAL '1 hour' THEN 'healthy'
    ELSE 'stale'
  END as health_status
FROM slack_sync_state sss
JOIN slack_channels sc ON sss.channel_id = sc.channel_id
WHERE sss.is_active = TRUE;

-- =============================================================================
-- INITIAL DATA AND CONFIGURATION
-- =============================================================================

-- Insert default sync configuration for common settings
INSERT INTO slack_sync_state (
  channel_id,
  workspace_id,
  sync_interval_seconds,
  batch_size,
  sync_status
) VALUES
  ('default', 'default', 600, 200, 'pending')
ON CONFLICT (channel_id) DO NOTHING;

-- =============================================================================
-- COMMENTS AND DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE slack_messages IS 'Core table storing Slack messages with full-text search capabilities';
COMMENT ON TABLE slack_attachments IS 'File attachments from Slack messages with content extraction status';
COMMENT ON TABLE slack_sync_state IS 'Per-channel sync state tracking with error handling';
COMMENT ON TABLE slack_channels IS 'Cached Slack channel information and metadata';
COMMENT ON TABLE slack_users IS 'Cached Slack user information and profiles';

COMMENT ON COLUMN slack_messages.search_vector IS 'Automatically generated search vector for full-text search';
COMMENT ON COLUMN slack_messages.thread_id IS 'Thread ID if message is part of a thread';
COMMENT ON COLUMN slack_messages.parent_message_id IS 'Parent message ID for threaded conversations';
COMMENT ON COLUMN slack_sync_state.consecutive_errors IS 'Count of consecutive errors for automatic backoff';
COMMENT ON COLUMN slack_attachments.extracted_content IS 'Extracted text content from file attachments';