// =============================================================================
// ONYX Slack Connector Authentication Tests
// =============================================================================

import { SlackAuth } from '@/lib/slack/auth';
import { SlackConfig } from '@/types/slack';

// Mock the logger
jest.mock('@/lib/logger', () => ({
  logInfo: jest.fn(),
  logError: jest.fn(),
  logTimer: jest.fn(() => jest.fn()),
}));

describe('SlackAuth', () => {
  let slackAuth: SlackAuth;
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

    slackAuth = new SlackAuth(mockConfig);
  });

  describe('constructor', () => {
    it('should create an instance with valid config', () => {
      expect(slackAuth).toBeDefined();
    });

    it('should throw error for missing bot token', () => {
      expect(() => {
        new SlackAuth({ ...mockConfig, bot_token: '' });
      }).toThrow('Slack bot token is required');
    });

    it('should throw error for invalid bot token format', () => {
      expect(() => {
        new SlackAuth({ ...mockConfig, bot_token: 'invalid-token' });
      }).toThrow('Invalid bot token format');
    });
  });

  describe('validateBotTokenFormat', () => {
    it('should validate correct bot token format', async () => {
      const { validateBotTokenFormat } = require('@/lib/slack/auth');
      const result = validateBotTokenFormat('xoxb-1234567890-abcdef123456-7890abcdef12');

      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should reject invalid token formats', async () => {
      const { validateBotTokenFormat } = require('@/lib/slack/auth');

      // Empty token
      let result = validateBotTokenFormat('');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Token is required and must be a string');

      // Wrong prefix
      result = validateBotTokenFormat('xoxp-1234567890');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Invalid token format. Expected xoxb- prefix for bot token');
    });
  });

  describe('extractScopesFromToken', () => {
    it('should return empty array for invalid JWT', async () => {
      const { extractScopesFromToken } = require('@/lib/slack/auth');
      const scopes = extractScopesFromToken('invalid-jwt');

      expect(scopes).toEqual([]);
    });
  });

  describe('hasRequiredScopes', () => {
    it('should check required scopes correctly', async () => {
      const { hasRequiredScopes, REQUIRED_SCOPES } = require('@/lib/slack/auth');

      const availableScopes = ['channels:history', 'channels:read', 'users:read', 'files:read'];
      const result = hasRequiredScopes(availableScopes);

      expect(result.hasAll).toBe(false); // Missing some required scopes
      expect(result.missing.length).toBeGreaterThan(0);

      // Check when all scopes are present
      const allScopes = [...REQUIRED_SCOPES];
      const fullResult = hasRequiredScopes(allScopes);

      expect(fullResult.hasAll).toBe(true);
      expect(fullResult.missing).toEqual([]);
    });
  });

  describe('generateOAuthUrl', () => {
    it('should generate OAuth URL with parameters', async () => {
      const { generateOAuthUrl } = require('@/lib/slack/auth');
      const url = generateOAuthUrl(
        'test-client-id',
        'https://example.com/callback',
        ['channels:read', 'users:read'],
        'test-state'
      );

      expect(url).toContain('slack.com/oauth/v2/authorize');
      expect(url).toContain('client_id=test-client-id');
      expect(url).toContain('redirect_uri=https://example.com/callback');
      expect(url).toContain('scope=channels:read users:read');
      expect(url).toContain('state=test-state');
    });

    it('should generate OAuth URL without state', async () => {
      const { generateOAuthUrl } = require('@/lib/slack/auth');
      const url = generateOAuthUrl('test-client-id', 'https://example.com/callback');

      expect(url).toContain('slack.com/oauth/v2/authorize');
      expect(url).not.toContain('state=');
    });
  });
});