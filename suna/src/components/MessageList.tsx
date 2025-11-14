'use client';

import React, { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  className?: string;
}

export function MessageList({
  messages,
  isStreaming = false,
  className = '',
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div className={`flex-1 flex items-center justify-center ${className}`}>
        <div className="text-center max-w-md px-4">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-full bg-manus-surface flex items-center justify-center">
              <Bot className="w-8 h-8 text-manus-accent" />
            </div>
          </div>
          <h2 className="text-2xl font-semibold text-manus-text mb-2">
            Start a conversation
          </h2>
          <p className="text-manus-muted">
            Ask me anything. I'm here to help you think strategically and make better decisions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex-1 overflow-y-auto scrollbar-thin ${className}`}
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      <div className="max-w-chat mx-auto px-4 py-6 space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-manus-accent flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" aria-hidden="true" />
              </div>
            )}

            <div
              className={`message ${
                message.role === 'user'
                  ? 'message-user'
                  : 'message-assistant'
              } max-w-[80%] md:max-w-[70%]`}
            >
              <div className="prose prose-invert max-w-none">
                <p className="text-sm md:text-base whitespace-pre-wrap break-words">
                  {message.content}
                </p>
              </div>
              <div className="mt-2 text-xs opacity-70">
                {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-manus-surface border border-manus-border flex items-center justify-center">
                <User className="w-5 h-5 text-manus-text" aria-hidden="true" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-manus-accent flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" aria-hidden="true" />
            </div>
            <div className="message message-assistant">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
