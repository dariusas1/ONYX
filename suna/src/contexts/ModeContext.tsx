import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { storage } from '../utils/storage';
import { SettingsService } from '../services/settingsService';

// Type definitions
type Mode = 'chat' | 'agent';
type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

interface ModeState {
  currentMode: Mode;
  isLoading: boolean;
  syncStatus: SyncStatus;
  error: string | null;
  lastSyncTime: string | null;
}

interface ModeContextValue extends ModeState {
  isAgentMode: boolean;
  isChatMode: boolean;
  canSync: boolean;
  toggleMode: () => void;
  setMode: (mode: Mode) => void;
  clearError: () => void;
}

type ModeAction =
  | { type: 'TOGGLE_MODE' }
  | { type: 'SET_MODE'; payload: Mode }
  | { type: 'MODE_CHANGE_SUCCESS' }
  | { type: 'MODE_CHANGE_ERROR'; payload: string }
  | { type: 'SYNC_SUCCESS' }
  | { type: 'SYNC_ERROR'; payload: string };

// Action types for mode management
const MODE_ACTIONS = {
  TOGGLE_MODE: 'TOGGLE_MODE',
  SET_MODE: 'SET_MODE',
  MODE_CHANGE_SUCCESS: 'MODE_CHANGE_SUCCESS',
  MODE_CHANGE_ERROR: 'MODE_CHANGE_ERROR',
  SYNC_SUCCESS: 'SYNC_SUCCESS',
  SYNC_ERROR: 'SYNC_ERROR'
};

// Initial state
const initialState: ModeState = {
  currentMode: 'chat',
  isLoading: false,
  syncStatus: 'idle',
  error: null,
  lastSyncTime: null
};

// Reducer for mode state management
const modeReducer = (state: ModeState, action: ModeAction): ModeState => {
  switch (action.type) {
    case MODE_ACTIONS.TOGGLE_MODE:
      return {
        ...state,
        currentMode: state.currentMode === 'chat' ? 'agent' : 'chat',
        syncStatus: 'syncing',
        error: null
      };

    case MODE_ACTIONS.SET_MODE:
      return {
        ...state,
        currentMode: action.payload,
        syncStatus: 'syncing',
        error: null
      };

    case MODE_ACTIONS.MODE_CHANGE_SUCCESS:
      return {
        ...state,
        syncStatus: 'success',
        lastSyncTime: new Date().toISOString()
      };

    case MODE_ACTIONS.MODE_CHANGE_ERROR:
      return {
        ...state,
        syncStatus: 'error',
        error: action.payload
      };

    case MODE_ACTIONS.SYNC_SUCCESS:
      return {
        ...state,
        syncStatus: 'success',
        error: null,
        lastSyncTime: new Date().toISOString()
      };

    case MODE_ACTIONS.SYNC_ERROR:
      return {
        ...state,
        syncStatus: 'error',
        error: action.payload
      };

    default:
      return state;
  }
};

// Context creation
const ModeContext = createContext<ModeContextValue | undefined>(undefined);

// Custom provider component
export const ModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(modeReducer, initialState);

  // Load mode from localStorage on mount
  useEffect(() => {
    const loadInitialMode = async () => {
      try {
        const savedMode = storage.get('agent_mode');
        if (savedMode && ['chat', 'agent'].includes(savedMode)) {
          dispatch({ type: MODE_ACTIONS.SET_MODE, payload: savedMode });
        }

        // Try to sync with cloud if available
        const cloudSettings = await SettingsService.loadFromCloud();
        if (cloudSettings.success && cloudSettings.settings.agent_mode && cloudSettings.settings.agent_mode !== savedMode) {
          // Cloud preference takes precedence
          dispatch({ type: MODE_ACTIONS.SET_MODE, payload: cloudSettings.settings.agent_mode });
          storage.set('agent_mode', cloudSettings.settings.agent_mode);
        }
      } catch (error) {
        console.warn('Failed to load mode preference:', error);
      }
    };

    loadInitialMode();
  }, []);

  // Sync mode changes to localStorage and Supabase
  useEffect(() => {
    const syncMode = async () => {
      if (state.syncStatus === 'syncing') {
        try {
          // Immediate localStorage save
          storage.set('agent_mode', state.currentMode);

          // Async cloud sync
          await SettingsService.setSetting('agent_mode', state.currentMode);

          dispatch({ type: MODE_ACTIONS.MODE_CHANGE_SUCCESS });
        } catch (error) {
          console.error('Failed to sync mode preference:', error);
          dispatch({
            type: MODE_ACTIONS.MODE_CHANGE_ERROR,
            payload: error.message
          });

          // Optimistic rollback on sync failure
          const fallbackMode = storage.get('agent_mode');
          if (fallbackMode && fallbackMode !== state.currentMode) {
            dispatch({ type: MODE_ACTIONS.SET_MODE, payload: fallbackMode });
          }
        }
      }
    };

    syncMode();
  }, [state.currentMode, state.syncStatus]);

  // Action handlers
  const toggleMode = () => {
    dispatch({ type: MODE_ACTIONS.TOGGLE_MODE });
  };

  const setMode = (mode: Mode) => {
    if (['chat', 'agent'].includes(mode)) {
      dispatch({ type: MODE_ACTIONS.SET_MODE, payload: mode });
    }
  };

  const clearError = () => {
    dispatch({ type: MODE_ACTIONS.SYNC_ERROR, payload: null });
  };

  // Computed values
  const isAgentMode = state.currentMode === 'agent';
  const isChatMode = state.currentMode === 'chat';
  const canSync = state.syncStatus !== 'syncing';

  const value = {
    // State
    ...state,

    // Computed
    isAgentMode,
    isChatMode,
    canSync,

    // Actions
    toggleMode,
    setMode,
    clearError
  };

  return (
    <ModeContext.Provider value={value}>
      {children}
    </ModeContext.Provider>
  );
};

// Custom hook for using mode context
export const useMode = (): ModeContextValue => {
  const context = useContext(ModeContext);

  if (!context) {
    throw new Error('useMode must be used within a ModeProvider');
  }

  return context;
};

// Export context for testing
export { ModeContext };