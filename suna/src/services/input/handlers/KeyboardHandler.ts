/**
 * KeyboardHandler - Comprehensive keyboard input processing for VNC workspace
 *
 * Handles:
 * - Keyboard input capture and character mapping
 * - Modifier key state tracking (Ctrl, Alt, Shift, Cmd/Meta)
 * - Special key handling (function keys, system keys)
 * - International character support
 * - Keyboard shortcuts and conflict resolution
 * - Auto-repeat and key timing
 * - Input Method Editor (IME) support
 */

import { EventEmitter } from 'events';

export interface ModifierState {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean; // Cmd on Mac, Windows key on Windows
}

export interface KeyboardEvent {
  type: 'keydown' | 'keyup' | 'keypress' | 'repeat';
  keyCode: number; // JavaScript key code
  key: string; // JavaScript key string
  charCode: number; // Character code (for text input)
  modifiers: ModifierState;
  isAutoRepeat: boolean;
  timestamp: number;
}

export interface KeyboardShortcut {
  key: string;
  modifiers: Partial<ModifierState>;
  action: string;
  description?: string;
}

export interface KeyboardHandlerConfig {
  enableAutoRepeat: boolean;
  keyDelay: number; // ms between auto-repeats
  enableIMESupport: boolean;
  enableLogging: boolean;
  shortcuts?: KeyboardShortcut[];
}

export class KeyboardHandler extends EventEmitter {
  private config: KeyboardHandlerConfig;
  private element: HTMLElement | null = null;
  private isAttached = false;

  // Current state
  private currentModifiers: ModifierState = {
    ctrl: false,
    alt: false,
    shift: false,
    meta: false
  };

  private pressedKeys: Set<number> = new Set();
  private keyRepeatTimers: Map<number, number> = new Map();

  // Default shortcuts that should be handled
  private defaultShortcuts: KeyboardShortcut[] = [
    { key: 'c', modifiers: { ctrl: true }, action: 'copy', description: 'Copy' },
    { key: 'v', modifiers: { ctrl: true }, action: 'paste', description: 'Paste' },
    { key: 'x', modifiers: { ctrl: true }, action: 'cut', description: 'Cut' },
    { key: 'z', modifiers: { ctrl: true }, action: 'undo', description: 'Undo' },
    { key: 'y', modifiers: { ctrl: true }, action: 'redo', description: 'Redo' },
    { key: 'a', modifiers: { ctrl: true }, action: 'selectall', description: 'Select All' },
    { key: 's', modifiers: { ctrl: true }, action: 'save', description: 'Save' },
    { key: 'Tab', modifiers: {}, action: 'tab', description: 'Tab' },
    { key: 'Enter', modifiers: {}, action: 'enter', description: 'Enter' },
    { key: 'Escape', modifiers: {}, action: 'escape', description: 'Escape' }
  ];

  private shortcuts: KeyboardShortcut[];

  constructor(config: Partial<KeyboardHandlerConfig> = {}) {
    super();

    this.config = {
      enableAutoRepeat: true,
      keyDelay: 50, // 50ms between auto-repeats
      enableIMESupport: true,
      enableLogging: true,
      ...config
    };

    this.shortcuts = [...(config.shortcuts || []), ...this.defaultShortcuts];
  }

  /**
   * Attach keyboard event handlers to an element
   */
  public attachToElement(element: HTMLElement): void {
    if (this.isAttached) {
      this.detach();
    }

    this.element = element;
    this.setupEventListeners();
    this.isAttached = true;

    if (this.config.enableLogging) {
      console.log('KeyboardHandler attached to element:', element);
    }
  }

  /**
   * Detach event handlers
   */
  public detach(): void {
    if (!this.element || !this.isAttached) return;

    this.removeEventListeners();
    this.clearAllKeyRepeatTimers();
    this.element = null;
    this.isAttached = false;

    if (this.config.enableLogging) {
      console.log('KeyboardHandler detached');
    }
  }

  /**
   * Set keyboard shortcuts
   */
  public setShortcuts(shortcuts: KeyboardShortcut[]): void {
    this.shortcuts = [...shortcuts, ...this.defaultShortcuts];
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<KeyboardHandlerConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  private setupEventListeners(): void {
    if (!this.element) return;

    this.element.addEventListener('keydown', this.handleKeyDown);
    this.element.addEventListener('keyup', this.handleKeyUp);
    this.element.addEventListener('keypress', this.handleKeyPress);

    // Handle IME composition events
    if (this.config.enableIMESupport) {
      this.element.addEventListener('compositionstart', this.handleCompositionStart);
      this.element.addEventListener('compositionupdate', this.handleCompositionUpdate);
      this.element.addEventListener('compositionend', this.handleCompositionEnd);
    }

    // Prevent default browser behavior for certain shortcuts
    this.element.addEventListener('beforeinput', this.handleBeforeInput);
  }

  private removeEventListeners(): void {
    if (!this.element) return;

    this.element.removeEventListener('keydown', this.handleKeyDown);
    this.element.removeEventListener('keyup', this.handleKeyUp);
    this.element.removeEventListener('keypress', this.handleKeyPress);

    if (this.config.enableIMESupport) {
      this.element.removeEventListener('compositionstart', this.handleCompositionStart);
      this.element.removeEventListener('compositionupdate', this.handleCompositionUpdate);
      this.element.removeEventListener('compositionend', this.handleCompositionEnd);
    }

    this.element.removeEventListener('beforeinput', this.handleBeforeInput);
  }

  private updateModifierState(event: KeyboardEvent): void {
    this.currentModifiers = {
      ctrl: event.ctrlKey,
      alt: event.altKey,
      shift: event.shiftKey,
      meta: event.metaKey
    };
  }

  private handleKeyDown = (e: KeyboardEvent): void => {
    // Prevent default behavior for keyboard shortcuts
    const shortcut = this.detectShortcut(e);
    if (shortcut) {
      e.preventDefault();
      e.stopPropagation();
      this.emit('shortcut', shortcut);
    }

    this.updateModifierState(e);

    // Check for auto-repeat
    const isAutoRepeat = this.pressedKeys.has(e.keyCode);
    this.pressedKeys.add(e.keyCode);

    const keyboardEvent: KeyboardEvent = {
      type: isAutoRepeat ? 'repeat' : 'keydown',
      keyCode: e.keyCode,
      key: e.key,
      charCode: e.charCode,
      modifiers: { ...this.currentModifiers },
      isAutoRepeat,
      timestamp: Date.now()
    };

    // Handle auto-repeat if enabled
    if (this.config.enableAutoRepeat && !isAutoRepeat && e.repeat === false) {
      this.startKeyRepeat(e.keyCode, keyboardEvent);
    }

    this.emit('keyboardEvent', keyboardEvent);

    if (this.config.enableLogging) {
      console.log('Key down:', keyboardEvent);
    }
  };

  private handleKeyUp = (e: KeyboardEvent): void => {
    this.updateModifierState(e);
    this.pressedKeys.delete(e.keyCode);
    this.clearKeyRepeatTimer(e.keyCode);

    const keyboardEvent: KeyboardEvent = {
      type: 'keyup',
      keyCode: e.keyCode,
      key: e.key,
      charCode: e.charCode,
      modifiers: { ...this.currentModifiers },
      isAutoRepeat: false,
      timestamp: Date.now()
    };

    this.emit('keyboardEvent', keyboardEvent);

    if (this.config.enableLogging) {
      console.log('Key up:', keyboardEvent);
    }
  };

  private handleKeyPress = (e: KeyboardEvent): void => {
    // This event provides the actual character for text input
    const keyboardEvent: KeyboardEvent = {
      type: 'keypress',
      keyCode: e.keyCode,
      key: e.key,
      charCode: e.charCode,
      modifiers: { ...this.currentModifiers },
      isAutoRepeat: false,
      timestamp: Date.now()
    };

    this.emit('keyboardEvent', keyboardEvent);

    if (this.config.enableLogging) {
      console.log('Key press:', keyboardEvent);
    }
  };

  private handleBeforeInput = (e: InputEvent): void => {
    // Prevent certain default behaviors that might interfere with VNC
    if (e.inputType === 'insertText' && this.currentModifiers.ctrl) {
      e.preventDefault();
    }
  };

  private handleCompositionStart = (e: CompositionEvent): void => {
    if (this.config.enableLogging) {
      console.log('IME composition started:', e.data);
    }
  };

  private handleCompositionUpdate = (e: CompositionEvent): void => {
    if (this.config.enableLogging) {
      console.log('IME composition updated:', e.data);
    }
  };

  private handleCompositionEnd = (e: CompositionEvent): void => {
    if (this.config.enableLogging) {
      console.log('IME composition ended:', e.data);
    }
  };

  private detectShortcut(event: KeyboardEvent): KeyboardShortcut | null {
    const key = event.key;
    const modifiers = {
      ctrl: event.ctrlKey,
      alt: event.altKey,
      shift: event.shiftKey,
      meta: event.metaKey
    };

    return this.shortcuts.find(shortcut =>
      shortcut.key.toLowerCase() === key.toLowerCase() &&
      this.modifiersMatch(shortcut.modifiers, modifiers)
    ) || null;
  }

  private modifiersMatch(required: Partial<ModifierState>, current: ModifierState): boolean {
    return Object.entries(required).every(([key, value]) => current[key as keyof ModifierState] === value);
  }

  private startKeyRepeat(keyCode: number, initialEvent: KeyboardEvent): void {
    if (!this.config.enableAutoRepeat) return;

    // Start repeat after initial delay
    const timer = window.setTimeout(() => {
      this.scheduleKeyRepeat(keyCode, initialEvent);
    }, this.config.keyDelay * 4); // Initial delay is 4x repeat delay

    this.keyRepeatTimers.set(keyCode, timer);
  }

  private scheduleKeyRepeat(keyCode: number, initialEvent: KeyboardEvent): void {
    if (!this.pressedKeys.has(keyCode)) return;

    // Emit repeat event
    const repeatEvent: KeyboardEvent = {
      ...initialEvent,
      type: 'repeat',
      isAutoRepeat: true,
      timestamp: Date.now()
    };

    this.emit('keyboardEvent', repeatEvent);

    // Schedule next repeat
    const timer = window.setTimeout(() => {
      this.scheduleKeyRepeat(keyCode, initialEvent);
    }, this.config.keyDelay);

    this.keyRepeatTimers.set(keyCode, timer);
  }

  private clearKeyRepeatTimer(keyCode: number): void {
    const timer = this.keyRepeatTimers.get(keyCode);
    if (timer) {
      clearTimeout(timer);
      this.keyRepeatTimers.delete(keyCode);
    }
  }

  private clearAllKeyRepeatTimers(): void {
    for (const timer of this.keyRepeatTimers.values()) {
      clearTimeout(timer);
    }
    this.keyRepeatTimers.clear();
  }

  /**
   * Map browser key codes to VNC key codes
   */
  public mapKeyCode(browserKeyCode: number): number {
    // This would map browser key codes to VNC-specific key codes
    // For now, return the browser keyCode as-is
    return browserKeyCode;
  }

  /**
   * Convert key string to character code
   */
  public getKeyCharCode(key: string, modifiers: ModifierState): number {
    // Convert key string to character code considering modifier state
    // This is a simplified implementation
    if (key.length === 1) {
      return key.charCodeAt(0);
    }

    // Handle special keys and modified characters
    switch (key) {
      case 'Enter': return 13;
      case 'Escape': return 27;
      case 'Backspace': return 8;
      case 'Tab': return 9;
      case 'Space': return 32;
      default: return 0;
    }
  }

  /**
   * Get current keyboard state
   */
  public getCurrentState() {
    return {
      modifiers: { ...this.currentModifiers },
      pressedKeys: Array.from(this.pressedKeys),
      isAttached: this.isAttached
    };
  }

  /**
   * Check if key is currently pressed
   */
  public isKeyPressed(keyCode: number): boolean {
    return this.pressedKeys.has(keyCode);
  }

  /**
   * Get current modifier state
   */
  public getModifiers(): ModifierState {
    return { ...this.currentModifiers };
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.detach();
    this.removeAllListeners();
  }
}

export default KeyboardHandler;