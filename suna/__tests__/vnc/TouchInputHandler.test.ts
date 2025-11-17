/**
 * Tests for Touch Input Handler
 */

import { TouchInputHandler } from '../../../src/lib/vnc/TouchInputHandler';

// Mock for event handler
const mockOnInputEvent = jest.fn();

describe('TouchInputHandler', () => {
  let touchHandler: TouchInputHandler;

  beforeEach(() => {
    touchHandler = new TouchInputHandler({}, mockOnInputEvent);
    jest.clearAllMocks();
  });

  afterEach(() => {
    touchHandler.clearTouchState();
  });

  describe('Single Touch', () => {
    test('should handle touch start', () => {
      const mockEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1,
          radiusX: 10,
          radiusY: 10
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(mockEvent);

      expect(mockEvent.preventDefault).toHaveBeenCalled();
      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'down',
        data: expect.objectContaining({
          button: 0,
          position: { x: 100, y: 200 }
        })
      });
    });

    test('should handle touch move', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const moveEvent = {
        touches: [{
          identifier: 1,
          clientX: 110,
          clientY: 210,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchMove(moveEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'move',
        data: expect.objectContaining({
          position: { x: 110, y: 210 }
        })
      });
    });

    test('should handle touch end', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const endEvent = {
        changedTouches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 0
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchEnd(endEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'up',
        data: expect.objectContaining({
          button: 0,
          position: { x: 100, y: 200 }
        })
      });
    });

    test('should detect tap gesture', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const endEvent = {
        changedTouches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 0
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchEnd(endEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'tap',
        data: expect.objectContaining({
          touches: expect.arrayContaining([
            expect.objectContaining({ x: 100, y: 200 })
          ])
        })
      });
    });

    test('should detect double tap', () => {
      const firstTap = {
        touches: [{ identifier: 1, clientX: 100, clientY: 200, force: 1 }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const firstEnd = {
        changedTouches: [{ identifier: 1, clientX: 100, clientY: 200, force: 0 }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const secondTap = {
        touches: [{ identifier: 2, clientX: 100, clientY: 200, force: 1 }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const secondEnd = {
        changedTouches: [{ identifier: 2, clientX: 100, clientY: 200, force: 0 }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(firstTap);
      touchHandler.handleTouchEnd(firstEnd);

      // Simulate quick second tap
      setTimeout(() => {
        touchHandler.handleTouchStart(secondTap);
        touchHandler.handleTouchEnd(secondEnd);

        expect(mockOnInputEvent).toHaveBeenCalledWith({
          type: 'touch',
          action: 'double-tap',
          data: expect.any(Object)
        });
      }, 200);
    });

    test('should detect long press', () => {
      jest.useFakeTimers();

      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);

      // Fast-forward past long press threshold
      jest.advanceTimersByTime(600);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'long-press',
        data: expect.objectContaining({
          touches: expect.arrayContaining([
            expect.objectContaining({ x: 100, y: 200 })
          ])
        })
      });

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'context',
        data: expect.objectContaining({
          button: 2, // Right button for long press
          position: { x: 100, y: 200 }
        })
      });

      jest.useRealTimers();
    });
  });

  describe('Swipe Detection', () => {
    test('should detect right swipe', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const moveEvent = {
        touches: [{
          identifier: 1,
          clientX: 150,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchMove(moveEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'swipe',
        data: expect.objectContaining({
          direction: 'right',
          distance: expect.any(Number)
        })
      });
    });

    test('should detect vertical swipe', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const moveEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 250,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchMove(moveEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'swipe',
        data: expect.objectContaining({
          direction: 'down'
        })
      });
    });

    test('should not detect swipe for small movements', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const moveEvent = {
        touches: [{
          identifier: 1,
          clientX: 105,
          clientY: 202,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchMove(moveEvent);

      expect(mockOnInputEvent).not.toHaveBeenCalledWith(
        expect.objectContaining({ action: 'swipe' })
      );
    });
  });

  describe('Multi-Touch', () => {
    test('should handle two finger pinch', () => {
      const startEvent = {
        touches: [
          { identifier: 1, clientX: 100, clientY: 200, force: 1 },
          { identifier: 2, clientX: 200, clientY: 200, force: 1 }
        ],
        preventDefault: jest.fn()
      } as TouchEvent;

      const pinchEvent = {
        touches: [
          { identifier: 1, clientX: 90, clientY: 200, force: 1 },
          { identifier: 2, clientX: 210, clientY: 200, force: 1 }
        ],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchMove(pinchEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'pinch',
        data: expect.objectContaining({
          scale: expect.any(Number),
          distance: expect.any(Number)
        })
      });
    });

    test('should handle two finger scroll', () => {
      const startEvent = {
        touches: [
          { identifier: 1, clientX: 100, clientY: 200, force: 1 },
          { identifier: 2, clientX: 200, clientY: 200, force: 1 }
        ],
        preventDefault: jest.fn()
      } as TouchEvent;

      const scrollEvent = {
        touches: [
          { identifier: 1, clientX: 100, clientY: 150, force: 1 },
          { identifier: 2, clientX: 200, clientY: 150, force: 1 }
        ],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchMove(scrollEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'mouse',
        action: 'scroll',
        data: expect.objectContaining({
          deltaY: expect.any(Number),
          position: { x: 150, y: 150 }
        })
      });
    });

    test('should handle multi-touch events', () => {
      const multiTouchEvent = {
        touches: [
          { identifier: 1, clientX: 100, clientY: 200, force: 1 },
          { identifier: 2, clientX: 150, clientY: 250, force: 1 },
          { identifier: 3, clientX: 200, clientY: 200, force: 1 }
        ],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(multiTouchEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'multi-touch',
        data: expect.objectContaining({
          touches: expect.arrayContaining([
            expect.objectContaining({ id: 1 }),
            expect.objectContaining({ id: 2 }),
            expect.objectContaining({ id: 3 })
          ])
        })
      });
    });
  });

  describe('Touch State Management', () => {
    test('should track active touches', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);

      const activeTouches = touchHandler.getActiveTouches();
      expect(activeTouches).toHaveLength(1);
      expect(activeTouches[0]).toEqual(expect.objectContaining({
        id: 1,
        x: 100,
        y: 200
      }));
    });

    test('should track touching state', () => {
      expect(touchHandler.isTouching()).toBe(false);

      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      expect(touchHandler.isTouching()).toBe(true);

      const endEvent = {
        changedTouches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 0
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchEnd(endEvent);
      expect(touchHandler.isTouching()).toBe(false);
    });

    test('should maintain touch history', () => {
      const events = [
        { touches: [{ identifier: 1, clientX: 100, clientY: 200, force: 1 }], preventDefault: jest.fn() },
        { touches: [{ identifier: 1, clientX: 110, clientY: 210, force: 1 }], preventDefault: jest.fn() },
        { touches: [{ identifier: 1, clientX: 120, clientY: 220, force: 1 }], preventDefault: jest.fn() }
      ] as TouchEvent[];

      events.forEach(event => touchHandler.handleTouchMove(event));

      const history = touchHandler.getTouchHistory();
      expect(history.length).toBeGreaterThan(2);
      expect(history[0]).toEqual(expect.objectContaining({ x: 100, y: 200 }));
    });
  });

  describe('Touch Cancel', () => {
    test('should handle touch cancel', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const cancelEvent = {
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchCancel(cancelEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'cancel',
        data: expect.any(Object)
      });

      expect(touchHandler.isTouching()).toBe(false);
    });
  });

  describe('Configuration', () => {
    test('should update configuration', () => {
      touchHandler.updateConfig({
        tapThreshold: 100,
        longPressThreshold: 750,
        swipeThreshold: 50
      });

      jest.useFakeTimers();

      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);

      // Fast-forward past new long press threshold
      jest.advanceTimersByTime(800);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'long-press',
        data: expect.any(Object)
      });

      jest.useRealTimers();
    });
  });

  describe('Gesture Thresholds', () => {
    test('should respect touch slop for tap detection', () => {
      const startEvent = {
        touches: [{
          identifier: 1,
          clientX: 100,
          clientY: 200,
          force: 1
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      const endEvent = {
        changedTouches: [{
          identifier: 1,
          clientX: 105, // Small movement within slop
          clientY: 205,
          force: 0
        }],
        preventDefault: jest.fn()
      } as TouchEvent;

      touchHandler.handleTouchStart(startEvent);
      touchHandler.handleTouchEnd(endEvent);

      // Should still detect tap despite small movement
      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'touch',
        action: 'tap',
        data: expect.any(Object)
      });
    });
  });

  describe('Performance', () => {
    test('should clean up old touch history', () => {
      jest.useFakeTimers();

      // Add some touches
      for (let i = 0; i < 5; i++) {
        const event = {
          touches: [{
            identifier: i,
            clientX: i * 10,
            clientY: i * 10,
            force: 1
          }],
          preventDefault: jest.fn()
        } as TouchEvent;

        touchHandler.handleTouchMove(event);
      }

      // Fast-forward past cleanup time
      jest.advanceTimersByTime(6000);

      // History should be cleaned up
      const history = touchHandler.getTouchHistory();
      expect(history.length).toBeLessThan(5);

      jest.useRealTimers();
    });
  });
});