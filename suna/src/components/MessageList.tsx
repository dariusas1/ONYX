'use client';

import React, { useEffect, useRef, useState } from 'react';
import { User, Bot } from 'lucide-react';

import { Citation } from '../lib/citation-extractor';
import { CitationList } from './CitationList';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  citations?: Citation[];
}

export interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  className?: string;
  showCitations?: boolean;
  onCitationClick?: (citation: Citation) => void;
}

export function MessageList({
  messages,
  isStreaming = false,
  className = '',
  showCitations = true,
  onCitationClick
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Render content with inline citations
  const renderContentWithCitations = (message: Message) => {
    if (!message.citations || message.citations.length === 0) {
      return message.content;
    }

    // Replace citation markers with clickable elements
    let content = message.content;
    const citationPattern = /\[(\d+)\]/g;

    return content.split(citationPattern).map((part, index) => {
      // Even indices are text, odd indices are citation numbers
      if (index % 2 === 0) {
        return part;
      } else {
        const citationIndex = parseInt(part);
        const citation = message.citations?.find(c => c.index === citationIndex);

        if (citation) {
          return (
            <button
              key={`citation-${index}`}
              onClick={() => onCitationClick?.(citation)}
              className="inline-flex items-center justify-center w-5 h-5 rounded bg-manus-surface hover:bg-manus-accent text-manus-accent hover:text-white text-xs font-semibold transition-colors cursor-pointer mx-1"
              title={citation.documentName || `Citation ${citationIndex}`}
              aria-label={`View source ${citationIndex}`}
            >
              {citationIndex}
            </button>
          );
        }

        return <span key={`citation-${index}`}>[{citationIndex}]</span>;
      }
    });
  };

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
                  {message.role === 'assistant' ? renderContentWithCitations(message) : message.content}
                </p>
              </div>

              {/* Citations List for Assistant Messages */}
              {showCitations && message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                <div className="mt-3">
                  <CitationList
                    citations={message.citations}
                    maxVisible={2}
                    onCitationClick={onCitationClick}
                    className="border-t border-manus-border pt-3"
                  />
                </div>
              )}

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
