'use client'

import { useState, useEffect, useCallback } from 'react'
import type { AgentMode } from '@/components/ModeToggle'

export interface AgentModeState {
  mode: AgentMode
  isEnabled: boolean
  hasAcceptedWarning: boolean
  consentTimestamp?: string
  lastModeChange?: string | null
}

interface UseAgentModeOptions {
  onModeChange?: (mode: AgentMode) => void
  onWarningAccept?: () => void
  onWarningReject?: () => void
  persistToStorage?: boolean
}

const STORAGE_KEY = 'agent-mode-settings'
const CONSENT_STORAGE_KEY = 'agent-mode-consent'

export function useAgentMode(options: UseAgentModeOptions = {}) {
  const {
    onModeChange,
    onWarningAccept,
    onWarningReject,
    persistToStorage = true
  } = options

  const [state, setState] = useState<AgentModeState>(() => {
    if (typeof window === 'undefined') {
      return {
        mode: 'chat',
        isEnabled: false,
        hasAcceptedWarning: false
      }
    }

    // Load from localStorage on mount
    if (persistToStorage) {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          return {
            mode: parsed.mode || 'chat',
            isEnabled: parsed.isEnabled || false,
            hasAcceptedWarning: parsed.hasAcceptedWarning || false,
            consentTimestamp: parsed.consentTimestamp,
            lastModeChange: parsed.lastModeChange
          }
        }
      } catch (error) {
        console.warn('Failed to load agent mode settings from localStorage:', error)
      }
    }

    return {
      mode: 'chat',
      isEnabled: false,
      hasAcceptedWarning: false
    }
  })

  // Save to localStorage when state changes
  useEffect(() => {
    if (persistToStorage && typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
      } catch (error) {
        console.warn('Failed to save agent mode settings to localStorage:', error)
      }
    }
  }, [state, persistToStorage])

  // Listen for storage events (cross-tab synchronization)
  useEffect(() => {
    if (typeof window === 'undefined' || !persistToStorage) return

    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY && event.newValue) {
        try {
          const newState = JSON.parse(event.newValue)
          setState(newState)
        } catch (error) {
          console.warn('Failed to parse agent mode settings from storage event:', error)
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [persistToStorage])

  const changeMode = useCallback((newMode: AgentMode) => {
    setState(prev => {
      const newState = {
        ...prev,
        mode: newMode,
        lastModeChange: new Date().toISOString()
      }

      // Call callback if provided
      if (onModeChange) {
        onModeChange(newMode)
      }

      return newState
    })
  }, [onModeChange])

  const enableAgentMode = useCallback(() => {
    setState(prev => {
      const newState = {
        ...prev,
        isEnabled: true,
        lastModeChange: new Date().toISOString()
      }

      if (onModeChange && prev.mode !== 'agent') {
        onModeChange('agent')
      }

      return newState
    })
  }, [onModeChange])

  const disableAgentMode = useCallback(() => {
    setState(prev => {
      const newState = {
        ...prev,
        isEnabled: false,
        mode: 'chat' as AgentMode,
        lastModeChange: new Date().toISOString()
      }

      if (onModeChange) {
        onModeChange('chat')
      }

      return newState
    })
  }, [onModeChange])

  const acceptWarning = useCallback(() => {
    setState(prev => {
      const newState = {
        ...prev,
        hasAcceptedWarning: true,
        consentTimestamp: new Date().toISOString()
      }

      if (onWarningAccept) {
        onWarningAccept()
      }

      return newState
    })
  }, [onWarningAccept])

  const rejectWarning = useCallback(() => {
    setState(prev => ({
      ...prev,
      hasAcceptedWarning: false,
      isEnabled: false,
      mode: 'chat' as AgentMode
    }))

    if (onWarningReject) {
      onWarningReject()
    }
  }, [onWarningReject])

  const resetSettings = useCallback(() => {
    const newState = {
      mode: 'chat' as AgentMode,
      isEnabled: false,
      hasAcceptedWarning: false
    }

    setState(newState)

    if (persistToStorage && typeof window !== 'undefined') {
      try {
        localStorage.removeItem(STORAGE_KEY)
        localStorage.removeItem(CONSENT_STORAGE_KEY)
      } catch (error) {
        console.warn('Failed to clear agent mode settings from localStorage:', error)
      }
    }
  }, [persistToStorage])

  const canUseAgentMode = state.isEnabled && state.hasAcceptedWarning

  // Audit logging function
  const logAudit = useCallback((action: string, details: any = {}) => {
    if (typeof window === 'undefined') return

    const auditEntry = {
      timestamp: new Date().toISOString(),
      action,
      details: {
        ...details,
        previousState: state,
        userAgent: navigator.userAgent,
        url: window.location.href
      }
    }

    // In a real implementation, this would send to your audit API
    console.log('Agent Mode Audit:', auditEntry)

    // Store audit log locally for debugging
    try {
      const auditKey = `agent-mode-audit-${Date.now()}`
      localStorage.setItem(auditKey, JSON.stringify(auditEntry))
    } catch (error) {
      console.warn('Failed to store audit entry:', error)
    }
  }, [state])

  // Log important state changes
  useEffect(() => {
    logAudit('state_change', { newState: state })
  }, [state, logAudit])

  return {
    // State
    mode: state.mode,
    isEnabled: state.isEnabled,
    hasAcceptedWarning: state.hasAcceptedWarning,
    consentTimestamp: state.consentTimestamp,
    lastModeChange: state.lastModeChange,
    canUseAgentMode,

    // Actions
    changeMode,
    enableAgentMode,
    disableAgentMode,
    acceptWarning,
    rejectWarning,
    resetSettings,

    // Utility
    logAudit
  }
}

export default useAgentMode