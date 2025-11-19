import React, { useRef, useEffect, useCallback } from 'react';

export const TouchInputHandler = ({ onTouchInput, children }) => {
  const touchStateRef = useRef({
    activeTouches: new Map(),
    lastGestureTime: 0,
    gestureThreshold: 50,
    pinchDistance: 0
  });

  // Convert touch coordinates to VNC coordinates
  const getVNCCoordinates = useCallback((touch, canvas) => {
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (touch.clientX - rect.left) * scaleX,
      y: (touch.clientY - rect.top) * scaleY
    };
  }, []);

  // Handle single touch (mouse events)
  const handleTouchStart = useCallback((e) => {
    e.preventDefault();
    const canvas = e.currentTarget;
    const touches = e.touches;

    if (touches.length === 1) {
      // Single touch - treat as mouse down
      const touch = touches[0];
      const coords = getVNCCoordinates(touch, canvas);

      touchStateRef.current.activeTouches.set(touch.identifier, {
        startX: coords.x,
        startY: coords.y,
        lastX: coords.x,
        lastY: coords.y,
        startTime: Date.now()
      });

      onTouchInput?.({
        type: 'mousedown',
        x: coords.x,
        y: coords.y,
        button: 0 // Left click
      });
    } else if (touches.length === 2) {
      // Two touches - pinch zoom gesture
      const touch1 = touches[0];
      const touch2 = touches[1];

      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );

      touchStateRef.current.pinchDistance = distance;
      touchStateRef.current.lastGestureTime = Date.now();
    }
  }, [getVNCCoordinates, onTouchInput]);

  const handleTouchMove = useCallback((e) => {
    e.preventDefault();
    const canvas = e.currentTarget;
    const touches = e.touches;

    if (touches.length === 1) {
      // Single touch move - treat as mouse move
      const touch = touches[0];
      const coords = getVNCCoordinates(touch, canvas);
      const touchState = touchStateRef.current.activeTouches.get(touch.identifier);

      if (touchState) {
        onTouchInput?.({
          type: 'mousemove',
          x: coords.x,
          y: coords.y,
          button: 0
        });

        touchState.lastX = coords.x;
        touchState.lastY = coords.y;
      }
    } else if (touches.length === 2) {
      // Two touches - pinch zoom
      const touch1 = touches[0];
      const touch2 = touches[1];

      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );

      const scaleDelta = distance / touchStateRef.current.pinchDistance;

      if (Math.abs(scaleDelta - 1) > 0.1) {
        // Significant zoom change
        onTouchInput?.({
          type: 'pinchzoom',
          scale: scaleDelta,
          centerX: (touch1.clientX + touch2.clientX) / 2,
          centerY: (touch1.clientY + touch2.clientY) / 2
        });

        touchStateRef.current.pinchDistance = distance;
        touchStateRef.current.lastGestureTime = Date.now();
      }
    }
  }, [getVNCCoordinates, onTouchInput]);

  const handleTouchEnd = useCallback((e) => {
    e.preventDefault();
    const canvas = e.currentTarget;
    const touches = e.changedTouches;

    if (touches.length === 1 && touchStateRef.current.activeTouches.size === 1) {
      // Single touch end - treat as mouse up
      const touch = touches[0];
      const coords = getVNCCoordinates(touch, canvas);
      const touchState = touchStateRef.current.activeTouches.get(touch.identifier);

      if (touchState) {
        const duration = Date.now() - touchState.startTime;
        const distance = Math.hypot(
          coords.x - touchState.startX,
          coords.y - touchState.startY
        );

        // Check for tap (short duration, small distance)
        if (duration < 200 && distance < 10) {
          // Tap gesture
          onTouchInput?.({
            type: 'click',
            x: coords.x,
            y: coords.y
          });
        }

        // Always send mouse up
        onTouchInput?.({
          type: 'mouseup',
          x: coords.x,
          y: coords.y,
          button: 0
        });

        touchStateRef.current.activeTouches.delete(touch.identifier);
      }
    } else {
      // Clear all touches
      for (const touch of touches) {
        touchStateRef.current.activeTouches.delete(touch.identifier);
      }
    }

    // Reset pinch state
    if (touchStateRef.current.activeTouches.size === 0) {
      touchStateRef.current.pinchDistance = 0;
    }
  }, [getVNCCoordinates, onTouchInput]);

  // Handle touch cancel
  const handleTouchCancel = useCallback((e) => {
    e.preventDefault();

    // Clear all active touches
    touchStateRef.current.activeTouches.clear();
    touchStateRef.current.pinchDistance = 0;
  }, []);

  // Prevent default touch behaviors on the element
  useEffect(() => {
    const element = touchStateRef.current.element;
    if (element) {
      element.style.touchAction = 'none';
    }
  }, []);

  // Add gesture detection for double-tap, long-press, etc.
  const handleDoubleTap = useCallback((e) => {
    const touch = e.touches[0];
    const coords = getVNCCoordinates(touch, e.currentTarget);

    // Double-tap - right click equivalent
    onTouchInput?.({
      type: 'mousedown',
      x: coords.x,
      y: coords.y,
      button: 2 // Right click
    });

    onTouchInput?.({
      type: 'mouseup',
      x: coords.x,
      y: coords.y,
      button: 2
    });
  }, [getVNCCoordinates, onTouchInput]);

  // Create a wrapper component that adds touch event handlers
  const TouchWrapper = useCallback(({ children }) => {
    if (typeof children === 'string' || typeof children === 'number') {
      return children;
    }

    if (React.isValidElement(children)) {
      return React.cloneElement(children, {
        ref: (el) => {
          touchStateRef.current.element = el;
          // Forward ref to original ref if exists
          if (children.ref) {
            if (typeof children.ref === 'function') {
              children.ref(el);
            } else if (children.ref.current !== undefined) {
              children.ref.current = el;
            }
          }
        },
        onTouchStart: handleTouchStart,
        onTouchMove: handleTouchMove,
        onTouchEnd: handleTouchEnd,
        onTouchCancel: handleTouchCancel,
        onDoubleClick: handleDoubleTap,
        style: {
          ...children.props.style,
          touchAction: 'none'
        }
      });
    }

    return children;
  }, [handleTouchStart, handleTouchMove, handleTouchEnd, handleTouchCancel, handleDoubleTap]);

  return <TouchWrapper>{children}</TouchWrapper>;
};

export default TouchInputHandler;