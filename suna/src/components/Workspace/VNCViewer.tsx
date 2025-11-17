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

  // Handle keyboard events for VNC shortcuts
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!session.isConnected || !hasControl) return;

    // Handle common VNC shortcuts
    if (event.ctrlKey || event.metaKey) {
      switch (event.key) {
        case '+':
        case '=':
          // Zoom in
          setLocalScale(prev => Math.min(prev + 0.1, 2.0));
          event.preventDefault();
          break;
        case '-':
          // Zoom out
          setLocalScale(prev => Math.max(prev - 0.1, 0.5));
          event.preventDefault();
          break;
        case '0':
          // Reset zoom
          setLocalScale(1.0);
          event.preventDefault();
          break;
      }
    }
  }, [session.isConnected, hasControl]);

  // Add keyboard event listeners
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
          className={`w-full h-full ${!session.isConnected ? 'opacity-0' : 'opacity-100'}`}
          style={{
            transform: `scale(${localScale})`,
            transformOrigin: 'center center'
          }}
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