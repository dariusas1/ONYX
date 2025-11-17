'use client';

import React, { useEffect, useRef, useCallback } from 'react';
import { Monitor, Maximize2, Minimize2, Wifi, WifiOff } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';

interface VNCViewerProps {
  className?: string;
  onConnectionChange?: (connected: boolean) => void;
}

export const VNCViewer: React.FC<VNCViewerProps> = ({ className = '', onConnectionChange }) => {
  const {
    session,
    config,
    qualitySettings,
    connect,
    disconnect,
    updateQualitySettings,
    containerRef,
    rfbRef,
    hasControl,
    controlOwner
  } = useWorkspace();

  const localContainerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = React.useState(false);
  const [localScale, setLocalScale] = React.useState(1.0);

  // Forward containerRef to local ref
  useEffect(() => {
    if (containerRef && localContainerRef.current) {
      (containerRef as React.MutableRefObject<HTMLDivElement | null>).current = localContainerRef.current;
    }
  }, [containerRef]);

  // Handle connection changes
  useEffect(() => {
    onConnectionChange?.(session.isConnected);
  }, [session.isConnected, onConnectionChange]);

  // Auto-connect when component mounts and workspace is open
  useEffect(() => {
    if (session.connectionState === 'disconnected' && !session.isConnected) {
      connect().catch(console.error);
    }
  }, [session.connectionState, session.isConnected, connect]);

  // Handle keyboard events for VNC input
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!session.isConnected || !hasControl) return;

    // Forward keyboard event to VNC
    if (rfbRef.current) {
      // Map DOM keyboard event to VNC keysym
      let keysym = 0;

      // Handle special keys and modifiers
      if (event.ctrlKey || event.metaKey) {
        keysym |= 0x0001; // Control mask
      }
      if (event.shiftKey) {
        keysym |= 0x0002; // Shift mask
      }
      if (event.altKey) {
        keysym |= 0x0004; // Alt mask
      }

      // Handle common VNC shortcuts locally
      if (event.ctrlKey || event.metaKey) {
        switch (event.key) {
          case '+':
          case '=':
            // Zoom in
            setLocalScale(prev => Math.min(prev + 0.1, 2.0));
            event.preventDefault();
            return;
          case '-':
            // Zoom out
            setLocalScale(prev => Math.max(prev - 0.1, 0.5));
            event.preventDefault();
            return;
          case '0':
            // Reset zoom
            setLocalScale(1.0);
            event.preventDefault();
            return;
        }
      }

      // Convert key to VNC keysym (simplified mapping)
      const keyMap: { [key: string]: number } = {
        'Enter': 0xFF0D,
        'Escape': 0xFF1B,
        'Backspace': 0xFF08,
        'Tab': 0xFF09,
        'Delete': 0xFFFF,
        'Home': 0xFF50,
        'End': 0xFF57,
        'PageUp': 0xFF55,
        'PageDown': 0xFF56,
        'ArrowUp': 0xFF52,
        'ArrowDown': 0xFF54,
        'ArrowLeft': 0xFF51,
        'ArrowRight': 0xFF53,
        'F1': 0xFFBE,
        'F2': 0xFFBF,
        'F3': 0xFFC0,
        'F4': 0xFFC1,
        'F5': 0xFFC2,
        'F6': 0xFFC3,
        'F7': 0xFFC4,
        'F8': 0xFFC5,
        'F9': 0xFFC6,
        'F10': 0xFFC7,
        'F11': 0xFFC8,
        'F12': 0xFFC9,
      };

      // Map keys
      if (keyMap[event.key]) {
        keysym |= keyMap[event.key];
      } else if (event.key.length === 1) {
        // Regular printable character
        keysym |= event.key.charCodeAt(0);
      } else {
        // Default to space if we can't map it
        keysym |= 0x020;
      }

      // Send key event to VNC
      try {
        rfbRef.current.sendKey({
          keysym,
          keyCode: event.keyCode,
        });
      } catch (error) {
        console.error('Failed to send keyboard event to VNC:', error);
      }
    }
  }, [session.isConnected, hasControl, rfbRef]);

  // Handle mouse events for VNC input
  const handleMouseDown = useCallback((event: React.MouseEvent) => {
    if (!session.isConnected || !hasControl || !rfbRef.current) return;

    // Get mouse position relative to VNC container
    const rect = localContainerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Map mouse button to VNC button mask
    let buttonMask = 0;
    switch (event.button) {
      case 0: // Left click
        buttonMask = 1;
        break;
      case 1: // Middle click
        buttonMask = 4;
        break;
      case 2: // Right click
        buttonMask = 2;
        break;
      case 3: // Back button
        buttonMask = 8;
        break;
      case 4: // Forward button
        buttonMask = 16;
        break;
    }

    try {
      rfbRef.current.sendMouseButton(x, y, buttonMask, true);
    } catch (error) {
      console.error('Failed to send mouse down event to VNC:', error);
    }
  }, [session.isConnected, hasControl, rfbRef]);

  const handleMouseUp = useCallback((event: React.MouseEvent) => {
    if (!session.isConnected || !hasControl || !rfbRef.current) return;

    const rect = localContainerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    let buttonMask = 0;
    switch (event.button) {
      case 0: // Left click
        buttonMask = 1;
        break;
      case 1: // Middle click
        buttonMask = 4;
        break;
      case 2: // Right click
        buttonMask = 2;
        break;
      case 3: // Back button
        buttonMask = 8;
        break;
      case 4: // Forward button
        buttonMask = 16;
        break;
    }

    try {
      rfbRef.current.sendMouseButton(x, y, buttonMask, false);
    } catch (error) {
      console.error('Failed to send mouse up event to VNC:', error);
    }
  }, [session.isConnected, hasControl, rfbRef]);

  const handleMouseMove = useCallback((event: React.MouseEvent) => {
    if (!session.isConnected || !hasControl || !rfbRef.current) return;

    const rect = localContainerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    try {
      rfbRef.current.sendMouseMove(x, y);
    } catch (error) {
      console.error('Failed to send mouse move event to VNC:', error);
    }
  }, [session.isConnected, hasControl, rfbRef]);

  const handleWheel = useCallback((event: React.WheelEvent) => {
    if (!session.isConnected || !hasControl || !rfbRef.current) return;

    event.preventDefault();

    const rect = localContainerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Normalize scroll delta and convert to VNC scroll button
    const delta = event.deltaY || event.deltaX;
    const scrollButton = delta > 0 ? 5 : 4; // Scroll down = 5, Scroll up = 4

    try {
      rfbRef.current.sendMouseButton(x, y, scrollButton, true);
      // Immediately release the scroll button
      setTimeout(() => {
        rfbRef.current?.sendMouseButton(x, y, scrollButton, false);
      }, 50);
    } catch (error) {
      console.error('Failed to send mouse wheel event to VNC:', error);
    }
  }, [session.isConnected, hasControl, rfbRef]);

  // Add event listeners
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Handle fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      localContainerRef.current?.parentElement?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  // Handle fullscreen change events
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Manual reconnection
  const handleReconnect = useCallback(() => {
    disconnect();
    setTimeout(() => {
      connect().catch(console.error);
    }, 1000);
  }, [disconnect, connect]);

  // Quality adjustment shortcuts
  const improveQuality = useCallback(() => {
    updateQualitySettings({
      quality: Math.max(qualitySettings.quality - 1, 0),
      compression: Math.max(qualitySettings.compression - 1, 0)
    });
  }, [qualitySettings, updateQualitySettings]);

  const improvePerformance = useCallback(() => {
    updateQualitySettings({
      quality: Math.min(qualitySettings.quality + 1, 9),
      compression: Math.min(qualitySettings.compression + 1, 9)
    });
  }, [qualitySettings, updateQualitySettings]);

  // Connection status indicator
  const getConnectionIcon = () => {
    switch (session.connectionState) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-green-500" />;
      case 'connecting':
      case 'reconnecting':
        return <Wifi className="w-4 h-4 text-yellow-500 animate-pulse" />;
      case 'error':
      case 'disconnected':
        return <WifiOff className="w-4 h-4 text-red-500" />;
      default:
        return <WifiOff className="w-4 h-4 text-gray-500" />;
    }
  };

  const getConnectionText = () => {
    switch (session.connectionState) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'reconnecting':
        return 'Reconnecting...';
      case 'error':
        return 'Connection Error';
      case 'disconnected':
        return 'Disconnected';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className={`flex flex-col h-full bg-gray-900 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-3">
          <Monitor className="w-5 h-5 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">VNC Workspace</span>
          <div className="flex items-center space-x-1">
            {getConnectionIcon()}
            <span className="text-xs text-gray-400">{getConnectionText()}</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Control indicator */}
          {session.isConnected && (
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${
                hasControl ? 'bg-green-500' :
                controlOwner === 'agent' ? 'bg-yellow-500' : 'bg-gray-500'
              }`} />
              <span className="text-xs text-gray-400">
                {hasControl ? 'Your Control' :
                 controlOwner === 'agent' ? 'Agent Control' : 'No Control'}
              </span>
            </div>
          )}

          {/* Quality indicator */}
          {session.isConnected && (
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${
                session.connectionQuality === 'excellent' ? 'bg-green-500' :
                session.connectionQuality === 'good' ? 'bg-yellow-500' :
                session.connectionQuality === 'poor' ? 'bg-orange-500' : 'bg-red-500'
              }`} />
              <span className="text-xs text-gray-400">
                {session.latency > 0 ? `${session.latency}ms` : 'N/A'}
              </span>
            </div>
          )}

          {/* Action buttons */}
          <button
            onClick={improveQuality}
            disabled={!session.isConnected}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Improve Quality (Ctrl+Shift+Q)"
          >
            Quality
          </button>

          <button
            onClick={improvePerformance}
            disabled={!session.isConnected}
            className="px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Improve Performance (Ctrl+Shift+P)"
          >
            Speed
          </button>

          <button
            onClick={toggleFullscreen}
            disabled={!session.isConnected}
            className="p-1 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
            title="Toggle Fullscreen (F11)"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* VNC Display Area */}
      <div className="flex-1 relative overflow-hidden">
        {session.connectionState === 'connecting' && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900 z-10">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-400">Connecting to VNC server...</p>
            </div>
          </div>
        )}

        {session.connectionState === 'error' && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900 z-10">
            <div className="text-center max-w-md">
              <WifiOff className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-200 mb-2">Connection Failed</h3>
              <p className="text-gray-400 mb-4">
                Unable to connect to the VNC server. Please check your network connection and try again.
              </p>
              <button
                onClick={handleReconnect}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Reconnect
              </button>
            </div>
          </div>
        )}

        {session.connectionState === 'disconnected' && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900 z-10">
            <div className="text-center max-w-md">
              <WifiOff className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-200 mb-2">Not Connected</h3>
              <p className="text-gray-400 mb-4">
                The VNC workspace is not connected. Click the button below to establish a connection.
              </p>
              <button
                onClick={handleReconnect}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Connect
              </button>
            </div>
          </div>
        )}

        {/* VNC Container */}
        <div
          ref={localContainerRef}
          className={`w-full h-full ${!session.isConnected ? 'opacity-0' : 'opacity-100'} ${hasControl ? 'cursor-auto' : 'cursor-not-allowed'}`}
          style={{
            transform: `scale(${localScale})`,
            transformOrigin: 'center center'
          }}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseMove={handleMouseMove}
          onWheel={handleWheel}
          onContextMenu={(e) => e.preventDefault()} // Prevent context menu
          tabIndex={0} // Make focusable for keyboard events
          autoFocus
        />

        {/* Zoom indicator */}
        {localScale !== 1.0 && (
          <div className="absolute bottom-4 right-4 px-2 py-1 bg-gray-800 text-gray-300 text-xs rounded">
            {Math.round(localScale * 100)}%
          </div>
        )}
      </div>

      {/* Footer with connection info */}
      {session.isConnected && (
        <div className="px-4 py-2 bg-gray-800 border-t border-gray-700">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <div className="flex items-center space-x-4">
              <span>Host: {config.host}:{config.port}</span>
              <span>Quality: {qualitySettings.quality}/9</span>
              <span>Compression: {qualitySettings.compression}/9</span>
            </div>
            <div className="flex items-center space-x-4">
              <span>Frame Rate: {session.metrics.frameRate} fps</span>
              <span>Bandwidth: {Math.round(session.metrics.bandwidth)} kbps</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};