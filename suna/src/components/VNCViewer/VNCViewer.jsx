import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Monitor, Wifi, WifiOff, Loader2, Maximize2, Minimize2, Settings } from 'lucide-react';
import { InputManager } from '../../services/input/InputManager';
import RFB from '@novnc/novnc/lib/rfb.js';

export const VNCViewer = ({
  url = process.env.NEXT_PUBLIC_VNC_URL || 'ws://localhost:6080',
  onConnect,
  onDisconnect,
  onError,
  className = '',
  scale = true,
  quality = parseInt(process.env.NEXT_PUBLIC_VNC_QUALITY) || 6,
  compression = parseInt(process.env.NEXT_PUBLIC_VNC_COMPRESSION) || 1,
  shared = true,
  localCursor = true,
  viewOnly = false
}) => {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const rfbRef = useRef(null);
  const inputManagerRef = useRef<InputManager | null>(null);

  const [connectionState, setConnectionState] = useState('disconnected'); // disconnected, connecting, connected, error
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [inputMetrics, setInputMetrics] = useState(null);
  const [rfbState, setRfbState] = useState('disconnected');
  const [showSettings, setShowSettings] = useState(false);

  // Initialize Input Manager
  const initializeInputManager = useCallback(() => {
    if (!containerRef.current) return;

    const inputManager = new InputManager({
      enableMouse: true,
      enableKeyboard: true,
      enableTouch: true,
      rateLimitMs: 16,
      maxQueueSize: 1000,
      latencyThreshold: 500,
      enableLogging: process.env.NODE_ENV === 'development'
    });

    // Set up input manager event handlers
    inputManager.on('connected', () => {
      console.log('Input manager connected');
    });

    inputManager.on('disconnected', () => {
      console.log('Input manager disconnected');
    });

    inputManager.on('error', (error) => {
      console.error('Input manager error:', error);
      setError('Input connection error');
    });

    inputManager.on('highLatency', (data) => {
      console.warn('High input latency detected:', data.latency);
    });

    inputManager.on('processingError', (error) => {
      console.error('Input processing error:', error);
    });

    // Store reference
    inputManagerRef.current = inputManager;

    // Start metrics collection
    const metricsInterval = setInterval(() => {
      if (inputManagerRef.current) {
        setInputMetrics(inputManagerRef.current.getMetrics());
      }
    }, 1000);

    // Cleanup function
    return () => {
      clearInterval(metricsInterval);
      if (inputManagerRef.current) {
        inputManagerRef.current.destroy();
        inputManagerRef.current = null;
      }
    };

  }, []);

  // Initialize VNC connection with real noVNC client
  const connectVNC = useCallback(async () => {
    if (!canvasRef.current) return;

    try {
      setConnectionState('connecting');
      setError(null);

      // Initialize input manager first
      const cleanupInput = initializeInputManager();

      // Connect input manager to WebSocket
      if (inputManagerRef.current) {
        await inputManagerRef.current.connect(url);

        // Attach input handlers to VNC container
        inputManagerRef.current.captureMouseEvents(containerRef.current);
        inputManagerRef.current.captureKeyboardEvents(containerRef.current);
        inputManagerRef.current.captureTouchEvents(containerRef.current);
        inputManagerRef.current.requestFocus(containerRef.current);
      }

      // Create RFB (Remote Frame Buffer) connection using noVNC
      const rfb = new RFB(canvasRef.current, url, {
        shared: shared,
        localCursor: localCursor,
        viewOnly: viewOnly,
        credentials: { password: process.env.NEXT_PUBLIC_VNC_PASSWORD || '' }
      });

      rfbRef.current = rfb;

      // RFB event handlers
      rfb.addEventListener('connect', () => {
        console.log('VNC connection established via noVNC');
        setConnectionState('connected');
        setRfbState('connected');
        onConnect?.();
      });

      rfb.addEventListener('disconnect', (e) => {
        console.log('VNC connection disconnected:', e.detail.reason);
        setConnectionState('disconnected');
        setRfbState('disconnected');
        onDisconnect?.(e.detail.reason || 'Connection closed');

        // Cleanup input manager on disconnect
        cleanupInput?.();
      });

      rfb.addEventListener('credentialsrequired', () => {
        console.log('VNC credentials required');
        setError('VNC password required');
        setConnectionState('error');
      });

      rfb.addEventListener('securityfailure', (e) => {
        console.error('VNC security failure:', e.detail.reason);
        const errorMsg = `Security failure: ${e.detail.reason}`;
        setError(errorMsg);
        setConnectionState('error');
        onError?.(errorMsg);
        cleanupInput?.();
      });

      rfb.addEventListener('bell', () => {
        console.log('VNC bell received');
        // Handle server bell if needed
      });

      rfb.addEventListener('clipboard', (e) => {
        console.log('VNC clipboard data received:', e.detail.text);
        // Handle clipboard sync if needed
      });

      // Handle resize events from VNC server
      rfb.addEventListener('desktopname', (e) => {
        console.log('VNC desktop name:', e.detail.name);
      });

      // Configure quality and compression
      rfb.quality = quality;
      rfb.compression = compression;

    } catch (err) {
      const errorMsg = `Failed to connect: ${err.message}`;
      setError(errorMsg);
      setConnectionState('error');
      onError?.(errorMsg);
    }
  }, [url, onConnect, onDisconnect, onError, initializeInputManager, shared, localCursor, viewOnly, quality, compression]);

  // VNC display quality control
  const updateQuality = useCallback((newQuality) => {
    if (rfbRef.current && rfbRef.current.state === 'connected') {
      rfbRef.current.quality = newQuality;
      console.log(`VNC quality updated to: ${newQuality}`);
    }
  }, []);

  // VNC compression control
  const updateCompression = useCallback((newCompression) => {
    if (rfbRef.current && rfbRef.current.state === 'connected') {
      rfbRef.current.compression = newCompression;
      console.log(`VNC compression updated to: ${newCompression}`);
    }
  }, []);

  // VNC scaling control
  const toggleScaling = useCallback(() => {
    if (rfbRef.current) {
      rfbRef.current.scaleViewport = !rfbRef.current.scaleViewport;
      console.log(`VNC scaling: ${rfbRef.current.scaleViewport ? 'enabled' : 'disabled'}`);
    }
  }, []);

  // Disconnect VNC connection
  const disconnectVNC = useCallback(() => {
    // Disconnect input manager first
    if (inputManagerRef.current) {
      inputManagerRef.current.destroy();
      inputManagerRef.current = null;
    }

    // Disconnect RFB connection
    if (rfbRef.current) {
      rfbRef.current.disconnect();
      rfbRef.current = null;
    }

    setConnectionState('disconnected');
    setRfbState('disconnected');
    setError(null);
    setInputMetrics(null);
  }, []);

  // Retry connection
  const retryConnection = useCallback(() => {
    disconnectVNC();
    setTimeout(connectVNC, 1000);
  }, [disconnectVNC, connectVNC]);

  // Toggle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  // Toggle settings panel
  const toggleSettings = useCallback(() => {
    setShowSettings(prev => !prev);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connectVNC();

    // Handle canvas resize
    const updateDimensions = () => {
      if (containerRef.current && canvasRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({ width: clientWidth, height: clientHeight });

        // RFB client handles canvas resizing automatically
        // No need to manually set canvas dimensions
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);

    return () => {
      window.removeEventListener('resize', updateDimensions);
      disconnectVNC();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-black ${className}`}
    >
      {/* Connection Status Overlay */}
      {connectionState !== 'connected' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/90 z-10">
          <div className="text-center">
            {connectionState === 'connecting' && (
              <>
                <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
                <p className="text-white text-lg font-medium">Connecting to workspace...</p>
                <p className="text-gray-400 text-sm mt-2">VNC Server: {url}</p>
              </>
            )}

            {connectionState === 'disconnected' && (
              <>
                <WifiOff className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-300 text-lg font-medium mb-2">Disconnected from workspace</p>
                <button
                  onClick={retryConnection}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Reconnect
                </button>
              </>
            )}

            {connectionState === 'error' && (
              <>
                <WifiOff className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <p className="text-red-400 text-lg font-medium mb-2">Connection Error</p>
                <p className="text-gray-400 text-sm mb-4">{error}</p>
                <button
                  onClick={retryConnection}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Retry
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* VNC Canvas */}
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{
          imageRendering: scale ? 'auto' : 'pixelated',
          cursor: connectionState === 'connected' ? 'default' : 'wait'
        }}
      />

      {/* Connection Status Indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
        {connectionState === 'connected' ? (
          <Wifi className="w-4 h-4 text-green-400" />
        ) : connectionState === 'connecting' ? (
          <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
        ) : (
          <WifiOff className="w-4 h-4 text-red-400" />
        )}
        <span className="text-white text-xs font-medium capitalize">
          {connectionState}
        </span>
      </div>

      {/* Controls */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <button
          onClick={toggleSettings}
          className="p-2 bg-black/50 backdrop-blur-sm rounded-lg text-white hover:bg-black/70 transition-colors"
          title="VNC Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
        <button
          onClick={toggleFullscreen}
          className="p-2 bg-black/50 backdrop-blur-sm rounded-lg text-white hover:bg-black/70 transition-colors"
          title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
        >
          {isFullscreen ? (
            <Minimize2 className="w-4 h-4" />
          ) : (
            <Maximize2 className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="absolute top-16 right-4 bg-black/90 backdrop-blur-sm rounded-lg p-4 space-y-3 z-20 min-w-64">
          <h3 className="text-white text-sm font-medium mb-3">VNC Settings</h3>

          {/* Quality Control */}
          <div className="space-y-2">
            <label className="text-gray-300 text-xs">Quality (0-9)</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0"
                max="9"
                value={quality}
                onChange={(e) => updateQuality(parseInt(e.target.value))}
                className="flex-1"
              />
              <span className="text-white text-xs w-4">{quality}</span>
            </div>
          </div>

          {/* Compression Control */}
          <div className="space-y-2">
            <label className="text-gray-300 text-xs">Compression (0-9)</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0"
                max="9"
                value={compression}
                onChange={(e) => updateCompression(parseInt(e.target.value))}
                className="flex-1"
              />
              <span className="text-white text-xs w-4">{compression}</span>
            </div>
          </div>

          {/* Scaling Toggle */}
          <div className="flex items-center justify-between">
            <span className="text-gray-300 text-xs">Scale to Fit</span>
            <button
              onClick={toggleScaling}
              className={`px-2 py-1 text-xs rounded ${scale ? 'bg-blue-500 text-white' : 'bg-gray-600 text-gray-300'}`}
            >
              {scale ? 'On' : 'Off'}
            </button>
          </div>

          {/* Connection Info */}
          <div className="pt-2 border-t border-gray-600">
            <div className="text-gray-400 text-xs">
              <div>Server: {url}</div>
              <div>RFB State: {rfbState}</div>
              <div>View Only: {viewOnly ? 'Yes' : 'No'}</div>
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={toggleSettings}
            className="w-full px-3 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-500 transition-colors"
          >
            Close
          </button>
        </div>
      )}

      {/* Workspace Info */}
      <div className="absolute bottom-4 left-4 space-y-2">
        {dimensions.width > 0 && dimensions.height > 0 && (
          <div className="bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
            <div className="flex items-center gap-2">
              <Monitor className="w-4 h-4 text-white" />
              <span className="text-white text-xs font-medium">
                {dimensions.width} × {dimensions.height}
              </span>
            </div>
          </div>
        )}

        {/* Input Metrics */}
        {inputMetrics && connectionState === 'connected' && (
          <div className="bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-white text-xs font-medium">
                  Input Active
                </span>
              </div>

              {inputMetrics.averageLatency > 0 && (
                <div className="text-gray-300 text-xs">
                  Latency: {Math.round(inputMetrics.averageLatency)}ms
                  {inputMetrics.averageLatency > 500 && (
                    <span className="text-yellow-400 ml-1">⚠️</span>
                  )}
                </div>
              )}

              <div className="text-gray-300 text-xs">
                Events: {inputMetrics.eventsProcessed}
                {inputMetrics.eventsDropped > 0 && (
                  <span className="text-red-400 ml-1">({inputMetrics.eventsDropped} dropped)</span>
                )}
              </div>

              {inputMetrics.queueSize > 0 && (
                <div className="text-gray-300 text-xs">
                  Queue: {inputMetrics.queueSize}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VNCViewer;