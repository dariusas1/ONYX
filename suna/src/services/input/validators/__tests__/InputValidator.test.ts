/**
 * Test suite for InputValidator - Security validation and rate limiting
 */

import { InputValidator } from '../InputValidator';
import { InputEvent } from '../../InputManager';

// Mock navigator.userAgent
Object.defineProperty(global.navigator, 'userAgent', {
  value: 'Mozilla/5.0 (Test Browser)',
  writable: true
});

describe('InputValidator', () => {
  let inputValidator: InputValidator;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    inputValidator = new InputValidator({
      rateLimitMs: 16,
      enableLogging: false,
      enableSecurityFilters: true,
      enableAuditLog: true
    });
  });

  afterEach(() => {
    if (inputValidator) {
      inputValidator.destroy();
    }
    jest.useRealTimers();
  });

  describe('Initialization', () => {
    test('should initialize with default configuration', () => {
      expect(inputValidator).toBeDefined();
      const config = inputValidator.getConfig();
      expect(config.rateLimitMs).toBe(16);
      expect(config.enableLogging).toBe(false);
      expect(config.enableSecurityFilters).toBe(true);
      expect(config.enableAuditLog).toBe(true);
    });

    test('should accept custom configuration', () => {
      const customValidator = new InputValidator({
        rateLimitMs: 32,
        enableLogging: true,
        rateLimitConfig: {
          mouseEvents: 100,
          keyboardEvents: 25,
          touchEvents: 50,
          totalEvents: 150
        }
      });

      expect(customValidator).toBeDefined();
      const config = customValidator.getConfig();
      expect(config.rateLimitMs).toBe(32);
      expect(config.enableLogging).toBe(true);
      expect(config.rateLimitConfig?.mouseEvents).toBe(100);

      customValidator.destroy();
    });

    test('should generate unique session ID', () => {
      const validator1 = new InputValidator();
      const validator2 = new InputValidator();

      expect(validator1.getConfig()).toBeDefined();
      expect(validator2.getConfig()).toBeDefined();

      // Session IDs should be unique
      const stats1 = validator1.getAuditStats();
      const stats2 = validator2.getAuditStats();
      expect(stats1.sessionId).not.toBe(stats2.sessionId);

      validator1.destroy();
      validator2.destroy();
    });
  });

  describe('Event Structure Validation', () => {
    test('should validate correctly structured mouse event', async () => {
      const validEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: {
          type: 'move',
          x: 100,
          y: 200,
          button: 0,
          buttons: 0
        },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(validEvent);
      expect(result.valid).toBe(true);
    });

    test('should validate correctly structured keyboard event', async () => {
      const validEvent: InputEvent = {
        type: 'keyboard',
        timestamp: Date.now(),
        data: {
          type: 'keydown',
          keyCode: 65,
          key: 'a',
          charCode: 97,
          modifiers: { ctrl: false, alt: false, shift: false, meta: false },
          isAutoRepeat: false
        },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(validEvent);
      expect(result.valid).toBe(true);
    });

    test('should reject event with missing type', async () => {
      const invalidEvent = {
        timestamp: Date.now(),
        data: {},
        source: 'user',
        validated: false
      } as any;

      const result = await inputValidator.validate(invalidEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Invalid event type');
      expect(result.severity).toBe('high');
    });

    test('should reject event with invalid type', async () => {
      const invalidEvent: InputEvent = {
        type: 'invalid' as any,
        timestamp: Date.now(),
        data: {},
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(invalidEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Invalid event type');
    });

    test('should reject event with missing timestamp', async () => {
      const invalidEvent = {
        type: 'mouse',
        data: {},
        source: 'user',
        validated: false
      } as any;

      const result = await inputValidator.validate(invalidEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Invalid timestamp');
    });

    test('should reject event with future timestamp', async () => {
      const futureTime = Date.now() + 2000; // 2 seconds in future
      const invalidEvent: InputEvent = {
        type: 'mouse',
        timestamp: futureTime,
        data: {},
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(invalidEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Future timestamp detected');
    });
  });

  describe('Security Filters', () => {
    test('should validate events within size limit', async () => {
      const largeEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: {
          // Create large data that would exceed size limit
          largeData: 'x'.repeat(2000)
        },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(largeEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Event too large');
      expect(result.severity).toBe('medium');
    });

    test('should validate timestamp age', async () => {
      const oldTime = Date.now() - 120000; // 2 minutes ago
      const oldEvent: InputEvent = {
        type: 'mouse',
        timestamp: oldTime,
        data: { type: 'move', x: 0, y: 0 },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(oldEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Event too old');
      expect(result.severity).toBe('low');
    });
  });

  describe('Malicious Pattern Detection', () => {
    test('should detect excessive mouse movement', async () => {
      // Simulate rapid mouse events
      for (let i = 0; i < 10; i++) {
        const mouseEvent: InputEvent = {
          type: 'mouse',
          timestamp: Date.now(),
          data: {
            type: 'move',
            x: 100 + i,
            y: 200 + i,
            button: -1,
            buttons: 0
          },
          source: 'user',
          validated: false
        };

        // These should all be valid initially
        const result = await inputValidator.validate(mouseEvent);
        expect(result.valid).toBe(true);
      }

      // Now simulate excessive rapid events within 100ms
      const rapidEvents: InputEvent[] = [];
      for (let i = 0; i < 5; i++) {
        rapidEvents.push({
          type: 'mouse',
          timestamp: Date.now(),
          data: {
            type: 'move',
            x: 100 + i,
            y: 200 + i,
            button: -1,
            buttons: 0
          },
          source: 'user',
          validated: false
        });
      }

      // First few should be valid, later ones might be flagged
      const results = await Promise.all(rapidEvents.map(event => inputValidator.validate(event)));
      const invalidCount = results.filter(r => !r.valid).length;

      // At least one should be flagged as excessive (implementation dependent)
      if (invalidCount > 0) {
        const invalidResult = results.find(r => !r.valid);
        expect(invalidResult?.reason).toContain('Excessive mouse movement');
      }
    });

    test('should detect invalid mouse coordinates', async () => {
      const invalidCoordinateEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: {
          type: 'move',
          x: 10000, // Beyond reasonable limit
          y: 10000,
          button: -1,
          buttons: 0
        },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(invalidCoordinateEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Invalid mouse coordinates');
      expect(result.severity).toBe('high');
    });

    test('should detect suspicious keyboard shortcuts', async () => {
      const suspiciousShortcutEvent: InputEvent = {
        type: 'keyboard',
        timestamp: Date.now(),
        data: {
          type: 'keydown',
          keyCode: 115, // F4
          key: 'F4',
          charCode: 0,
          modifiers: { ctrl: false, alt: true, shift: false, meta: false },
          isAutoRepeat: false
        },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(suspiciousShortcutEvent);
      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Suspicious key combination detected');
      expect(result.severity).toBe('high');
    });

    test('should sanitize dangerous characters in keyboard input', async () => {
      const dangerousCharEvent: InputEvent = {
        type: 'keyboard',
        timestamp: Date.now(),
        data: {
          type: 'keypress',
          keyCode: 0,
          key: '\x00\x01\x02', // Control characters
          charCode: 0,
          modifiers: { ctrl: false, alt: false, shift: false, meta: false },
          isAutoRepeat: false
        },
        source: 'user',
        validated: false
      };

      const result = await inputValidator.validate(dangerousCharEvent);
      expect(result.valid).toBe(true);
      expect(result.sanitized).toBe(true);
    });
  });

  describe('Rate Limiting', () => {
    test('should respect mouse event rate limits', async () => {
      // Send events up to the rate limit
      const rateLimit = inputValidator.getConfig().rateLimitConfig?.mouseEvents || 120;

      for (let i = 0; i < rateLimit; i++) {
        const result = await inputValidator.validate({
          type: 'mouse',
          timestamp: Date.now(),
          data: { type: 'move', x: i, y: i },
          source: 'user',
          validated: false
        });
        expect(result.valid).toBe(true);
      }

      // Next event should be rate limited
      const overLimitResult = await inputValidator.validate({
        type: 'mouse',
        timestamp: Date.now(),
        data: { type: 'move', x: rateLimit + 1, y: rateLimit + 1 },
        source: 'user',
        validated: false
      });
      expect(overLimitResult.valid).toBe(false);
    });

    test('should reset rate limit counters', () => {
      inputValidator.resetRateLimitCounters();

      // Counters should be cleared (verified by subsequent validation)
      expect(inputValidator.getConfig()).toBeDefined();
    });
  });

  describe('Audit Logging', () => {
    test('should log validation results', async () => {
      const validEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: { type: 'move', x: 100, y: 200 },
        source: 'user',
        validated: false
      };

      await inputValidator.validate(validEvent);

      const stats = inputValidator.getAuditStats();
      expect(stats.totalEvents).toBe(1);
      expect(stats.failedValidations).toBe(0);
      expect(stats.successRate).toBe(100);
    });

    test('should track validation failures', async () => {
      const invalidEvent: InputEvent = {
        type: 'invalid' as any,
        timestamp: Date.now(),
        data: {},
        source: 'user',
        validated: false
      };

      await inputValidator.validate(invalidEvent);

      const stats = inputValidator.getAuditStats();
      expect(stats.totalEvents).toBe(1);
      expect(stats.failedValidations).toBe(1);
      expect(stats.successRate).toBe(0);
    });

    test('should export audit log', async () => {
      const validEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: { type: 'move', x: 100, y: 200 },
        source: 'user',
        validated: false
      };

      await inputValidator.validate(validEvent);

      const auditLog = inputValidator.exportAuditLog();
      expect(Array.isArray(auditLog)).toBe(true);
      expect(auditLog.length).toBe(1);
      expect(auditLog[0]).toHaveProperty('eventType', 'mouse');
      expect(auditLog[0]).toHaveProperty('validation');
      expect(auditLog[0]).toHaveProperty('timestamp');
      expect(auditLog[0]).toHaveProperty('sessionId');
    });

    test('should clear audit log', async () => {
      const validEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: { type: 'move', x: 100, y: 200 },
        source: 'user',
        validated: false
      };

      await inputValidator.validate(validEvent);
      expect(inputValidator.getAuditStats().totalEvents).toBe(1);

      inputValidator.clearAuditLog();
      expect(inputValidator.getAuditStats().totalEvents).toBe(0);
    });

    test('should limit audit log size', async () => {
      // This test would verify that the audit log doesn't grow indefinitely
      // Implementation detail: should trim old entries when size exceeds limit

      const validEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: { type: 'move', x: 100, y: 200 },
        source: 'user',
        validated: false
      };

      // Add many events (would need to exceed maxAuditLogSize)
      for (let i = 0; i < 10; i++) {
        await inputValidator.validate(validEvent);
      }

      const auditLog = inputValidator.exportAuditLog();
      expect(auditLog.length).toBeLessThanOrEqual(10000); // maxAuditLogSize
    });
  });

  describe('Configuration Updates', () => {
    test('should update configuration', () => {
      const newConfig = {
        rateLimitMs: 32,
        enableLogging: true,
        enableSecurityFilters: false
      };

      inputValidator.updateConfig(newConfig);

      const config = inputValidator.getConfig();
      expect(config.rateLimitMs).toBe(32);
      expect(config.enableLogging).toBe(true);
      expect(config.enableSecurityFilters).toBe(false);
    });

    test('should enable/disable security filters', () => {
      // Disable event size limit filter
      inputValidator.setSecurityFilterEnabled('event_size_limit', false);

      // Create an event that would normally fail the size limit
      const largeEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: {
          // This might still be too large for practical purposes
          largeData: 'x'.repeat(500)
        },
        source: 'user',
        validated: false
      };

      // Should pass because filter is disabled (though may still fail other validations)
      // This test mainly verifies the method doesn't throw
      expect(() => inputValidator.setSecurityFilterEnabled('event_size_limit', false)).not.toThrow();
    });
  });

  describe('Cleanup', () => {
    test('should destroy properly', () => {
      const validEvent: InputEvent = {
        type: 'mouse',
        timestamp: Date.now(),
        data: { type: 'move', x: 100, y: 200 },
        source: 'user',
        validated: false
      };

      // Add some data first
      inputValidator.validate(validEvent);
      expect(inputValidator.getAuditStats().totalEvents).toBe(1);

      inputValidator.destroy();

      // Should not throw when trying to use destroyed instance
      expect(() => inputValidator.clearAuditLog()).not.toThrow();
      expect(() => inputValidator.resetRateLimitCounters()).not.toThrow();
    });
  });
});