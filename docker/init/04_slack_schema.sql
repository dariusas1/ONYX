-- =============================================================================
-- Slack Connector Schema
-- =============================================================================

-- Slack-specific document metadata table
CREATE TABLE IF NOT EXISTS slack_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT UNIQUE NOT NULL,  -- Slack message timestamp (ts)
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    user_id TEXT NOT NULL,
    user_name TEXT,
    timestamp TIMESTAMP NOT NULL,
    text TEXT NOT NULL,
    thread_id TEXT,  -- Parent message timestamp if in thread
    message_type TEXT NOT NULL CHECK (message_type IN ('message', 'thread_parent', 'thread_reply')),
    reactions JSONB,  -- {"reaction_name": ["user1", "user2"]}
    mentions JSONB,  -- {"users": ["U123"], "channels": ["C456"]}
    file_attachments JSONB,  -- Array of file metadata
    indexed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for slack_documents
CREATE INDEX IF NOT EXISTS idx_slack_documents_source_id ON slack_documents(source_id);
CREATE INDEX IF NOT EXISTS idx_slack_documents_channel_id ON slack_documents(channel_id);
CREATE INDEX IF NOT EXISTS idx_slack_documents_user_id ON slack_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_slack_documents_timestamp ON slack_documents(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_slack_documents_thread_id ON slack_documents(thread_id);
CREATE INDEX IF NOT EXISTS idx_slack_documents_message_type ON slack_documents(message_type);
CREATE INDEX IF NOT EXISTS idx_slack_documents_indexed_at ON slack_documents(indexed_at DESC);

-- Slack sync state table (similar to drive_sync_state)
CREATE TABLE IF NOT EXISTS slack_sync_state (
    user_id UUID PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
    team_id TEXT NOT NULL,
    team_name TEXT,
    bot_user_id TEXT,
    last_message_ts TEXT,  -- Latest message timestamp synced per channel
    last_channel_scan TIMESTAMP,
    channels_synced INTEGER DEFAULT 0,
    messages_synced INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0,
    files_processed INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    last_sync_at TIMESTAMP DEFAULT NOW(),
    last_error TEXT,
    error_details JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for slack_sync_state
CREATE INDEX IF NOT EXISTS idx_slack_sync_state_last_sync_at ON slack_sync_state(last_sync_at DESC);
CREATE INDEX IF NOT EXISTS idx_slack_sync_state_team_id ON slack_sync_state(team_id);

-- Slack channel tracking table
CREATE TABLE IF NOT EXISTS slack_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_type TEXT NOT NULL CHECK (channel_type IN ('public_channel', 'private_channel', 'im', 'mpim')),
    is_archived BOOLEAN DEFAULT FALSE,
    is_member BOOLEAN DEFAULT FALSE,  -- Whether bot is member
    last_message_ts TEXT,
    last_sync_at TIMESTAMP,
    sync_status TEXT DEFAULT 'pending' CHECK (sync_status IN ('pending', 'syncing', 'completed', 'failed')),
    messages_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, channel_id)
);

-- Indexes for slack_channels
CREATE INDEX IF NOT EXISTS idx_slack_channels_user_id ON slack_channels(user_id);
CREATE INDEX IF NOT EXISTS idx_slack_channels_channel_type ON slack_channels(channel_type);
CREATE INDEX IF NOT EXISTS idx_slack_channels_sync_status ON slack_channels(sync_status);
CREATE INDEX IF NOT EXISTS idx_slack_channels_last_sync_at ON slack_channels(last_sync_at DESC);

-- Comments for documentation
COMMENT ON TABLE slack_documents IS 'Stores Slack message metadata and content for RAG indexing';
COMMENT ON TABLE slack_sync_state IS 'Tracks sync progress and state for Slack integration';
COMMENT ON TABLE slack_channels IS 'Stores information about Slack channels accessible to the bot';

-- Column comments
COMMENT ON COLUMN slack_documents.source_id IS 'Slack message timestamp (ts) - unique identifier';
COMMENT ON COLUMN slack_documents.thread_id IS 'Parent message timestamp if this is a thread reply';
COMMENT ON COLUMN slack_documents.message_type IS 'message: regular message, thread_parent: message with replies, thread_reply: reply to parent';
COMMENT ON COLUMN slack_documents.reactions IS 'JSON object of emoji reactions and users who reacted';
COMMENT ON COLUMN slack_documents.mentions IS 'JSON object of user and channel mentions in message';
COMMENT ON COLUMN slack_documents.file_attachments IS 'JSON array of file metadata objects';
COMMENT ON COLUMN slack_sync_state.last_message_ts IS 'Latest message timestamp processed (used for incremental sync)';
COMMENT ON COLUMN slack_channels.is_member IS 'Whether the bot has access to this channel';