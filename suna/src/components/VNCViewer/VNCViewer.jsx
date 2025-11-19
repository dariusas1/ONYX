import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Monitor, Wifi, WifiOff, Loader2, Maximize2, Minimize2, Settings } from 'lucide-react';
import RFB from '@novnc/novnc/core/rfb';
import KeyTable from '@novnc/novnc/core/input/keysym';
import TouchInputHandler from './TouchInputHandler';

export const VNCViewer = ({
  url = 'ws://localhost:6080',
  onConnect,
  onDisconnect,
  onError,
  className = '',
  scale = true,
  quality = 6,
  compression = 1
}) => {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const rfbRef = useRef(null);

  const [connectionState, setConnectionState] = useState('disconnected'); // disconnected, connecting, connected, error
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [showStats, setShowStats] = useState(false);
  const [stats, setStats] = useState({
    fps: 0,
    latency: 0,
    bandwidth: 0
  });

  // Initialize VNC connection with real noVNC client
  const connectVNC = useCallback(() => {
    if (!canvasRef.current) return;

    try {
      setConnectionState('connecting');
      setError(null);

      // Create RFB (Remote Frame Buffer) instance
      const rfb = new RFB(canvasRef.current, url, {
        // Connection options
        credentials: { password: '' }, // Will be set if needed
        wsProtocols: ['binary'],
        repeaterID: '',

        // Performance settings
        quality: quality,
        compression: compression,

        // Display settings
        scaleViewport: scale,
        resizeSession: false,
        showDotCursor: true,

        // Input settings
        viewOnly: false,
        shared: true,

        // Additional options
        localCursor: true,
        dragViewport: false,
        focusOnClick: false,
        clipViewport: false,
        scrollbars: false
      });

      rfbRef.current = rfb;

      // Event handlers for RFB
      rfb.addEventListener('connect', () => {
        console.log('VNC connected successfully');
        setConnectionState('connected');
        onConnect?.();
      });

      rfb.addEventListener('disconnect', (e) => {
        console.log('VNC disconnected:', e.detail.reason);
        setConnectionState('disconnected');
        onDisconnect?.(e.detail.reason || 'Connection closed');
        rfbRef.current = null;
      });

      rfb.addEventListener('credentialsrequired', () => {
        // Handle authentication if required
        console.log('VNC authentication required');
        rfb.sendCredentials({ password: '' });
      });

      rfb.addEventListener('securityfailure', (e) => {
        console.error('VNC security failure:', e.detail.reason);
        const errorMsg = `Security failure: ${e.detail.reason}`;
        setError(errorMsg);
        setConnectionState('error');
        onError?.(errorMsg);
      });

      rfb.addEventListener('bell', () => {
        // Handle server bell
        console.log('VNC bell received');
      });

      rfb.addEventListener('desktopname', (e) => {
        console.log('VNC desktop name:', e.detail.name);
      });

      rfb.addEventListener('clipboard', (e) => {
        // Handle clipboard data from server
        console.log('VNC clipboard data received');
      });

      // Frame timing for FPS calculation
      let frameCount = 0;
      let lastFpsUpdate = Date.now();

      rfb.addEventListener('framebufferupdate', () => {
        frameCount++;
        const now = Date.now();
        const timeDiff = now - lastFpsUpdate;

        if (timeDiff >= 1000) {
          const fps = (frameCount * 1000) / timeDiff;
          setStats(prev => ({ ...prev, fps: Math.round(fps) }));
          frameCount = 0;
          lastFpsUpdate = now;
        }
      });

      // Handle connection errors
      rfb.addEventListener('failure', (e) => {
        console.error('VNC connection failure:', e.detail.reason);
        const errorMsg = `Connection failed: ${e.detail.reason}`;
        setError(errorMsg);
        setConnectionState('error');
        onError?.(errorMsg);
      });

    } catch (err) {
      const errorMsg = `Failed to initialize VNC: ${err.message}`;
      setError(errorMsg);
      setConnectionState('error');
      onError?.(errorMsg);
    }
  }, [url, onConnect, onDisconnect, onError, scale, quality, compression]);

  // Disconnect VNC connection
  const disconnectVNC = useCallback(() => {
    if (rfbRef.current) {
      rfbRef.current.disconnect();
      rfbRef.current = null;
    }
    setConnectionState('disconnected');
    setError(null);
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

  // Auto-connect on mount
  useEffect(() => {
    connectVNC();

    // Handle canvas resize
    const updateDimensions = () => {
      if (containerRef.current && canvasRef.current) {
        const { clientWidth, clientHeight } = containerRef.current;
        setDimensions({ width: clientWidth, height: clientHeight });

        // Resize VNC display if connected
        if (rfbRef.current) {
          rfbRef.current.resize(clientWidth, clientHeight);
        }
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);

    return () => {
      window.removeEventListener('resize', updateDimensions);
      disconnectVNC();
    };
  }, []);

  // Handle keyboard events when VNC viewer is focused
  const handleKeyDown = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      // Prevent default behavior for VNC keys
      e.preventDefault();

      // Send keyboard event to VNC
      const keyboardEvent = new KeyboardEvent('keydown', {
        key: e.key,
        code: e.code,
        keyCode: e.keyCode,
        location: e.location,
        ctrlKey: e.ctrlKey,
        shiftKey: e.shiftKey,
        altKey: e.altKey,
        metaKey: e.metaKey
      });

      rfbRef.current.keyboardEvents.push(keyboardEvent);
    }
  }, [connectionState]);

  const handleKeyUp = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      e.preventDefault();

      const keyboardEvent = new KeyboardEvent('keyup', {
        key: e.key,
        code: e.code,
        keyCode: e.keyCode,
        location: e.location,
        ctrlKey: e.ctrlKey,
        shiftKey: e.shiftKey,
        altKey: e.altKey,
        metaKey: e.metaKey
      });

      rfbRef.current.keyboardEvents.push(keyboardEvent);
    }
  }, [connectionState]);

  // Handle mouse events
  const handleMouseDown = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      rfbRef.current.sendMouseButton(x, y, e.button, true);
    }
  }, [connectionState]);

  const handleMouseUp = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      rfbRef.current.sendMouseButton(x, y, e.button, false);
    }
  }, [connectionState]);

  const handleMouseMove = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      rfbRef.current.sendMouseMove(x, y);
    }
  }, [connectionState]);

  const handleContextMenu = useCallback((e) => {
    e.preventDefault();
    if (connectionState === 'connected' && rfbRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      rfbRef.current.sendMouseButton(x, y, 2, true); // Right click
      rfbRef.current.sendMouseButton(x, y, 2, false);
    }
  }, [connectionState]);

  // Handle wheel events for scrolling
  const handleWheel = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      e.preventDefault();

      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Convert wheel delta to VNC scroll amount
      const scrollAmount = -Math.sign(e.deltaY) * 120; // Standard wheel click value

      rfbRef.current.sendMouseWheel(x, y, 0, scrollAmount);
    }
  }, [connectionState]);

  // Handle touch input events
  const handleTouchInput = useCallback((event) => {
    if (connectionState !== 'connected' || !rfbRef.current) return;

    switch (event.type) {
      case 'mousedown':
        rfbRef.current.sendMouseButton(event.x, event.y, event.button, true);
        break;
      case 'mouseup':
        rfbRef.current.sendMouseButton(event.x, event.y, event.button, false);
        break;
      case 'mousemove':
        rfbRef.current.sendMouseMove(event.x, event.y);
        break;
      case 'click':
        rfbRef.current.sendMouseButton(event.x, event.y, 0, true);
        rfbRef.current.sendMouseButton(event.x, event.y, 0, false);
        break;
      case 'pinchzoom':
        // Handle pinch zoom - for now, just log it as pinch zoom is complex
        console.log('Pinch zoom:', event.scale, event.centerX, event.centerY);
        // Could implement zoom functionality here if needed
        break;
    }
  }, [connectionState]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-black ${className}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onKeyUp={handleKeyUp}
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

      {/* VNC Canvas with Touch Input Handler */}
      <TouchInputHandler onTouchInput={handleTouchInput}>
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseMove={handleMouseMove}
          onContextMenu={handleContextMenu}
          onWheel={handleWheel}
          style={{
            cursor: connectionState === 'connected' ? 'default' : 'wait'
          }}
        />
      </TouchInputHandler>

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
        {/* Stats Toggle */}
        <button
          onClick={() => setShowStats(!showStats)}
          className="p-2 bg-black/50 backdrop-blur-sm rounded-lg text-white hover:bg-black/70 transition-colors"
          title="Toggle Stats"
        >
          <Settings className="w-4 h-4" />
        </button>

        {/* Fullscreen Toggle */}
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

      {/* Stats Display */}
      {showStats && (
        <div className="absolute bottom-4 left-4 bg-black/70 backdrop-blur-sm rounded-lg px-3 py-2 text-white text-xs">
          <div className="space-y-1">
            <div>FPS: {stats.fps}</div>
            <div>Quality: {quality}/9</div>
            <div>Compression: {compression}/9</div>
            <div>Scale: {scale ? 'On' : 'Off'}</div>
          </div>
        </div>
      )}

      {/* Workspace Info */}
      {dimensions.width > 0 && dimensions.height > 0 && !showStats && (
        <div className="absolute bottom-4 left-4 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4 text-white" />
            <span className="text-white text-xs font-medium">
              {dimensions.width} × {dimensions.height}
            </span>
          </div>
        </div>
      )}

      {/* Touch Controls for Mobile/Tablet */}
      <div className="lg:hidden absolute bottom-4 right-4 flex items-center gap-2 bg-black/70 backdrop-blur-sm rounded-lg px-3 py-2">
        <div className="text-white text-xs">
          Touch controls enabled
        </div>
      </div>
    </div>
  );
};

export default VNCViewer;