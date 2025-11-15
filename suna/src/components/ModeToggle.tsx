'use client'

import React, { useState } from 'react'
import { Settings, Bot, MessageSquare, ChevronDown, Shield } from 'lucide-react'

export type AgentMode = 'chat' | 'agent'

interface ModeToggleProps {
  currentMode: AgentMode
  onModeChange: (mode: AgentMode) => void
  disabled?: boolean
  showLabel?: boolean
  className?: string
}

export function ModeToggle({
  currentMode,
  onModeChange,
  disabled = false,
  showLabel = true,
  className = ''
}: ModeToggleProps) {
  const [isOpen, setIsOpen] = useState(false)

  const modes = [
    {
      value: 'chat' as AgentMode,
      label: 'Chat Mode',
      icon: MessageSquare,
      description: 'Interactive conversation mode',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50 hover:bg-blue-100'
    },
    {
      value: 'agent' as AgentMode,
      label: 'Agent Mode',
      icon: Bot,
      description: 'Autonomous agent execution mode',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50 hover:bg-purple-100'
    }
  ]

  const currentModeConfig = modes.find(mode => mode.value === currentMode)

  const handleModeSelect = (mode: AgentMode) => {
    if (mode !== currentMode) {
      onModeChange(mode)
    }
    setIsOpen(false)
  }

  return (
    <div className={`relative ${className}`}>
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200
          ${disabled
            ? 'bg-gray-100 text-gray-400 border-gray-300 cursor-not-allowed'
            : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400 hover:shadow-sm cursor-pointer'
          }
        `}
        aria-label={`Current mode: ${currentModeConfig?.label}. Click to change mode.`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        {currentModeConfig && (
          <>
            <currentModeConfig.icon className={`w-4 h-4 ${currentModeConfig.color}`} />
            {showLabel && (
              <span className="text-sm font-medium">{currentModeConfig.label}</span>
            )}
            <ChevronDown
              className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            />
          </>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Menu */}
          <div className="absolute top-full left-0 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
            <div className="p-2">
              <div className="flex items-center gap-2 px-3 py-2 mb-2">
                <Settings className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-semibold text-gray-700">Select Mode</span>
              </div>

              <div
                role="listbox"
                aria-label="Agent modes"
                className="space-y-1"
              >
                {modes.map((mode) => (
                  <button
                    key={mode.value}
                    role="option"
                    aria-selected={mode.value === currentMode}
                    onClick={() => handleModeSelect(mode.value)}
                    className={`
                      w-full flex items-center gap-3 px-3 py-3 rounded-md transition-colors duration-150
                      ${mode.value === currentMode
                        ? 'bg-blue-50 border border-blue-200'
                        : mode.bgColor
                      }
                    `}
                  >
                    <mode.icon className={`w-5 h-5 ${mode.color}`} />
                    <div className="flex-1 text-left">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${
                          mode.value === currentMode ? 'text-blue-900' : 'text-gray-900'
                        }`}>
                          {mode.label}
                        </span>
                        {mode.value === 'agent' && (
                          <Shield className="w-3 h-3 text-orange-500" title="Requires consent" />
                        )}
                      </div>
                      <p className={`text-xs ${
                        mode.value === currentMode ? 'text-blue-700' : 'text-gray-600'
                      }`}>
                        {mode.description}
                      </p>
                    </div>
                    {mode.value === currentMode && (
                      <div className="w-2 h-2 bg-blue-500 rounded-full" />
                    )}
                  </button>
                ))}
              </div>

              {/* Mode Info */}
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="px-3 py-2">
                  <p className="text-xs text-gray-600">
                    <strong>Current:</strong> {currentModeConfig?.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {currentMode === 'agent'
                      ? 'Agent mode can execute tasks autonomously. Enable with caution.'
                      : 'Chat mode requires your confirmation for each action.'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ModeToggle