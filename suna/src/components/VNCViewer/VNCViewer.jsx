import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Monitor, Wifi, WifiOff, Loader2, Maximize2, Minimize2 } from 'lucide-react';

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
  const vncRef = useRef(null);

  const [connectionState, setConnectionState] = useState('disconnected'); // disconnected, connecting, connected, error
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Initialize VNC connection
  const connectVNC = useCallback(async () => {
    if (!canvasRef.current) return;

    try {
      setConnectionState('connecting');
      setError(null);

      // Dynamically import noVNC to avoid SSR issues
      const RFB = await import('@novnc/novnc/lib/rfb.js');

      const rfb = new RFB.default(canvasRef.current, url, {
        credentials: {
          password: '' // Add password if required
        },
        scale,
        quality,
        compression
      });

      vncRef.current = rfb;

      // Event handlers
      rfb.addEventListener('connect', () => {
        setConnectionState('connected');
        onConnect?.();
      });

      rfb.addEventListener('disconnect', (e) => {
        setConnectionState('disconnected');
        onDisconnect?.(e.detail?.reason || 'Connection closed');
      });

      rfb.addEventListener('credentialsrequired', () => {
        // Handle credential requirements if needed
        const password = prompt('VNC Password:');
        if (password) {
          rfb.sendCredentials({ password });
        }
      });

      rfb.addEventListener('securityfailure', (e) => {
        const errorMsg = `Security failure: ${e.detail?.reason || 'Unknown error'}`;
        setError(errorMsg);
        setConnectionState('error');
        onError?.(errorMsg);
      });

      // Handle canvas resize
      const updateDimensions = () => {
        if (containerRef.current && canvasRef.current) {
          const { clientWidth, clientHeight } = containerRef.current;
          setDimensions({ width: clientWidth, height: clientHeight });
        }
      };

      updateDimensions();
      window.addEventListener('resize', updateDimensions);

      return () => {
        window.removeEventListener('resize', updateDimensions);
      };

    } catch (err) {
      const errorMsg = `Failed to connect: ${err.message}`;
      setError(errorMsg);
      setConnectionState('error');
      onError?.(errorMsg);
    }
  }, [url, scale, quality, compression, onConnect, onDisconnect, onError]);

  // Disconnect VNC connection
  const disconnectVNC = useCallback(() => {
    if (vncRef.current) {
      vncRef.current.disconnect();
      vncRef.current = null;
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

    return () => {
      disconnectVNC();
    };
  }, []);

  // Handle keyboard events when in focus
  const handleKeyDown = useCallback((e) => {
    if (connectionState === 'connected' && vncRef.current) {
      vncRef.current.focus();
      vncRef.current.sendKey(e.key, e.code, e.getModifierState('Shift'), e.getModifierState('Control'), e.getModifierState('Alt'), e.getModifierState('Meta'));
    }
  }, [connectionState]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-black ${className}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Connection Status Overlay */}
      {connectionState !== 'connected' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/90 z-10">
          <div className="text-center">
            {connectionState === 'connecting' && (
              <>
                <Loader2 className="w-12 h-12 text-blue-400 animate-spin mx-auto mb-4" />
                <p className="text-white text-lg font-medium">Connecting to workspace...</p>
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
          imageRendering: 'pixelated',
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

      {/* Workspace Info */}
      {dimensions.width > 0 && dimensions.height > 0 && (
        <div className="absolute bottom-4 left-4 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <Monitor className="w-4 h-4 text-white" />
            <span className="text-white text-xs font-medium">
              {dimensions.width} × {dimensions.height}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default VNCViewer;