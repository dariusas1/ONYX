import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Monitor, Eye, EyeOff, Settings, X, ChevronLeft, ChevronRight } from 'lucide-react';
import VNCViewer from '../VNCViewer/VNCViewer';
import { useWorkspace } from '../../contexts/WorkspaceContext';

export const WorkspacePanel = ({
  isOpen = false,
  onToggle,
  className = '',
  vncUrl = 'ws://localhost:6080'
}) => {
  // Use workspace context for state management
  const {
    isExpanded,
    vncSettings,
    isConnected,
    isConnecting,
    hasError,
    setWorkspaceVisibility,
    updateVncSetting,
    setConnectionState,
    setConnectionError
  } = useWorkspace();

  const [showSettings, setShowSettings] = useState(false);
  const [isTablet, setIsTablet] = useState(false);

  const panelRef = useRef(null);

  // Detect tablet viewport for responsive design
  useEffect(() => {
    const checkTabletViewport = () => {
      const width = window.innerWidth;
      setIsTablet(width >= 768 && width <= 1024);
    };

    checkTabletViewport();
    window.addEventListener('resize', checkTabletViewport);
    return () => window.removeEventListener('resize', checkTabletViewport);
  }, []);

  // Handle VNC connection events with context integration
  const handleVNCConnect = useCallback(() => {
    console.log('VNC connected to workspace');
    setConnectionState('connected');
    setConnectionError(null);
  }, [setConnectionState, setConnectionError]);

  const handleVNCDisconnect = useCallback((reason) => {
    console.log('VNC disconnected:', reason);
    setConnectionState('disconnected');
  }, [setConnectionState]);

  const handleVNCError = useCallback((error) => {
    console.error('VNC connection error:', error);
    setConnectionState('error');
    setConnectionError(error);
  }, [setConnectionState, setConnectionError]);

  // Toggle panel expansion with context integration
  const toggleExpansion = useCallback(() => {
    // This would need to be added to workspace context if we want to persist it
    // For now, using local state as it's UI preference, not workspace state
    setIsExpanded(prev => !prev);
  }, []);

  // Handle setting changes with context integration
  const handleSettingChange = useCallback((key, value) => {
    updateVncSetting(key, value);
  }, [updateVncSetting]);

  // Enhanced responsive panel width classes
  const getPanelWidthClasses = useCallback(() => {
    if (isTablet) {
      // Tablets always use full width or 2/3 for better touch interaction
      return isExpanded ? 'w-full' : 'w-2/3';
    }
    // Desktop uses 30% or 1/2 width
    return isExpanded ? 'w-1/2' : 'w-[30%]';
  }, [isTablet, isExpanded]);

  const panelWidthClasses = getPanelWidthClasses();
  const panelPositionClasses = isOpen ? 'translate-x-0' : 'translate-x-full';

  // Handle escape key to close panel
  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === 'Escape' && isOpen && !isTablet) {
        onToggle?.();
      }
    };

    document.addEventListener('keydown', handleEscKey);
    return () => document.removeEventListener('keydown', handleEscKey);
  }, [isOpen, isTablet, onToggle]);

  return (
    <>
      {/* Enhanced Workspace Toggle Button */}
      <div
        className={`
          fixed top-20 right-4 z-40 transition-all duration-300
          ${isOpen ? (isTablet ? 'translate-x-[-80%]' : 'translate-x-[-35%]') : 'translate-x-0'}
        `}
      >
        <button
          onClick={onToggle}
          className={`
            flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg
            hover:bg-blue-600 transition-all duration-200 shadow-lg
            ${isOpen ? (isTablet ? 'pr-2' : 'pr-6') : ''}
            ${isTablet && isOpen ? 'pl-2' : ''}
          `}
        >
          {isOpen ? (
            <>
              {isTablet ? <ChevronRight className="w-4 h-4" /> : null}
              <span className="font-medium hidden sm:inline">Hide</span>
            </>
          ) : (
            <>
              <Monitor className="w-4 h-4" />
              {!isTablet && <Eye className="w-4 h-4" />}
              {!isTablet && <span className="font-medium">Show Workspace</span>}
            </>
          )}
        </button>
      </div>

      {/* Enhanced Workspace Panel */}
      <div
        ref={panelRef}
        className={`
          fixed top-0 right-0 h-full bg-gray-900 shadow-2xl z-30
          transition-all duration-300 ease-in-out
          ${panelWidthClasses} ${panelPositionClasses} ${className}
          ${isTablet ? 'rounded-l-lg' : ''}
        `}
      >
        {/* Enhanced Panel Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <Monitor className="w-5 h-5 text-blue-400" />
            <h2 className="text-white font-semibold">Workspace</h2>
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400 animate-pulse' :
              isConnecting ? 'bg-yellow-400 animate-pulse' :
              hasError ? 'bg-red-400' : 'bg-gray-400'
            }`} />
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            {/* Connection Status Quick Indicator */}
            {(isTablet || isExpanded) && (
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                isConnected ? 'bg-green-500/20 text-green-400' :
                isConnecting ? 'bg-yellow-500/20 text-yellow-400' :
                hasError ? 'bg-red-500/20 text-red-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : hasError ? 'Error' : 'Offline'}
              </div>
            )}

            {/* Settings Button */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`
                p-2 rounded-lg transition-colors
                ${showSettings ?
                  'text-white bg-blue-600 hover:bg-blue-700' :
                  'text-gray-400 hover:text-white hover:bg-gray-800'
                }
              `}
              title="Workspace Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* Expand/Collapse Button - hide on tablets for better UX */}
            {!isTablet && (
              <button
                onClick={toggleExpansion}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                title={isExpanded ? "Collapse Panel" : "Expand Panel"}
              >
                {isExpanded ? (
                  <ChevronRight className="w-4 h-4" />
                ) : (
                  <ChevronLeft className="w-4 h-4" />
                )}
              </button>
            )}

            {/* Close Button */}
            <button
              onClick={onToggle}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title={`Hide Workspace${isTablet ? ' (ESC)' : ''}`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Panel Content */}
        <div className="flex flex-col h-[calc(100%-73px)]">
          {/* Enhanced Settings Panel with context integration */}
          {showSettings && (
            <div className="p-4 border-b border-gray-700 bg-gray-800/50">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4" />
                VNC Settings
              </h3>

              <div className="space-y-4">
                {/* Scale Setting */}
                <div className="flex items-center justify-between">
                  <label className="text-gray-300 text-sm">
                    Scale to Fit
                    <span className="block text-gray-500 text-xs mt-1">
                      Better for {isTablet ? 'tablet' : 'desktop'} viewing
                    </span>
                  </label>
                  <button
                    onClick={() => handleSettingChange('scale', !vncSettings.scale)}
                    className={`
                      relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${vncSettings.scale ? 'bg-blue-500' : 'bg-gray-600'}
                    `}
                  >
                    <span
                      className={`
                        inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${vncSettings.scale ? 'translate-x-6' : 'translate-x-1'}
                      `}
                    />
                  </button>
                </div>

                {/* Quality Setting with descriptions */}
                <div>
                  <label className="text-gray-300 text-sm block mb-2">
                    Quality: {vncSettings.quality}/9
                    <span className="block text-gray-500 text-xs mt-1">
                      Higher quality = more bandwidth
                    </span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="9"
                    value={vncSettings.quality}
                    onChange={(e) => handleSettingChange('quality', parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Fast</span>
                    <span>Balanced</span>
                    <span>High</span>
                  </div>
                </div>

                {/* Compression Setting with descriptions */}
                <div>
                  <label className="text-gray-300 text-sm block mb-2">
                    Compression: {vncSettings.compression}/9
                    <span className="block text-gray-500 text-xs mt-1">
                      Higher compression = less bandwidth
                    </span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="9"
                    value={vncSettings.compression}
                    onChange={(e) => handleSettingChange('compression', parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>None</span>
                    <span>Medium</span>
                    <span>Max</span>
                  </div>
                </div>

                {/* Connection Info */}
                {isConnected && (
                  <div className="pt-2 border-t border-gray-700">
                    <div className="text-xs text-gray-400">
                      <div className="flex justify-between mb-1">
                        <span>Server:</span>
                        <span className="text-gray-300">{vncUrl}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Status:</span>
                        <span className="text-green-400">Connected</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Enhanced VNC Viewer */}
          <div className="flex-1 relative overflow-hidden">
            <VNCViewer
              url={vncUrl}
              onConnect={handleVNCConnect}
              onDisconnect={handleVNCDisconnect}
              onError={handleVNCError}
              scale={vncSettings.scale}
              quality={vncSettings.quality}
              compression={vncSettings.compression}
              className="w-full h-full"
            />
          </div>
        </div>

        {/* Enhanced Resize Handle - only on desktop */}
        {!isExpanded && !isTablet && (
          <div
            className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-16 bg-gray-600 cursor-ew-resize hover:bg-blue-500 transition-colors rounded-r"
            title="Drag to resize panel"
          />
        )}
      </div>

      {/* Enhanced Overlay for responsive design */}
      {isOpen && (
        <div
          className={`fixed inset-0 z-20 transition-opacity duration-300 ${
            isTablet ? 'bg-black/50' : 'lg:hidden bg-black/50'
          }`}
          onClick={onToggle}
        />
      )}
    </>
  );
};

export default WorkspacePanel;