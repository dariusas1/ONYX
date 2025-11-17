'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { VNCWebSocketConnection, VNCEvent } from '../lib/vnc/VNCWebSocketConnection';
import { MouseInputHandler } from '../lib/vnc/MouseInputHandler';
import { KeyboardInputHandler } from '../lib/vnc/KeyboardInputHandler';
import { TouchInputHandler } from '../lib/vnc/TouchInputHandler';
import { InputLatencyOptimizer } from '../lib/vnc/InputLatencyOptimizer';
import { Monitor, Wifi, WifiOff, AlertTriangle } from 'lucide-react';

export interface VNCWorkspaceProps {
  vncUrl: string;
  password?: string;
  width?: number;
  height?: number;
  className?: string;
  onConnectionChange?: (connected: boolean) => void;
  onError?: (error: Error) => void;
}

export interface PerformanceMetrics {
  latency: number;
  frameRate: number;
  queueDepth: number;
  networkQuality: number;
}

export function VNCWorkspace({
  vncUrl,
  password,
  width = 1920,
  height = 1080,
  className = '',
  onConnectionChange,
  onError
}: VNCWorkspaceProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    latency: 0,
    frameRate: 0,
    queueDepth: 0,
    networkQuality: 1
  });
  const [showControls, setShowControls] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Refs for input handlers and connection
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const connectionRef = useRef<VNCWebSocketConnection | null>(null);
  const mouseHandlerRef = useRef<MouseInputHandler | null>(null);
  const keyboardHandlerRef = useRef<KeyboardInputHandler | null>(null);
  const touchHandlerRef = useRef<TouchInputHandler | null>(null);
  const latencyOptimizerRef = useRef<InputLatencyOptimizer | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Initialize VNC connection
  const initializeConnection = useCallback(async () => {
    setIsLoading(true);

    try {
      // Create WebSocket connection
      const connection = new VNCWebSocketConnection({
        url: vncUrl,
        password,
        retryAttempts: 3,
        retryDelay: 1000
      });

      // Set up event handlers
      connection.on('connected', () => {
        setIsConnected(true);
        onConnectionChange?.(true);
        setIsLoading(false);
      });

      connection.on('disconnected', () => {
        setIsConnected(false);
        onConnectionChange?.(false);
        setIsLoading(false);
      });

      connection.on('error', (error) => {
        console.error('VNC connection error:', error);
        onError?.(error as Error);
        setIsLoading(false);
      });

      connection.on('latency-update', (latencyMetrics) => {
        setMetrics(prev => ({
          ...prev,
          latency: latencyMetrics.roundTrip,
          queueDepth: latencyMetrics.queueSize
        }));
      });

      // Connect to VNC server
      await connection.connect();
      connectionRef.current = connection;

    } catch (error) {
      console.error('Failed to initialize VNC connection:', error);
      onError?.(error as Error);
      setIsLoading(false);
    }
  }, [vncUrl, password, onConnectionChange, onError]);

  // Initialize input handlers
  const initializeInputHandlers = useCallback(() => {
    if (!containerRef.current || !connectionRef.current) return;

    const container = containerRef.current;
    const connection = connectionRef.current;

    // Create latency optimizer
    const latencyOptimizer = new InputLatencyOptimizer(
      {
        maxLatency: 500,
        batchSize: 10,
        batchTimeout: 16,
        predictionEnabled: true,
        adaptiveQuality: true
      },
      (events) => {
        // Send optimized events to VNC server
        events.forEach(event => {
          connection.sendInputEvent(event);
        });
      }
    );

    // Create mouse input handler
    const mouseHandler = new MouseInputHandler(
      {
        enablePrediction: true,
        smoothingFactor: 0.3,
        maxPredictionDistance: 50,
        doubleClickThreshold: 300,
        movementThreshold: 1
      },
      (event) => {
        // Optimize and send mouse events
        latencyOptimizer.addEvent(event);
      }
    );

    // Create keyboard input handler
    const keyboardHandler = new KeyboardInputHandler(
      {
        enableAutoRepeat: true,
        repeatDelay: 500,
        repeatInterval: 50,
        enableComposition: true,
        internationalLayout: 'en-US'
      },
      (event) => {
        // Optimize and send keyboard events
        latencyOptimizer.addEvent(event);
      }
    );

    // Create touch input handler
    const touchHandler = new TouchInputHandler(
      {
        tapThreshold: 200,
        doubleTapThreshold: 300,
        longPressThreshold: 500,
        swipeThreshold: 30,
        pinchThreshold: 0.1,
        scrollThreshold: 10,
        touchSlop: 8,
        maxTouchPoints: 10
      },
      (event) => {
        // Optimize and send touch events
        latencyOptimizer.addEvent(event);
      }
    );

    // Add mouse event listeners
    container.addEventListener('mousemove', (e) => mouseHandler.handleMouseMove(e));
    container.addEventListener('mousedown', (e) => mouseHandler.handleMouseDown(e));
    container.addEventListener('mouseup', (e) => mouseHandler.handleMouseUp(e));
    container.addEventListener('wheel', (e) => mouseHandler.handleWheel(e), { passive: false });
    container.addEventListener('contextmenu', (e) => mouseHandler.handleContextMenu(e));

    // Add keyboard event listeners
    container.addEventListener('keydown', (e) => keyboardHandler.handleKeyDown(e));
    container.addEventListener('keyup', (e) => keyboardHandler.handleKeyUp(e));
    container.addEventListener('compositionstart', (e) => keyboardHandler.handleCompositionStart(e));
    container.addEventListener('compositionend', (e) => keyboardHandler.handleCompositionEnd(e));
    container.addEventListener('input', (e) => keyboardHandler.handleInput(e));

    // Add touch event listeners
    container.addEventListener('touchstart', (e) => touchHandler.handleTouchStart(e), { passive: false });
    container.addEventListener('touchmove', (e) => touchHandler.handleTouchMove(e), { passive: false });
    container.addEventListener('touchend', (e) => touchHandler.handleTouchEnd(e), { passive: false });
    container.addEventListener('touchcancel', (e) => touchHandler.handleTouchCancel(e), { passive: false });

    // Store references
    mouseHandlerRef.current = mouseHandler;
    keyboardHandlerRef.current = keyboardHandler;
    touchHandlerRef.current = touchHandler;
    latencyOptimizerRef.current = latencyOptimizer;

    // Set container focus for keyboard input
    container.focus();

  }, []);

  // Handle fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  // Handle reconnection
  const handleReconnect = useCallback(() => {
    if (connectionRef.current) {
      connectionRef.current.disconnect();
    }
    initializeConnection();
  }, [initializeConnection]);

  // Update metrics periodically
  const updateMetrics = useCallback(() => {
    if (latencyOptimizerRef.current) {
      const optimizerMetrics = latencyOptimizerRef.current.getMetrics();
      const networkQuality = latencyOptimizerRef.current.getNetworkQuality();

      setMetrics(prev => ({
        ...prev,
        latency: optimizerMetrics.roundTripTime,
        queueDepth: optimizerMetrics.queueDepth,
        networkQuality: networkQuality.quality,
        frameRate: prev.frameRate // Would be calculated from canvas updates
      }));
    }

    animationFrameRef.current = requestAnimationFrame(updateMetrics);
  }, []);

  // Initialize component
  useEffect(() => {
    initializeConnection();

    return () => {
      // Cleanup
      if (connectionRef.current) {
        connectionRef.current.disconnect();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [initializeConnection]);

  // Initialize input handlers when connected
  useEffect(() => {
    if (isConnected) {
      initializeInputHandlers();
      updateMetrics();
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isConnected, initializeInputHandlers, updateMetrics]);

  // Calculate connection status color
  const getStatusColor = () => {
    if (!isConnected) return 'text-red-500';
    if (metrics.latency > 500) return 'text-yellow-500';
    if (metrics.networkQuality < 0.5) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getStatusIcon = () => {
    if (!isConnected) return <WifiOff className="w-4 h-4" />;
    if (metrics.latency > 500 || metrics.networkQuality < 0.5) return <AlertTriangle className="w-4 h-4" />;
    return <Wifi className="w-4 h-4" />;
  };

  return (
    <div className={`relative bg-black ${className}`}>
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900 z-50">
          <div className="text-white text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
            <p>Connecting to remote workspace...</p>
          </div>
        </div>
      )}

      {/* VNC Container */}
      <div
        ref={containerRef}
        className="relative w-full h-full overflow-hidden cursor-crosshair"
        style={{ width, height }}
        tabIndex={0}
        onMouseEnter={() => setShowControls(true)}
        onMouseLeave={() => setShowControls(false)}
        onFocus={() => console.log('VNC workspace focused')}
        onBlur={() => console.log('VNC workspace blurred')}
      >
        {/* noVNC Canvas */}
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="absolute inset-0 w-full h-full"
          style={{ imageRendering: 'pixelated' }}
        />

        {/* Control overlay */}
        <div className={`absolute top-4 right-4 flex items-center gap-2 bg-gray-900/80 backdrop-blur-sm rounded-lg px-3 py-2 transition-opacity duration-300 ${
          showControls ? 'opacity-100' : 'opacity-0'
        }`}>
          {/* Connection status */}
          <div className={`flex items-center gap-2 ${getStatusColor()}`}>
            {getStatusIcon()}
            <span className="text-sm font-medium">
              {metrics.latency > 0 ? `${Math.round(metrics.latency)}ms` : 'Connected'}
            </span>
          </div>

          {/* Network quality indicator */}
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-gray-600"></div>
            <div className={`w-2 h-2 rounded-full ${
              metrics.networkQuality > 0.7 ? 'bg-green-500' :
              metrics.networkQuality > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
            }`}></div>
            <div className="w-2 h-2 rounded-full bg-gray-600"></div>
          </div>

          {/* Fullscreen toggle */}
          <button
            onClick={toggleFullscreen}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            <Monitor className="w-4 h-4 text-gray-300" />
          </button>

          {/* Reconnect button */}
          {!isConnected && (
            <button
              onClick={handleReconnect}
              className="p-1 hover:bg-gray-700 rounded transition-colors"
              title="Reconnect"
            >
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
            </button>
          )}
        </div>

        {/* Performance metrics overlay (debug) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="absolute bottom-4 left-4 bg-gray-900/80 backdrop-blur-sm rounded-lg px-3 py-2 text-xs text-gray-300">
            <div>Queue: {metrics.queueDepth}</div>
            <div>FPS: {metrics.frameRate}</div>
            <div>Quality: {Math.round(metrics.networkQuality * 100)}%</div>
            <div>Mode: {latencyOptimizerRef.current?.getOptimizationMode()}</div>
          </div>
        )}
      </div>

      {/* Mobile touch indicator */}
      <div className="md:hidden absolute bottom-4 right-4 bg-gray-900/80 backdrop-blur-sm rounded-lg px-3 py-2 text-xs text-gray-300">
        Touch input enabled
      </div>
    </div>
  );
}