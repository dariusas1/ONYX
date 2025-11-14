'use client';

import React, { useState, useCallback } from 'react';
import { MessageList, Message } from './MessageList';
import { InputBox } from './InputBox';

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
    <div
      className={`flex-1 flex flex-col min-h-0 ${className}`}
      role="main"
      aria-label="Chat conversation"
    >
      <div className="flex-1 flex flex-col min-h-0">
        <MessageList
          messages={messages}
          isStreaming={isStreaming}
          className="flex-1"
          aria-live="polite"
          aria-label="Messages in conversation"
        />
      </div>

      <div className="flex-shrink-0">
        <InputBox
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={isStreaming}
          aria-label="Type and send your message"
        />
      </div>
    </div>
  );
}
