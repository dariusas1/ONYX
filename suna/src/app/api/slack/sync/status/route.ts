// =============================================================================
// ONYX Slack Sync Status API Endpoint
// =============================================================================
// Provides real-time sync status and metrics

import { NextRequest, NextResponse } from 'next/server';
import { SlackConnector, SlackConfig } from '@/types/slack';
import { query } from '@/lib/database';
import { logInfo, logError } from '@/lib/logger';

// In-memory storage for connector instances
const connectors = new Map<string, SlackConnector>();

export async function GET(request: NextRequest) {
  const timer = logTimer('slack_sync_status_api');

  try {
    const { searchParams } = new URL(request.url);
    const workspaceId = searchParams.get('workspace_id');

    if (!workspaceId) {
      return NextResponse.json(
        { error: 'workspace_id parameter is required' },
        { status: 400 }
      );
    }

    // Get connector status
    let connectorStatus = null;
    const connector = connectors.get(workspace_id);
    if (connector) {
      connectorStatus = await (connector as any).getStatus();
    }

    // Get database sync state
    let syncState = null;
    try {
      const syncStateResult = await query(`
        SELECT
          COUNT(*) as total_channels,
          COUNT(CASE WHEN sync_status = 'running' THEN 1 END) as channels_syncing,
          COUNT(CASE WHEN sync_status = 'success' THEN 1 END) as channels_successful,
          COUNT(CASE WHEN sync_status = 'error' THEN 1 END) as channels_with_errors,
          COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_channels,
          COALESCE(SUM(message_count), 0) as total_messages,
          COALESCE(SUM(attachment_count), 0) as total_attachments,
          COALESCE(SUM(error_count), 0) as total_errors,
          MAX(last_sync_timestamp) as most_recent_sync
        FROM slack_sync_state
        WHERE workspace_id = $1 OR workspace_id IS NULL
      `, [workspaceId]);

      if (syncStateResult.rows[0]) {
        syncState = syncStateResult.rows[0];
      }

      // Get recent sync errors
      const recentErrorsResult = await query(`
        SELECT channel_id, last_error, last_error_at, error_count
        FROM slack_sync_state
        WHERE (workspace_id = $1 OR workspace_id IS NULL) AND last_error IS NOT NULL
        ORDER BY last_error_at DESC
        LIMIT 5
      `, [workspaceId]);

      const recentErrors = recentErrorsResult.rows;

      timer();
      return NextResponse.json({
        workspace_id,
        timestamp: new Date().toISOString(),
        connector: connectorStatus,
        sync_state: syncState,
        recent_errors: recentErrors,
        health_status: {
          overall_health: connectorStatus ? 'healthy' : 'disconnected',
          connector_available: !!connectorStatus,
          sync_active: syncState ? syncState.channels_syncing > 0 : false,
          error_rate: syncState && syncState.total_messages > 0
            ? (syncState.total_errors / syncState.total_messages) * 100
            : 0,
          last_sync: syncState?.most_recent_sync
        }
      });

    } catch (error) {
      timer();
      logError('slack_sync_status_database_failed', {
        workspace_id,
        error: error instanceof Error ? error.message : 'Unknown error'
      });

      // Return basic status without database info
      return NextResponse.json({
        workspace_id,
        timestamp: new Date().toISOString(),
        connector: connectorStatus,
        sync_state: null,
        recent_errors: [],
        health_status: {
          overall_health: connectorStatus ? 'healthy' : 'disconnected',
          connector_available: !!connectorStatus,
          sync_active: false,
          error_rate: 0,
          last_sync: null
        }
      });
    }

  } catch (error) {
    timer();
    logError('slack_sync_status_api_failed', {
      workspace_id,
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    }, error instanceof Error ? error.message : 'Unknown error');

    return NextResponse.json(
      {
        error: 'Failed to get Slack sync status',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}