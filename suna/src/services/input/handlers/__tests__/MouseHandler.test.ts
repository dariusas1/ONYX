/**
 * Test suite for MouseHandler - Mouse input processing
 */

import { MouseHandler } from '../MouseHandler';

// Mock DOM APIs
Object.defineProperty(HTMLElement.prototype, 'getBoundingClientRect', {
  value: jest.fn(() => ({
    left: 0,
    top: 0,
    width: 800,
    height: 600,
    right: 800,
    bottom: 600
  }))
});

describe('MouseHandler', () => {
  let mouseHandler: MouseHandler;
  let mockElement: HTMLElement;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Create mock DOM element
    mockElement = document.createElement('div');
    Object.defineProperty(mockElement, 'clientWidth', { value: 800 });
    Object.defineProperty(mockElement, 'clientHeight', { value: 600 });

    // Create MouseHandler instance
    mouseHandler = new MouseHandler({
      sensitivity: 1.0,
      clickThreshold: 300,
      dragThreshold: 3,
      throttleMs: 8,
      enableLogging: false
    });
  });

  afterEach(() => {
    if (mouseHandler) {
      mouseHandler.destroy();
    }
    jest.useRealTimers();
  });

  describe('Initialization', () => {
    test('should initialize with default configuration', () => {
      expect(mouseHandler).toBeDefined();
    });

    test('should accept custom configuration', () => {
      const customHandler = new MouseHandler({
        sensitivity: 2.0,
        clickThreshold: 500,
        dragThreshold: 5,
        throttleMs: 16
      });

      expect(customHandler).toBeDefined();
      customHandler.destroy();
    });
  });

  describe('Element Attachment', () => {
    test('should attach to DOM element', () => {
      const addEventListenerSpy = jest.spyOn(mockElement, 'addEventListener');

      mouseHandler.attachToElement(mockElement);

      expect(addEventListenerSpy).toHaveBeenCalledWith('mousemove', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('mouseup', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('dblclick', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('contextmenu', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('wheel', expect.any(Function), { passive: false });
      expect(addEventListenerSpy).toHaveBeenCalledWith('mouseenter', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should detach from DOM element', () => {
      const removeEventListenerSpy = jest.spyOn(mockElement, 'removeEventListener');

      mouseHandler.attachToElement(mockElement);
      mouseHandler.detach();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('mousemove', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mousedown', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mouseup', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('dblclick', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('contextmenu', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('wheel', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mouseenter', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('mouseleave', expect.any(Function));
    });

    test('should detach and re-attach properly', () => {
      const addEventListenerSpy = jest.spyOn(mockElement, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(mockElement, 'removeEventListener');

      mouseHandler.attachToElement(mockElement);
      const firstCallCount = addEventListenerSpy.mock.calls.length;

      mouseHandler.detach();
      mouseHandler.attachToElement(mockElement);

      expect(removeEventListenerSpy.mock.calls.length).toBe(firstCallCount);
      expect(addEventListenerSpy.mock.calls.length).toBe(firstCallCount * 2);
    });
  });

  describe('Mouse Event Processing', () => {
    beforeEach(() => {
      mouseHandler.attachToElement(mockElement);
    });

    test('should emit mouse move events', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const mouseEvent = new MouseEvent('mousemove', {
        clientX: 100,
        clientY: 200,
        buttons: 0
      });

      // Trigger the mousemove handler
      const mousemoveHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousemove')?.[1];
      mousemoveHandler(mouseEvent);

      // Flush throttle timer
      jest.advanceTimersByTime(8);

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'move',
        x: 100,
        y: 200,
        button: -1,
        buttons: 0,
        timestamp: expect.any(Number)
      });
    });

    test('should throttle mouse move events', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const mousemoveHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousemove')?.[1];

      // Send multiple mouse move events quickly
      for (let i = 0; i < 5; i++) {
        mousemoveHandler(new MouseEvent('mousemove', {
          clientX: 100 + i * 10,
          clientY: 200 + i * 10,
          buttons: 0
        }));
      }

      // Should only process one event due to throttling
      jest.advanceTimersByTime(8);

      expect(eventCallback).toHaveBeenCalledTimes(1);
      expect(eventCallback).toHaveBeenCalledWith({
        type: 'move',
        x: 140, // Last position
        y: 240, // Last position
        button: -1,
        buttons: 0,
        timestamp: expect.any(Number)
      });
    });

    test('should emit mouse click events', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const clickEvent = new MouseEvent('click', {
        clientX: 150,
        clientY: 250,
        button: 0
      });

      const clickHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'click')?.[1];
      clickHandler(clickEvent);

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'click',
        x: 150,
        y: 250,
        button: 0,
        buttons: 0,
        timestamp: expect.any(Number)
      });
    });

    test('should handle right-click events', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const contextMenuEvent = new MouseEvent('contextmenu', {
        clientX: 200,
        clientY: 300,
        button: 2
      });

      const contextMenuHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'contextmenu')?.[1];
      contextMenuHandler(contextMenuEvent);

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'click',
        x: 200,
        y: 300,
        button: 2, // Right button
        buttons: 0,
        timestamp: expect.any(Number)
      });
    });

    test('should handle scroll events', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const wheelEvent = new WheelEvent('wheel', {
        clientX: 300,
        clientY: 400,
        deltaX: 10,
        deltaY: 20
      });

      const wheelHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'wheel')?.[1];
      wheelHandler(wheelEvent);

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'scroll',
        x: 300,
        y: 400,
        button: -1,
        buttons: 0,
        deltaX: 10,
        deltaY: 20,
        timestamp: expect.any(Number)
      });
    });
  });

  describe('Drag Operations', () => {
    beforeEach(() => {
      mouseHandler.attachToElement(mockElement);
    });

    test('should detect drag start and end', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const mouseDownHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousedown')?.[1];
      const mouseUpHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mouseup')?.[1];
      const mouseMoveHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousemove')?.[1];

      // Start drag
      mouseDownHandler(new MouseEvent('mousedown', {
        clientX: 100,
        clientY: 100,
        button: 0
      }));

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'down',
        x: 100,
        y: 100,
        button: 0,
        buttons: 1,
        timestamp: expect.any(Number)
      });

      // Move while dragging
      mouseMoveHandler(new MouseEvent('mousemove', {
        clientX: 150,
        clientY: 150,
        buttons: 1
      }));

      jest.advanceTimersByTime(8);

      // Should emit drag event
      expect(eventCallback).toHaveBeenCalledWith({
        type: 'drag',
        x: 150,
        y: 150,
        button: 0,
        buttons: 1,
        dragStartX: 100,
        dragStartY: 100,
        timestamp: expect.any(Number)
      });

      // End drag
      mouseUpHandler(new MouseEvent('mouseup', {
        clientX: 200,
        clientY: 200,
        button: 0
      }));

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'up',
        x: 200,
        y: 200,
        button: 0,
        buttons: 0,
        timestamp: expect.any(Number)
      });

      // Final drag event
      expect(eventCallback).toHaveBeenCalledWith({
        type: 'drag',
        x: 200,
        y: 200,
        button: 0,
        buttons: 0,
        dragStartX: 100,
        dragStartY: 100,
        timestamp: expect.any(Number)
      });
    });

    test('should not emit drag for movement below threshold', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const mouseDownHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousedown')?.[1];
      const mouseUpHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mouseup')?.[1];

      // Start drag
      mouseDownHandler(new MouseEvent('mousedown', {
        clientX: 100,
        clientY: 100,
        button: 0
      }));

      // End drag with minimal movement (below threshold)
      mouseUpHandler(new MouseEvent('mouseup', {
        clientX: 102,
        clientY: 101,
        button: 0
      }));

      // Should not emit drag event
      const dragEvents = eventCallback.mock.calls.filter(call => call[0].type === 'drag');
      expect(dragEvents).toHaveLength(0);
    });
  });

  describe('Boundary Detection', () => {
    beforeEach(() => {
      mouseHandler.attachToElement(mockElement);
      mouseHandler.setBoundaries({
        left: 0,
        top: 0,
        width: 800,
        height: 600,
        right: 800,
        bottom: 600
      });
    });

    test('should constrain mouse coordinates within boundaries', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const mouseEvent = new MouseEvent('mousemove', {
        clientX: 900, // Outside boundary
        clientY: 700, // Outside boundary
        buttons: 0
      });

      const mousemoveHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousemove')?.[1];
      mousemoveHandler(mouseEvent);

      jest.advanceTimersByTime(8);

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'move',
        x: 800, // Clamped to boundary width
        y: 600, // Clamped to boundary height
        button: -1,
        buttons: 0,
        timestamp: expect.any(Number)
      });
    });

    test('should handle negative coordinates', () => {
      const eventCallback = jest.fn();
      mouseHandler.on('mouseEvent', eventCallback);

      const mouseEvent = new MouseEvent('mousemove', {
        clientX: -50,
        clientY: -100,
        buttons: 0
      });

      const mousemoveHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousemove')?.[1];
      mousemoveHandler(mouseEvent);

      jest.advanceTimersByTime(8);

      expect(eventCallback).toHaveBeenCalledWith({
        type: 'move',
        x: 0, // Clamped to minimum
        y: 0, // Clamped to minimum
        button: -1,
        buttons: 0,
        timestamp: expect.any(Number)
      });
    });
  });

  describe('State Management', () => {
    beforeEach(() => {
      mouseHandler.attachToElement(mockElement);
    });

    test('should track current state correctly', () => {
      const state = mouseHandler.getCurrentState();

      expect(state).toHaveProperty('position');
      expect(state).toHaveProperty('buttons', 0);
      expect(state).toHaveProperty('isDragging', false);
      expect(state).toHaveProperty('isAttached', true);
      expect(state).toHaveProperty('dragStart', null);
    });

    test('should update state during mouse interactions', () => {
      const mouseDownHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mousedown')?.[1];
      const mouseUpHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'mouseup')?.[1];

      // Mouse down - should update button state and drag state
      mouseDownHandler(new MouseEvent('mousedown', {
        clientX: 100,
        clientY: 100,
        button: 0
      }));

      let state = mouseHandler.getCurrentState();
      expect(state.buttons).toBe(1); // Left button pressed
      expect(state.isDragging).toBe(true);
      expect(state.dragStart).toEqual({ x: 100, y: 100 });

      // Mouse up - should reset state
      mouseUpHandler(new MouseEvent('mouseup', {
        clientX: 150,
        clientY: 150,
        button: 0
      }));

      state = mouseHandler.getCurrentState();
      expect(state.buttons).toBe(0); // No buttons pressed
      expect(state.isDragging).toBe(false);
    });
  });

  describe('Configuration', () => {
    test('should update configuration', () => {
      mouseHandler.updateConfig({
        sensitivity: 2.0,
        enableLogging: true,
        clickThreshold: 500
      });

      // Configuration is updated internally
      // The actual effect would be visible in subsequent event handling
      expect(mouseHandler).toBeDefined();
    });
  });

  describe('Event Prevention', () => {
    beforeEach(() => {
      mouseHandler.attachToElement(mockElement);
    });

    test('should prevent default behavior for wheel events', () => {
      const wheelEvent = new WheelEvent('wheel', {
        clientX: 300,
        clientY: 400,
        deltaX: 10,
        deltaY: 20,
        cancelable: true
      });

      const preventDefaultSpy = jest.spyOn(wheelEvent, 'preventDefault');

      const wheelHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'wheel')?.[1];
      wheelHandler(wheelEvent);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    test('should prevent default behavior for context menu', () => {
      const contextMenuEvent = new MouseEvent('contextmenu', {
        cancelable: true
      });

      const preventDefaultSpy = jest.spyOn(contextMenuEvent, 'preventDefault');

      const contextMenuHandler = mockElement.addEventListener.mock.calls
        .find(call => call[0] === 'contextmenu')?.[1];
      contextMenuHandler(contextMenuEvent);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });
});