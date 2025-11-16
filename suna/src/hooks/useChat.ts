/**
 * useChat Hook - Streaming Chat Interface
 *
 * React hook for managing chat conversations with streaming support,
 * message persistence, and performance monitoring.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// Re-use the Message interface from MessageList
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

export interface StreamingState {
  isStreaming: boolean;
  currentMessageId?: string;
  currentContent: string;
  firstTokenLatency?: number;
  totalTokens?: number;
  error?: string;
}

export interface UseChatOptions {
  conversationId?: string;
  autoLoad?: boolean;
  onError?: (error: string) => void;
  onMessageComplete?: (message: Message) => void;
}

export interface UseChatReturn {
  // Messages
  messages: Message[];

  // State
  sending: boolean;
  error?: string;

  // Streaming state
  isStreaming: boolean;
  firstTokenLatency?: number;
  currentContent: string;
  totalTokens?: number;
  streamingError?: string;

  // Actions
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
  clearMessages: () => void;
  loadMessages: (conversationId: string) => Promise<void>;
}

const API_BASE = process.env.NODE_ENV === 'development'
  ? 'http://localhost:3000'
  : '';

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { conversationId, autoLoad = false, onError, onMessageComplete } = options;

  // Core state
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | undefined>();

  // Streaming state
  const [streamingState, setStreamingState] = useState<StreamingState>({
    isStreaming: false,
    currentContent: '',
  });

  // Refs for managing streaming state
  const eventSourceRef = useRef<EventSource | null>(null);
  const currentMessageRef = useRef<string>('');
  const streamingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Clear error state
  const clearError = useCallback(() => {
    setError(undefined);
    setStreamingState(prev => ({ ...prev, error: undefined }));
  }, []);

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    clearError();
  }, [clearError]);

  // Load conversation history
  const loadMessages = useCallback(async (convId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${convId}/messages`);
      if (!response.ok) {
        throw new Error(`Failed to load messages: ${response.statusText}`);
      }

      const data = await response.json();
      const loadedMessages: Message[] = data.messages?.map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        metadata: msg.metadata
      })) || [];

      setMessages(loadedMessages);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load messages';
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, [onError]);

  // Process SSE chunk
  const processSSEChunk = useCallback((chunk: string) => {
    const lines = chunk.split('\n');
    let event = '';
    let data = '';

    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data = line.substring(5).trim();
      }

      // Empty line indicates end of message
      if (line === '' && event && data) {
        try {
          const parsedData = JSON.parse(data);
          handleSSEEvent(event, parsedData);
          event = '';
          data = '';
        } catch (error) {
          console.warn('Failed to parse SSE data:', error);
        }
      }
    }
  }, []);

  // Handle SSE events
  const handleSSEEvent = useCallback((event: string, data: any) => {
    switch (event) {
      case 'message':
        // New content chunk
        if (data.content) {
          currentMessageRef.current += data.content;
          setStreamingState(prev => ({
            ...prev,
            currentContent: currentMessageRef.current,
          }));
        }
        break;

      case 'metrics':
        // Performance metrics
        if (data.first_token_latency) {
          setStreamingState(prev => ({
            ...prev,
            firstTokenLatency: data.first_token_latency,
          }));
        }
        if (data.total_tokens) {
          setStreamingState(prev => ({
            ...prev,
            totalTokens: data.total_tokens,
          }));
        }
        break;

      case 'error':
        // Streaming error
        const errorMessage = data.error || 'Unknown streaming error';
        setStreamingState(prev => ({
          ...prev,
          error: errorMessage,
          isStreaming: false,
        }));
        setError(errorMessage);
        onError?.(errorMessage);
        break;

      case 'complete':
        // Streaming completed
        const finalMessage: Message = {
          id: data.message_id || `msg_${Date.now()}`,
          role: 'assistant',
          content: currentMessageRef.current,
          timestamp: new Date(),
          metadata: {
            messageId: data.message_id,
            modelUsed: data.model_used,
            totalTokens: data.total_tokens,
            totalTime: data.total_time,
            finishReason: data.finish_reason,
          }
        };

        // Add to messages list
        setMessages(prev => [...prev, finalMessage]);
        onMessageComplete?.(finalMessage);

        // Reset streaming state
        setStreamingState({
          isStreaming: false,
          currentContent: '',
        });

        // Clear current message ref
        currentMessageRef.current = '';
        break;

      default:
        console.debug('Unknown SSE event:', event, data);
    }
  }, [onError, onMessageComplete]);

  // Send message with streaming
  const sendMessage = useCallback(async (content: string) => {
    if (sending || streamingState.isStreaming) {
      return;
    }

    // Add user message immediately
    const userMessage: Message = {
      id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setSending(true);
    clearError();

    try {
      // Prepare request payload
      const payload = {
        message: content,
        conversation_id: conversationId,
        model: 'manus-primary',
      };

      // Create EventSource for streaming
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Get response as stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      // Start streaming
      setStreamingState(prev => ({
        ...prev,
        isStreaming: true,
        currentContent: '',
        error: undefined,
      }));

      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.trim()) {
              processSSEChunk(line + '\n');
            }
          }
        }

        // Process any remaining buffer content
        if (buffer.trim()) {
          processSSEChunk(buffer);
        }
      } finally {
        reader.releaseLock();
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      setError(errorMessage);
      setStreamingState(prev => ({
        ...prev,
        error: errorMessage,
        isStreaming: false,
      }));
      onError?.(errorMessage);
    } finally {
      setSending(false);
    }
  }, [conversationId, sending, streamingState.isStreaming, clearError, onError, processSSEChunk]);

  // Auto-load messages on mount
  useEffect(() => {
    if (autoLoad && conversationId) {
      loadMessages(conversationId);
    }
  }, [autoLoad, conversationId, loadMessages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
      }
    };
  }, []);

  // Timeout protection for streaming
  useEffect(() => {
    if (streamingState.isStreaming) {
      streamingTimeoutRef.current = setTimeout(() => {
        setStreamingState(prev => ({
          ...prev,
          isStreaming: false,
          error: 'Streaming timeout',
        }));
        setError('Streaming timeout');
      }, 60000); // 60 second timeout
    } else if (streamingTimeoutRef.current) {
      clearTimeout(streamingTimeoutRef.current);
      streamingTimeoutRef.current = null;
    }

    return () => {
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
      }
    };
  }, [streamingState.isStreaming]);

  return {
    // Messages
    messages,

    // State
    sending,
    error,

    // Streaming state
    isStreaming: streamingState.isStreaming,
    firstTokenLatency: streamingState.firstTokenLatency,
    currentContent: streamingState.currentContent,
    totalTokens: streamingState.totalTokens,
    streamingError: streamingState.error,

    // Actions
    sendMessage,
    clearError,
    clearMessages,
    loadMessages,
  };
}