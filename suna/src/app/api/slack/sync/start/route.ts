// =============================================================================
// ONYX Slack Sync Start API Endpoint
// =============================================================================
// Starts Slack synchronization process (manual trigger)

import { NextRequest, NextResponse } from 'next/server';
import { SlackConnector, SlackConfig } from '@/types/slack';
import { query } from '@/lib/database';
import { logInfo, logError } from '@/lib/logger';

// In-memory storage for connector instances (in production, use proper service registry)
const connectors = new Map<string, SlackConnector>();

export async function POST(request: NextRequest) {
  const timer = logTimer('slack_sync_start_api');

  try {
    const body = await request.json();
    const { channel_ids, incremental, batch_size, workspace_id } = body;

    // Validate request body
    if (!workspace_id) {
      return NextResponse.json(
        { error: 'workspace_id is required' },
        { status: 400 }
      );
    }

    // Check if we have environment variables for Slack
    const botToken = process.env.SLACK_BOT_TOKEN;
    if (!botToken) {
      return NextResponse.json(
        { error: 'Slack bot token not configured' },
        { status: 500 }
      );
    }

    // Create Slack configuration
    const config: SlackConfig = {
      bot_token: botToken,
      signing_secret: process.env.SLACK_SIGNING_SECRET,
      client_id: process.env.SLACK_CLIENT_ID,
      client_secret: process.env.SLACK_CLIENT_SECRET,
      workspace_id: workspace_id,
      sync_interval_seconds: 600, // 10 minutes
      batch_size: batch_size || 200,
      max_file_size_bytes: 10 * 1024 * 1024, // 10MB
      attachment_cache_dir: process.env.SLACK_ATTACHMENT_CACHE_DIR || '/tmp/slack-attachments',
      max_attachment_cache_size_bytes: 1024 * 1024 * 1024, // 1GB
      enable_file_extraction: true,
      supported_file_types: ['pdf', 'doc', 'docx', 'txt', 'md', 'csv', 'json', 'png', 'jpg', 'jpeg'],
      rate_limit_tier: 1
    };

    // Get or create connector instance
    let connector = connectors.get(workspace_id);
    if (!connector) {
      // Import SlackConnector class (dynamic import to avoid bundling issues)
      const { SlackConnector: SlackConnectorClass } = await import('@/lib/slack/connector');

      connector = new SlackConnectorClass({
        config,
        database: { query },
        logger: { logInfo, logError }
      });

      await connector.initialize();
      connectors.set(workspace_id, connector);
    }

    logInfo('slack_sync_start_requested', {
      workspace_id,
      channel_ids: channel_ids?.length || 'all',
      incremental: incremental || false,
      batch_size: batch_size || 200
    });

    // Start synchronization
    let syncResult;
    if (channel_ids && channel_ids.length > 0) {
      // Sync specific channels
      syncResult = [];
      for (const channelId of channel_ids) {
        try {
          const channelResult = await (connector as any).syncChannel(channelId, {
            incremental: incremental,
            batch_size: batch_size || 200
          });
          syncResult.push({
            channel_id: channelId,
            success: channelResult.errors.length === 0,
            messages_synced: channelResult.messages_synced,
            attachments_synced: channelResult.attachments_synced,
            errors: channelResult.errors
          });
        } catch (error) {
          syncResult.push({
            channel_id: channelId,
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }
      }
    } else {
      // Sync all channels
      syncResult = await connector.startSync({
        incremental: incremental,
        batch_size: batch_size || 200
      });
    }

    timer();
    return NextResponse.json({
      success: true,
      message: 'Slack synchronization started',
      workspace_id,
      result: syncResult,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    timer();
    logError('slack_sync_start_api_failed', {
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    }, error instanceof Error ? error.message : 'Unknown error');

    return NextResponse.json(
      {
        error: 'Failed to start Slack synchronization',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}