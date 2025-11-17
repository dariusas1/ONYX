'use client';

import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { RFB } from 'novnc-client';
import type {
  WorkspaceContextType,
  WorkspaceSession,
  VNCConnectionConfig,
  VNCQualitySettings,
  ControlRequest,
  ConnectionMetrics,
  WorkspaceViewMode
} from '@/lib/types/workspace';

// Initial state
const initialSession: WorkspaceSession = {
  id: '',
  isConnected: false,
  hasControl: false,
  controlOwner: 'agent',
  connectionState: 'disconnected',
  lastActivity: new Date(),
  latency: 0,
  connectionQuality: 'excellent'
};

const initialConfig: VNCConnectionConfig = {
  host: window.location.hostname,
  port: 6080,
  path: '/websockify',
  encrypt: window.location.protocol === 'https:',
  resizeSession: true
};

const initialQualitySettings: VNCQualitySettings = {
  quality: 6,
  compression: 2,
  scaleLevel: 1.0
};

const initialMetrics: ConnectionMetrics = {
  roundTripTime: 0,
  bandwidth: 0,
  frameRate: 0,
  droppedFrames: 0,
  totalBytes: 0
};

// Action types
type WorkspaceAction =
  | { type: 'SET_CONNECTION_STATE'; payload: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error' }
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'SET_CONTROL_OWNER'; payload: 'agent' | 'founder' | null }
  | { type: 'SET_HAS_CONTROL'; payload: boolean }
  | { type: 'SET_LATENCY'; payload: number }
  | { type: 'SET_CONNECTION_QUALITY'; payload: 'excellent' | 'good' | 'poor' | 'terrible' }
  | { type: 'SET_QUALITY_SETTINGS'; payload: Partial<VNCQualitySettings> }
  | { type: 'SET_VIEW_MODE'; payload: WorkspaceViewMode }
  | { type: 'TOGGLE_WORKSPACE' }
  | { type: 'TOGGLE_QUALITY_CONTROLS' }
  | { type: 'TOGGLE_CONNECTION_STATUS' }
  | { type: 'SET_PENDING_CONTROL_REQUEST'; payload: ControlRequest | null }
  | { type: 'UPDATE_METRICS'; payload: Partial<ConnectionMetrics> }
  | { type: 'RESET_SESSION' };

// Reducer
interface WorkspaceState {
  session: WorkspaceSession;
  config: VNCConnectionConfig;
  qualitySettings: VNCQualitySettings;
  viewMode: WorkspaceViewMode;
  isWorkspaceOpen: boolean;
  showQualityControls: boolean;
  showConnectionStatus: boolean;
  pendingControlRequest: ControlRequest | null;
  metrics: ConnectionMetrics;
}

const workspaceReducer = (state: WorkspaceState, action: WorkspaceAction): WorkspaceState => {
  switch (action.type) {
    case 'SET_CONNECTION_STATE':
      return {
        ...state,
        session: {
          ...state.session,
          connectionState: action.payload,
          lastActivity: new Date()
        }
      };

    case 'SET_CONNECTED':
      return {
        ...state,
        session: {
          ...state.session,
          isConnected: action.payload,
          lastActivity: new Date()
        }
      };

    case 'SET_CONTROL_OWNER':
      return {
        ...state,
        session: {
          ...state.session,
          controlOwner: action.payload,
          hasControl: action.payload === 'founder',
          lastActivity: new Date()
        }
      };

    case 'SET_HAS_CONTROL':
      return {
        ...state,
        session: {
          ...state.session,
          hasControl: action.payload,
          lastActivity: new Date()
        }
      };

    case 'SET_LATENCY':
      return {
        ...state,
        session: {
          ...state.session,
          latency: action.payload,
          connectionQuality: action.payload < 100 ? 'excellent' :
                         action.payload < 200 ? 'good' :
                         action.payload < 500 ? 'poor' : 'terrible'
        }
      };

    case 'SET_CONNECTION_QUALITY':
      return {
        ...state,
        session: {
          ...state.session,
          connectionQuality: action.payload
        }
      };

    case 'SET_QUALITY_SETTINGS':
      return {
        ...state,
        qualitySettings: {
          ...state.qualitySettings,
          ...action.payload
        }
      };

    case 'SET_VIEW_MODE':
      return {
        ...state,
        viewMode: action.payload
      };

    case 'TOGGLE_WORKSPACE':
      return {
        ...state,
        isWorkspaceOpen: !state.isWorkspaceOpen
      };

    case 'TOGGLE_QUALITY_CONTROLS':
      return {
        ...state,
        showQualityControls: !state.showQualityControls
      };

    case 'TOGGLE_CONNECTION_STATUS':
      return {
        ...state,
        showConnectionStatus: !state.showConnectionStatus
      };

    case 'SET_PENDING_CONTROL_REQUEST':
      return {
        ...state,
        pendingControlRequest: action.payload
      };

    case 'UPDATE_METRICS':
      return {
        ...state,
        metrics: {
          ...state.metrics,
          ...action.payload
        }
      };

    case 'RESET_SESSION':
      return {
        ...state,
        session: { ...initialSession, id: state.session.id },
        pendingControlRequest: null,
        metrics: initialMetrics
      };

    default:
      return state;
  }
};

// Create context
const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

// Provider component
export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(workspaceReducer, {
    session: initialSession,
    config: initialConfig,
    qualitySettings: initialQualitySettings,
    viewMode: 'sidebar',
    isWorkspaceOpen: false,
    showQualityControls: false,
    showConnectionStatus: true,
    pendingControlRequest: null,
    metrics: initialMetrics
  });

  // Store RFB instance reference
  const rfbRef = React.useRef<RFB | null>(null);
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  // Performance monitoring state
  const frameRateRef = React.useRef<number>(0);
  const frameCountRef = React.useRef<number>(0);
  const lastFrameTimeRef = React.useRef<number>(Date.now());
  const bandwidthRef = React.useRef<number>(0);
  const lastBytesRef = React.useRef<number>(0);
  const frameRateIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  // Load saved settings from localStorage
  useEffect(() => {
    try {
      const savedQuality = localStorage.getItem('workspace-quality-settings');
      const savedViewMode = localStorage.getItem('workspace-view-mode');

      if (savedQuality) {
        dispatch({
          type: 'SET_QUALITY_SETTINGS',
          payload: JSON.parse(savedQuality)
        });
      }

      if (savedViewMode && ['sidebar', 'overlay', 'fullscreen'].includes(savedViewMode)) {
        dispatch({
          type: 'SET_VIEW_MODE',
          payload: savedViewMode as WorkspaceViewMode
        });
      }
    } catch (error) {
      console.warn('Failed to load workspace settings from localStorage:', error);
    }
  }, []);

  // Save quality settings to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('workspace-quality-settings', JSON.stringify(state.qualitySettings));
    } catch (error) {
      console.warn('Failed to save quality settings to localStorage:', error);
    }
  }, [state.qualitySettings]);

  // Save view mode to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('workspace-view-mode', state.viewMode);
    } catch (error) {
      console.warn('Failed to save view mode to localStorage:', error);
    }
  }, [state.viewMode]);

  // Performance monitoring functions
  const startPerformanceMonitoring = useCallback(() => {
    // Reset counters
    frameCountRef.current = 0;
    lastFrameTimeRef.current = Date.now();
    lastBytesRef.current = 0;

    // Start frame rate monitoring (calculate every second)
    frameRateIntervalRef.current = setInterval(() => {
      const now = Date.now();
      const deltaTime = (now - lastFrameTimeRef.current) / 1000; // seconds

      if (deltaTime > 0) {
        const currentFrameRate = frameCountRef.current / deltaTime;
        frameRateRef.current = Math.round(currentFrameRate);

        // Calculate bandwidth (simplified)
        const currentBandwidth = bandwidthRef.current;

        // Update metrics in state
        dispatch({
          type: 'UPDATE_METRICS',
          payload: {
            frameRate: frameRateRef.current,
            bandwidth: currentBandwidth,
            totalBytes: lastBytesRef.current
          }
        });

        // Reset counters for next interval
        frameCountRef.current = 0;
        lastFrameTimeRef.current = now;
        bandwidthRef.current = 0;

        // Quality adjustment based on performance
        adjustQualityBasedOnPerformance(currentFrameRate, currentBandwidth);
      }
    }, 1000);

    // Listen for frame updates from noVNC
    if (rfbRef.current) {
      rfbRef.current.addEventListener('fbframebufferupdate', () => {
        frameCountRef.current++;

        // Estimate bandwidth (simplified calculation)
        // In a real implementation, you'd track actual bytes transferred
        const estimatedFrameBytes = 1920 * 1080 * 4 / 10; // Rough estimate
        bandwidthRef.current += estimatedFrameBytes / 1024; // KB
        lastBytesRef.current += estimatedFrameBytes;
      });
    }
  }, []);

  const stopPerformanceMonitoring = useCallback(() => {
    if (frameRateIntervalRef.current) {
      clearInterval(frameRateIntervalRef.current);
      frameRateIntervalRef.current = null;
    }
  }, []);

  const adjustQualityBasedOnPerformance = useCallback((frameRate: number, bandwidth: number) => {
    const targetFrameRate = 30;
    const maxBandwidth = 5000; // 5 Mbps

    // Auto-adjust quality to maintain target performance
    if (frameRate < targetFrameRate * 0.8 || bandwidth > maxBandwidth) {
      // Performance is poor, reduce quality
      const newQuality = Math.min(state.qualitySettings.quality + 1, 9);
      const newCompression = Math.min(state.qualitySettings.compression + 1, 9);

      if (newQuality !== state.qualitySettings.quality ||
          newCompression !== state.qualitySettings.compression) {
        dispatch({
          type: 'SET_QUALITY_SETTINGS',
          payload: { quality: newQuality, compression: newCompression }
        });
        console.log(`Auto-adjusted quality for performance: Quality=${newQuality}, Compression=${newCompression}`);
      }
    } else if (frameRate > targetFrameRate * 1.2 && bandwidth < maxBandwidth * 0.7) {
      // Performance is good, can improve quality
      const newQuality = Math.max(state.qualitySettings.quality - 1, 0);
      const newCompression = Math.max(state.qualitySettings.compression - 1, 0);

      if (newQuality !== state.qualitySettings.quality ||
          newCompression !== state.qualitySettings.compression) {
        dispatch({
          type: 'SET_QUALITY_SETTINGS',
          payload: { quality: newQuality, compression: newCompression }
        });
        console.log(`Auto-improved quality: Quality=${newQuality}, Compression=${newCompression}`);
      }
    }
  }, [state.qualitySettings.quality, state.qualitySettings.compression]);

  // Latency measurement
  const measureLatency = useCallback(() => {
    const startTime = Date.now();

    // Send a small data packet to measure round-trip time
    if (rfbRef.current && state.session.isConnected) {
      // noVNC doesn't have a direct ping method, so we'll use a keyboard event
      // that should have minimal impact
      const originalFbsKeyEvent = rfbRef.current.sendKey;
      const pingKey = { keysym: 0, keyCode: 0 };

      // Override briefly to measure timing
      const measureStart = Date.now();
      rfbRef.current.sendKey(pingKey);
      const measureEnd = Date.now();

      const latency = measureEnd - measureStart;
      dispatch({ type: 'SET_LATENCY', payload: latency });
    }
  }, [state.session.isConnected]);

  // Auto-reconnect logic
  const reconnect = useCallback(async () => {
    if (state.session.connectionState !== 'disconnected') return;

    dispatch({ type: 'SET_CONNECTION_STATE', payload: 'reconnecting' });

    try {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds before reconnecting
      await connect();
    } catch (error) {
      console.error('Reconnection failed:', error);
      dispatch({ type: 'SET_CONNECTION_STATE', payload: 'error' });
    }
  }, [state.session.connectionState]);

  // Connection management
  const connect = useCallback(async () => {
    if (rfbRef.current) {
      rfbRef.current.disconnect();
    }

    dispatch({ type: 'SET_CONNECTION_STATE', payload: 'connecting' });

    try {
      const sessionId = `workspace-${Date.now()}`;
      dispatch({
        type: 'SET_CONNECTED',
        payload: false
      });

      if (containerRef.current) {
        // Determine WebSocket protocol based on current page protocol
        const wsProtocol = state.config.encrypt ? 'wss' : 'ws';
        const wsUrl = `${wsProtocol}://${state.config.host}:${state.config.port}${state.config.path}`;

        const rfb = new RFB(containerRef.current, wsUrl, {
          encrypt: state.config.encrypt,
          resizeSession: state.config.resizeSession,
          retry: true,
          retry_delay: 2000,
          // Add authentication token if available
          shared: true,
          local_cursor: true,
          dotCursor: false
        });

        rfbRef.current = rfb;

        rfb.addEventListener('connect', () => {
          dispatch({ type: 'SET_CONNECTED', payload: true });
          dispatch({ type: 'SET_CONNECTION_STATE', payload: 'connected' });
          console.log('VNC connected successfully');

          // Start performance monitoring
          startPerformanceMonitoring();
        });

        rfb.addEventListener('disconnect', () => {
          dispatch({ type: 'SET_CONNECTED', payload: false });
          dispatch({ type: 'SET_CONNECTION_STATE', payload: 'disconnected' });
          console.log('VNC disconnected');

          // Stop performance monitoring
          stopPerformanceMonitoring();
        });

        rfb.addEventListener('securityfailure', () => {
          dispatch({ type: 'SET_CONNECTION_STATE', payload: 'error' });
          console.error('VNC security failure');
        });

        rfb.addEventListener('credentialsrequired', () => {
          console.log('VNC credentials required - attempting JWT authentication');

          // Get authentication token from session storage or local storage
          const getAuthToken = () => {
            // Try NextAuth session first
            try {
              const sessionData = sessionStorage.getItem('next-auth.session-token');
              if (sessionData) return sessionData;
            } catch (e) {
              console.warn('Failed to get NextAuth session token:', e);
            }

            // Fallback to workspace-specific token
            try {
              const workspaceToken = localStorage.getItem('workspace-auth-token');
              if (workspaceToken) return workspaceToken;
            } catch (e) {
              console.warn('Failed to get workspace token:', e);
            }

            return null;
          };

          const authToken = getAuthToken();

          if (authToken) {
            // Send JWT token as VNC password
            rfb.sendCredentials({ password: authToken });
            console.log('Sent JWT authentication token to VNC server');
          } else {
            console.error('No authentication token available for VNC connection');
            dispatch({ type: 'SET_CONNECTION_STATE', payload: 'error' });
          }
        });

        rfb.addEventListener('serververification', () => {
          console.log('VNC server verification required - validating server certificate');

          // In production, implement proper server certificate validation
          // For now, we'll accept the connection but log the verification requirement
          if (state.config.encrypt) {
            console.warn('SECURITY: Implement proper server certificate validation for WSS connections');
          }
        });

        // Update quality settings when connected
        rfb.quality = state.qualitySettings.quality;
        rfb.compression = state.qualitySettings.compression;
        rfb.scale = state.qualitySettings.scaleLevel;
      }
    } catch (error) {
      console.error('Failed to connect to VNC server:', error);
      dispatch({ type: 'SET_CONNECTION_STATE', payload: 'error' });
      throw error;
    }
  }, [state.config, state.qualitySettings]);

  const disconnect = useCallback(() => {
    if (rfbRef.current) {
      rfbRef.current.disconnect();
      rfbRef.current = null;
    }
    dispatch({ type: 'RESET_SESSION' });
  }, []);

  // Control management
  const takeControl = useCallback(async (reason?: string) => {
    const request: ControlRequest = {
      id: `control-${Date.now()}`,
      requester: 'founder',
      timestamp: new Date(),
      reason,
      status: 'pending'
    };

    dispatch({ type: 'SET_PENDING_CONTROL_REQUEST', payload: request });

    try {
      const response = await fetch('/api/workspace/take-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          dispatch({ type: 'SET_CONTROL_OWNER', payload: 'founder' });
          dispatch({ type: 'SET_HAS_CONTROL', payload: true });
          dispatch({ type: 'SET_PENDING_CONTROL_REQUEST', payload: null });
        }
      } else {
        throw new Error('Failed to take control');
      }
    } catch (error) {
      console.error('Failed to take control:', error);
      dispatch({ type: 'SET_PENDING_CONTROL_REQUEST', payload: null });
      throw error;
    }
  }, []);

  const releaseControl = useCallback(async () => {
    try {
      const response = await fetch('/api/workspace/release-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        dispatch({ type: 'SET_CONTROL_OWNER', payload: 'agent' });
        dispatch({ type: 'SET_HAS_CONTROL', payload: false });
      } else {
        throw new Error('Failed to release control');
      }
    } catch (error) {
      console.error('Failed to release control:', error);
      throw error;
    }
  }, []);

  // Actions
  const updateQualitySettings = useCallback((settings: Partial<VNCQualitySettings>) => {
    dispatch({ type: 'SET_QUALITY_SETTINGS', payload: settings });

    if (rfbRef.current) {
      if (settings.quality !== undefined) {
        rfbRef.current.quality = settings.quality;
      }
      if (settings.compression !== undefined) {
        rfbRef.current.compression = settings.compression;
      }
      if (settings.scaleLevel !== undefined) {
        rfbRef.current.scale = settings.scaleLevel;
      }
    }
  }, []);

  const setViewMode = useCallback((mode: WorkspaceViewMode) => {
    dispatch({ type: 'SET_VIEW_MODE', payload: mode });
  }, []);

  const toggleWorkspace = useCallback(() => {
    dispatch({ type: 'TOGGLE_WORKSPACE' });
  }, []);

  const sendClipboardData = useCallback((data: string) => {
    if (rfbRef.current && state.session.isConnected) {
      rfbRef.current.clipboardPasteFrom(data);
    }
  }, [state.session.isConnected]);

  const requestScreenCapture = useCallback(async (): Promise<string> => {
    if (!rfbRef.current || !state.session.isConnected) {
      throw new Error('VNC not connected');
    }

    // noVNC doesn't have a built-in screenshot method
    // We'll need to implement this differently
    return new Promise((resolve, reject) => {
      // For now, return a placeholder
      reject(new Error('Screen capture not yet implemented'));
    });
  }, [state.session.isConnected]);

  // Periodic latency measurement
  useEffect(() => {
    if (state.session.isConnected) {
      const interval = setInterval(measureLatency, 5000); // Measure every 5 seconds
      return () => clearInterval(interval);
    }
  }, [state.session.isConnected, measureLatency]);

  // Auto-reconnect on disconnect
  useEffect(() => {
    if (state.session.connectionState === 'disconnected' && state.isWorkspaceOpen) {
      const timeout = setTimeout(reconnect, 3000);
      return () => clearTimeout(timeout);
    }
  }, [state.session.connectionState, state.isWorkspaceOpen, reconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPerformanceMonitoring();
      if (rfbRef.current) {
        rfbRef.current.disconnect();
      }
    };
  }, []);

  const contextValue: WorkspaceContextType = {
    ...state,
    connect,
    disconnect,
    takeControl,
    releaseControl,
    updateQualitySettings,
    setViewMode,
    toggleWorkspace,
    sendClipboardData,
    requestScreenCapture,
    containerRef,
    rfbRef
  };

  return (
    <WorkspaceContext.Provider value={contextValue}>
      {children}
    </WorkspaceContext.Provider>
  );
};

// Hook to use workspace context
export const useWorkspace = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};