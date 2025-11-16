/**
 * InputManager - Centralized input event handling for VNC workspace
 *
 * Provides comprehensive mouse, keyboard, and touch input management with:
 * - Event capture and validation
 * - Security filtering and rate limiting
 * - Focus management
 * - Performance optimization
 * - Error handling and recovery
 */

import { MouseHandler } from './handlers/MouseHandler';
import { KeyboardHandler } from './handlers/KeyboardHandler';
import { TouchHandler } from './handlers/TouchHandler';
import { FocusManager } from './managers/FocusManager';
import { InputValidator } from './validators/InputValidator';
import { WebSocketInputService } from './services/WebSocketInputService';
import { EventEmitter } from 'events';

export interface InputEvent {
  type: 'mouse' | 'keyboard' | 'touch' | 'focus';
  timestamp: number;
  data: any;
  source: 'user' | 'system';
  validated: boolean;
}

export interface InputManagerConfig {
  enableMouse: boolean;
  enableKeyboard: boolean;
  enableTouch: boolean;
  rateLimitMs: number;
  maxQueueSize: number;
  latencyThreshold: number;
  enableLogging: boolean;
}

export class InputManager extends EventEmitter {
  private mouseHandler: MouseHandler;
  private keyboardHandler: KeyboardHandler;
  private touchHandler: TouchHandler;
  private focusManager: FocusManager;
  private inputValidator: InputValidator;
  private webSocketService: WebSocketInputService;

  private eventQueue: InputEvent[] = [];
  private isProcessing = false;
  private lastProcessTime = 0;
  private config: InputManagerConfig;

  // Performance metrics
  private metrics = {
    eventsProcessed: 0,
    eventsDropped: 0,
    averageLatency: 0,
    maxLatency: 0,
    validationErrors: 0,
    rateLimitHits: 0
  };

  constructor(config: Partial<InputManagerConfig> = {}) {
    super();

    this.config = {
      enableMouse: true,
      enableKeyboard: true,
      enableTouch: true,
      rateLimitMs: 16, // ~60fps
      maxQueueSize: 1000,
      latencyThreshold: 500,
      enableLogging: true,
      ...config
    };

    this.initializeHandlers();
    this.setupEventForwarding();
  }

  private initializeHandlers(): void {
    this.inputValidator = new InputValidator({
      rateLimitMs: this.config.rateLimitMs,
      enableLogging: this.config.enableLogging
    });

    this.webSocketService = new WebSocketInputService();
    this.focusManager = new FocusManager();

    this.mouseHandler = new MouseHandler({
      sensitivity: 1.0,
      enableLogging: this.config.enableLogging
    });

    this.keyboardHandler = new KeyboardHandler({
      enableAutoRepeat: true,
      enableLogging: this.config.enableLogging
    });

    this.touchHandler = new TouchHandler({
      gestureThreshold: 10,
      pinchSensitivity: 1.0,
      enableLogging: this.config.enableLogging
    });
  }

  private setupEventForwarding(): void {
    // Mouse events
    this.mouseHandler.on('mouseEvent', (event) => {
      this.handleInputEvent({
        type: 'mouse',
        timestamp: Date.now(),
        data: event,
        source: 'user',
        validated: false
      });
    });

    // Keyboard events
    this.keyboardHandler.on('keyboardEvent', (event) => {
      this.handleInputEvent({
        type: 'keyboard',
        timestamp: Date.now(),
        data: event,
        source: 'user',
        validated: false
      });
    });

    // Touch events
    this.touchHandler.on('touchEvent', (event) => {
      this.handleInputEvent({
        type: 'touch',
        timestamp: Date.now(),
        data: event,
        source: 'user',
        validated: false
      });
    });

    // Focus events
    this.focusManager.on('focusEvent', (event) => {
      this.handleInputEvent({
        type: 'focus',
        timestamp: Date.now(),
        data: event,
        source: 'system',
        validated: false
      });
    });

    // WebSocket connection events
    this.webSocketService.on('connected', () => {
      this.emit('connected');
      this.processQueuedEvents();
    });

    this.webSocketService.on('disconnected', () => {
      this.emit('disconnected');
    });

    this.webSocketService.on('error', (error) => {
      this.emit('error', error);
    });
  }

  /**
   * Main input event processing pipeline
   */
  private async handleInputEvent(inputEvent: InputEvent): Promise<void> {
    try {
      // Validation and security checks
      const validationResult = await this.inputValidator.validate(inputEvent);
      if (!validationResult.valid) {
        this.metrics.validationErrors++;
        if (this.config.enableLogging) {
          console.warn('Input validation failed:', validationResult.reason);
        }
        return;
      }

      // Rate limiting check
      if (!this.inputValidator.checkRateLimit(inputEvent.type)) {
        this.metrics.rateLimitHits++;
        if (this.config.enableLogging) {
          console.warn('Rate limit exceeded for input type:', inputEvent.type);
        }
        return;
      }

      // Mark as validated
      inputEvent.validated = true;

      // Add to processing queue
      this.addToQueue(inputEvent);

      // Process queue if not already processing
      if (!this.isProcessing) {
        this.processQueue();
      }

    } catch (error) {
      console.error('Error processing input event:', error);
      this.emit('processingError', error);
    }
  }

  private addToQueue(inputEvent: InputEvent): void {
    if (this.eventQueue.length >= this.config.maxQueueSize) {
      // Drop oldest event if queue is full
      this.eventQueue.shift();
      this.metrics.eventsDropped++;
    }

    this.eventQueue.push(inputEvent);
  }

  private async processQueue(): Promise<void> {
    if (this.isProcessing) return;

    this.isProcessing = true;
    this.lastProcessTime = performance.now();

    try {
      while (this.eventQueue.length > 0) {
        const event = this.eventQueue.shift()!;
        await this.processEvent(event);
        this.metrics.eventsProcessed++;

        // Rate limiting between processing batches
        const now = performance.now();
        const elapsed = now - this.lastProcessTime;
        if (elapsed < this.config.rateLimitMs) {
          await new Promise(resolve =>
            setTimeout(resolve, this.config.rateLimitMs - elapsed)
          );
        }
        this.lastProcessTime = performance.now();
      }
    } finally {
      this.isProcessing = false;
    }
  }

  private async processEvent(inputEvent: InputEvent): Promise<void> {
    const startTime = performance.now();

    try {
      switch (inputEvent.type) {
        case 'mouse':
          await this.webSocketService.sendMouseEvent(inputEvent.data);
          break;
        case 'keyboard':
          await this.webSocketService.sendKeyboardEvent(inputEvent.data);
          break;
        case 'touch':
          await this.webSocketService.sendTouchEvent(inputEvent.data);
          break;
        case 'focus':
          await this.webSocketService.sendFocusEvent(inputEvent.data);
          break;
      }

      // Update latency metrics
      const latency = performance.now() - startTime;
      this.updateLatencyMetrics(latency);

      if (latency > this.config.latencyThreshold) {
        this.emit('highLatency', { event: inputEvent, latency });
      }

    } catch (error) {
      console.error('Error sending input event:', error);
      this.emit('sendError', { event: inputEvent, error });
    }
  }

  private updateLatencyMetrics(latency: number): void {
    // Update average latency (exponential moving average)
    const alpha = 0.1; // Smoothing factor
    this.metrics.averageLatency =
      this.metrics.averageLatency === 0
        ? latency
        : alpha * latency + (1 - alpha) * this.metrics.averageLatency;

    // Update max latency
    this.metrics.maxLatency = Math.max(this.metrics.maxLatency, latency);
  }

  private async processQueuedEvents(): Promise<void> {
    if (this.eventQueue.length > 0) {
      await this.processQueue();
    }
  }

  /**
   * Public API methods
   */

  public connect(websocketUrl: string): Promise<void> {
    return this.webSocketService.connect(websocketUrl);
  }

  public disconnect(): void {
    this.webSocketService.disconnect();
  }

  public isConnected(): boolean {
    return this.webSocketService.isConnected();
  }

  // Mouse input capture
  public captureMouseEvents(element: HTMLElement): void {
    if (!this.config.enableMouse) return;

    this.mouseHandler.attachToElement(element);
    this.focusManager.setBoundary(element.getBoundingClientRect());
  }

  // Keyboard input capture
  public captureKeyboardEvents(element: HTMLElement): void {
    if (!this.config.enableKeyboard) return;

    this.keyboardHandler.attachToElement(element);
  }

  // Touch input capture
  public captureTouchEvents(element: HTMLElement): void {
    if (!this.config.enableTouch) return;

    this.touchHandler.attachToElement(element);
  }

  // Focus management
  public requestFocus(element: HTMLElement): void {
    this.focusManager.requestFocus(element);
  }

  public releaseFocus(): void {
    this.focusManager.releaseFocus();
  }

  public hasFocus(): boolean {
    return this.focusManager.hasFocus();
  }

  // Configuration
  public updateConfig(newConfig: Partial<InputManagerConfig>): void {
    this.config = { ...this.config, ...newConfig };

    // Update handler configurations
    if (newConfig.enableLogging !== undefined) {
      this.mouseHandler.updateConfig({ enableLogging: newConfig.enableLogging });
      this.keyboardHandler.updateConfig({ enableLogging: newConfig.enableLogging });
      this.touchHandler.updateConfig({ enableLogging: newConfig.enableLogging });
      this.inputValidator.updateConfig({ enableLogging: newConfig.enableLogging });
    }

    if (newConfig.rateLimitMs !== undefined) {
      this.inputValidator.updateConfig({ rateLimitMs: newConfig.rateLimitMs });
    }
  }

  // Metrics and monitoring
  public getMetrics() {
    return {
      ...this.metrics,
      queueSize: this.eventQueue.length,
      isProcessing: this.isProcessing,
      isConnected: this.isConnected()
    };
  }

  public resetMetrics(): void {
    this.metrics = {
      eventsProcessed: 0,
      eventsDropped: 0,
      averageLatency: 0,
      maxLatency: 0,
      validationErrors: 0,
      rateLimitHits: 0
    };
  }

  // Cleanup
  public destroy(): void {
    this.mouseHandler.destroy();
    this.keyboardHandler.destroy();
    this.touchHandler.destroy();
    this.focusManager.destroy();
    this.webSocketService.disconnect();
    this.eventQueue = [];
    this.removeAllListeners();
  }
}

export default InputManager;