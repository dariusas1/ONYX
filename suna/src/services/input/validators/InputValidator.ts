/**
 * InputValidator - Security validation and sanitization for input events
 *
 * Provides:
 * - Input event validation and sanitization
 * - Rate limiting and abuse prevention
 * - Malicious input pattern detection
 * - Comprehensive audit logging
 * - Security policy enforcement
 * - Input quality assessment
 */

import { InputEvent } from '../InputManager';

export interface ValidationResult {
  valid: boolean;
  reason?: string;
  sanitized?: boolean;
  severity?: 'low' | 'medium' | 'high' | 'critical';
}

export interface SecurityFilter {
  name: string;
  validate: (event: InputEvent) => ValidationResult;
  enabled: boolean;
}

export interface RateLimitConfig {
  mouseEvents: number; // max events per second
  keyboardEvents: number;
  touchEvents: number;
  totalEvents: number;
  burstLimit: number; // burst capacity
}

export interface InputValidatorConfig {
  rateLimitMs: number;
  enableLogging: boolean;
  enableSecurityFilters: boolean;
  enableAuditLog: boolean;
  securityFilters?: SecurityFilter[];
  rateLimitConfig?: RateLimitConfig;
}

export interface AuditLogEntry {
  timestamp: number;
  userId?: string;
  sessionId: string;
  eventType: string;
  validation: ValidationResult;
  event: InputEvent;
  userAgent: string;
  ipAddress?: string;
}

export class InputValidator {
  private config: InputValidatorConfig;
  private sessionId: string;
  private userAgent: string;

  // Rate limiting
  private eventCounters: Map<string, number[]> = [];
  private lastRateLimitCheck = 0;

  // Security filters
  private securityFilters: SecurityFilter[];

  // Audit logging
  private auditLog: AuditLogEntry[] = [];
  private maxAuditLogSize = 10000;

  // Malicious patterns
  private maliciousPatterns = [
    {
      name: 'excessive_mouse_movement',
      pattern: 'rapid_mouse_movement',
      threshold: 1000, // events per second
      description: 'Suspiciously rapid mouse movement'
    },
    {
      name: 'keyboard_flooding',
      pattern: 'rapid_key_presses',
      threshold: 50, // keys per second
      description: 'Possible keyboard flood attack'
    },
    {
      name: 'coordinate_out_of_bounds',
      pattern: 'invalid_coordinates',
      description: 'Mouse coordinates outside reasonable bounds'
    },
    {
      name: 'suspicious_key_combinations',
      pattern: 'dangerous_shortcuts',
      description: 'Potentially harmful keyboard shortcuts'
    }
  ];

  constructor(config: Partial<InputValidatorConfig> = {}) {
    this.config = {
      rateLimitMs: 16, // ~60fps
      enableLogging: true,
      enableSecurityFilters: true,
      enableAuditLog: true,
      ...config
    };

    this.sessionId = this.generateSessionId();
    this.userAgent = navigator.userAgent;

    // Default rate limiting configuration
    this.config.rateLimitConfig = {
      mouseEvents: 120, // 120 events per second
      keyboardEvents: 30, // 30 keys per second
      touchEvents: 60, // 60 touches per second
      totalEvents: 200, // 200 total events per second
      burstLimit: 500, // burst capacity
      ...config.rateLimitConfig
    };

    // Initialize security filters
    this.securityFilters = [
      ...(config.securityFilters || []),
      ...this.createDefaultSecurityFilters()
    ];
  }

  /**
   * Validate an input event
   */
  public async validate(event: InputEvent): Promise<ValidationResult> {
    const timestamp = Date.now();

    try {
      // Basic structural validation
      const structuralValidation = this.validateEventStructure(event);
      if (!structuralValidation.valid) {
        await this.logAuditEvent(event, structuralValidation);
        return structuralValidation;
      }

      // Security filters
      if (this.config.enableSecurityFilters) {
        for (const filter of this.securityFilters) {
          if (!filter.enabled) continue;

          const filterResult = filter.validate(event);
          if (!filterResult.valid) {
            await this.logAuditEvent(event, filterResult);
            return filterResult;
          }
        }
      }

      // Malicious pattern detection
      const patternResult = this.checkMaliciousPatterns(event);
      if (!patternResult.valid) {
        await this.logAuditEvent(event, patternResult);
        return patternResult;
      }

      // Sanitization
      const sanitizedEvent = this.sanitizeEvent(event);

      // Update validation result if sanitization occurred
      if (sanitizedEvent !== event) {
        const sanitizedResult: ValidationResult = {
          valid: true,
          sanitized: true,
          severity: 'low'
        };

        await this.logAuditEvent(sanitizedEvent, sanitizedResult);
        return sanitizedResult;
      }

      // Valid event
      const validResult: ValidationResult = { valid: true };
      await this.logAuditEvent(event, validResult);
      return validResult;

    } catch (error) {
      console.error('Input validation error:', error);
      const errorResult: ValidationResult = {
        valid: false,
        reason: 'Validation system error',
        severity: 'critical'
      };

      await this.logAuditEvent(event, errorResult);
      return errorResult;
    }
  }

  /**
   * Check if event respects rate limits
   */
  public checkRateLimit(eventType: string): boolean {
    const now = Date.now();
    const oneSecondAgo = now - 1000;

    // Clean old counters
    if (now - this.lastRateLimitCheck > 1000) {
      this.cleanupOldCounters(oneSecondAgo);
      this.lastRateLimitCheck = now;
    }

    // Get appropriate rate limit
    const rateLimit = this.getRateLimitForEventType(eventType);
    if (!rateLimit) return true;

    // Get current counter
    const counter = this.eventCounters.get(eventType) || [];
    const recentCount = counter.filter(timestamp => timestamp > oneSecondAgo).length;

    // Check rate limit
    if (recentCount >= rateLimit) {
      if (this.config.enableLogging) {
        console.warn(`Rate limit exceeded for ${eventType}: ${recentCount}/${rateLimit}`);
      }
      return false;
    }

    // Add current event to counter
    counter.push(now);
    this.eventCounters.set(eventType, counter);

    return true;
  }

  /**
   * Basic event structure validation
   */
  private validateEventStructure(event: InputEvent): ValidationResult {
    if (!event || typeof event !== 'object') {
      return {
        valid: false,
        reason: 'Invalid event structure',
        severity: 'high'
      };
    }

    if (!event.type || !['mouse', 'keyboard', 'touch', 'focus'].includes(event.type)) {
      return {
        valid: false,
        reason: 'Invalid event type',
        severity: 'high'
      };
    }

    if (!event.timestamp || typeof event.timestamp !== 'number') {
      return {
        valid: false,
        reason: 'Invalid timestamp',
        severity: 'medium'
      };
    }

    // Check for future timestamps (possible tampering)
    if (event.timestamp > Date.now() + 1000) {
      return {
        valid: false,
        reason: 'Future timestamp detected',
        severity: 'high'
      };
    }

    return { valid: true };
  }

  /**
   * Check against malicious patterns
   */
  private checkMaliciousPatterns(event: InputEvent): ValidationResult {
    // Excessive mouse movement
    if (event.type === 'mouse') {
      if (this.detectExcessiveMouseMovement(event)) {
        return {
          valid: false,
          reason: 'Excessive mouse movement detected',
          severity: 'medium'
        };
      }

      if (this.detectInvalidCoordinates(event)) {
        return {
          valid: false,
          reason: 'Invalid mouse coordinates',
          severity: 'high'
        };
      }
    }

    // Keyboard flooding
    if (event.type === 'keyboard') {
      if (this.detectKeyboardFlooding(event)) {
        return {
          valid: false,
          reason: 'Keyboard flooding detected',
          severity: 'medium'
        };
      }

      if (this.detectSuspiciousKeyCombinations(event)) {
        return {
          valid: false,
          reason: 'Suspicious key combination detected',
          severity: 'high'
        };
      }
    }

    return { valid: true };
  }

  private detectExcessiveMouseMovement(event: InputEvent): boolean {
    if (!this.config.rateLimitConfig) return false;

    const mouseCounter = this.eventCounters.get('mouse') || [];
    const recentMouseEvents = mouseCounter.filter(
      timestamp => Date.now() - timestamp < 100
    ).length;

    return recentMouseEvents > this.maliciousPatterns[0].threshold;
  }

  private detectInvalidCoordinates(event: InputEvent): boolean {
    if (event.type !== 'mouse' || !event.data) return false;

    const { x, y } = event.data;

    // Check for unreasonable coordinates (assuming max 8K display)
    const maxCoordinate = 7680;
    const minCoordinate = 0;

    return x < minCoordinate || x > maxCoordinate || y < minCoordinate || y > maxCoordinate;
  }

  private detectKeyboardFlooding(event: InputEvent): boolean {
    if (!this.config.rateLimitConfig) return false;

    const keyboardCounter = this.eventCounters.get('keyboard') || [];
    const recentKeyboardEvents = keyboardCounter.filter(
      timestamp => Date.now() - timestamp < 1000
    ).length;

    return recentKeyboardEvents > this.maliciousPatterns[1].threshold;
  }

  private detectSuspiciousKeyCombinations(event: InputEvent): boolean {
    if (event.type !== 'keyboard' || !event.data) return false;

    const { key, modifiers } = event.data;

    // Check for dangerous system shortcuts that might be attempted
    const dangerousCombinations = [
      { key: 'F4', modifiers: { alt: true } },
      { key: 'Tab', modifiers: { alt: true } },
      { key: 'Escape', modifiers: { ctrl: true, shift: true } },
      { key: 'Delete', modifiers: { ctrl: true, alt: true } }
    ];

    return dangerousCombinations.some(combo =>
      combo.key.toLowerCase() === key?.toLowerCase() &&
      this.modifiersMatch(combo.modifiers, modifiers || {})
    );
  }

  private modifiersMatch(required: any, actual: any): boolean {
    return Object.entries(required).every(([key, value]) => actual[key] === value);
  }

  /**
   * Sanitize input event
   */
  private sanitizeEvent(event: InputEvent): InputEvent {
    let sanitized = false;
    const sanitizedEvent = { ...event };

    // Sanitize mouse coordinates
    if (event.type === 'mouse' && event.data) {
      const { x, y } = event.data;
      const maxCoordinate = 7680;

      if (x !== Math.max(0, Math.min(x, maxCoordinate)) ||
          y !== Math.max(0, Math.min(y, maxCoordinate))) {
        sanitizedEvent.data = {
          ...event.data,
          x: Math.max(0, Math.min(x, maxCoordinate)),
          y: Math.max(0, Math.min(y, maxCoordinate))
        };
        sanitized = true;
      }
    }

    // Sanitize keyboard input
    if (event.type === 'keyboard' && event.data) {
      const { key } = event.data;

      // Remove potentially dangerous characters
      if (key && typeof key === 'string') {
        const sanitizedKey = key.replace(/[\x00-\x1F\x7F]/g, '');
        if (sanitizedKey !== key) {
          sanitizedEvent.data = {
            ...event.data,
            key: sanitizedKey
          };
          sanitized = true;
        }
      }
    }

    // Update timestamp if it's in the future
    if (event.timestamp > Date.now()) {
      sanitizedEvent.timestamp = Date.now();
      sanitized = true;
    }

    return sanitized ? sanitizedEvent : event;
  }

  /**
   * Create default security filters
   */
  private createDefaultSecurityFilters(): SecurityFilter[] {
    return [
      {
        name: 'event_size_limit',
        enabled: true,
        validate: (event: InputEvent): ValidationResult => {
          const maxEventSize = 1024; // 1KB max event size
          const eventSize = JSON.stringify(event).length;

          if (eventSize > maxEventSize) {
            return {
              valid: false,
              reason: 'Event too large',
              severity: 'medium'
            };
          }

          return { valid: true };
        }
      },

      {
        name: 'timestamp_validation',
        enabled: true,
        validate: (event: InputEvent): ValidationResult => {
          const now = Date.now();
          const maxAge = 60000; // 1 minute max age

          if (now - event.timestamp > maxAge) {
            return {
              valid: false,
              reason: 'Event too old',
              severity: 'low'
            };
          }

          return { valid: true };
        }
      },

      {
        name: 'session_validation',
        enabled: true,
        validate: (event: InputEvent): ValidationResult => {
          // Add session-based validation logic here
          // For now, just validate that we have a session
          if (!this.sessionId) {
            return {
              valid: false,
              reason: 'No active session',
              severity: 'high'
            };
          }

          return { valid: true };
        }
      }
    ];
  }

  private getRateLimitForEventType(eventType: string): number {
    const config = this.config.rateLimitConfig;
    if (!config) return Infinity;

    switch (eventType) {
      case 'mouse': return config.mouseEvents;
      case 'keyboard': return config.keyboardEvents;
      case 'touch': return config.touchEvents;
      default: return config.totalEvents;
    }
  }

  private cleanupOldCounters(cutoffTime: number): void {
    for (const [eventType, counter] of this.eventCounters.entries()) {
      const validTimestamps = counter.filter(timestamp => timestamp > cutoffTime);
      this.eventCounters.set(eventType, validTimestamps);
    }
  }

  /**
   * Audit logging
   */
  private async logAuditEvent(event: InputEvent, validation: ValidationResult): Promise<void> {
    if (!this.config.enableAuditLog) return;

    const logEntry: AuditLogEntry = {
      timestamp: Date.now(),
      sessionId: this.sessionId,
      eventType: event.type,
      validation,
      event: {
        ...event,
        // Remove potentially sensitive data from audit log
        data: validation.valid ? event.data : '[sanitized]'
      },
      userAgent: this.userAgent
      // IP address would be added server-side
    };

    this.auditLog.push(logEntry);

    // Trim audit log if it gets too large
    if (this.auditLog.length > this.maxAuditLogSize) {
      this.auditLog = this.auditLog.slice(-this.maxAuditLogSize);
    }

    // Log to console for development
    if (this.config.enableLogging && !validation.valid) {
      console.warn('Input validation failed:', logEntry);
    }
  }

  /**
   * Get audit log statistics
   */
  public getAuditStats() {
    const totalEvents = this.auditLog.length;
    const failedValidations = this.auditLog.filter(entry => !entry.validation.valid).length;
    const sanitizedEvents = this.auditLog.filter(entry => entry.validation.sanitized).length;

    const validationFailuresByType = this.auditLog
      .filter(entry => !entry.validation.valid)
      .reduce((acc, entry) => {
        acc[entry.eventType] = (acc[entry.eventType] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

    const failuresByReason = this.auditLog
      .filter(entry => !entry.validation.valid && entry.validation.reason)
      .reduce((acc, entry) => {
        const reason = entry.validation.reason!;
        acc[reason] = (acc[reason] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

    return {
      totalEvents,
      failedValidations,
      sanitizedEvents,
      successRate: totalEvents > 0 ? ((totalEvents - failedValidations) / totalEvents) * 100 : 0,
      validationFailuresByType,
      failuresByReason,
      sessionId: this.sessionId
    };
  }

  /**
   * Export audit log
   */
  public exportAuditLog(): AuditLogEntry[] {
    return [...this.auditLog];
  }

  /**
   * Clear audit log
   */
  public clearAuditLog(): void {
    this.auditLog = [];
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<InputValidatorConfig>): void {
    this.config = { ...this.config, ...newConfig };

    if (newConfig.rateLimitConfig) {
      this.config.rateLimitConfig = {
        ...this.config.rateLimitConfig,
        ...newConfig.rateLimitConfig
      };
    }

    if (newConfig.securityFilters) {
      this.securityFilters = [...newConfig.securityFilters, ...this.createDefaultSecurityFilters()];
    }
  }

  /**
   * Enable/disable security filter
   */
  public setSecurityFilterEnabled(filterName: string, enabled: boolean): void {
    const filter = this.securityFilters.find(f => f.name === filterName);
    if (filter) {
      filter.enabled = enabled;
    }
  }

  /**
   * Get current configuration
   */
  public getConfig(): InputValidatorConfig {
    return { ...this.config };
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Reset rate limit counters
   */
  public resetRateLimitCounters(): void {
    this.eventCounters.clear();
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.clearAuditLog();
    this.resetRateLimitCounters();
    this.securityFilters = [];
  }
}

export default InputValidator;