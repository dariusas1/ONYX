// =============================================================================
// ONYX Slack Connector Types
// =============================================================================
// TypeScript interfaces for Slack API integration and message processing

import { WebClient } from '@slack/web-api';

// =============================================================================
// SLACK API TYPES
// =============================================================================

export interface SlackMessage {
  id: string;
  channel_id: string;
  user_id: string;
  thread_id?: string;
  parent_message_id?: string;
  timestamp: string; // Slack timestamp format
  text?: string;
  message_type: 'message' | 'file_share' | 'bot_message';
  subtype?: string;
  team_id?: string;
  files?: SlackFile[];
  attachments?: SlackAttachment[];
  reactions?: SlackReaction[];
  is_deleted?: boolean;
}

export interface SlackFile {
  id: string;
  name: string;
  mimetype?: string;
  filetype?: string;
  size: number;
  url_private?: string;
  url_private_download?: string;
  permalink?: string;
  permalink_public?: string;
  title?: string;
  mode?: string;
  editable?: boolean;
  external_id?: string;
  external_url?: string;
  has_rich_preview?: boolean;
  content_extractor?: string;
  thumb_64?: string;
  thumb_80?: string;
  thumb_360?: string;
  thumb_480?: string;
  thumb_720?: string;
  thumb_960?: string;
  thumb_1024?: string;
  original_h?: number;
  original_w?: number;
  thumb_tiny?: string;
  thumb_video?: string;
  display_as_bot?: boolean;
}

export interface SlackAttachment {
  id: string;
  fallback?: string;
  color?: string;
  pretext?: string;
  author_name?: string;
  author_link?: string;
  author_icon?: string;
  title?: string;
  title_link?: string;
  text?: string;
  fields?: SlackAttachmentField[];
  image_url?: string;
  thumb_url?: string;
  footer?: string;
  footer_icon?: string;
  ts?: string;
  actions?: SlackAttachmentAction[];
  callback_id?: string;
  attachment_type?: string;
  blocks?: any[];
  app_id?: string;
  bot_id?: string;
  channel_id?: string;
  is_app_unfurl?: boolean;
  is_msg_unfurl?: boolean;
  is_reply_unfurl?: boolean;
  original_url?: string;
  app_unfurl_url?: string;
}

export interface SlackAttachmentField {
  title?: string;
  value?: string;
  short?: boolean;
}

export interface SlackAttachmentAction {
  id: string;
  name: string;
  text: string;
  type: string;
  value?: string;
  url?: string;
  style?: string;
}

export interface SlackReaction {
  name: string;
  count: number;
  users: string[];
}

export interface SlackChannel {
  id: string;
  name: string;
  display_name?: string;
  purpose?: {
    value: string;
  };
  topic?: {
    value: string;
  };
  is_member: boolean;
  is_archived: boolean;
  is_general: boolean;
  created: number;
  creator: string;
  is_shared: boolean;
  is_org_shared: boolean;
  is_pending_ext_shared: boolean;
  parent_conversation?: string;
  conversation_host_id?: string;
  msg_count?: number;
  member_count?: number;
  pins?: string[];
  locale?: string;
  last_read?: string;
  latest?: string;
  unread_count?: number;
  unread_count_display?: number;
  connected_team_ids?: string[];
  is_open: boolean;
  priority?: number;
  is_thread_broadcast?: boolean;
}

export interface SlackUser {
  id: string;
  team_id?: string;
  name: string;
  deleted: boolean;
  color: string;
  real_name: string;
  tz: string;
  tz_label: string;
  tz_offset: number;
  profile: {
    title?: string;
    phone?: string;
    skype?: string;
    real_name?: string;
    real_name_normalized?: string;
    display_name?: string;
    display_name_normalized?: string;
    status_text?: string;
    status_emoji?: string;
    status_expiration?: number;
    avatar_hash?: string;
    image_original?: string;
    is_custom_image?: boolean;
    email?: string;
    first_name?: string;
    last_name?: string;
    image_24?: string;
    image_32?: string;
    image_48?: string;
    image_72?: string;
    image_192?: string;
    image_512?: string;
    image_1024?: string;
    status_text_canonical?: string;
    team?: string;
  };
  is_admin: boolean;
  is_owner: boolean;
  is_primary_owner: boolean;
  is_restricted: boolean;
  is_ultra_restricted: boolean;
  is_bot: boolean;
  is_app_user: boolean;
  updated: number;
  has_2fa?: boolean;
  two_factor_type?: string;
  has_files?: boolean;
}

// =============================================================================
// DATABASE TYPES
// =============================================================================

export interface SlackMessageRecord {
  id: string;
  slack_message_id: string;
  channel_id: string;
  user_id: string;
  thread_id?: string;
  parent_message_id?: string;
  timestamp: Date;
  text?: string;
  message_type: string;
  subtype?: string;
  team_id?: string;
  created_at: Date;
  updated_at: Date;
  indexed_at?: Date;
  sync_batch_id?: string;
}

export interface SlackAttachmentRecord {
  id: string;
  message_id: string;
  slack_file_id: string;
  filename: string;
  file_type?: string;
  mimetype?: string;
  size_bytes?: number;
  url?: string;
  permalink_url?: string;
  local_path?: string;
  content_extracted: boolean;
  extracted_content?: string;
  extracted_at?: Date;
  extraction_error?: string;
  metadata: Record<string, any>;
  created_at: Date;
  updated_at: Date;
}

export interface SlackSyncStateRecord {
  id: string;
  channel_id: string;
  workspace_id?: string;
  last_sync_timestamp?: Date;
  last_message_timestamp?: Date;
  oldest_message_timestamp?: Date;
  message_count: number;
  attachment_count: number;
  error_count: number;
  last_error?: string;
  last_error_at?: Date;
  consecutive_errors: number;
  sync_status: 'pending' | 'running' | 'success' | 'error' | 'disabled';
  is_active: boolean;
  sync_interval_seconds: number;
  batch_size: number;
  created_at: Date;
  updated_at: Date;
  last_success_at?: Date;
}

export interface SlackChannelRecord {
  id: string;
  channel_id: string;
  workspace_id?: string;
  name: string;
  display_name?: string;
  purpose?: string;
  topic?: string;
  channel_type: 'public_channel' | 'private_channel' | 'mpim' | 'im';
  is_member: boolean;
  is_archived: boolean;
  created_by?: string;
  created_at?: number;
  updated_at: Date;
}

export interface SlackUserRecord {
  id: string;
  user_id: string;
  workspace_id?: string;
  name: string;
  display_name?: string;
  real_name?: string;
  email?: string;
  avatar_url?: string;
  is_bot: boolean;
  is_app_user: boolean;
  is_admin: boolean;
  is_owner: boolean;
  profile: Record<string, any>;
  updated_at: Date;
}

// =============================================================================
// PROCESSING TYPES
// =============================================================================

export interface ProcessedMessage {
  message: SlackMessageRecord;
  attachments: SlackAttachmentRecord[];
  user?: SlackUserRecord;
  channel?: SlackChannelRecord;
  thread_context?: ThreadContext;
  search_content: string;
}

export interface ThreadContext {
  thread_id: string;
  parent_message: SlackMessageRecord;
  replies: SlackMessageRecord[];
  total_replies: number;
  participants: string[];
  last_reply: Date;
}

export interface FileContent {
  file_id: string;
  content: string;
  metadata: {
    filename: string;
    mimetype: string;
    size: number;
    extracted_at: Date;
    extraction_method: string;
  };
}

export interface SyncBatch {
  id: string;
  started_at: Date;
  completed_at?: Date;
  channel_id: string;
  workspace_id?: string;
  message_count: number;
  attachment_count: number;
  errors: SyncError[];
  status: 'running' | 'completed' | 'failed';
}

export interface SyncError {
  timestamp: Date;
  type: 'api_error' | 'file_error' | 'database_error' | 'validation_error';
  message: string;
  details?: Record<string, any>;
  recoverable: boolean;
}

// =============================================================================
// CONFIGURATION TYPES
// =============================================================================

export interface SlackConfig {
  bot_token: string;
  signing_secret?: string;
  client_id?: string;
  client_secret?: string;
  workspace_id?: string;
  sync_interval_seconds: number;
  batch_size: number;
  max_file_size_bytes: number;
  attachment_cache_dir: string;
  max_attachment_cache_size_bytes: number;
  enable_file_extraction: boolean;
  supported_file_types: string[];
  rate_limit_tier: number;
}

export interface SlackConnectorOptions {
  config: SlackConfig;
  database: any; // Database connection
  logger: any; // Logger instance
  metrics: any; // Metrics instance
}

export interface SyncOptions {
  channel_ids?: string[];
  incremental?: boolean;
  batch_size?: number;
  since_timestamp?: Date;
  dry_run?: boolean;
}

// =============================================================================
// API TYPES
// =============================================================================

export interface SlackSyncStatus {
  workspace_id?: string;
  is_running: boolean;
  last_sync?: Date;
  channels: ChannelSyncStatus[];
  total_messages: number;
  total_attachments: number;
  error_rate: number;
  uptime_percentage: number;
}

export interface ChannelSyncStatus {
  channel_id: string;
  channel_name: string;
  channel_type: string;
  sync_status: string;
  last_sync?: Date;
  message_count: number;
  attachment_count: number;
  error_count: number;
  health_status: 'healthy' | 'warning' | 'critical' | 'stale';
}

export interface SlackMetrics {
  sync_operations_total: number;
  sync_operations_success: number;
  sync_operations_failed: number;
  messages_processed: number;
  attachments_processed: number;
  files_extracted: number;
  average_sync_latency: number;
  api_calls_total: number;
  api_calls_failed: number;
  database_queries_total: number;
  database_queries_failed: number;
}

// =============================================================================
// SEARCH TYPES
// =============================================================================

export interface SlackSearchResult {
  message_id: string;
  slack_message_id: string;
  channel_id: string;
  user_id: string;
  thread_id?: string;
  timestamp: Date;
  text?: string;
  rank: number;
  snippet: string;
  channel_name?: string;
  user_name?: string;
  attachments?: SlackAttachmentRecord[];
}

export interface SlackSearchOptions {
  query: string;
  workspace_id?: string;
  channel_id?: string;
  user_id?: string;
  thread_id?: string;
  date_from?: Date;
  date_to?: Date;
  message_types?: string[];
  file_types?: string[];
  limit?: number;
  offset?: number;
  include_attachments?: boolean;
}

// =============================================================================
// ERROR TYPES
// =============================================================================

export class SlackConnectorError extends Error {
  constructor(
    message: string,
    public type: 'authentication' | 'api' | 'database' | 'file_processing' | 'validation',
    public details?: Record<string, any>,
    public recoverable: boolean = false
  ) {
    super(message);
    this.name = 'SlackConnectorError';
  }
}

export class SlackApiError extends SlackConnectorError {
  constructor(
    message: string,
    public apiMethod: string,
    public statusCode?: number,
    public retryable: boolean = false,
    public backoffMs?: number
  ) {
    super(message, 'api', { apiMethod, statusCode, retryable }, retryable);
    this.name = 'SlackApiError';
  }
}

export class SlackFileProcessingError extends SlackConnectorError {
  constructor(
    message: string,
    public fileId: string,
    public fileName: string,
    public fileType?: string
  ) {
    super(message, 'file_processing', { fileId, fileName, fileType }, true);
    this.name = 'SlackFileProcessingError';
  }
}

// =============================================================================
// WEBHOOK EVENT TYPES
// =============================================================================

export interface SlackWebhookEvent {
  type: string;
  team_id?: string;
  enterprise_id?: string;
  api_app_id?: string;
  event: {
    type: string;
    user?: string;
    channel?: string;
    text?: string;
    ts?: string;
    thread_ts?: string;
    subtype?: string;
    files?: SlackFile[];
    attachments?: SlackAttachment[];
    [key: string]: any;
  };
  event_id: string;
  event_time: number;
  authed_users: string[];
  authorizations?: Array<{
    enterprise_id?: string;
    team_id: string;
    user_id: string;
    is_bot: boolean;
    is_enterprise_install: boolean;
  }>;
}

export interface SlackChallengeEvent {
  type: 'url_verification';
  token: string;
  challenge: string;
}

// =============================================================================
// UTILITY TYPES
// =============================================================================

export type SlackChannelType = 'public_channel' | 'private_channel' | 'mpim' | 'im';
export type SyncStatus = 'pending' | 'running' | 'success' | 'error' | 'disabled';
export type HealthStatus = 'healthy' | 'warning' | 'critical' | 'stale';

export interface PaginationOptions {
  limit?: number;
  cursor?: string;
  page?: number;
}

export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: number;
  retry_after?: number;
}

export interface ApiResponse<T = any> {
  ok: boolean;
  data?: T;
  error?: string;
  headers?: Record<string, string>;
  rateLimit?: RateLimitInfo;
}