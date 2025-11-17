'use client';

import React, { useEffect } from 'react';
import {
  X,
  Minimize2,
  Maximize2,
  Settings,
  Wifi,
  Monitor,
  Layers
} from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { VNCViewer } from './VNCViewer';
import { ConnectionStatus } from './ConnectionStatus';
import { ControlOverlay } from './ControlOverlay';
import { QualityControls } from './QualityControls';

interface WorkspacePanelProps {
  className?: string;
}

export const WorkspacePanel: React.FC<WorkspacePanelProps> = ({ className = '' }) => {
  const {
    session,
    viewMode,
    isWorkspaceOpen,
    showQualityControls,
    showConnectionStatus,
    toggleWorkspace,
    setViewMode,
    toggleQualityControls,
    toggleConnectionStatus
  } = useWorkspace();

  // Close workspace on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isWorkspaceOpen) {
        toggleWorkspace();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isWorkspaceOpen, toggleWorkspace]);

  if (!isWorkspaceOpen) {
    return null;
  }

  const getViewModeClasses = () => {
    switch (viewMode) {
      case 'overlay':
        return 'fixed inset-4 z-50 bg-gray-900/95 backdrop-blur-sm border border-gray-700 rounded-lg';
      case 'fullscreen':
        return 'fixed inset-0 z-50 bg-gray-900';
      case 'sidebar':
      default:
        return 'fixed right-0 top-0 h-full w-1/3 bg-gray-900 border-l border-gray-700 z-40';
    }
  };

  const getHeaderPosition = () => {
    switch (viewMode) {
      case 'overlay':
      case 'fullscreen':
        return 'absolute top-0 left-0 right-0';
      case 'sidebar':
      default:
        return 'relative';
    }
  };

  const getContentClasses = () => {
    const base = 'flex flex-col h-full';

    if (viewMode === 'sidebar') {
      return `${base} w-full`;
    }

    return `${base} w-full h-full`;
  };

  return (
    <div className={`${getViewModeClasses()} ${className}`}>
      {/* Header */}
      <div className={`${getHeaderPosition()} bg-gray-800 border-b border-gray-700 z-10`}>
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center space-x-3">
            <Monitor className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-gray-200">VNC Workspace</h2>
            {session.isConnected && (
              <div className={`w-2 h-2 rounded-full ${
                session.connectionQuality === 'excellent' ? 'bg-green-500' :
                session.connectionQuality === 'good' ? 'bg-yellow-500' :
                session.connectionQuality === 'poor' ? 'bg-orange-500' : 'bg-red-500'
              }`} />
            )}
          </div>

          <div className="flex items-center space-x-2">
            {/* View Mode Toggle */}
            <div className="flex items-center space-x-1 bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setViewMode('sidebar')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'sidebar' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
                title="Sidebar view"
              >
                <Layers className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('overlay')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'overlay' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
                title="Overlay view"
              >
                <Monitor className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('fullscreen')}
                className={`p-1.5 rounded transition-colors ${
                  viewMode === 'fullscreen' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
                title="Fullscreen view"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>

            {/* Status Indicators */}
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleConnectionStatus}
                className={`p-1.5 rounded transition-colors ${
                  showConnectionStatus ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
                title="Connection status"
              >
                <Wifi className="w-4 h-4" />
              </button>
              <button
                onClick={toggleQualityControls}
                className={`p-1.5 rounded transition-colors ${
                  showQualityControls ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                }`}
                title="Quality settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>

            {/* Close Button */}
            <button
              onClick={toggleWorkspace}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
              title="Close workspace (Escape)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className={getContentClasses()} style={{ marginTop: viewMode !== 'sidebar' ? '60px' : '0' }}>
        {viewMode === 'sidebar' ? (
          // Sidebar Layout - Single column
          <div className="flex-1 flex flex-col">
            <VNCViewer />

            {/* Collapsible Panels */}
            <div className="border-t border-gray-700">
              {/* Control Overlay */}
              <div className="p-4">
                <ControlOverlay />
              </div>

              {/* Connection Status */}
              {showConnectionStatus && (
                <div className="px-4 pb-4">
                  <ConnectionStatus />
                </div>
              )}

              {/* Quality Controls */}
              {showQualityControls && (
                <div className="px-4 pb-4">
                  <QualityControls />
                </div>
              )}
            </div>
          </div>
        ) : (
          // Overlay/Fullscreen Layout - Split view
          <div className="flex-1 flex">
            {/* VNC Viewer - Main Area */}
            <div className="flex-1 relative">
              <VNCViewer />
            </div>

            {/* Side Panel */}
            <div className="w-80 border-l border-gray-700 overflow-y-auto">
              <div className="p-4 space-y-4">
                {/* Control Overlay */}
                <ControlOverlay />

                {/* Connection Status */}
                {showConnectionStatus && (
                  <ConnectionStatus />
                )}

                {/* Quality Controls */}
                {showQualityControls && (
                  <QualityControls />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mobile Overlay Controls */}
      {viewMode === 'overlay' && (
        <div className="absolute bottom-4 left-4 right-4 flex justify-between">
          <div className="flex items-center space-x-2 bg-gray-800/90 backdrop-blur-sm rounded-lg px-3 py-2">
            <Monitor className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-300">
              {session.isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <div className="flex items-center space-x-2 bg-gray-800/90 backdrop-blur-sm rounded-lg px-3 py-2">
            <button
              onClick={() => setViewMode('sidebar')}
              className="p-1 text-gray-400 hover:text-white"
              title="Switch to sidebar"
            >
              <Minimize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {session.connectionState === 'connecting' && viewMode !== 'sidebar' && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 backdrop-blur-sm z-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-300">Connecting to workspace...</p>
          </div>
        </div>
      )}

      {/* Error Overlay */}
      {session.connectionState === 'error' && viewMode !== 'sidebar' && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 backdrop-blur-sm z-20">
          <div className="text-center max-w-md">
            <Wifi className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-200 mb-2">Connection Failed</h3>
            <p className="text-gray-400 mb-6">
              Unable to connect to the workspace. Please check your network connection and try again.
            </p>
            <div className="flex items-center justify-center space-x-4">
              <button
                onClick={() => setViewMode('sidebar')}
                className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600"
              >
                Switch to Sidebar
              </button>
              <button
                onClick={toggleWorkspace}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Close Workspace
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};