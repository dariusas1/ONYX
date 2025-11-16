/**
 * Test suite for InputManager - Comprehensive input event handling
 */

import { InputManager } from '../InputManager';

// Mock dependencies
jest.mock('../handlers/MouseHandler', () => ({
  MouseHandler: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    attachToElement: jest.fn(),
    destroy: jest.fn(),
    updateConfig: jest.fn()
  }))
}));

jest.mock('../handlers/KeyboardHandler', () => ({
  KeyboardHandler: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    attachToElement: jest.fn(),
    destroy: jest.fn(),
    updateConfig: jest.fn()
  }))
}));

jest.mock('../handlers/TouchHandler', () => ({
  TouchHandler: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    attachToElement: jest.fn(),
    destroy: jest.fn(),
    updateConfig: jest.fn()
  }))
}));

jest.mock('../managers/FocusManager', () => ({
  FocusManager: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    requestFocus: jest.fn(),
    releaseFocus: jest.fn(),
    hasFocus: jest.fn().mockReturnValue(false),
    setBoundary: jest.fn(),
    destroy: jest.fn()
  }))
}));

jest.mock('../validators/InputValidator', () => ({
  InputValidator: jest.fn().mockImplementation(() => ({
    validate: jest.fn().mockResolvedValue({ valid: true }),
    checkRateLimit: jest.fn().mockReturnValue(true),
    updateConfig: jest.fn(),
    destroy: jest.fn()
  }))
}));

jest.mock('../services/WebSocketInputService', () => ({
  WebSocketInputService: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    connect: jest.fn().mockResolvedValue(undefined),
    disconnect: jest.fn(),
    isConnected: jest.fn().mockReturnValue(true),
    sendMouseEvent: jest.fn(),
    sendKeyboardEvent: jest.fn(),
    sendTouchEvent: jest.fn(),
    sendFocusEvent: jest.fn(),
    destroy: jest.fn()
  }))
}));

describe('InputManager', () => {
  let inputManager: InputManager;
  let mockElement: HTMLElement;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();

    // Create mock DOM element
    mockElement = document.createElement('div');
    mockElement.getBoundingClientRect = jest.fn().mockReturnValue({
      left: 0,
      top: 0,
      width: 800,
      height: 600,
      right: 800,
      bottom: 600
    });

    // Create InputManager instance
    inputManager = new InputManager({
      enableMouse: true,
      enableKeyboard: true,
      enableTouch: true,
      rateLimitMs: 16,
      maxQueueSize: 100,
      latencyThreshold: 500,
      enableLogging: false
    });
  });

  afterEach(() => {
    if (inputManager) {
      inputManager.destroy();
    }
  });

  describe('Initialization', () => {
    test('should initialize with default configuration', () => {
      expect(inputManager).toBeDefined();
      expect(inputManager.isConnected()).toBe(false);
    });

    test('should accept custom configuration', () => {
      const customConfig = {
        enableMouse: false,
        enableKeyboard: false,
        enableTouch: false,
        rateLimitMs: 32,
        latencyThreshold: 1000
      };

      const customManager = new InputManager(customConfig);
      expect(customManager).toBeDefined();
      customManager.destroy();
    });

    test('should initialize all handlers and services', () => {
      // Check that required modules are being used
      expect(require('../handlers/MouseHandler').MouseHandler).toHaveBeenCalled();
      expect(require('../handlers/KeyboardHandler').KeyboardHandler).toHaveBeenCalled();
      expect(require('../handlers/TouchHandler').TouchHandler).toHaveBeenCalled();
      expect(require('../managers/FocusManager').FocusManager).toHaveBeenCalled();
      expect(require('../validators/InputValidator').InputValidator).toHaveBeenCalled();
      expect(require('../services/WebSocketInputService').WebSocketInputService).toHaveBeenCalled();
    });
  });

  describe('Connection Management', () => {
    test('should connect to WebSocket URL', async () => {
      const url = 'ws://localhost:6080';
      await inputManager.connect(url);

      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      expect(webSocketService.connect).toHaveBeenCalledWith(url);
    });

    test('should disconnect properly', () => {
      inputManager.disconnect();

      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      expect(webSocketService.disconnect).toHaveBeenCalled();
    });

    test('should report connection status correctly', () => {
      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      webSocketService.isConnected.mockReturnValue(true);

      expect(inputManager.isConnected()).toBe(true);

      webSocketService.isConnected.mockReturnValue(false);
      expect(inputManager.isConnected()).toBe(false);
    });
  });

  describe('Input Event Capture', () => {
    beforeEach(async () => {
      // Connect for input tests
      await inputManager.connect('ws://localhost:6080');
    });

    test('should capture mouse events', () => {
      inputManager.captureMouseEvents(mockElement);

      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      expect(mouseHandler.attachToElement).toHaveBeenCalledWith(mockElement);
    });

    test('should capture keyboard events', () => {
      inputManager.captureKeyboardEvents(mockElement);

      const keyboardHandler = require('../handlers/KeyboardHandler').KeyboardHandler.mock.instances[0];
      expect(keyboardHandler.attachToElement).toHaveBeenCalledWith(mockElement);
    });

    test('should capture touch events', () => {
      inputManager.captureTouchEvents(mockElement);

      const touchHandler = require('../handlers/TouchHandler').TouchHandler.mock.instances[0];
      expect(touchHandler.attachToElement).toHaveBeenCalledWith(mockElement);
    });

    test('should manage focus', () => {
      inputManager.requestFocus(mockElement);
      expect(inputManager.hasFocus()).toBe(true);

      inputManager.releaseFocus();
      expect(inputManager.hasFocus()).toBe(false);
    });
  });

  describe('Event Processing Pipeline', () => {
    beforeEach(async () => {
      await inputManager.connect('ws://localhost:6080');
      inputManager.captureMouseEvents(mockElement);
    });

    test('should process validated events', async () => {
      const inputValidator = require('../validators/InputValidator').InputValidator.mock.instances[0];
      inputValidator.validate.mockResolvedValue({ valid: true });
      inputValidator.checkRateLimit.mockReturnValue(true);

      // Simulate mouse event from handler
      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      const emitCallback = mouseHandler.on.mock.calls.find(call => call[0] === 'mouseEvent')?.[1];

      if (emitCallback) {
        emitCallback({
          type: 'move',
          x: 100,
          y: 200,
          button: 0,
          buttons: 0,
          timestamp: Date.now()
        });
      }

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 20));

      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      expect(webSocketService.sendMouseEvent).toHaveBeenCalled();
    });

    test('should reject invalid events', async () => {
      const inputValidator = require('../validators/InputValidator').InputValidator.mock.instances[0];
      inputValidator.validate.mockResolvedValue({
        valid: false,
        reason: 'Invalid event'
      });

      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      const emitCallback = mouseHandler.on.mock.calls.find(call => call[0] === 'mouseEvent')?.[1];

      if (emitCallback) {
        emitCallback({
          type: 'move',
          x: 100,
          y: 200,
          button: 0,
          buttons: 0,
          timestamp: Date.now()
        });
      }

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 20));

      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      expect(webSocketService.sendMouseEvent).not.toHaveBeenCalled();
    });

    test('should respect rate limits', async () => {
      const inputValidator = require('../validators/InputValidator').InputValidator.mock.instances[0];
      inputValidator.validate.mockResolvedValue({ valid: true });
      inputValidator.checkRateLimit.mockReturnValue(false); // Rate limited

      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      const emitCallback = mouseHandler.on.mock.calls.find(call => call[0] === 'mouseEvent')?.[1];

      if (emitCallback) {
        emitCallback({
          type: 'move',
          x: 100,
          y: 200,
          button: 0,
          buttons: 0,
          timestamp: Date.now()
        });
      }

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 20));

      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      expect(webSocketService.sendMouseEvent).not.toHaveBeenCalled();
    });
  });

  describe('Metrics and Monitoring', () => {
    beforeEach(async () => {
      await inputManager.connect('ws://localhost:6080');
    });

    test('should provide initial metrics', () => {
      const metrics = inputManager.getMetrics();

      expect(metrics).toHaveProperty('eventsProcessed', 0);
      expect(metrics).toHaveProperty('eventsDropped', 0);
      expect(metrics).toHaveProperty('averageLatency', 0);
      expect(metrics).toHaveProperty('maxLatency', 0);
      expect(metrics).toHaveProperty('validationErrors', 0);
      expect(metrics).toHaveProperty('rateLimitHits', 0);
      expect(metrics).toHaveProperty('queueSize', 0);
      expect(metrics).toHaveProperty('isProcessing', false);
      expect(metrics).toHaveProperty('isConnected', true);
    });

    test('should reset metrics', () => {
      inputManager.getMetrics(); // Initialize metrics
      inputManager.resetMetrics();

      const metrics = inputManager.getMetrics();
      expect(metrics.eventsProcessed).toBe(0);
      expect(metrics.eventsDropped).toBe(0);
      expect(metrics.averageLatency).toBe(0);
      expect(metrics.maxLatency).toBe(0);
    });
  });

  describe('Configuration Updates', () => {
    test('should update configuration', () => {
      const newConfig = {
        rateLimitMs: 32,
        latencyThreshold: 1000,
        enableLogging: true
      };

      inputManager.updateConfig(newConfig);

      // Verify config was updated by checking that handlers were updated
      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      const keyboardHandler = require('../handlers/KeyboardHandler').KeyboardHandler.mock.instances[0];
      const touchHandler = require('../handlers/TouchHandler').TouchHandler.mock.instances[0];
      const inputValidator = require('../validators/InputValidator').InputValidator.mock.instances[0];

      expect(mouseHandler.updateConfig).toHaveBeenCalledWith({ enableLogging: true });
      expect(keyboardHandler.updateConfig).toHaveBeenCalledWith({ enableLogging: true });
      expect(touchHandler.updateConfig).toHaveBeenCalledWith({ enableLogging: true });
      expect(inputValidator.updateConfig).toHaveBeenCalledWith({
        enableLogging: true,
        rateLimitMs: 32
      });
    });
  });

  describe('Error Handling', () => {
    test('should emit error events for WebSocket issues', async () => {
      const errorCallback = jest.fn();
      inputManager.on('error', errorCallback);

      await inputManager.connect('ws://localhost:6080');

      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];
      const emitCallback = webSocketService.on.mock.calls.find(call => call[0] === 'error')?.[1];

      if (emitCallback) {
        emitCallback(new Error('Connection failed'));
      }

      expect(errorCallback).toHaveBeenCalled();
    });

    test('should emit processing errors', async () => {
      const errorCallback = jest.fn();
      inputManager.on('processingError', errorCallback);

      // Mock validator to throw error
      const inputValidator = require('../validators/InputValidator').InputValidator.mock.instances[0];
      inputValidator.validate.mockRejectedValue(new Error('Validation failed'));

      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      const emitCallback = mouseHandler.on.mock.calls.find(call => call[0] === 'mouseEvent')?.[1];

      if (emitCallback) {
        emitCallback({
          type: 'move',
          x: 100,
          y: 200,
          button: 0,
          buttons: 0,
          timestamp: Date.now()
        });
      }

      // Wait for processing
      await new Promise(resolve => setTimeout(resolve, 20));

      expect(errorCallback).toHaveBeenCalled();
    });
  });

  describe('Cleanup', () => {
    test('should destroy all components properly', () => {
      inputManager.destroy();

      const mouseHandler = require('../handlers/MouseHandler').MouseHandler.mock.instances[0];
      const keyboardHandler = require('../handlers/KeyboardHandler').KeyboardHandler.mock.instances[0];
      const touchHandler = require('../handlers/TouchHandler').TouchHandler.mock.instances[0];
      const focusManager = require('../managers/FocusManager').FocusManager.mock.instances[0];
      const inputValidator = require('../validators/InputValidator').InputValidator.mock.instances[0];
      const webSocketService = require('../services/WebSocketInputService').WebSocketInputService.mock.instances[0];

      expect(mouseHandler.destroy).toHaveBeenCalled();
      expect(keyboardHandler.destroy).toHaveBeenCalled();
      expect(touchHandler.destroy).toHaveBeenCalled();
      expect(focusManager.destroy).toHaveBeenCalled();
      expect(inputValidator.destroy).toHaveBeenCalled();
      expect(webSocketService.disconnect).toHaveBeenCalled();
    });
  });
});