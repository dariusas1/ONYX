import { useMode } from '../contexts/ModeContext';

/**
 * Custom hook for easy mode operations and computed values
 * Provides a simplified interface for working with mode state
 */
export const useModeHook = () => {
  const {
    currentMode,
    isAgentMode,
    isChatMode,
    isLoading,
    syncStatus,
    error,
    lastSyncTime,
    canSync,
    toggleMode,
    setMode,
    clearError
  } = useMode();

  return {
    // Current mode state
    currentMode,
    isAgentMode,
    isChatMode,

    // UI state
    isLoading,
    syncStatus,
    error,
    lastSyncTime,
    canSync,

    // Mode actions
    toggleMode,
    setMode,
    clearError,

    // Convenience methods
    enableAgentMode: () => setMode('agent'),
    enableChatMode: () => setMode('chat'),

    // Computed states
    isSyncing: syncStatus === 'syncing',
    hasError: syncStatus === 'error',
    isSynced: syncStatus === 'success',

    // Mode-specific configurations
    modeConfig: {
      chat: {
        label: 'Chat Mode',
        description: 'Advisory mode for conversations and guidance',
        color: 'blue',
        icon: 'MessageSquare'
      },
      agent: {
        label: 'Agent Mode',
        description: 'Execution mode for autonomous task completion',
        color: 'orange',
        icon: 'Bot'
      }
    },

    // Current mode configuration
    currentConfig: isAgentMode
      ? {
          label: 'Agent Mode',
          description: 'Execution mode for autonomous task completion',
          color: 'orange',
          icon: 'Bot'
        }
      : {
          label: 'Chat Mode',
          description: 'Advisory mode for conversations and guidance',
          color: 'blue',
          icon: 'MessageSquare'
        }
  };
};

// Export with a more common name
export default useModeHook;