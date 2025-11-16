/**
 * TouchHandler - Touch device input processing for VNC workspace
 *
 * Handles:
 * - Touch event mapping to mouse events
 * - Multi-touch gesture support (pinch, swipe)
 * - Touch scrolling and zooming
 * - On-screen keyboard integration
 * - Touch device detection and optimization
 * - Gesture recognition and interpretation
 */

import { EventEmitter } from 'events';

export interface TouchPoint {
  id: number;
  x: number;
  y: number;
  startX: number;
  startY: number;
  timestamp: number;
}

export interface TouchEvent {
  type: 'touchstart' | 'touchmove' | 'touchend' | 'touchcancel' | 'gesture';
  touches: TouchPoint[];
  changedTouches: TouchPoint[];
  gestureType?: 'pinch' | 'swipe' | 'zoom' | 'rotate' | 'tap' | 'doubletap';
  gestureValue?: number; // Distance for pinch, velocity for swipe, scale for zoom
  gestureCenter?: { x: number; y: number };
  timestamp: number;
}

export interface TouchHandlerConfig {
  gestureThreshold: number; // pixels for gesture detection
  pinchSensitivity: number;
  swipeThreshold: number; // minimum velocity for swipe
  tapThreshold: number; // ms for tap detection
  doubleTapThreshold: number; // ms for double-tap
  enableGestures: boolean;
  enableLogging: boolean;
}

export class TouchHandler extends EventEmitter {
  private config: TouchHandlerConfig;
  private element: HTMLElement | null = null;
  private isAttached = false;

  // Touch state tracking
  private activeTouches: Map<number, TouchPoint> = new Map();
  private lastTouchTime = 0;
  private tapCount = 0;
  private gestureState = {
    isPinching: false,
    isSwiping: false,
    initialDistance: 0,
    initialAngle: 0,
    lastDistance: 0,
    center: { x: 0, y: 0 }
  };

  // On-screen keyboard state
  private onScreenKeyboardVisible = false;
  private keyboardElement: HTMLElement | null = null;

  constructor(config: Partial<TouchHandlerConfig> = {}) {
    super();

    this.config = {
      gestureThreshold: 10,
      pinchSensitivity: 1.0,
      swipeThreshold: 50,
      tapThreshold: 300,
      doubleTapThreshold: 300,
      enableGestures: true,
      enableLogging: true,
      ...config
    };
  }

  /**
   * Attach touch event handlers to an element
   */
  public attachToElement(element: HTMLElement): void {
    if (this.isAttached) {
      this.detach();
    }

    this.element = element;
    this.setupEventListeners();
    this.isAttached = true;

    if (this.config.enableLogging) {
      console.log('TouchHandler attached to element:', element);
    }
  }

  /**
   * Detach event handlers
   */
  public detach(): void {
    if (!this.element || !this.isAttached) return;

    this.removeEventListeners();
    this.element = null;
    this.isAttached = false;
    this.resetTouchState();

    if (this.config.enableLogging) {
      console.log('TouchHandler detached');
    }
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<TouchHandlerConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  private setupEventListeners(): void {
    if (!this.element) return;

    this.element.addEventListener('touchstart', this.handleTouchStart, { passive: false });
    this.element.addEventListener('touchmove', this.handleTouchMove, { passive: false });
    this.element.addEventListener('touchend', this.handleTouchEnd, { passive: false });
    this.element.addEventListener('touchcancel', this.handleTouchCancel, { passive: false });

    // Prevent default touch behaviors that interfere with VNC
    this.element.addEventListener('gesturestart', this.preventGesture);
    this.element.addEventListener('gesturechange', this.preventGesture);
    this.element.addEventListener('gestureend', this.preventGesture);
  }

  private removeEventListeners(): void {
    if (!this.element) return;

    this.element.removeEventListener('touchstart', this.handleTouchStart);
    this.element.removeEventListener('touchmove', this.handleTouchMove);
    this.element.removeEventListener('touchend', this.handleTouchEnd);
    this.element.removeEventListener('touchcancel', this.handleTouchCancel);
    this.element.removeEventListener('gesturestart', this.preventGesture);
    this.element.removeEventListener('gesturechange', this.preventGesture);
    this.element.removeEventListener('gestureend', this.preventGesture);
  }

  private preventGesture = (e: Event): void => {
    e.preventDefault();
  };

  private handleTouchStart = (e: TouchEvent): void => {
    e.preventDefault();

    const now = Date.now();
    const touches = Array.from(e.touches);

    // Track new touches
    for (const touch of touches) {
      const touchPoint: TouchPoint = {
        id: touch.identifier,
        x: touch.clientX,
        y: touch.clientY,
        startX: touch.clientX,
        startY: touch.clientY,
        timestamp: now
      };

      this.activeTouches.set(touch.identifier, touchPoint);
    }

    // Initialize gesture state for multi-touch
    if (touches.length === 2 && this.config.enableGestures) {
      this.initializeGestureState(touches);
    }

    // Check for tap/double-tap
    if (touches.length === 1) {
      this.handleTapDetection(now);
    }

    const touchEvent: TouchEvent = {
      type: 'touchstart',
      touches: Array.from(this.activeTouches.values()),
      changedTouches: this.getChangedTouches(e.changedTouches),
      timestamp: now
    };

    this.emit('touchEvent', touchEvent);

    if (this.config.enableLogging) {
      console.log('Touch start:', touchEvent);
    }
  };

  private handleTouchMove = (e: TouchEvent): void => {
    e.preventDefault();

    const now = Date.now();
    const touches = Array.from(e.touches);

    // Update active touch positions
    for (const touch of touches) {
      const touchPoint = this.activeTouches.get(touch.identifier);
      if (touchPoint) {
        touchPoint.x = touch.clientX;
        touchPoint.y = touch.clientY;
      }
    }

    let gestureEvent: TouchEvent | null = null;

    // Handle multi-touch gestures
    if (touches.length === 2 && this.config.enableGestures) {
      gestureEvent = this.handleMultiTouchGesture(touches);
    } else if (touches.length === 1) {
      // Single touch movement maps to mouse movement
      const touch = touches[0];
      const touchPoint = this.activeTouches.get(touch.identifier)!;

      gestureEvent = {
        type: 'touchmove',
        touches: [touchPoint],
        changedTouches: this.getChangedTouches(e.changedTouches),
        timestamp: now
      };
    }

    if (gestureEvent) {
      this.emit('touchEvent', gestureEvent);
    }

    if (this.config.enableLogging && this.config.enableGestures && touches.length >= 2) {
      console.log('Touch move (multi-touch):', gestureEvent);
    }
  };

  private handleTouchEnd = (e: TouchEvent): void => {
    e.preventDefault();

    const now = Date.now();
    const touches = Array.from(e.touches);
    const changedTouches = Array.from(e.changedTouches);

    // Remove ended touches
    for (const touch of changedTouches) {
      this.activeTouches.delete(touch.identifier);
    }

    // Finalize gesture state
    if (touches.length === 0) {
      this.finalizeGestureState();
    } else if (touches.length === 1 && this.config.enableGestures) {
      // Transition from multi-touch to single-touch
      this.resetGestureState();
    }

    const touchEvent: TouchEvent = {
      type: 'touchend',
      touches: Array.from(this.activeTouches.values()),
      changedTouches: this.getChangedTouches(changedTouches),
      timestamp: now
    };

    this.emit('touchEvent', touchEvent);

    if (this.config.enableLogging) {
      console.log('Touch end:', touchEvent);
    }
  };

  private handleTouchCancel = (e: TouchEvent): void => {
    e.preventDefault();

    // Clear all active touches
    this.activeTouches.clear();
    this.resetGestureState();

    const touchEvent: TouchEvent = {
      type: 'touchcancel',
      touches: [],
      changedTouches: this.getChangedTouches(e.changedTouches),
      timestamp: Date.now()
    };

    this.emit('touchEvent', touchEvent);

    if (this.config.enableLogging) {
      console.log('Touch cancel:', touchEvent);
    }
  };

  private getChangedTouches(changedTouches: TouchList): TouchPoint[] {
    return Array.from(changedTouches).map(touch => ({
      id: touch.identifier,
      x: touch.clientX,
      y: touch.clientY,
      startX: touch.clientX,
      startY: touch.clientY,
      timestamp: Date.now()
    }));
  }

  /**
   * Gesture detection and handling
   */
  private initializeGestureState(touches: Touch[]): void {
    const touch1 = touches[0];
    const touch2 = touches[1];

    const centerX = (touch1.clientX + touch2.clientX) / 2;
    const centerY = (touch1.clientY + touch2.clientY) / 2;

    const distance = this.calculateDistance(touch1, touch2);
    const angle = this.calculateAngle(touch1, touch2);

    this.gestureState = {
      isPinching: false,
      isSwiping: false,
      initialDistance: distance,
      initialAngle: angle,
      lastDistance: distance,
      center: { x: centerX, y: centerY }
    };
  }

  private handleMultiTouchGesture(touches: Touch[]): TouchEvent | null {
    if (touches.length !== 2) return null;

    const touch1 = touches[0];
    const touch2 = touches[1];

    const centerX = (touch1.clientX + touch2.clientX) / 2;
    const centerY = (touch1.clientY + touch2.clientY) / 2;

    const currentDistance = this.calculateDistance(touch1, touch2);
    const currentAngle = this.calculateAngle(touch1, touch2);

    const distanceDelta = currentDistance - this.gestureState.lastDistance;
    const scale = currentDistance / this.gestureState.initialDistance;

    // Detect pinch/zoom gesture
    if (Math.abs(distanceDelta) > this.config.gestureThreshold) {
      this.gestureState.isPinching = true;

      return {
        type: 'touchmove',
        touches: Array.from(this.activeTouches.values()),
        changedTouches: [],
        gestureType: 'pinch',
        gestureValue: scale,
        gestureCenter: { x: centerX, y: centerY },
        timestamp: Date.now()
      };
    }

    this.gestureState.lastDistance = currentDistance;
    return null;
  }

  private finalizeGestureState(): void {
    if (this.gestureState.isPinching) {
      const scale = this.gestureState.lastDistance / this.gestureState.initialDistance;

      const gestureEvent: TouchEvent = {
        type: 'gesture',
        touches: [],
        changedTouches: [],
        gestureType: 'zoom',
        gestureValue: scale,
        gestureCenter: this.gestureState.center,
        timestamp: Date.now()
      };

      this.emit('touchEvent', gestureEvent);
    }

    this.resetGestureState();
  }

  private resetGestureState(): void {
    this.gestureState = {
      isPinching: false,
      isSwiping: false,
      initialDistance: 0,
      initialAngle: 0,
      lastDistance: 0,
      center: { x: 0, y: 0 }
    };
  }

  private calculateDistance(touch1: Touch, touch2: Touch): number {
    const dx = touch2.clientX - touch1.clientX;
    const dy = touch2.clientY - touch1.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  private calculateAngle(touch1: Touch, touch2: Touch): number {
    const dx = touch2.clientX - touch1.clientX;
    const dy = touch2.clientY - touch1.clientY;
    return Math.atan2(dy, dx);
  }

  /**
   * Tap detection
   */
  private handleTapDetection(timestamp: number): void {
    const timeSinceLastTap = timestamp - this.lastTouchTime;

    if (timeSinceLastTap < this.config.doubleTapThreshold) {
      this.tapCount++;
      if (this.tapCount === 2) {
        // Double tap detected
        this.emit('touchEvent', {
          type: 'gesture',
          touches: Array.from(this.activeTouches.values()),
          changedTouches: [],
          gestureType: 'doubletap',
          gestureCenter: { x: this.activeTouches.values().next().value.x, y: this.activeTouches.values().next().value.y },
          timestamp
        });

        this.tapCount = 0;
      }
    } else {
      this.tapCount = 1;
    }

    this.lastTouchTime = timestamp;

    // Schedule single tap if no second tap occurs
    setTimeout(() => {
      if (this.tapCount === 1) {
        this.emit('touchEvent', {
          type: 'gesture',
          touches: Array.from(this.activeTouches.values()),
          changedTouches: [],
          gestureType: 'tap',
          gestureCenter: { x: this.activeTouches.values().next().value.x, y: this.activeTouches.values().next().value.y },
          timestamp: Date.now()
        });
        this.tapCount = 0;
      }
    }, this.config.doubleTapThreshold);
  }

  /**
   * On-screen keyboard integration
   */
  public showOnScreenKeyboard(): void {
    if (this.onScreenKeyboardVisible) return;

    this.keyboardElement = this.createOnScreenKeyboard();
    document.body.appendChild(this.keyboardElement);
    this.onScreenKeyboardVisible = true;

    // Adjust VNC viewer size to account for keyboard
    this.adjustVNCViewerForKeyboard(true);
  }

  public hideOnScreenKeyboard(): void {
    if (!this.onScreenKeyboardVisible || !this.keyboardElement) return;

    this.keyboardElement.remove();
    this.keyboardElement = null;
    this.onScreenKeyboardVisible = false;

    // Restore VNC viewer size
    this.adjustVNCViewerForKeyboard(false);
  }

  private createOnScreenKeyboard(): HTMLElement {
    const keyboard = document.createElement('div');
    keyboard.className = 'vnc-onscreen-keyboard';
    keyboard.style.cssText = `
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: #1f2937;
      border-top: 1px solid #374151;
      padding: 10px;
      z-index: 1001;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      justify-content: center;
    `;

    // Basic QWERTY layout
    const keys = [
      ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],
      ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
      ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"],
      ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/'],
      ['Shift', 'Space', 'Backspace', 'Enter']
    ];

    keys.forEach(row => {
      const rowElement = document.createElement('div');
      rowElement.style.display = 'flex';
      rowElement.style.gap = '5px';
      rowElement.style.marginBottom = '5px';

      row.forEach(key => {
        const keyElement = this.createKeyboardKey(key);
        rowElement.appendChild(keyElement);
      });

      keyboard.appendChild(rowElement);
    });

    // Add close button
    const closeButton = document.createElement('button');
    closeButton.textContent = '✕';
    closeButton.style.cssText = `
      position: absolute;
      top: 5px;
      right: 5px;
      background: #ef4444;
      color: white;
      border: none;
      border-radius: 50%;
      width: 24px;
      height: 24px;
      cursor: pointer;
    `;
    closeButton.onclick = () => this.hideOnScreenKeyboard();
    keyboard.appendChild(closeButton);

    return keyboard;
  }

  private createKeyboardKey(key: string): HTMLButtonElement {
    const button = document.createElement('button');
    button.textContent = key;
    button.style.cssText = `
      background: #374151;
      color: white;
      border: 1px solid #4b5563;
      border-radius: 4px;
      padding: 8px 12px;
      cursor: pointer;
      font-size: 14px;
      min-width: ${key.length === 1 ? '30px' : 'auto'};
    `;

    button.onclick = () => {
      const keyCode = this.getKeyCode(key);
      const modifiers = key === 'Shift' ? { shift: true } : {};

      this.emit('touchEvent', {
        type: 'gesture',
        touches: [],
        changedTouches: [],
        gestureType: 'keyinput',
        gestureValue: keyCode,
        gestureCenter: { x: 0, y: 0 },
        timestamp: Date.now()
      });
    };

    return button;
  }

  private getKeyCode(key: string): number {
    const keyMap: { [key: string]: number } = {
      'Shift': 16,
      'Space': 32,
      'Backspace': 8,
      'Enter': 13
    };

    return keyMap[key] || key.charCodeAt(0);
  }

  private adjustVNCViewerForKeyboard(visible: boolean): void {
    if (!this.element) return;

    const keyboardHeight = visible ? 200 : 0;
    this.element.style.height = `calc(100% - ${keyboardHeight}px)`;
  }

  /**
   * Touch device detection
   */
  public static isTouchDevice(): boolean {
    return (
      'ontouchstart' in window ||
      navigator.maxTouchPoints > 0 ||
      (navigator as any).msMaxTouchPoints > 0
    );
  }

  public static getTouchCapabilities(): {
    maxTouchPoints: number;
    supportsTouch: boolean;
    supportsPointer: boolean;
  } {
    return {
      maxTouchPoints: navigator.maxTouchPoints || 0,
      supportsTouch: 'ontouchstart' in window,
      supportsPointer: 'onpointerdown' in window
    };
  }

  /**
   * Get current touch state
   */
  public getCurrentState() {
    return {
      isAttached: this.isAttached,
      activeTouchCount: this.activeTouches.size,
      activeTouches: Array.from(this.activeTouches.values()),
      gestureState: { ...this.gestureState },
      onScreenKeyboardVisible: this.onScreenKeyboardVisible
    };
  }

  /**
   * Reset all touch state
   */
  private resetTouchState(): void {
    this.activeTouches.clear();
    this.resetGestureState();
    this.tapCount = 0;
    this.lastTouchTime = 0;
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.detach();
    this.hideOnScreenKeyboard();
    this.removeAllListeners();
  }
}

export default TouchHandler;