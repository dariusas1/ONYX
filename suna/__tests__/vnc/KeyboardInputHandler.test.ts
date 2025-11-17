/**
 * Tests for Keyboard Input Handler
 */

import { KeyboardInputHandler, VNC_KEY_CODES } from '../../../src/lib/vnc/KeyboardInputHandler';

// Mock for event handler
const mockOnInputEvent = jest.fn();

describe('KeyboardInputHandler', () => {
  let keyboardHandler: KeyboardInputHandler;

  beforeEach(() => {
    keyboardHandler = new KeyboardInputHandler({}, mockOnInputEvent);
    jest.clearAllMocks();
  });

  afterEach(() => {
    keyboardHandler.clearKeyStates();
  });

  describe('Key Events', () => {
    test('should handle key down events', () => {
      const mockEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'down',
        data: expect.objectContaining({
          key: 'a',
          code: 'KeyA',
          ctrlKey: false,
          shiftKey: false,
          altKey: false,
          metaKey: false
        })
      });
    });

    test('should handle key up events', () => {
      const mockEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyUp(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'up',
        data: expect.objectContaining({
          key: 'a',
          code: 'KeyA'
        })
      });
    });

    test('should handle modifier keys', () => {
      const mockEvent = {
        key: 'Control',
        code: 'ControlLeft',
        location: 1,
        ctrlKey: true,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'down',
        data: expect.objectContaining({
          key: 'Control',
          code: 'ControlLeft',
          ctrlKey: true
        })
      });
    });

    test('should prevent duplicate key down events', () => {
      const mockEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(mockEvent);
      keyboardHandler.handleKeyDown(mockEvent); // Duplicate

      expect(mockOnInputEvent).toHaveBeenCalledTimes(1);
    });

    test('should handle key combinations', () => {
      const ctrlCEvent = {
        key: 'c',
        code: 'KeyC',
        location: 0,
        ctrlKey: true,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(ctrlCEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'down',
        data: expect.objectContaining({
          key: 'c',
          ctrlKey: true
        })
      });
    });
  });

  describe('Auto-repeat', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    test('should setup auto-repeat for repeatable keys', () => {
      const mockEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(mockEvent);

      // Fast-forward past initial delay
      jest.advanceTimersByTime(600);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'repeat',
        data: expect.objectContaining({
          key: 'a'
        })
      });
    });

    test('should not repeat non-repeatable keys', () => {
      const shiftKeyEvent = {
        key: 'Shift',
        code: 'ShiftLeft',
        location: 1,
        ctrlKey: false,
        shiftKey: true,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(shiftKeyEvent);

      // Fast-forward past initial delay
      jest.advanceTimersByTime(600);

      expect(mockOnInputEvent).not.toHaveBeenCalledWith(
        expect.objectContaining({ action: 'repeat' })
      );
    });

    test('should stop repeat on key up', () => {
      const mockEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(mockEvent);

      // Fast-forward a bit
      jest.advanceTimersByTime(100);

      // Release key
      keyboardHandler.handleKeyUp({
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent);

      // Fast-forward past repeat delay
      jest.advanceTimersByTime(500);

      expect(mockOnInputEvent).not.toHaveBeenCalledWith(
        expect.objectContaining({ action: 'repeat' })
      );
    });
  });

  describe('Composition Input', () => {
    test('should handle composition start', () => {
      const mockEvent = {
        data: 'test'
      } as CompositionEvent;

      keyboardHandler.handleCompositionStart(mockEvent);

      // Should not send any events during composition
      expect(mockOnInputEvent).not.toHaveBeenCalled();
    });

    test('should handle composition end', () => {
      const startEvent = { data: '' } as CompositionEvent;
      const endEvent = { data: 'こんにちは' } as CompositionEvent;

      keyboardHandler.handleCompositionStart(startEvent);
      keyboardHandler.handleCompositionEnd(endEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'composed',
        data: expect.objectContaining({
          key: 'こんにちは'
        })
      });
    });

    test('should handle input events', () => {
      const mockEvent = {
        data: '🌟'
      } as InputEvent;

      keyboardHandler.handleInput(mockEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'input',
        data: expect.objectContaining({
          key: '🌟'
        })
      });
    });
  });

  describe('Key State Management', () => {
    test('should track key states', () => {
      const keyEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      expect(keyboardHandler.isKeyPressed('a')).toBe(false);

      keyboardHandler.handleKeyDown(keyEvent);
      expect(keyboardHandler.isKeyPressed('a')).toBe(true);

      keyboardHandler.handleKeyUp({
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent);
      expect(keyboardHandler.isKeyPressed('a')).toBe(false);
    });

    test('should get all key states', () => {
      const keys = ['a', 'b', 'c'];
      const events = keys.map(key => ({
        key,
        code: `Key${key.toUpperCase()}`,
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent);

      events.forEach(event => keyboardHandler.handleKeyDown(event));

      const keyStates = keyboardHandler.getKeyState();
      expect(keyStates.size).toBeGreaterThan(0);
      keys.forEach(key => {
        expect(Array.from(keyStates.values()).includes(true)).toBe(true);
      });
    });
  });

  describe('VNC Key Codes', () => {
    test('should provide correct VNC key codes', () => {
      expect(VNC_KEY_CODES['a']).toBe(0x61);
      expect(VNC_KEY_CODES['Enter']).toBe(0xff0d);
      expect(VNC_KEY_CODES['Escape']).toBe(0xff1b);
      expect(VNC_KEY_CODES['ArrowUp']).toBe(0xff52);
    });

    test('should get VNC key code for regular keys', () => {
      const keyCode = keyboardHandler.getVNCKeyCode('a');
      expect(keyCode).toBe(0x61);
    });

    test('should get VNC key code for shifted characters', () => {
      const keyCode = keyboardHandler.getVNCKeyCode('!', true);
      expect(keyCode).toBe(0x31); // Shifted ! maps to '1' key code
    });
  });

  describe('International Layout Support', () => {
    test('should support layout changes', () => {
      keyboardHandler.setLayout('fr-FR');
      expect(keyboardHandler.getCurrentLayout()).toBe('fr-FR');
    });

    test('should handle dead keys for international characters', () => {
      // This is a simplified test - actual dead key handling would be more complex
      const result = keyboardHandler['handleDeadKey']('`', 'a');
      // This depends on the implementation of dead key combinations
      expect(typeof result).toBe('string');
    });
  });

  describe('Configuration', () => {
    test('should update configuration', () => {
      keyboardHandler.updateConfig({
        enableAutoRepeat: false,
        repeatDelay: 1000,
        repeatInterval: 100
      });

      // Test that auto-repeat is disabled
      const mockEvent = {
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(mockEvent);

      // Fast-forward past delay
      jest.advanceTimersByTime(1100);

      expect(mockOnInputEvent).not.toHaveBeenCalledWith(
        expect.objectContaining({ action: 'repeat' })
      );
    });
  });

  describe('Special Keys', () => {
    test('should handle function keys', () => {
      const fKeyEvent = {
        key: 'F1',
        code: 'F1',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(fKeyEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'down',
        data: expect.objectContaining({
          key: 'F1',
          code: 'F1'
        })
      });
    });

    test('should handle navigation keys', () => {
      const arrowEvent = {
        key: 'ArrowUp',
        code: 'ArrowUp',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(arrowEvent);

      expect(mockOnInputEvent).toHaveBeenCalledWith({
        type: 'keyboard',
        action: 'down',
        data: expect.objectContaining({
          key: 'ArrowUp',
          code: 'ArrowUp'
        })
      });
    });

    test('should handle modifier keys on different locations', () => {
      const leftShift = {
        key: 'Shift',
        code: 'ShiftLeft',
        location: 1,
        ctrlKey: false,
        shiftKey: true,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      const rightShift = {
        key: 'Shift',
        code: 'ShiftRight',
        location: 2,
        ctrlKey: false,
        shiftKey: true,
        altKey: false,
        metaKey: false
      } as KeyboardEvent;

      keyboardHandler.handleKeyDown(leftShift);
      keyboardHandler.handleKeyDown(rightShift);

      expect(mockOnInputEvent).toHaveBeenCalledTimes(2);
      expect(mockOnInputEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ code: 'ShiftLeft', location: 1 })
        })
      );
      expect(mockOnInputEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({ code: 'ShiftRight', location: 2 })
        })
      );
    });
  });

  describe('State Cleanup', () => {
    test('should clear all key states', () => {
      // Press some keys
      keyboardHandler.handleKeyDown({
        key: 'a',
        code: 'KeyA',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent);

      keyboardHandler.handleKeyDown({
        key: 'b',
        code: 'KeyB',
        location: 0,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        metaKey: false
      } as KeyboardEvent);

      expect(keyboardHandler.isKeyPressed('a')).toBe(true);
      expect(keyboardHandler.isKeyPressed('b')).toBe(true);

      keyboardHandler.clearKeyStates();

      expect(keyboardHandler.isKeyPressed('a')).toBe(false);
      expect(keyboardHandler.isKeyPressed('b')).toBe(false);
    });
  });
});