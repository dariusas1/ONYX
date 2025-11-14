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
      <div
        className={`flex-1 flex items-center justify-center ${className}`}
        role="status"
        aria-label="No messages yet"
      >
        <div className="text-center max-w-md px-4 sm:px-6 lg:px-8">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-manus-surface flex items-center justify-center">
              <Bot className="w-8 h-8 sm:w-10 sm:h-10 text-manus-accent" />
            </div>
          </div>
          <h2 className="text-xl sm:text-2xl font-semibold text-manus-text mb-3">
            Start a conversation
          </h2>
          <p className="text-manus-muted text-sm sm:text-base leading-relaxed">
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
      tabIndex={0}
    >
      <div className="max-w-chat mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6">
        {messages.map((message, index) => (
          <div
            key={message.id}
            className={`flex gap-3 sm:gap-4 ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
            role="article"
            aria-labelledby={`message-${message.id}-content`}
            aria-describedby={`message-${message.id}-timestamp`}
          >
            {message.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-manus-accent flex items-center justify-center">
                <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" aria-hidden="true" />
              </div>
            )}

            <div
              className={`message ${
                message.role === 'user'
                  ? 'message-user'
                  : 'message-assistant'
              } max-w-[75%] sm:max-w-[80%] md:max-w-[70%] min-w-0`}
              id={`message-${message.id}-content`}
            >
              <div className="prose prose-invert max-w-none">
                <p className="text-sm sm:text-base whitespace-pre-wrap break-words leading-relaxed">
                  {message.content}
                </p>
              </div>
              <div
                className="mt-2 text-xs opacity-70"
                id={`message-${message.id}-timestamp`}
                aria-label={`Message sent at ${message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}`}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-manus-surface border border-manus-border flex items-center justify-center">
                <User className="w-4 h-4 sm:w-5 sm:h-5 text-manus-text" aria-hidden="true" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && (
          <div
            className="flex gap-3 sm:gap-4 justify-start"
            role="status"
            aria-live="polite"
            aria-label="Assistant is typing"
          >
            <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-manus-accent flex items-center justify-center">
              <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" aria-hidden="true" />
            </div>
            <div className="message message-assistant">
              <div className="flex items-center gap-2">
                <span className="sr-only">Assistant is typing</span>
                <div className="flex gap-1" aria-hidden="true">
                  <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
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
