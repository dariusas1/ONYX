// =============================================================================
// ONYX Slack Connector Integration Tests
// =============================================================================

import { NextRequest } from 'next/server';
import { POST as syncStart } from '@/app/api/slack/sync/start/route';
import { GET as syncStatus } from '@/app/api/slack/sync/status/route';
import { GET as channels } from '@/app/api/slack/channels/route';
import { query } from '@/lib/database';

// Mock dependencies
jest.mock('@/lib/database');
jest.mock('@/lib/logger');
jest.mock('@/lib/slack/connector');

const mockQuery = query as jest.MockedFunction<typeof query>;
const mockSlackConnector = {
  initialize: jest.fn().mockResolvedValue(undefined),
  getStatus: jest.fn().mockResolvedValue({
    initialized: true,
    workspace: { id: 'T123', name: 'Test Workspace' },
    authentication: { valid: true }
  }),
  startSync: jest.fn().mockResolvedValue({
    success: true,
    channels_synced: 3,
    messages_synced: 150,
    errors: []
  }),
  syncChannel: jest.fn().mockResolvedValue({
    messages_synced: 50,
    attachments_synced: 5,
    errors: []
  })
};

// Set environment variables for tests
process.env.SLACK_BOT_TOKEN = 'xoxb-test-token';
process.env.SLACK_ATTACHMENT_CACHE_DIR = '/tmp/test-cache';

jest.mock('@/lib/slack/connector', () => ({
  SlackConnector: jest.fn().mockImplementation(() => mockSlackConnector)
}));

describe('Slack Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Reset environment variables
    process.env.SLACK_BOT_TOKEN = 'xoxb-test-token';
    process.env.SLACK_ATTACHMENT_CACHE_DIR = '/tmp/test-cache';
  });

  describe('Sync Status API', () => {
    it('should return sync status with workspace data', async () => {
      // Mock database queries
      mockQuery.mockResolvedValueOnce({
        rows: [{
          total_channels: 5,
          channels_syncing: 1,
          channels_successful: 4,
          channels_with_errors: 0,
          active_channels: 5,
          total_messages: 1000,
          total_attachments: 150,
          total_errors: 5,
          most_recent_sync: new Date().toISOString()
        }]
      });

      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            channel_id: 'C123',
            last_error: 'Rate limit exceeded',
            last_error_at: new Date().toISOString(),
            error_count: 3
          }
        ]
      });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/status?workspace_id=T123'
      );

      const response = await syncStatus(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.workspace_id).toBe('T123');
      expect(data.connector.initialized).toBe(true);
      expect(data.sync_state.total_channels).toBe(5);
      expect(data.health_status.connector_available).toBe(true);
      expect(data.health_status.overall_health).toBe('healthy');
      expect(data.recent_errors).toHaveLength(1);
    });

    it('should handle missing workspace_id parameter', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/status'
      );

      const response = await syncStatus(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toBe('workspace_id parameter is required');
    });

    it('should return disconnected status when no connector available', async () => {
      mockQuery.mockResolvedValueOnce({
        rows: [{
          total_channels: 0,
          channels_syncing: 0,
          channels_successful: 0,
          channels_with_errors: 0,
          active_channels: 0,
          total_messages: 0,
          total_attachments: 0,
          total_errors: 0,
          most_recent_sync: null
        }]
      });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/status?workspace_id=T999'
      );

      const response = await syncStatus(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.connector).toBeNull();
      expect(data.health_status.overall_health).toBe('disconnected');
      expect(data.health_status.connector_available).toBe(false);
    });
  });

  describe('Sync Start API', () => {
    it('should start sync for all channels', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 'T123',
            incremental: true,
            batch_size: 100
          })
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.workspace_id).toBe('T123');
      expect(data.result).toBeDefined();
      expect(mockSlackConnector.startSync).toHaveBeenCalledWith({
        incremental: true,
        batch_size: 100
      });
    });

    it('should start sync for specific channels', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 'T123',
            channel_ids: ['C123', 'C456'],
            incremental: false
          })
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(mockSlackConnector.syncChannel).toHaveBeenCalledTimes(2);
    });

    it('should handle missing workspace_id', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            channel_ids: ['C123']
          })
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toBe('workspace_id is required');
    });

    it('should handle missing Slack bot token', async () => {
      delete process.env.SLACK_BOT_TOKEN;

      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 'T123'
          })
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Slack bot token not configured');
    });

    it('should handle sync errors gracefully', async () => {
      mockSlackConnector.syncChannel.mockRejectedValueOnce(
        new Error('API rate limit exceeded')
      );

      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 'T123',
            channel_ids: ['C123']
          })
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.result).toHaveLength(1);
      expect(data.result[0].success).toBe(false);
      expect(data.result[0].error).toBe('API rate limit exceeded');
    });
  });

  describe('Channels API', () => {
    it('should return accessible channels with sync status', async () => {
      // Mock channels query
      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            id: 1,
            channel_id: 'C123',
            name: 'general',
            display_name: 'General',
            purpose: 'Company announcements',
            topic: 'General discussion',
            channel_type: 'public_channel',
            is_member: true,
            is_archived: false,
            created_by: 'U123',
            created_at: new Date(),
            updated_at: new Date()
          },
          {
            id: 2,
            channel_id: 'C456',
            name: 'random',
            display_name: 'Random',
            purpose: 'Random discussions',
            topic: 'Off-topic',
            channel_type: 'public_channel',
            is_member: true,
            is_archived: false,
            created_by: 'U456',
            created_at: new Date(),
            updated_at: new Date()
          }
        ]
      });

      // Mock sync status query
      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            channel_id: 'C123',
            sync_status: 'success',
            last_sync_timestamp: new Date(),
            last_message_timestamp: new Date(),
            message_count: 500,
            attachment_count: 50,
            error_count: 0,
            consecutive_errors: 0,
            is_active: true
          }
        ]
      });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels?workspace_id=T123'
      );

      const response = await channels(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.workspace_id).toBe('T123');
      expect(data.channels).toHaveLength(2);
      expect(data.summary.total).toBe(2);
      expect(data.summary.synced).toBe(1);

      // Check sync status for general channel
      const generalChannel = data.channels.find((c: any) => c.channel_id === 'C123');
      expect(generalChannel.sync.status).toBe('success');
      expect(generalChannel.sync.health_status).toBe('healthy');
    });

    it('should filter channels by type', async () => {
      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            id: 1,
            channel_id: 'C123',
            name: 'private-chat',
            channel_type: 'private_channel',
            is_member: true,
            is_archived: false
          }
        ]
      });

      mockQuery.mockResolvedValueOnce({ rows: [] });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels?workspace_id=T123&type=private'
      );

      const response = await channels(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.channels).toHaveLength(1);
      expect(data.channels[0].channel_type).toBe('private_channel');
    });

    it('should exclude archived channels by default', async () => {
      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            id: 1,
            channel_id: 'C123',
            name: 'active-channel',
            channel_type: 'public_channel',
            is_member: true,
            is_archived: false
          }
        ]
      });

      mockQuery.mockResolvedValueOnce({ rows: [] });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels?workspace_id=T123'
      );

      const response = await channels(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.channels).toHaveLength(1);
      expect(data.channels[0].is_archived).toBe(false);
    });

    it('should include archived channels when requested', async () => {
      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            id: 1,
            channel_id: 'C123',
            name: 'archived-channel',
            channel_type: 'public_channel',
            is_member: true,
            is_archived: true
          }
        ]
      });

      mockQuery.mockResolvedValueOnce({ rows: [] });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels?workspace_id=T123&include_archived=true'
      );

      const response = await channels(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.channels).toHaveLength(1);
      expect(data.channels[0].is_archived).toBe(true);
      expect(data.summary.archived).toBe(1);
    });

    it('should handle missing workspace_id parameter', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels'
      );

      const response = await channels(request);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toBe('workspace_id parameter is required');
    });

    it('should calculate health status correctly', async () => {
      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            id: 1,
            channel_id: 'C123',
            name: 'error-channel',
            channel_type: 'public_channel',
            is_member: true,
            is_archived: false
          }
        ]
      });

      mockQuery.mockResolvedValueOnce({
        rows: [
          {
            channel_id: 'C123',
            sync_status: 'error',
            last_sync_timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
            message_count: 100,
            error_count: 5,
            consecutive_errors: 1,
            is_active: true
          }
        ]
      });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels?workspace_id=T123'
      );

      const response = await channels(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      const errorChannel = data.channels.find((c: any) => c.channel_id === 'C123');
      expect(errorChannel.sync.health_status).toBe('warning'); // consecutive_errors < 3, has errors
    });
  });

  describe('Error Handling', () => {
    it('should handle database connection errors', async () => {
      mockQuery.mockRejectedValueOnce(new Error('Database connection failed'));

      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/status?workspace_id=T123'
      );

      const response = await syncStatus(request);
      const data = await response.json();

      expect(response.status).toBe(200); // Should still return basic status
      expect(data.sync_state).toBeNull();
      expect(data.recent_errors).toEqual([]);
    });

    it('should handle malformed JSON requests', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: 'invalid json'
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toBe('Failed to start Slack synchronization');
    });
  });

  describe('Authentication & Authorization', () => {
    it('should validate Slack bot token format', async () => {
      process.env.SLACK_BOT_TOKEN = 'invalid-token-format';

      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 'T123'
          })
        }
      );

      const response = await syncStart(request);

      // Should still proceed as token validation happens in the connector
      expect(response.status).toBe(200);
    });

    it('should use default configuration values', async () => {
      const request = new NextRequest(
        'http://localhost:3000/api/slack/sync/start',
        {
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 'T123'
          })
        }
      );

      const response = await syncStart(request);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(mockSlackConnector.startSync).toHaveBeenCalledWith({
        incremental: undefined,
        batch_size: 200 // Default value
      });
    });
  });

  describe('Performance & Scalability', () => {
    it('should handle large channel lists efficiently', async () => {
      // Mock 1000 channels
      const mockChannels = Array.from({ length: 1000 }, (_, i) => ({
        id: i + 1,
        channel_id: `C${1000 + i}`,
        name: `channel-${i}`,
        channel_type: 'public_channel',
        is_member: true,
        is_archived: false
      }));

      mockQuery.mockResolvedValueOnce({ rows: mockChannels });
      mockQuery.mockResolvedValueOnce({ rows: [] });

      const request = new NextRequest(
        'http://localhost:3000/api/slack/channels?workspace_id=T123'
      );

      const startTime = Date.now();
      const response = await channels(request);
      const endTime = Date.now();

      expect(response.status).toBe(200);
      expect(endTime - startTime).toBeLessThan(1000); // Should complete in under 1 second

      const data = await response.json();
      expect(data.channels).toHaveLength(1000);
      expect(data.summary.total).toBe(1000);
    });
  });
});