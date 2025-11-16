import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Monitor, Wifi, WifiOff, Loader2, Maximize2, Minimize2 } from 'lucide-react';
import RFB from '@novnc/novnc/core/rfb';
import KeyTable from '@novnc/novnc/core/input/keysym';
import Mouse from '@novnc/novnc/core/input/mouse';

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

  // Initialize VNC connection using noVNC library
  const connectVNC = useCallback(() => {
    if (!canvasRef.current) {
      console.error('Canvas element not available for VNC connection');
      return;
    }

    try {
      setConnectionState('connecting');
      setError(null);

      // Create RFB (Remote Frame Buffer) connection using noVNC
      const rfb = new RFB(canvasRef.current, url, {
        // Connection options
        shared: true, // Allow multiple connections to the same desktop
        repeaterID: '',
        credentials: (req) => {
          // For Story 8-1 security integration, this will be enhanced
          return { password: '' }; // Default password for now
        }
      });

      rfbRef.current = rfb;

      // Configure display settings
      rfb.scaleViewport = scale;
      rfb.resizeSession = false;
      rfb.qualityLevel = quality;
      rfb.compressionLevel = compression;

      // Connection event handlers
      rfb.addEventListener('connect', () => {
        console.log('VNC connected successfully using noVNC');
        setConnectionState('connected');
        setError(null);
        onConnect?.();
      });

      rfb.addEventListener('disconnect', (e) => {
        console.log('VNC disconnected:', e.detail.reason);
        setConnectionState('disconnected');
        onDisconnect?.(e.detail.reason || 'Connection closed');
      });

      rfb.addEventListener('credentialsrequired', (e) => {
        console.log('VNC credentials required');
        // Handle authentication if needed
        // For now, just send empty password (will be enhanced for Story 8-1 integration)
        rfb.sendCredentials({ password: '' });
      });

      rfb.addEventListener('securityfailure', (e) => {
        console.error('VNC security failure:', e.detail.reason);
        const errorMsg = `Security failure: ${e.detail.reason}`;
        setError(errorMsg);
        setConnectionState('error');
        onError?.(errorMsg);
      });

      // Error handling
      rfb.addEventListener('serverboundary', (e) => {
        console.log('VNC server boundary updated:', e.detail);
        // Update dimensions when server sends new screen size
        updateCanvasDimensions();
      });

    } catch (err) {
      console.error('Failed to initialize VNC connection:', err);
      const errorMsg = `Failed to connect: ${err.message}`;
      setError(errorMsg);
      setConnectionState('error');
      onError?.(errorMsg);
    }
  }, [url, scale, quality, compression, onConnect, onDisconnect, onError]);

  // Update canvas dimensions based on container and VNC framebuffer
  const updateCanvasDimensions = useCallback(() => {
    if (containerRef.current && canvasRef.current && rfbRef.current) {
      const { clientWidth, clientHeight } = containerRef.current;
      const fbWidth = rfbRef.current._fbWidth;
      const fbHeight = rfbRef.current._fbHeight;

      setDimensions({
        width: fbWidth || clientWidth,
        height: fbHeight || clientHeight
      });

      // Update canvas size
      canvasRef.current.width = fbWidth || clientWidth;
      canvasRef.current.height = fbHeight || clientHeight;
    }
  }, []);

  // Disconnect VNC connection
  const disconnectVNC = useCallback(() => {
    if (rfbRef.current) {
      try {
        rfbRef.current.disconnect();
        rfbRef.current = null;
      } catch (err) {
        console.warn('Error during VNC disconnect:', err);
      }
    }
    setConnectionState('disconnected');
    setError(null);
  }, []);

  // Retry connection with exponential backoff
  const retryConnection = useCallback(() => {
    disconnectVNC();

    // Implement retry with delay for better connection stability
    const retryDelay = Math.min(1000 * Math.pow(2, 2), 5000); // Max 5 seconds
    setTimeout(connectVNC, retryDelay);
  }, [disconnectVNC, connectVNC]);

  // Toggle fullscreen mode
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch(err => {
        console.warn('Failed to enter fullscreen:', err);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      }).catch(err => {
        console.warn('Failed to exit fullscreen:', err);
      });
    }
  }, []);

  // Handle fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Auto-connect on component mount
  useEffect(() => {
    connectVNC();

    // Handle window resize for responsive design
    const handleResize = () => {
      updateCanvasDimensions();
    };

    window.addEventListener('resize', handleResize);

    // Initial dimension update
    setTimeout(updateCanvasDimensions, 100);

    return () => {
      window.removeEventListener('resize', handleResize);
      disconnectVNC();
    };
  }, []);

  // Update VNC settings when props change
  useEffect(() => {
    if (rfbRef.current && connectionState === 'connected') {
      rfbRef.current.scaleViewport = scale;
      rfbRef.current.qualityLevel = quality;
      rfbRef.current.compressionLevel = compression;
    }
  }, [scale, quality, compression, connectionState]);

  // Handle keyboard events when canvas is focused
  const handleKeyDown = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      // Prevent default behavior for certain keys
      e.preventDefault();

      // Map keyboard events to VNC key codes
      const keyCode = e.keyCode || e.which;
      const keySym = KeyTable[XK_KEYS[keyCode]] || KeyTable.XK_VoidSymbol;

      // Send key event to VNC server
      rfbRef.current.sendKey(keySym, 1, e.shiftKey, e.ctrlKey, e.altKey, e.metaKey);
    }
  }, [connectionState]);

  // Handle key up events
  const handleKeyUp = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      e.preventDefault();

      const keyCode = e.keyCode || e.which;
      const keySym = KeyTable[XK_KEYS[keyCode]] || KeyTable.XK_VoidSymbol;

      rfbRef.current.sendKey(keySym, 0, e.shiftKey, e.ctrlKey, e.altKey, e.metaKey);
    }
  }, [connectionState]);

  // Handle mouse events
  const handleMouseDown = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      const button = e.button === 0 ? 1 : e.button === 1 ? 4 : e.button === 2 ? 2 : 0;
      rfbRef.current.sendMouseEvent(e.clientX, e.clientY, button, 1);
    }
  }, [connectionState]);

  const handleMouseUp = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      const button = e.button === 0 ? 1 : e.button === 1 ? 4 : e.button === 2 ? 2 : 0;
      rfbRef.current.sendMouseEvent(e.clientX, e.clientY, button, 0);
    }
  }, [connectionState]);

  const handleMouseMove = useCallback((e) => {
    if (connectionState === 'connected' && rfbRef.current) {
      const button = (e.buttons & 1) ? 1 : (e.buttons & 2) ? 4 : (e.buttons & 4) ? 2 : 0;
      rfbRef.current.sendMouseEvent(e.clientX, e.clientY, button, e.buttons > 0);
    }
  }, [connectionState]);

  // Key code mapping for common keys
  const XK_KEYS = {
    8: 'BackSpace',
    9: 'Tab',
    13: 'Return',
    16: 'Shift_L',
    17: 'Control_L',
    18: 'Alt_L',
    20: 'Caps_Lock',
    27: 'Escape',
    32: 'space',
    37: 'Left',
    38: 'Up',
    39: 'Right',
    40: 'Down',
    45: 'Insert',
    46: 'Delete',
    112: 'F1', 113: 'F2', 114: 'F3', 115: 'F4', 116: 'F5', 117: 'F6',
    118: 'F7', 119: 'F8', 120: 'F9', 121: 'F10', 122: 'F11', 123: 'F12'
  };

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
          <div className="text-center max-w-md px-4">
            {connectionState === 'connecting' && (
              <>
                <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
                <p className="text-white text-lg font-medium">Connecting to workspace...</p>
                <p className="text-gray-400 text-sm mt-2">VNC Server: {url}</p>
                <div className="mt-4 text-gray-500 text-xs">
                  <p>• Establishing secure connection</p>
                  <p>• Initializing VNC protocol</p>
                  <p>• Loading remote desktop...</p>
                </div>
              </>
            )}

            {connectionState === 'disconnected' && (
              <>
                <WifiOff className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-300 text-lg font-medium mb-2">Disconnected from workspace</p>
                <p className="text-gray-500 text-sm mb-4">
                  The VNC connection has been closed. Click reconnect to restore your workspace session.
                </p>
                <button
                  onClick={retryConnection}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
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
                <div className="space-y-2">
                  <button
                    onClick={retryConnection}
                    className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium w-full"
                  >
                    Retry Connection
                  </button>
                  <p className="text-gray-500 text-xs">
                    If the problem persists, check that the noVNC server is running on port 6080
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* VNC Canvas with proper event handling */}
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{
          imageRendering: scale ? 'auto' : 'pixelated',
          cursor: connectionState === 'connected' ? 'default' : 'wait',
          touchAction: 'none' // Prevent touch scrolling on tablets
        }}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseUp} // Ensure button is released when mouse leaves canvas
      />

      {/* Enhanced Connection Status Indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
        {connectionState === 'connected' ? (
          <>
            <Wifi className="w-4 h-4 text-green-400" />
            <span className="text-white text-xs font-medium">Connected</span>
          </>
        ) : connectionState === 'connecting' ? (
          <>
            <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
            <span className="text-white text-xs font-medium">Connecting...</span>
          </>
        ) : (
          <>
            <WifiOff className="w-4 h-4 text-red-400" />
            <span className="text-white text-xs font-medium capitalize">
              {connectionState}
            </span>
          </>
        )}
      </div>

      {/* Enhanced Controls */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <button
          onClick={retryConnection}
          className="p-2 bg-black/50 backdrop-blur-sm rounded-lg text-white hover:bg-black/70 transition-colors"
          title="Reconnect to workspace"
          disabled={connectionState === 'connecting'}
        >
          <Loader2 className={`w-4 h-4 ${connectionState === 'connecting' ? 'animate-spin' : ''}`} />
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

      {/* Enhanced Workspace Info */}
      {dimensions.width > 0 && dimensions.height > 0 && (
        <div className="absolute bottom-4 left-4 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4 text-white" />
            <span className="text-white text-xs font-medium">
              {dimensions.width} × {dimensions.height}
            </span>
          </div>
          {connectionState === 'connected' && (
            <div className="text-white text-xs opacity-75 mt-1">
              Remote Desktop Active
            </div>
          )}
        </div>
      )}

      {/* Performance indicator for responsive design */}
      {connectionState === 'connected' && (
        <div className="absolute bottom-4 right-4 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
          <div className="text-white text-xs opacity-75">
            {scale ? 'Scaled' : 'Original Size'} • Quality: {quality}/9
          </div>
        </div>
      )}
    </div>
  );
};

export default VNCViewer;