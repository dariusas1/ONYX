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
  const wsRef = useRef(null);

  const [connectionState, setConnectionState] = useState('disconnected'); // disconnected, connecting, connected, error
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Initialize VNC connection
  const connectVNC = useCallback(() => {
    if (!canvasRef.current) return;

    try {
      setConnectionState('connecting');
      setError(null);

      // Create WebSocket connection for VNC protocol
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        console.log('VNC WebSocket connection opened');
        // Simple VNC handshake (placeholder for actual VNC protocol)
        setConnectionState('connected');
        onConnect?.();
      };

      ws.onmessage = (event) => {
        // Handle VNC protocol messages
        console.log('VNC message received');
        // Placeholder for actual VNC rendering logic
        renderVNCFrame(event.data);
      };

      ws.onclose = (event) => {
        console.log('VNC connection closed');
        setConnectionState('disconnected');
        onDisconnect?.(event.reason || 'Connection closed');
      };

      ws.onerror = (error) => {
        console.error('VNC WebSocket error:', error);
        const errorMsg = 'WebSocket connection failed';
        setError(errorMsg);
        setConnectionState('error');
        onError?.(errorMsg);
      };

    } catch (err) {
      const errorMsg = `Failed to connect: ${err.message}`;
      setError(errorMsg);
      setConnectionState('error');
      onError?.(errorMsg);
    }
  }, [url, onConnect, onDisconnect, onError]);

  // Simple VNC frame rendering (placeholder)
  const renderVNCFrame = useCallback((data) => {
    if (!canvasRef.current) return;

    const ctx = canvasRef.current.getContext('2d');
    if (!ctx) return;

    // This is a placeholder for actual VNC rendering
    // In a real implementation, this would decode VNC protocol messages
    // and render the remote desktop to the canvas

    // For demo purposes, create a simple gradient
    const width = canvasRef.current.width;
    const height = canvasRef.current.height;

    const gradient = ctx.createLinearGradient(0, 0, width, height);
    gradient.addColorStop(0, '#1a1a2e');
    gradient.addColorStop(0.5, '#16213e');
    gradient.addColorStop(1, '#0f3460');

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    // Add some demo text
    ctx.fillStyle = '#ffffff';
    ctx.font = '20px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('VNC Workspace View', width / 2, height / 2);
    ctx.fillText(`Connected to: ${url}`, width / 2, height / 2 + 30);
  }, [url]);

  // Disconnect VNC connection
  const disconnectVNC = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
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

        // Set canvas dimensions
        canvasRef.current.width = clientWidth;
        canvasRef.current.height = clientHeight;

        // Re-render frame if connected
        if (connectionState === 'connected') {
          renderVNCFrame(new ArrayBuffer(0));
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

  // Handle keyboard events when in focus
  const handleKeyDown = useCallback((e) => {
    if (connectionState === 'connected' && wsRef.current) {
      // Send keyboard events to VNC server
      const keyCode = e.keyCode;
      const keyData = new Uint8Array([keyCode]);
      wsRef.current.send(keyData);
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