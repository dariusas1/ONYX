'use client';

import React, { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: {
    messageId?: string;
    modelUsed?: string;
    totalTokens?: number;
    totalTime?: number;
    finishReason?: string;
    firstTokenLatency?: number;
  };
}

export interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  firstTokenLatency?: number;
  totalTokens?: number;
  className?: string;
}

export function MessageList({
  messages,
  isStreaming = false,
  streamingContent = '',
  firstTokenLatency,
  totalTokens,
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
                <div className="flex items-center justify-between">
                  <span>
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>

                  {/* Performance metadata for assistant messages */}
                  {message.role === 'assistant' && message.metadata && (
                    <div className="flex items-center gap-2 ml-2">
                      {message.metadata.firstTokenLatency && (
                        <span className="flex items-center gap-1" title="First token latency">
                          <span>⚡</span>
                          <span>{message.metadata.firstTokenLatency}ms</span>
                        </span>
                      )}
                      {message.metadata.totalTokens && (
                        <span className="flex items-center gap-1" title="Total tokens">
                          <span>🔤</span>
                          <span>{message.metadata.totalTokens}</span>
                        </span>
                      )}
                      {message.metadata.totalTime && (
                        <span className="flex items-center gap-1" title="Total time">
                          <span>⏱️</span>
                          <span>{(message.metadata.totalTime / 1000).toFixed(1)}s</span>
                        </span>
                      )}
                      {message.metadata.modelUsed && (
                        <span className="hidden sm:inline" title="Model used">
                          {message.metadata.modelUsed}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-manus-surface border border-manus-border flex items-center justify-center">
                <User className="w-4 h-4 sm:w-5 sm:h-5 text-manus-text" aria-hidden="true" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && (
          <div
            className="flex gap-3 sm:gap-4 justify-start"
            role="status"
            aria-live="polite"
            aria-label="Assistant is responding"
          >
            <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-manus-accent flex items-center justify-center">
              <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" aria-hidden="true" />
            </div>
            <div className="message message-assistant max-w-[75%] sm:max-w-[80%] md:max-w-[70%] min-w-0">
              {/* Streaming content or typing indicator */}
              {streamingContent ? (
                <div className="prose prose-invert max-w-none">
                  <p className="text-sm sm:text-base whitespace-pre-wrap break-words leading-relaxed">
                    {streamingContent}
                    <span className="inline-block w-1 h-4 bg-manus-accent animate-pulse ml-1" />
                  </p>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="sr-only">Assistant is typing</span>
                  <div className="flex gap-1" aria-hidden="true">
                    <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-manus-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}

              {/* Performance metrics during streaming */}
              <div className="mt-2 flex items-center gap-3 text-xs opacity-70">
                {firstTokenLatency && (
                  <span className="flex items-center gap-1">
                    <span>⚡</span>
                    <span>{firstTokenLatency}ms</span>
                  </span>
                )}
                {totalTokens && (
                  <span className="flex items-center gap-1">
                    <span>🔤</span>
                    <span>{totalTokens} tokens</span>
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span>Streaming...</span>
                </span>
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
