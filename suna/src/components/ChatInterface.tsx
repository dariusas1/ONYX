'use client';

import React from 'react';
import { MessageList, Message } from './MessageList';
import { InputBox } from './InputBox';
import { useChat } from '@/hooks/useChat';

export interface ChatInterfaceProps {
  conversationId?: string;
  className?: string;
}

export function ChatInterface({
  conversationId: _conversationId,
  className = '',
}: ChatInterfaceProps) {
  const {
    messages,
    sending,
    error,
    isStreaming,
    firstTokenLatency,
    currentContent,
    totalTokens,
    streamingError,
    sendMessage,
    clearError
  } = useChat({
    conversationId: _conversationId,
    autoLoad: true
  });

  const handleSubmit = React.useCallback(
    async (message: string) => {
      if (sending || isStreaming) return;

      try {
        await sendMessage(message);
      } catch (error) {
        console.error('Failed to send message:', error);
        // Error is handled by the hook
      }
    },
    [sendMessage, sending, isStreaming]
  );

  return (
    <div
      className={`flex-1 flex flex-col min-h-0 ${className}`}
      role="main"
      aria-label="Chat conversation"
    >
      <div className="flex-1 flex flex-col min-h-0">
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          streamingContent={currentContent}
          firstTokenLatency={firstTokenLatency}
          totalTokens={totalTokens}
          className="flex-1"
          aria-live="polite"
          aria-label="Messages in conversation"
        />
      </div>

      <div className="flex-shrink-0">
        <InputBox
          onSubmit={handleSubmit}
          disabled={sending || isStreaming}
          aria-label="Type and send your message"
          error={error || streamingError}
          onClearError={clearError}
        />
      </div>
    </div>
  );
}
