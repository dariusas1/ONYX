/**
 * MouseHandler - Comprehensive mouse input processing for VNC workspace
 *
 * Handles:
 * - Mouse movement with smooth tracking
 * - Click, double-click, and drag operations
 * - Scroll wheel events
 * - Multi-button support (left, right, middle)
 * - Boundary detection and restriction
 * - Performance optimization with event throttling
 */

import { EventEmitter } from 'events';

export interface MouseEvent {
  type: 'move' | 'down' | 'up' | 'click' | 'dblclick' | 'drag' | 'scroll';
  x: number;
  y: number;
  button: number; // 0=left, 1=middle, 2=right
  buttons: number; // Bitmask of pressed buttons
  deltaX?: number; // For scroll events
  deltaY?: number; // For scroll events
  dragStartX?: number; // For drag events
  dragStartY?: number; // For drag events
  timestamp: number;
}

export interface MouseHandlerConfig {
  sensitivity: number;
  clickThreshold: number; // ms for double-click detection
  dragThreshold: number; // pixels for drag detection
  throttleMs: number; // Event throttling
  enableLogging: boolean;
}

export class MouseHandler extends EventEmitter {
  private config: MouseHandlerConfig;
  private element: HTMLElement | null = null;
  private boundaries: DOMRect | null = null;

  // State tracking
  private isAttached = false;
  private isDragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private lastClickTime = 0;
  private lastClickButton = -1;
  private currentButtons = 0;

  // Performance optimization
  private lastMoveTime = 0;
  private moveThrottleTimer: number | null = null;
  private moveEventQueue: MouseEvent[] = [];

  // Position tracking
  private currentPosition = { x: 0, y: 0 };
  private lastPosition = { x: 0, y: 0 };

  constructor(config: Partial<MouseHandlerConfig> = {}) {
    super();

    this.config = {
      sensitivity: 1.0,
      clickThreshold: 300, // 300ms for double-click
      dragThreshold: 3, // 3 pixels for drag detection
      throttleMs: 8, // ~120fps for mouse movement
      enableLogging: true,
      ...config
    };
  }

  /**
   * Attach mouse event handlers to an element
   */
  public attachToElement(element: HTMLElement): void {
    if (this.isAttached) {
      this.detach();
    }

    this.element = element;
    this.setupEventListeners();
    this.isAttached = true;

    if (this.config.enableLogging) {
      console.log('MouseHandler attached to element:', element);
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
    this.clearThrottleTimer();

    if (this.config.enableLogging) {
      console.log('MouseHandler detached');
    }
  }

  /**
   * Set boundary detection rectangle
   */
  public setBoundaries(boundaries: DOMRect): void {
    this.boundaries = boundaries;

    if (this.config.enableLogging) {
      console.log('MouseHandler boundaries set:', boundaries);
    }
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<MouseHandlerConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  private setupEventListeners(): void {
    if (!this.element) return;

    // Mouse movement events
    this.element.addEventListener('mousemove', this.handleMouseMove);
    this.element.addEventListener('mouseenter', this.handleMouseEnter);
    this.element.addEventListener('mouseleave', this.handleMouseLeave);

    // Mouse button events
    this.element.addEventListener('mousedown', this.handleMouseDown);
    this.element.addEventListener('mouseup', this.handleMouseUp);
    this.element.addEventListener('click', this.handleClick);
    this.element.addEventListener('dblclick', this.handleDoubleClick);

    // Context menu (right-click)
    this.element.addEventListener('contextmenu', this.handleContextMenu);

    // Scroll events
    this.element.addEventListener('wheel', this.handleWheel, { passive: false });

    // Prevent default browser behavior for certain events
    this.element.addEventListener('dragstart', this.preventDragStart);
    this.element.addEventListener('selectstart', this.preventSelectStart);
  }

  private removeEventListeners(): void {
    if (!this.element) return;

    this.element.removeEventListener('mousemove', this.handleMouseMove);
    this.element.removeEventListener('mouseenter', this.handleMouseEnter);
    this.element.removeEventListener('mouseleave', this.handleMouseLeave);
    this.element.removeEventListener('mousedown', this.handleMouseDown);
    this.element.removeEventListener('mouseup', this.handleMouseUp);
    this.element.removeEventListener('click', this.handleClick);
    this.element.removeEventListener('dblclick', this.handleDoubleClick);
    this.element.removeEventListener('contextmenu', this.handleContextMenu);
    this.element.removeEventListener('wheel', this.handleWheel);
    this.element.removeEventListener('dragstart', this.preventDragStart);
    this.element.removeEventListener('selectstart', this.preventSelectStart);
  }

  private preventDragStart = (e: DragEvent): void => {
    e.preventDefault();
  };

  private preventSelectStart = (e: Event): void => {
    e.preventDefault();
  };

  /**
   * Get mouse position relative to element with boundary checking
   */
  private getRelativePosition(clientX: number, clientY: number): { x: number; y: number } {
    if (!this.element) return { x: 0, y: 0 };

    const rect = this.element.getBoundingClientRect();
    let x = (clientX - rect.left) * this.config.sensitivity;
    let y = (clientY - rect.top) * this.config.sensitivity;

    // Apply boundary constraints
    if (this.boundaries) {
      x = Math.max(0, Math.min(x, this.boundaries.width));
      y = Math.max(0, Math.min(y, this.boundaries.height));
    }

    return { x, y };
  }

  private handleMouseMove = (e: MouseEvent): void => {
    if (!this.isAttached) return;

    const position = this.getRelativePosition(e.clientX, e.clientY);
    this.currentPosition = position;

    // Check if this is a drag operation
    if (this.isDragging) {
      this.emitDragEvent(position);
    } else {
      // Throttle move events for performance
      this.throttleMouseMove(position);
    }
  };

  private throttleMouseMove(position: { x: number; y: number }): void {
    // Add to queue
    this.moveEventQueue.push({
      type: 'move',
      x: position.x,
      y: position.y,
      button: -1,
      buttons: this.currentButtons,
      timestamp: Date.now()
    });

    // Clear existing timer
    if (this.moveThrottleTimer) {
      clearTimeout(this.moveThrottleTimer);
    }

    // Set new timer
    this.moveThrottleTimer = window.setTimeout(() => {
      this.processMoveQueue();
    }, this.config.throttleMs);
  }

  private processMoveQueue(): void {
    if (this.moveEventQueue.length === 0) return;

    // Send the latest position (discard intermediate positions for performance)
    const latestEvent = this.moveEventQueue[this.moveEventQueue.length - 1];

    // Only emit if position changed significantly
    const deltaX = Math.abs(latestEvent.x - this.lastPosition.x);
    const deltaY = Math.abs(latestEvent.y - this.lastPosition.y);

    if (deltaX > 0.1 || deltaY > 0.1) {
      this.emit('mouseEvent', latestEvent);
      this.lastPosition = { x: latestEvent.x, y: latestEvent.y };
    }

    this.moveEventQueue = [];
    this.moveThrottleTimer = null;
  }

  private clearThrottleTimer(): void {
    if (this.moveThrottleTimer) {
      clearTimeout(this.moveThrottleTimer);
      this.moveThrottleTimer = null;
    }
    this.moveEventQueue = [];
  }

  private handleMouseEnter = (e: MouseEvent): void => {
    // Could be used for hover effects or focus management
    if (this.config.enableLogging) {
      console.log('Mouse entered VNC area');
    }
  };

  private handleMouseLeave = (e: MouseEvent): void => {
    // Clear drag state when mouse leaves
    if (this.isDragging) {
      this.isDragging = false;
      this.currentButtons = 0;
    }

    // Clear any pending move events
    this.clearThrottleTimer();

    if (this.config.enableLogging) {
      console.log('Mouse left VNC area');
    }
  };

  private handleMouseDown = (e: MouseEvent): void => {
    e.preventDefault();

    const position = this.getRelativePosition(e.clientX, e.clientY);
    const button = e.button;

    // Update button state
    this.currentButtons |= (1 << button);

    // Check for drag start
    if (button === 0) { // Left button
      this.isDragging = true;
      this.dragStartX = position.x;
      this.dragStartY = position.y;
    }

    const mouseEvent: MouseEvent = {
      type: 'down',
      x: position.x,
      y: position.y,
      button,
      buttons: this.currentButtons,
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);

    if (this.config.enableLogging) {
      console.log('Mouse down:', mouseEvent);
    }
  };

  private handleMouseUp = (e: MouseEvent): void => {
    e.preventDefault();

    const position = this.getRelativePosition(e.clientX, e.clientY);
    const button = e.button;

    // Update button state
    this.currentButtons &= ~(1 << button);

    const mouseEvent: MouseEvent = {
      type: 'up',
      x: position.x,
      y: position.y,
      button,
      buttons: this.currentButtons,
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);

    // Handle drag end
    if (this.isDragging && button === 0) {
      this.isDragging = false;

      const dragEvent: MouseEvent = {
        type: 'drag',
        x: position.x,
        y: position.y,
        button,
        buttons: this.currentButtons,
        dragStartX: this.dragStartX,
        dragStartY: this.dragStartY,
        timestamp: Date.now()
      };

      this.emit('mouseEvent', dragEvent);
    }

    if (this.config.enableLogging) {
      console.log('Mouse up:', mouseEvent);
    }
  };

  private handleClick = (e: MouseEvent): void => {
    e.preventDefault();

    const position = this.getRelativePosition(e.clientX, e.clientY);
    const button = e.button;

    const mouseEvent: MouseEvent = {
      type: 'click',
      x: position.x,
      y: position.y,
      button,
      buttons: this.currentButtons,
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);

    // Update double-click tracking
    this.lastClickTime = Date.now();
    this.lastClickButton = button;

    if (this.config.enableLogging) {
      console.log('Mouse click:', mouseEvent);
    }
  };

  private handleDoubleClick = (e: MouseEvent): void => {
    e.preventDefault();

    const position = this.getRelativePosition(e.clientX, e.clientY);
    const button = e.button;

    const mouseEvent: MouseEvent = {
      type: 'dblclick',
      x: position.x,
      y: position.y,
      button,
      buttons: this.currentButtons,
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);

    if (this.config.enableLogging) {
      console.log('Mouse double-click:', mouseEvent);
    }
  };

  private handleContextMenu = (e: MouseEvent): void => {
    e.preventDefault();

    const position = this.getRelativePosition(e.clientX, e.clientY);

    const mouseEvent: MouseEvent = {
      type: 'click', // Right-click is treated as click
      x: position.x,
      y: position.y,
      button: 2, // Right button
      buttons: this.currentButtons,
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);

    if (this.config.enableLogging) {
      console.log('Mouse right-click:', mouseEvent);
    }
  };

  private handleWheel = (e: WheelEvent): void => {
    e.preventDefault();

    const position = this.getRelativePosition(e.clientX, e.clientY);

    // Normalize scroll delta (different browsers have different values)
    const deltaX = e.deltaX || -e.deltaY || 0;
    const deltaY = e.deltaY || e.deltaX || 0;

    const mouseEvent: MouseEvent = {
      type: 'scroll',
      x: position.x,
      y: position.y,
      button: -1,
      buttons: this.currentButtons,
      deltaX: Math.sign(deltaX) * Math.min(Math.abs(deltaX), 100),
      deltaY: Math.sign(deltaY) * Math.min(Math.abs(deltaY), 100),
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);

    if (this.config.enableLogging) {
      console.log('Mouse wheel:', mouseEvent);
    }
  };

  private emitDragEvent(position: { x: number; y: number }): void {
    const mouseEvent: MouseEvent = {
      type: 'drag',
      x: position.x,
      y: position.y,
      button: 0, // Assume left button drag
      buttons: this.currentButtons,
      dragStartX: this.dragStartX,
      dragStartY: this.dragStartY,
      timestamp: Date.now()
    };

    this.emit('mouseEvent', mouseEvent);
  }

  /**
   * Get current mouse state
   */
  public getCurrentState() {
    return {
      position: this.currentPosition,
      buttons: this.currentButtons,
      isDragging: this.isDragging,
      dragStart: this.isDragging ? { x: this.dragStartX, y: this.dragStartY } : null,
      isAttached: this.isAttached
    };
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.detach();
    this.removeAllListeners();
  }
}

export default MouseHandler;