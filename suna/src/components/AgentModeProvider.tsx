'use client'

import React, { createContext, useContext, ReactNode } from 'react'
import useAgentMode, { type AgentMode, type UseAgentModeOptions } from '@/hooks/useAgentMode'

interface AgentModeContextValue {
  mode: AgentMode
  isEnabled: boolean
  hasAcceptedWarning: boolean
  consentTimestamp?: string
  lastModeChange?: string | null
  canUseAgentMode: boolean
  changeMode: (mode: AgentMode) => void
  enableAgentMode: () => void
  disableAgentMode: () => void
  acceptWarning: () => void
  rejectWarning: () => void
  resetSettings: () => void
}

const AgentModeContext = createContext<AgentModeContextValue | undefined>(undefined)

interface AgentModeProviderProps {
  children: ReactNode
  options?: UseAgentModeOptions
}

export function AgentModeProvider({ children, options = {} }: AgentModeProviderProps) {
  const agentMode = useAgentMode(options)

  const contextValue: AgentModeContextValue = {
    mode: agentMode.mode,
    isEnabled: agentMode.isEnabled,
    hasAcceptedWarning: agentMode.hasAcceptedWarning,
    consentTimestamp: agentMode.consentTimestamp,
    lastModeChange: agentMode.lastModeChange,
    canUseAgentMode: agentMode.canUseAgentMode,
    changeMode: agentMode.changeMode,
    enableAgentMode: agentMode.enableAgentMode,
    disableAgentMode: agentMode.disableAgentMode,
    acceptWarning: agentMode.acceptWarning,
    rejectWarning: agentMode.rejectWarning,
    resetSettings: agentMode.resetSettings
  }

  return (
    <AgentModeContext.Provider value={contextValue}>
      {children}
    </AgentModeContext.Provider>
  )
}

export function useAgentModeContext() {
  const context = useContext(AgentModeContext)
  if (context === undefined) {
    throw new Error('useAgentModeContext must be used within an AgentModeProvider')
  }
  return context
}

export default AgentModeProvider