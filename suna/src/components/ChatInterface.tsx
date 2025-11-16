'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { MessageList, Message } from './MessageList';
import { InputBox } from './InputBox';
import { MemoryInjectionNotification, useMemoryInjectionNotification } from './MemoryInjectionNotification';
import { useMode } from '../contexts/ModeContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { WorkspacePanel } from './WorkspacePanel/WorkspacePanel';

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
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

  // Memory injection notification hook
  const { injection, showNotification, hideNotification } = useMemoryInjectionNotification();

  // Mode operations for Agent Mode functionality
  const { isAgentMode, isLoading } = useMode();

  // Workspace operations for VNC functionality
  const { isWorkspaceVisible, toggleWorkspace } = useWorkspace();

  // Get Agent Mode warning message
  const getAgentModeWarning = () => {
    return 'Agent will execute actions. Review approval gates.';
  };

  // Generate conversation ID when needed
  useEffect(() => {
    if (!currentConversationId) {
      const newConversationId = `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      setCurrentConversationId(newConversationId);
    }
  }, [currentConversationId]);

  // Prepare memory injection for conversation start
  const prepareMemoryInjection = useCallback(async (message: string) => {
    if (!currentConversationId) return;

    try {
      // Call memory injection API to prepare context
      const response = await fetch('/api/injection/prepare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          current_message: message,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          // Show memory injection notification
          showNotification({
            memories_count: data.data.memories?.length || 0,
            instructions_count: data.data.standing_instructions?.length || 0,
            injection_time_ms: data.data.injection_time_ms || 0,
            performance_stats: {
              cache_hit: data.data.performance_stats?.cache_hit || false,
              memories: data.data.memories?.slice(0, 5) || [], // Show top 5 in notification
              instructions: data.data.standing_instructions?.slice(0, 3) || [], // Show top 3 in notification
            },
          });
        }
      }
    } catch (error) {
      console.warn('Memory injection preparation failed:', error);
      // Continue without memory injection on error
    }
  }, [currentConversationId, showNotification]);

  // Handle message submission with memory injection
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

      // Prepare memory injection for this message
      await prepareMemoryInjection(message);

      // Simulate streaming response (placeholder for Story 2.4)
      // In Story 2.4, this will be replaced with actual LiteLLM streaming with memory context
      setTimeout(() => {
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: `I received your message: "${message}". Full streaming and AI response functionality with memory injection context will be implemented in Story 2.4 (Message Streaming & Real-Time Response Display).`,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setIsStreaming(false);
      }, 1500);
    },
    [prepareMemoryInjection]
  );

  return (
    <>
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

      {/* Workspace Panel */}
      <WorkspacePanel
        isOpen={isWorkspaceVisible}
        onToggle={toggleWorkspace}
      />

      {/* Memory Injection Notification */}
      <MemoryInjectionNotification
        injection={injection}
        onDismiss={hideNotification}
      />
    </>
  );
}
