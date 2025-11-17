/**
 * Tests for Mouse Input Handler
 */

import { MouseInputHandler } from '../../../src/lib/vnc/MouseInputHandler';

// Mock for event handler
const mockOnInputEvent = jest.fn();

describe('MouseInputHandler', () => {
  let mouseHandler: MouseInputHandler;

  beforeEach(() => {
    mouseHandler = new MouseInputHandler({}, mockOnInputEvent);
    jest.clearAllMocks();
  });

  afterEach(() => {
    mouseHandler.clearMovementBuffer();
  });

  describe('Mouse Movement', () => {
    test('should handle mouse movement events', () => {
      const mockEvent = {
        clientX: 100,
        clientY: 200,
        buttons: 0
      } as MouseEvent;

      mouseHandler.handleMouseMove(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'move',
        data: expect.objectContaining({
          position: { x: 100, y: 200, timestamp: expect.any(Number) },
          buttons: 0
        })
      });
    });

    test('should apply smoothing when enabled', () => {
      const handler = new MouseInputHandler({ smoothingFactor: 0.5 }, mockOnInputEvent);

      const firstEvent = { clientX: 100, clientY: 200, buttons: 0 } as MouseEvent;
      const secondEvent = { clientX: 110, clientY: 210, buttons: 0 } as MouseEvent;

      handler.handleMouseMove(firstEvent);
      handler.handleMouseMove(secondEvent);

      expect(mockOnInputEvent).toHaveBeenCalledTimes(2);

      // Second event should be smoothed between first and second position
      const secondCall = mockOnInputEvent.mock.calls[1][0];
      expect(secondCall.data.position.x).toBeLessThan(110);
      expect(secondCall.data.position.y).toBeLessThan(210);
    });

    test('should respect movement threshold', () => {
      const handler = new MouseInputHandler({ movementThreshold: 5 }, mockOnInputEvent);

      const firstEvent = { clientX: 100, clientY: 200, buttons: 0 } as MouseEvent;
      const secondEvent = { clientX: 102, clientY: 202, buttons: 0 } as MouseEvent; // Small movement

      handler.handleMouseMove(firstEvent);
      handler.handleMouseMove(secondEvent);

      expect(mockOnInputEvent).toHaveBeenCalledTimes(1); // Only first event should be sent
    });
  });

  describe('Mouse Clicks', () => {
    test('should handle mouse down events', () => {
      const mockEvent = {
        clientX: 150,
        clientY: 250,
        button: 0 // Left button
      } as MouseEvent;

      mouseHandler.handleMouseDown(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'down',
        data: expect.objectContaining({
          button: 0,
          position: { x: 150, y: 250, timestamp: expect.any(Number) }
        })
      });
    });

    test('should handle mouse up events', () => {
      const mockEvent = {
        clientX: 150,
        clientY: 250,
        button: 1 // Middle button
      } as MouseEvent;

      mouseHandler.handleMouseUp(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'up',
        data: expect.objectContaining({
          button: 1,
          position: { x: 150, y: 250, timestamp: expect.any(Number) }
        })
      });
    });

    test('should detect double clicks', () => {
      const firstClick = { clientX: 100, clientY: 100, button: 0 } as MouseEvent;
      const secondClick = { clientX: 100, clientY: 100, button: 0 } as MouseEvent;

      mouseHandler.handleMouseDown(firstClick);
      mouseHandler.handleMouseUp({ clientX: 100, clientY: 100, button: 0 } as MouseEvent);

      // Wait a short time then click again
      setTimeout(() => {
        mouseHandler.handleMouseDown(secondClick);

        expect(mockOnInputEvent).toHaveBeenCalledWith({
          type: 'mouse',
          action: 'down',
          data: expect.any(Object),
          clickCount: 2
        });
      }, 100);
    });
  });

  describe('Mouse Scroll', () => {
    test('should handle wheel events', () => {
      const mockEvent = {
        clientX: 200,
        clientY: 300,
        deltaX: 10,
        deltaY: 20,
        deltaMode: WheelEvent.DOM_DELTA_PIXEL,
        preventDefault: jest.fn()
      } as WheelEvent;

      mouseHandler.handleWheel(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'scroll',
        data: expect.objectContaining({
          deltaX: 10,
          deltaY: 20,
          position: { x: 200, y: 300, timestamp: expect.any(Number) }
        })
      });

      expect(mockEvent.preventDefault).toHaveBeenCalled();
    });

    test('should normalize different scroll modes', () => {
      const lineModeEvent = {
        clientX: 200,
        clientY: 300,
        deltaX: 1,
        deltaY: 2,
        deltaMode: WheelEvent.DOM_DELTA_LINE,
        preventDefault: jest.fn()
      } as WheelEvent;

      mouseHandler.handleWheel(lineModeEvent);

      const callData = mockOnInputEvent.mock.calls[0][0].data;
      expect(callData.deltaX).toBe(16); // 1 line * 16 pixels
      expect(callData.deltaY).toBe(32); // 2 lines * 16 pixels
    });

    test('should ignore micro-scrolls', () => {
      const microScrollEvent = {
        clientX: 200,
        clientY: 300,
        deltaX: 0.5,
        deltaY: 0.5,
        deltaMode: WheelEvent.DOM_DELTA_PIXEL,
        preventDefault: jest.fn()
      } as WheelEvent;

      mouseHandler.handleWheel(microScrollEvent);

      expect(mockOnInputEvent).not.toHaveBeenCalled();
      expect(microScrollEvent.preventDefault).not.toHaveBeenCalled();
    });
  });

  describe('Context Menu', () => {
    test('should handle context menu events', () => {
      const mockEvent = {
        clientX: 300,
        clientY: 400,
        preventDefault: jest.fn()
      } as MouseEvent;

      mouseHandler.handleContextMenu(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'context',
        data: expect.objectContaining({
          button: 2, // Right button
          position: { x: 300, y: 400, timestamp: expect.any(Number) }
        })
      });

      expect(mockEvent.preventDefault).toHaveBeenCalled();
    });
  });

  describe('State Management', () => {
    test('should track mouse press state', () => {
      expect(mouseHandler.isMousePressed()).toBe(false);

      const downEvent = { clientX: 100, clientY: 100, button: 0 } as MouseEvent;
      const upEvent = { clientX: 100, clientY: 100, button: 0 } as MouseEvent;

      mouseHandler.handleMouseDown(downEvent);
      expect(mouseHandler.isMousePressed()).toBe(true);

      mouseHandler.handleMouseUp(upEvent);
      expect(mouseHandler.isMousePressed()).toBe(false);
    });

    test('should maintain movement buffer', () => {
      const events = [
        { clientX: 100, clientY: 100, buttons: 0 },
        { clientX: 110, clientY: 110, buttons: 0 },
        { clientX: 120, clientY: 120, buttons: 0 }
      ] as MouseEvent[];

      events.forEach(event => mouseHandler.handleMouseMove(event));

      const buffer = mouseHandler.getMovementBuffer();
      expect(buffer).toHaveLength(3);
      expect(buffer[0]).toEqual(expect.objectContaining({ x: 100, y: 100 }));
      expect(buffer[2]).toEqual(expect.objectContaining({ x: 120, y: 120 }));
    });

    test('should limit movement buffer size', () => {
      // Add more than 10 events
      for (let i = 0; i < 15; i++) {
        mouseHandler.handleMouseMove({
          clientX: i * 10,
          clientY: i * 10,
          buttons: 0
        } as MouseEvent);
      }

      const buffer = mouseHandler.getMovementBuffer();
      expect(buffer).toHaveLength(10); // Should be limited to 10
    });
  });

  describe('Prediction', () => {
    test('should predict next position when enabled', () => {
      const handler = new MouseInputHandler({ enablePrediction: true }, mockOnInputEvent);

      // Add some movement to build velocity
      handler.handleMouseMove({ clientX: 100, clientY: 100, buttons: 0 } as MouseEvent);
      handler.handleMouseMove({ clientX: 110, clientY: 110, buttons: 0 } as MouseEvent);
      handler.handleMouseMove({ clientX: 120, clientY: 120, buttons: 0 } as MouseEvent);

      const currentPosition = handler.getCurrentPosition();
      expect(currentPosition).toBeTruthy();
      expect(currentPosition!.x).toBeGreaterThanOrEqual(120);
      expect(currentPosition!.y).toBeGreaterThanOrEqual(120);
    });

    test('should return current position when prediction disabled', () => {
      const handler = new MouseInputHandler({ enablePrediction: false }, mockOnInputEvent);

      handler.handleMouseMove({ clientX: 100, clientY: 100, buttons: 0 } as MouseEvent);
      handler.handleMouseMove({ clientX: 110, clientY: 110, buttons: 0 } as MouseEvent);

      const currentPosition = handler.getCurrentPosition();
      expect(currentPosition).toEqual(expect.objectContaining({ x: 110, y: 110 }));
    });

    test('should calculate velocity for gesture detection', () => {
      // Add movement with known velocity
      mouseHandler.handleMouseMove({ clientX: 100, clientY: 100, buttons: 0 } as MouseEvent);

      // Small delay to ensure timestamp difference
      setTimeout(() => {
        mouseHandler.handleMouseMove({ clientX: 110, clientY: 110, buttons: 0 } as MouseEvent);

        const velocity = mouseHandler.getVelocity();
        expect(velocity).toBeTruthy();
        expect(velocity!.x).toBeGreaterThan(0);
        expect(velocity!.y).toBeGreaterThan(0);
      }, 50);
    });
  });

  describe('Configuration', () => {
    test('should update configuration', () => {
      mouseHandler.updateConfig({
        smoothingFactor: 0.8,
        movementThreshold: 3
      });

      // Test updated threshold
      const firstEvent = { clientX: 100, clientY: 100, buttons: 0 } as MouseEvent;
      const secondEvent = { clientX: 102, clientY: 102, buttons: 0 } as MouseEvent;

      mouseHandler.handleMouseMove(firstEvent);
      mouseHandler.handleMouseMove(secondEvent);

      expect(mockOnInputEvent).toHaveBeenCalledTimes(1); // Should be filtered by new threshold
    });
  });
});