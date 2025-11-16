'use client';

import React, { useState, useCallback } from 'react';
import { AlertTriangle } from 'lucide-react';
import { MessageList, Message } from './MessageList';
import { InputBox } from './InputBox';
import { useMode } from '../contexts/ModeContext';

export interface ChatInterfaceProps {
  conversationId?: string;
  className?: string;
}

export function ChatInterface({
  conversationId: _conversationId,
  className = '',
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  // Mode operations for Agent Mode functionality
  const { isAgentMode, isLoading } = useMode();

  // Get Agent Mode warning message
  const getAgentModeWarning = () => {
    return 'Agent will execute actions. Review approval gates.';
  };

  // Note: conversationId will be used in Story 2.3 for message persistence

  // Handle message submission
  // Note: Full streaming implementation will be added in Story 2.4
  const handleSubmit = useCallback(
    async (message: string) => {
      // Add user message to the list
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsStreaming(true);

      // Simulate streaming response (placeholder for Story 2.4)
      // In Story 2.4, this will be replaced with actual LiteLLM streaming
      setTimeout(() => {
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: `I received your message: "${message}". Full streaming and AI response functionality will be implemented in Story 2.4 (Message Streaming & Real-Time Response Display).`,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setIsStreaming(false);
      }, 1500);
    },
    []
  );

  return (
    <div className={`flex-1 flex flex-col ${className}`} role="main">
      {/* Agent Mode Warning Banner */}
      {isAgentMode && (
        <div
          className={`
            flex items-center gap-3 px-4 py-3 bg-yellow-500/10 border-b border-yellow-500/20
            transition-all duration-300 ease-in-out
            ${isLoading ? 'opacity-50' : 'opacity-100'}
          `}
          role="alert"
          aria-live="polite"
        >
          <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <span className="text-yellow-500 font-medium">
              {getAgentModeWarning()}
            </span>
          </div>
        </div>
      )}

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        className="flex-1"
      />
      <InputBox
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={isStreaming}
      />
    </div>
  );
}
