// =============================================================================
// ONYX Slack Connector Integration Tests
// =============================================================================

import { SlackConnector } from '@/lib/slack/connector';
import { SlackConfig } from '@/types/slack';

// Mock dependencies
jest.mock('@/lib/slack/auth');
jest.mock('@/lib/slack/permissions');
jest.mock('@/lib/slack/message-processor');
jest.mock('@/lib/slack/file-handler');
jest.mock('@/lib/database');
jest.mock('@/lib/logger', () => ({
  logInfo: jest.fn(),
  logError: jest.fn(),
  logTimer: jest.fn(() => jest.fn()),
}));

// Mock implementations
const mockAuth = {
  initialize: jest.fn().mockResolvedValue(undefined),
  validateToken: jest.fn().mockResolvedValue({
    valid: true,
    workspace_id: 'T1234567890',
    workspace_name: 'Test Workspace',
    team_id: 'T1234567890',
    user_id: 'U1234567890',
    bot_user_id: 'B1234567890',
    scopes: ['channels:history', 'channels:read', 'users:read', 'files:read'],
    missing_scopes: []
  }),
  getWorkspaceInfo: jest.fn().mockResolvedValue({
    id: 'T1234567890',
    name: 'Test Workspace',
    domain: 'test-workspace'
  }),
  canAccessChannel: jest.fn().mockResolvedValue(true),
  getClient: jest.fn().mockReturnValue({
    conversations: {
      history: jest.fn().mockResolvedValue({
        ok: true,
        messages: [],
        has_more: false
      }),
      list: jest.fn().mockResolvedValue({
        ok: true,
        channels: []
      }),
      info: jest.fn().mockResolvedValue({
        ok: true,
        channel: {}
      })
    }
    })
  },
  close: jest.fn().mockResolvedValue(undefined)
};

const mockPermissions = {
  getAccessibleChannels: jest.fn().mockResolvedValue([
    {
      id: '1',
      channel_id: 'C1234567890',
      name: 'general',
      channel_type: 'public_channel',
      is_member: true,
      is_archived: false
    }
  ]),
  canAccessChannel: jest.fn().mockResolvedValue(true),
  clearCache: jest.fn(),
  updateWorkspaceId: jest.fn().mockResolvedValue(undefined)
};

const mockMessageProcessor = {
  processMessage: jest.fn().mockResolvedValue({
    message: {
      id: '1',
      slack_message_id: '1234567890.123456',
      channel_id: 'C1234567890',
      user_id: 'U1234567890',
      timestamp: new Date(),
      text: 'Test message'
    },
    attachments: [],
    search_content: 'Test message'
  })
};

const mockFileHandler = {
  initialize: jest.fn().mockResolvedValue(undefined),
  processFile: jest.fn().mockResolvedValue({
    file_id: 'F1234567890',
    content: 'Test file content',
    metadata: {
      filename: 'test.txt',
      size: 17,
      extracted_at: new Date(),
      extraction_method: 'Plain text extraction'
    }
  }),
  close: jest.fn().mockResolvedValue(undefined)
};

jest.mock('@/lib/slack/auth', () => mockAuth);
jest.mock('@/lib/slack/permissions', () => mockPermissions);
jest.mock('@/lib/slack/message-processor', () => mockMessageProcessor);
jest.mock('@/lib/slack/file-handler', () => mockFileHandler);

describe('SlackConnector', () => {
  let slackConnector: SlackConnector;
  let mockConfig: SlackConfig;

  beforeEach(() => {
    mockConfig = {
      bot_token: 'xoxb-test-token',
      sync_interval_seconds: 600,
      batch_size: 200,
      max_file_size_bytes: 10 * 1024 * 1024,
      attachment_cache_dir: '/tmp/test-slack',
      max_attachment_cache_size_bytes: 1024 * 1024 * 1024,
      enable_file_extraction: true,
      supported_file_types: ['pdf', 'doc', 'txt'],
      rate_limit_tier: 1
    };

    // Reset all mocks
    jest.clearAllMocks();

    slackConnector = new SlackConnector({
      config: mockConfig,
      database: { query: jest.fn() },
      logger: { logInfo: jest.fn(), logError: jest.fn(), logTimer: jest.fn(() => jest.fn()) }
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create an instance with valid config', () => {
      expect(slackConnector).toBeDefined();
    });

    it('should initialize sub-services with config', () => {
      // Verify that the sub-services were called with correct config
      expect(require('@/lib/slack/auth')).toHaveBeenCalledWith(mockConfig);
      expect(require('@/lib/slack/permissions')).toHaveBeenCalledWith(
        expect.any(Object), // Auth instance
        expect.any(Object)  // Database instance
      );
    });
  });

  describe('initialize', () => {
    it('should initialize successfully with valid auth', async () => {
      await slackConnector.initialize();
      expect(mockAuth.initialize).toHaveBeenCalled();
      expect(mockAuth.validateToken).toHaveBeenCalled();
      expect(mockFileHandler.initialize).toHaveBeenCalled();
    });

    it('should throw error if auth validation fails', async () => {
      mockAuth.validateToken.mockResolvedValue({
        valid: false,
        errors: ['Invalid token']
      });

      await expect(slackConnector.initialize()).rejects.toThrow('Slack authentication validation failed');
    });
  });

  describe('getAccessibleChannels', () => {
    it('should return accessible channels after initialization', async () => {
      await slackConnector.initialize();

      const channels = await slackConnector['getAccessibleChannels']();

      expect(mockPermissions.getAccessibleChannels).toHaveBeenCalled();
      expect(channels).toHaveLength(1);
      expect(channels[0].channel_id).toBe('C1234567890');
      expect(channels[0].name).toBe('general');
    });
  });

  describe('canAccessChannel', () => {
    it('should check channel access permissions', async () => {
      await slackConnector.initialize();

      const canAccess = await slackConnector['canAccessChannel']('C1234567890');

      expect(mockPermissions.canAccessChannel).toHaveBeenCalledWith('C1234567890');
      expect(canAccess).toBe(true);
    });
  });

  describe('getStatus', () => {
    it('should return connector status', async () => {
      await slackConnector.initialize();

      const status = await slackConnector.getStatus();

      expect(status.initialized).toBe(true);
      expect(status.workspace).toBeDefined();
      expect(status.authentication).toBeDefined();
    });

    it('should return not initialized status before init', () => {
      const status = slackConnector.getStatus();

      expect(status.initialized).toBe(false);
      expect(status.workspace).toBeUndefined();
    });
  });

  describe('close', () => {
    it('should close all sub-services', async () => {
      await slackConnector.close();

      expect(mockAuth.close).toHaveBeenCalled();
      expect(mockFileHandler.close).toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('should handle initialization errors gracefully', async () => {
      mockAuth.initialize.mockRejectedValue(new Error('Auth failed'));

      await expect(slackConnector.initialize()).rejects.toThrow('Auth failed');
    });

    it('should handle channel sync errors', async () => {
      await slackConnector.initialize();

      // Mock a channel sync error
      mockAuth.getClient().conversations.history.mockRejectedValue(
        new Error('API error')
      );

      // Access the private method through bracket notation for testing
      await expect(
        (slackConnector as any).syncChannel('C1234567890')
      ).rejects.toThrow();
    });
  });
});