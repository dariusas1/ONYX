/**
 * FocusManager - Input focus control and management for VNC workspace
 *
 * Handles:
 * - Input focus boundaries and detection
 * - Focus switching between VNC and other UI components
 * - Keyboard shortcut conflict resolution
 * - Visual focus indicators
 * - Tab navigation and accessibility
 * - Focus state persistence
 */

import { EventEmitter } from 'events';

export interface FocusEvent {
  type: 'focus' | 'blur' | 'enter' | 'leave';
  element?: HTMLElement;
  timestamp: number;
  reason: 'user' | 'system' | 'boundary' | 'shortcut';
}

export interface FocusBoundary {
  element: HTMLElement;
  rect: DOMRect;
  active: boolean;
}

export interface KeyboardShortcut {
  key: string;
  modifiers: {
    ctrl?: boolean;
    alt?: boolean;
    shift?: boolean;
    meta?: boolean;
  };
  action: string;
  preventDefault?: boolean;
}

export interface FocusManagerConfig {
  enableVisualIndicators: boolean;
  enableTabNavigation: boolean;
  enableShortcutResolution: boolean;
  focusIndicationClass: string;
  shortcuts: KeyboardShortcut[];
}

export class FocusManager extends EventEmitter {
  private config: FocusManagerConfig;
  private currentElement: HTMLElement | null = null;
  private focusBoundary: FocusBoundary | null = null;
  private isWithinBoundary = false;
  private hasFocus = false;

  // Visual focus indicators
  private focusIndicator: HTMLElement | null = null;

  // Default shortcuts that should be handled by focus manager
  private defaultShortcuts: KeyboardShortcut[] = [
    { key: 'Tab', modifiers: {}, action: 'navigate', preventDefault: true },
    { key: 'Enter', modifiers: {}, action: 'activate', preventDefault: false },
    { key: 'Escape', modifiers: {}, action: 'exit', preventDefault: true },
    { key: 'F5', modifiers: {}, action: 'refresh', preventDefault: true },
    { key: 'F11', modifiers: {}, action: 'fullscreen', preventDefault: true }
  ];

  constructor(config: Partial<FocusManagerConfig> = {}) {
    super();

    this.config = {
      enableVisualIndicators: true,
      enableTabNavigation: true,
      enableShortcutResolution: true,
      focusIndicationClass: 'vnc-focus-indicator',
      shortcuts: [...(config.shortcuts || []), ...this.defaultShortcuts],
      ...config
    };
  }

  /**
   * Request focus for the VNC viewer
   */
  public requestFocus(element: HTMLElement): void {
    if (this.currentElement === element) return;

    const previousElement = this.currentElement;
    this.currentElement = element;
    this.hasFocus = true;

    // Create visual focus indicator if enabled
    if (this.config.enableVisualIndicators) {
      this.createFocusIndicator(element);
    }

    // Update boundary
    this.updateBoundary(element);

    // Emit focus event
    this.emit('focusEvent', {
      type: 'focus',
      element,
      timestamp: Date.now(),
      reason: 'user'
    });

    // Setup global event listeners
    this.setupGlobalListeners();

    if (this.config.enableTabNavigation) {
      element.tabIndex = 0;
      element.focus();
    }
  }

  /**
   * Release focus from the VNC viewer
   */
  public releaseFocus(): void {
    if (!this.currentElement) return;

    const element = this.currentElement;
    this.currentElement = null;
    this.hasFocus = false;
    this.isWithinBoundary = false;

    // Remove visual indicator
    this.removeFocusIndicator();

    // Remove global event listeners
    this.removeGlobalListeners();

    // Emit blur event
    this.emit('focusEvent', {
      type: 'blur',
      element,
      timestamp: Date.now(),
      reason: 'user'
    });
  }

  /**
   * Set boundary for focus detection
   */
  public setBoundary(boundary: DOMRect): void {
    if (this.focusBoundary) {
      this.focusBoundary.rect = boundary;
    } else {
      this.focusBoundary = {
        element: this.currentElement || document.body,
        rect: boundary,
        active: true
      };
    }
  }

  /**
   * Update boundary when element changes size or position
   */
  private updateBoundary(element: HTMLElement): void {
    const rect = element.getBoundingClientRect();
    this.setBoundary(rect);
  }

  /**
   * Check if a point is within the focus boundary
   */
  private isWithinBounds(x: number, y: number): boolean {
    if (!this.focusBoundary) return false;

    const { rect } = this.focusBoundary;
    return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
  }

  /**
   * Handle global mouse events for boundary detection
   */
  private setupGlobalListeners(): void {
    document.addEventListener('mousedown', this.handleGlobalMouseDown);
    document.addEventListener('click', this.handleGlobalClick);
    document.addEventListener('keydown', this.handleGlobalKeyDown);
  }

  private removeGlobalListeners(): void {
    document.removeEventListener('mousedown', this.handleGlobalMouseDown);
    document.removeEventListener('click', this.handleGlobalClick);
    document.removeEventListener('keydown', this.handleGlobalKeyDown);
  }

  private handleGlobalMouseDown = (e: MouseEvent): void => {
    const target = e.target as HTMLElement;
    const x = e.clientX;
    const y = e.clientY;

    const wasWithinBoundary = this.isWithinBoundary;
    this.isWithinBoundary = this.isWithinBounds(x, y);

    // Check if clicking outside boundary but have focus
    if (this.hasFocus && !this.isWithinBoundary && wasWithinBoundary) {
      this.emit('focusEvent', {
        type: 'leave',
        timestamp: Date.now(),
        reason: 'boundary'
      });
    }

    // Check if clicking inside boundary but don't have focus
    if (!this.hasFocus && this.isWithinBoundary && this.currentElement?.contains(target)) {
      this.requestFocus(this.currentElement);
    }
  };

  private handleGlobalClick = (e: MouseEvent): void => {
    // Handle click events that might not trigger mousedown (e.g., some mobile scenarios)
    const x = e.clientX;
    const y = e.clientY;

    if (!this.isWithinBounds(x, y) && this.hasFocus) {
      this.releaseFocus();
    }
  };

  private handleGlobalKeyDown = (e: KeyboardEvent): void => {
    if (!this.config.enableShortcutResolution || !this.hasFocus) return;

    const shortcut = this.detectShortcut(e);
    if (shortcut) {
      if (shortcut.preventDefault) {
        e.preventDefault();
        e.stopPropagation();
      }

      this.emit('shortcut', {
        ...shortcut,
        originalEvent: e,
        timestamp: Date.now()
      });
    }
  };

  private detectShortcut(event: KeyboardEvent): KeyboardShortcut | null {
    return this.config.shortcuts.find(shortcut => {
      return shortcut.key.toLowerCase() === event.key.toLowerCase() &&
        (!shortcut.modifiers.ctrl || event.ctrlKey) &&
        (!shortcut.modifiers.alt || event.altKey) &&
        (!shortcut.modifiers.shift || event.shiftKey) &&
        (!shortcut.modifiers.meta || event.metaKey);
    }) || null;
  }

  /**
   * Visual focus indicator management
   */
  private createFocusIndicator(element: HTMLElement): void {
    this.removeFocusIndicator();

    this.focusIndicator = document.createElement('div');
    this.focusIndicator.className = this.config.focusIndicationClass;
    this.focusIndicator.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      pointer-events: none;
      border: 2px solid #3b82f6;
      border-radius: 4px;
      box-shadow: 0 0 0 1px #1e40af, 0 0 8px rgba(59, 130, 246, 0.3);
      z-index: 1000;
      animation: vnc-focus-pulse 2s ease-in-out infinite;
    `;

    // Add pulse animation if not already in styles
    if (!document.querySelector('#vnc-focus-styles')) {
      const style = document.createElement('style');
      style.id = 'vnc-focus-styles';
      style.textContent = `
        @keyframes vnc-focus-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
        .${this.config.focusIndicationClass} {
          transition: all 0.2s ease-in-out;
        }
      `;
      document.head.appendChild(style);
    }

    // Position the indicator
    const rect = element.getBoundingClientRect();
    this.focusIndicator.style.top = `${rect.top}px`;
    this.focusIndicator.style.left = `${rect.left}px`;
    this.focusIndicator.style.width = `${rect.width}px`;
    this.focusIndicator.style.height = `${rect.height}px`;

    document.body.appendChild(this.focusIndicator);
  }

  private removeFocusIndicator(): void {
    if (this.focusIndicator) {
      this.focusIndicator.remove();
      this.focusIndicator = null;
    }
  }

  /**
   * Handle keyboard navigation within focus boundary
   */
  public handleTabNavigation(forward: boolean = true): boolean {
    if (!this.config.enableTabNavigation || !this.hasFocus) return false;

    // Get all focusable elements within the boundary
    const focusableElements = this.getFocusableElements();
    const currentIndex = focusableElements.indexOf(this.currentElement!);

    if (focusableElements.length > 1) {
      let nextIndex = forward ? currentIndex + 1 : currentIndex - 1;

      // Wrap around
      if (nextIndex >= focusableElements.length) nextIndex = 0;
      if (nextIndex < 0) nextIndex = focusableElements.length - 1;

      const nextElement = focusableElements[nextIndex];
      nextElement.focus();

      this.emit('focusEvent', {
        type: 'focus',
        element: nextElement,
        timestamp: Date.now(),
        reason: 'system'
      });

      return true;
    }

    return false;
  }

  private getFocusableElements(): HTMLElement[] {
    if (!this.focusBoundary) return [];

    const focusableSelectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      '[tabindex]:not([tabindex="-1"])',
      'div[contenteditable="true"]'
    ];

    const selector = focusableSelectors.join(', ');
    const elements = Array.from(this.focusBoundary.element.querySelectorAll(selector));

    return elements.filter(el => {
      const rect = (el as HTMLElement).getBoundingClientRect();
      return this.isWithinBounds(rect.left + rect.width / 2, rect.top + rect.height / 2);
    }) as HTMLElement[];
  }

  /**
   * Get current focus state
   */
  public getCurrentState() {
    return {
      hasFocus: this.hasFocus,
      currentElement: this.currentElement,
      isWithinBoundary: this.isWithinBoundary,
      focusBoundary: this.focusBoundary
    };
  }

  /**
   * Check if VNC viewer currently has focus
   */
  public hasFocusState(): boolean {
    return this.hasFocus;
  }

  /**
   * Check if mouse is within focus boundary
   */
  public isMouseWithinBoundary(): boolean {
    return this.isWithinBoundary;
  }

  /**
   * Update configuration
   */
  public updateConfig(newConfig: Partial<FocusManagerConfig>): void {
    this.config = { ...this.config, ...newConfig };

    // Recreate indicator if visual setting changed
    if (newConfig.enableVisualIndicators !== undefined) {
      if (this.hasFocus && this.currentElement) {
        if (newConfig.enableVisualIndicators) {
          this.createFocusIndicator(this.currentElement);
        } else {
          this.removeFocusIndicator();
        }
      }
    }
  }

  /**
   * Update focus indicator position (call when element moves or resizes)
   */
  public updateIndicatorPosition(): void {
    if (this.focusIndicator && this.currentElement) {
      const rect = this.currentElement.getBoundingClientRect();
      this.focusIndicator.style.top = `${rect.top}px`;
      this.focusIndicator.style.left = `${rect.left}px`;
      this.focusIndicator.style.width = `${rect.width}px`;
      this.focusIndicator.style.height = `${rect.height}px`;

      // Update boundary
      this.updateBoundary(this.currentElement);
    }
  }

  /**
   * Cleanup resources
   */
  public destroy(): void {
    this.releaseFocus();
    this.removeAllListeners();
    this.removeFocusIndicator();

    // Remove styles
    const styles = document.querySelector('#vnc-focus-styles');
    if (styles) {
      styles.remove();
    }
  }
}

export default FocusManager;