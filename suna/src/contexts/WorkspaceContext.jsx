'use client';

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { storage } from '../utils/storage';

// Action types for workspace state management
const WORKSPACE_ACTIONS = {
  TOGGLE_WORKSPACE: 'TOGGLE_WORKSPACE',
  SET_WORKSPACE_VISIBILITY: 'SET_WORKSPACE_VISIBILITY',
  SET_VNC_SETTINGS: 'SET_VNC_SETTINGS',
  UPDATE_VNC_SETTING: 'UPDATE_VNC_SETTING',
  SET_CONNECTION_STATE: 'SET_CONNECTION_STATE',
  SET_CONNECTION_ERROR: 'SET_CONNECTION_ERROR',
  CLEAR_CONNECTION_ERROR: 'CLEAR_CONNECTION_ERROR',
  LOAD_SETTINGS: 'LOAD_SETTINGS',
  SAVE_SETTINGS: 'SAVE_SETTINGS'
};

// Initial state
const initialState = {
  isWorkspaceVisible: false,
  isExpanded: false,
  vncSettings: {
    url: 'ws://localhost:6080',
    scale: true,
    quality: 6,
    compression: 1,
    autoConnect: true
  },
  connectionState: 'disconnected', // disconnected, connecting, connected, error
  connectionError: null,
  lastConnectedAt: null,
  connectionCount: 0
};

// Reducer for workspace state management
const workspaceReducer = (state, action) => {
  switch (action.type) {
    case WORKSPACE_ACTIONS.TOGGLE_WORKSPACE:
      return {
        ...state,
        isWorkspaceVisible: !state.isWorkspaceVisible
      };

    case WORKSPACE_ACTIONS.SET_WORKSPACE_VISIBILITY:
      return {
        ...state,
        isWorkspaceVisible: action.payload
      };

    case WORKSPACE_ACTIONS.SET_VNC_SETTINGS:
      return {
        ...state,
        vncSettings: {
          ...state.vncSettings,
          ...action.payload
        }
      };

    case WORKSPACE_ACTIONS.UPDATE_VNC_SETTING:
      return {
        ...state,
        vncSettings: {
          ...state.vncSettings,
          [action.payload.key]: action.payload.value
        }
      };

    case WORKSPACE_ACTIONS.SET_CONNECTION_STATE:
      return {
        ...state,
        connectionState: action.payload,
        connectionError: action.payload === 'connected' ? null : state.connectionError,
        lastConnectedAt: action.payload === 'connected' ? new Date().toISOString() : state.lastConnectedAt,
        connectionCount: action.payload === 'connected' ? state.connectionCount + 1 : state.connectionCount
      };

    case WORKSPACE_ACTIONS.SET_CONNECTION_ERROR:
      return {
        ...state,
        connectionState: 'error',
        connectionError: action.payload
      };

    case WORKSPACE_ACTIONS.CLEAR_CONNECTION_ERROR:
      return {
        ...state,
        connectionError: null
      };

    case WORKSPACE_ACTIONS.LOAD_SETTINGS:
      return {
        ...state,
        vncSettings: {
          ...state.vncSettings,
          ...action.payload
        }
      };

    case WORKSPACE_ACTIONS.SAVE_SETTINGS:
      // This action doesn't change state, just triggers save
      return state;

    default:
      return state;
  }
};

// Context creation
const WorkspaceContext = createContext();

// Custom provider component
export const WorkspaceProvider = ({ children }) => {
  const [state, dispatch] = useReducer(workspaceReducer, initialState);

  // Load workspace settings from localStorage on mount
  useEffect(() => {
    const loadWorkspaceSettings = () => {
      try {
        const savedSettings = storage.get('workspace_settings');
        if (savedSettings) {
          dispatch({
            type: WORKSPACE_ACTIONS.LOAD_SETTINGS,
            payload: savedSettings
          });
        }

        const savedVisibility = storage.get('workspace_visibility');
        if (savedVisibility !== null) {
          dispatch({
            type: WORKSPACE_ACTIONS.SET_WORKSPACE_VISIBILITY,
            payload: savedVisibility
          });
        }
      } catch (error) {
        console.warn('Failed to load workspace settings:', error);
      }
    };

    loadWorkspaceSettings();
  }, []);

  // Save workspace settings to localStorage when they change
  useEffect(() => {
    const saveWorkspaceSettings = () => {
      try {
        storage.set('workspace_settings', state.vncSettings);
        storage.set('workspace_visibility', state.isWorkspaceVisible);
      } catch (error) {
        console.warn('Failed to save workspace settings:', error);
      }
    };

    // Debounce save to avoid excessive writes
    const timeoutId = setTimeout(saveWorkspaceSettings, 500);
    return () => clearTimeout(timeoutId);
  }, [state.vncSettings, state.isWorkspaceVisible]);

  // Action creators
  const toggleWorkspace = () => {
    dispatch({ type: WORKSPACE_ACTIONS.TOGGLE_WORKSPACE });
  };

  const setWorkspaceVisibility = (visible) => {
    dispatch({
      type: WORKSPACE_ACTIONS.SET_WORKSPACE_VISIBILITY,
      payload: visible
    });
  };

  const setVncSettings = (settings) => {
    dispatch({
      type: WORKSPACE_ACTIONS.SET_VNC_SETTINGS,
      payload: settings
    });
  };

  const updateVncSetting = (key, value) => {
    dispatch({
      type: WORKSPACE_ACTIONS.UPDATE_VNC_SETTING,
      payload: { key, value }
    });
  };

  const setConnectionState = (connectionState) => {
    dispatch({
      type: WORKSPACE_ACTIONS.SET_CONNECTION_STATE,
      payload: connectionState
    });
  };

  const setConnectionError = (error) => {
    dispatch({
      type: WORKSPACE_ACTIONS.SET_CONNECTION_ERROR,
      payload: error
    });
  };

  const clearConnectionError = () => {
    dispatch({ type: WORKSPACE_ACTIONS.CLEAR_CONNECTION_ERROR });
  };

  // Computed values
  const isConnected = state.connectionState === 'connected';
  const isConnecting = state.connectionState === 'connecting';
  const hasError = state.connectionState === 'error';

  const value = {
    // State
    ...state,

    // Computed
    isConnected,
    isConnecting,
    hasError,

    // Actions
    toggleWorkspace,
    setWorkspaceVisibility,
    setVncSettings,
    updateVncSetting,
    setConnectionState,
    setConnectionError,
    clearConnectionError
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
};

// Custom hook for using workspace context
export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);

  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }

  return context;
};

// Export context for testing
export { WorkspaceContext };