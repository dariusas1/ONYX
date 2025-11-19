import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Monitor, Eye, EyeOff, Settings, X, ChevronLeft, ChevronRight, Smartphone, Tablet } from 'lucide-react';
import VNCViewer from '../VNCViewer/VNCViewer';

export const WorkspacePanel = ({
  isOpen = false,
  onToggle,
  className = '',
  vncUrl = 'ws://localhost:6080'
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const [vncSettings, setVncSettings] = useState({
    scale: true,
    quality: 6,
    compression: 1,
    autoConnect: true
  });

  const panelRef = useRef(null);

  // Detect device type for responsive design
  useEffect(() => {
    const checkDeviceType = () => {
      setIsMobile(window.innerWidth < 640);
      setIsTablet(window.innerWidth >= 640 && window.innerWidth < 1024);
    };

    checkDeviceType();
    window.addEventListener('resize', checkDeviceType);
    return () => window.removeEventListener('resize', checkDeviceType);
  }, []);

  // Handle VNC connection events
  const handleVNCConnect = useCallback(() => {
    console.log('VNC connected to workspace');
    // Auto-expand on mobile for better visibility
    if (isMobile) {
      setIsExpanded(true);
    }
  }, [isMobile]);

  const handleVNCDisconnect = useCallback((reason) => {
    console.log('VNC disconnected:', reason);
  }, []);

  const handleVNCError = useCallback((error) => {
    console.error('VNC connection error:', error);
  }, []);

  // Toggle panel expansion with responsive behavior
  const toggleExpansion = useCallback(() => {
    setIsExpanded(!isExpanded);
  }, [isExpanded]);

  // Handle setting changes
  const handleSettingChange = useCallback((key, value) => {
    setVncSettings(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  // Get responsive panel width classes
  const getPanelWidthClasses = useCallback(() => {
    if (isMobile || isTablet) {
      return 'w-full'; // Full width on mobile and tablet
    }
    return isExpanded ? 'w-1/2' : 'w-[30%]'; // Desktop sizes
  }, [isMobile, isTablet, isExpanded]);

  // Get panel position classes
  const getPanelPositionClasses = useCallback(() => {
    return isOpen ? 'translate-x-0' : 'translate-x-full';
  }, [isOpen]);

  // Handle overlay click for mobile
  const handleOverlayClick = useCallback(() => {
    if (isMobile) {
      onToggle();
    }
  }, [isMobile, onToggle]);

  // Get device indicator
  const getDeviceIcon = useCallback(() => {
    if (isMobile) return <Smartphone className="w-3 h-3" />;
    if (isTablet) return <Tablet className="w-3 h-3" />;
    return null;
  }, [isMobile, isTablet]);

  return (
    <>
      {/* Workspace Toggle Button */}
      <div
        className={`
          fixed top-20 right-4 z-40 transition-transform duration-300
          ${isOpen ? (isMobile ? 'translate-x-0' : 'translate-x-[-35%]') : 'translate-x-0'}
        `}
      >
        <button
          onClick={onToggle}
          className={`
            flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg
            hover:bg-blue-600 transition-all duration-200 shadow-lg
            ${isOpen && !isMobile ? 'pr-6' : ''}
          `}
        >
          {isOpen ? (
            <>
              {getDeviceIcon()}
              <ChevronRight className="w-4 h-4" />
            </>
          ) : (
            <>
              <Monitor className="w-4 h-4" />
              <Eye className="w-4 h-4" />
              <span className="font-medium hidden sm:inline">Show Workspace</span>
              <span className="font-medium sm:hidden">Workspace</span>
            </>
          )}
        </button>
      </div>

      {/* Workspace Panel */}
      <div
        ref={panelRef}
        className={`
          fixed top-0 right-0 h-full bg-gray-900 shadow-2xl z-30
          transition-all duration-300 ease-in-out
          ${getPanelWidthClasses()} ${getPanelPositionClasses()} ${className}
          ${isMobile ? 'w-full' : ''}
        `}
      >
        {/* Panel Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <Monitor className="w-5 h-5 text-blue-400" />
            <h2 className="text-white font-semibold">Workspace</h2>
            <div className={`w-2 h-2 rounded-full ${isExpanded ? 'bg-yellow-400 animate-pulse' : 'bg-green-400 animate-pulse'}`} />
            {(isMobile || isTablet) && (
              <span className="text-xs text-gray-400">
                {isMobile ? 'Mobile' : 'Tablet'}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Settings Button */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title="Workspace Settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* Expand/Collapse Button - Only on desktop */}
            {!isMobile && (
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
              title="Hide Workspace"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Panel Content */}
        <div className="flex flex-col h-[calc(100%-73px)]">
          {/* Settings Panel */}
          {showSettings && (
            <div className="p-4 border-b border-gray-700 bg-gray-800/50">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4" />
                VNC Settings
              </h3>

              <div className="space-y-4">
                {/* Auto Connect Setting */}
                <div className="flex items-center justify-between">
                  <label className="text-gray-300 text-sm">Auto Connect</label>
                  <button
                    onClick={() => handleSettingChange('autoConnect', !vncSettings.autoConnect)}
                    className={`
                      relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${vncSettings.autoConnect ? 'bg-blue-500' : 'bg-gray-600'}
                    `}
                  >
                    <span
                      className={`
                        inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${vncSettings.autoConnect ? 'translate-x-6' : 'translate-x-1'}
                      `}
                    />
                  </button>
                </div>

                {/* Scale Setting */}
                <div className="flex items-center justify-between">
                  <label className="text-gray-300 text-sm">Scale to Fit</label>
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

                {/* Quality Setting */}
                <div>
                  <label className="text-gray-300 text-sm block mb-2">
                    Quality: {vncSettings.quality}
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
                    <span>Low</span>
                    <span>High</span>
                  </div>
                </div>

                {/* Compression Setting */}
                <div>
                  <label className="text-gray-300 text-sm block mb-2">
                    Compression: {vncSettings.compression}
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
                    <span>Max</span>
                  </div>
                </div>

                {/* Touch Support Note */}
                {(isMobile || isTablet) && (
                  <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                    <p className="text-blue-400 text-xs">
                      <strong>Touch Controls:</strong> Tap, drag, and pinch to interact with the workspace.
                      {isMobile && ' Use the button below to minimize the panel for better visibility.'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VNC Viewer */}
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

          {/* Mobile Controls Footer */}
          {isMobile && (
            <div className="p-4 border-t border-gray-700 bg-gray-800/50">
              <div className="flex items-center justify-between">
                <div className="text-xs text-gray-400">
                  Touch gestures enabled
                </div>
                <button
                  onClick={toggleExpansion}
                  className="px-3 py-1 text-xs bg-gray-700 text-white rounded hover:bg-gray-600 transition-colors"
                >
                  {isExpanded ? 'Minimize' : 'Maximize'}
                </button>
              </div>
            </div>
          )}

          {/* Resize Handle - Desktop only */}
          {!isMobile && !isExpanded && (
            <div
              className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-16 bg-gray-600 cursor-ew-resize hover:bg-blue-500 transition-colors rounded-r"
              title="Drag to resize panel"
            />
          )}
        </div>
      </div>

      {/* Mobile/Tablet Overlay */}
      {(isMobile || isTablet) && isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20"
          onClick={handleOverlayClick}
        />
      )}
    </>
  );
};

export default WorkspacePanel;