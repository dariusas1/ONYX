// =============================================================================
// ONYX Slack Channels API Endpoint
// =============================================================================
// Lists accessible Slack channels

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/database';
import { logInfo, logError } from '@/lib/logger';

export async function GET(request: NextRequest) {
  const timer = logTimer('slack_channels_api');

  try {
    const { searchParams } = new URL(request.url);
    const workspaceId = searchParams.get('workspace_id');
    const includeArchived = searchParams.get('include_archived') === 'true';
    const filterType = searchParams.get('type'); // 'public', 'private', 'all'

    if (!workspaceId) {
      return NextResponse.json(
        { error: 'workspace_id parameter is required' },
        { status: 400 }
      );
    }

    // Build query with optional filters
    let whereClause = 'WHERE (workspace_id = $1 OR workspace_id IS NULL)';
    const queryParams = [workspaceId];

    if (!includeArchived) {
      whereClause += ' AND is_archived = FALSE';
    }

    if (filterType && filterType !== 'all') {
      if (filterType === 'public') {
        whereClause += ' AND channel_type = \'public_channel\'';
      } else if (filterType === 'private') {
        whereClause += ' AND channel_type IN (\'private_channel\', \'mpim\', \'im\')';
      }
    }

    const channelsResult = await query(`
      SELECT
        id,
        channel_id,
        name,
        display_name,
        purpose,
        topic,
        channel_type,
        is_member,
        is_archived,
        created_by,
        created_at,
        updated_at
      FROM slack_channels
      ${whereClause}
      ORDER BY name ASC
    `, queryParams);

    // Get sync status for each channel
    const channelIds = channelsResult.rows.map((row: any) => row.channel_id);
    let syncStatusMap: Record<string, any> = {};

    if (channelIds.length > 0) {
      const syncResult = await query(`
        SELECT
          channel_id,
          sync_status,
          last_sync_timestamp,
          last_message_timestamp,
          message_count,
          attachment_count,
          error_count,
          consecutive_errors,
          is_active
        FROM slack_sync_state
        WHERE channel_id = ANY($1)
      `, [channelIds]);

      syncResult.rows.forEach((row: any) => {
        syncStatusMap[row.channel_id] = row;
      });
    }

    // Combine channel info with sync status
    const channels = channelsResult.rows.map((row: any) => {
      const syncStatus = syncStatusMap[row.channel_id];
      return {
        ...row,
        sync: syncStatus ? {
          status: syncStatus.sync_status,
          last_sync: syncStatus.last_sync_timestamp,
          last_message: syncStatus.last_message_timestamp,
          message_count: syncStatus.message_count,
          attachment_count: syncStatus.attachment_count,
          error_count: syncStatus.error_count,
          consecutive_errors: syncStatus.consecutive_errors,
          is_active: syncStatus.is_active,
          health_status: syncStatus.consecutive_errors >= 3 ? 'critical' :
                       syncStatus.error_count > 0 ? 'warning' :
                       syncStatus.last_sync_timestamp && (Date.now() - new Date(syncStatus.last_sync_timestamp).getTime()) < 60 * 60 * 1000 ? 'healthy' : 'stale'
        } : {
          status: 'not_synced',
          health_status: 'unknown'
        }
      };
    });

    // Get summary statistics
    const summary = {
      total: channels.length,
      public_channels: channels.filter(c => c.channel_type === 'public_channel').length,
      private_channels: channels.filter(c => c.channel_type === 'private_channel').length,
      dm_channels: channels.filter(c => c.channel_type === 'im').length,
      group_dm_channels: channels.filter(c => c.channel_type === 'mpim').length,
      accessible: channels.filter(c => c.is_member).length,
      archived: channels.filter(c => c.is_archived).length,
      synced: Object.values(syncStatusMap).length,
      with_errors: Object.values(syncStatusMap).filter((s: any) => s.error_count > 0).length,
      critical_channels: Object.values(syncStatusMap).filter((s: any) => s.consecutive_errors >= 3).length
    };

    timer();
    return NextResponse.json({
      workspace_id,
      timestamp: new Date().toISOString(),
      summary,
      channels
    });

  } catch (error) {
    timer();
    logError('slack_channels_api_failed', {
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    }, error instanceof Error ? error.message : 'Unknown error');

    return NextResponse.json(
      {
        error: 'Failed to retrieve Slack channels',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}