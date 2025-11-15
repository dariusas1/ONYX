'use client'

import React, { useState, useRef, useEffect } from 'react'
import { X, AlertTriangle, Shield, Eye, Clock, CheckCircle } from 'lucide-react'

interface AgentModeWarningProps {
  isOpen: boolean
  onClose: () => void
  onAccept: () => void
  onReject: () => void
  mode?: 'agent' | 'chat'
}

export function AgentModeWarning({
  isOpen,
  onClose,
  onAccept,
  onReject,
  mode = 'agent'
}: AgentModeWarningProps) {
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false)
  const [readingProgress, setReadingProgress] = useState(0)
  const contentRef = useRef<HTMLDivElement>(null)
  const scrollTimeoutRef = useRef<NodeJS.Timeout>()

  // Track reading progress
  useEffect(() => {
    const handleScroll = () => {
      if (contentRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = contentRef.current
        const progress = Math.min((scrollTop / (scrollHeight - clientHeight)) * 100, 100)
        setReadingProgress(progress)

        // Consider "scrolled to bottom" when 90% through
        setHasScrolledToBottom(progress >= 90)

        // Clear existing timeout
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current)
        }

        // Set new timeout to ensure user has time to read
        scrollTimeoutRef.current = setTimeout(() => {
          setHasScrolledToBottom(true)
        }, 2000)
      }
    }

    const element = contentRef.current
    if (element && isOpen) {
      element.addEventListener('scroll', handleScroll)
      return () => {
        element.removeEventListener('scroll', handleScroll)
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current)
        }
      }
    }
  }, [isOpen])

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setHasScrolledToBottom(false)
      setReadingProgress(0)
    }
  }, [isOpen])

  const handleAccept = () => {
    // Log consent acceptance
    const consentData = {
      timestamp: new Date().toISOString(),
      mode,
      readingProgress,
      userAgent: navigator.userAgent,
      consentVersion: '1.0'
    }

    console.log('Agent Mode Consent Accepted:', consentData)

    // Store consent in localStorage
    try {
      localStorage.setItem('agent-mode-consent', JSON.stringify(consentData))
    } catch (error) {
      console.warn('Failed to store consent data:', error)
    }

    onAccept()
    onClose()
  }

  const handleReject = () => {
    onReject()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Enable Agent Mode?
              </h2>
              <p className="text-sm text-gray-600">
                Important information about autonomous execution
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close warning"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div
          ref={contentRef}
          className="flex-1 overflow-y-auto p-6"
          role="document"
          tabIndex={0}
        >
          {/* Reading Progress Indicator */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Reading Progress</span>
              <span>{Math.round(readingProgress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${readingProgress}%` }}
              />
            </div>
          </div>

          {/* Warning Content */}
          <div className="prose prose-sm max-w-none">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-yellow-900 mb-1">
                    Agent Mode Capabilities
                  </h3>
                  <p className="text-yellow-800 text-sm">
                    When enabled, Agent Mode can execute tasks autonomously on your behalf,
                    including making API calls, analyzing data, and taking actions without
                    requiring explicit confirmation for each step.
                  </p>
                </div>
              </div>
            </div>

            <section className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Eye className="w-4 h-4" />
                What Agent Mode Can Do
              </h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>Analyze complex requests and break them into actionable steps</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>Execute multi-step workflows without manual intervention</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>Access external APIs and services when needed</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span>Make autonomous decisions within established boundaries</span>
                </li>
              </ul>
            </section>

            <section className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-600" />
                Important Considerations
              </h3>
              <div className="space-y-3 text-sm text-gray-700">
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                  <p className="font-medium text-orange-900 mb-1">Autonomous Actions</p>
                  <p className="text-orange-800">
                    Agent Mode will execute actions automatically. Monitor the activity
                    and disable the mode if unexpected behavior occurs.
                  </p>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="font-medium text-blue-900 mb-1">Data Privacy</p>
                  <p className="text-blue-800">
                    Agent actions are logged for transparency and security. Review audit
                    trails regularly to monitor activity.
                  </p>
                </div>
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <p className="font-medium text-purple-900 mb-1">Resource Usage</p>
                  <p className="text-purple-800">
                    Agent Mode may make more API calls and process more data than Chat Mode,
                    which could affect usage limits and costs.
                  </p>
                </div>
              </div>
            </section>

            <section className="mb-6">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Your Responsibilities
              </h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li>• Monitor agent activity and results</li>
                <li>• Verify important outputs before use</li>
                <li>• Disable Agent Mode if issues occur</li>
                <li>• Review audit logs regularly</li>
                <li>• Keep your authentication credentials secure</li>
              </ul>
            </section>

            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600 text-center">
                By proceeding, you acknowledge that you have read and understood
                the implications of enabling Agent Mode.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-4 p-6 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">
            {!hasScrolledToBottom && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Please review all information before proceeding
              </span>
            )}
            {hasScrolledToBottom && (
              <span className="flex items-center gap-1 text-green-600">
                <CheckCircle className="w-3 h-3" />
                You can now enable Agent Mode
              </span>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleReject}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleAccept}
              disabled={!hasScrolledToBottom}
              className={`
                px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200
                ${hasScrolledToBottom
                  ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }
              `}
            >
              Enable Agent Mode
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AgentModeWarning