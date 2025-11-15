'use client';

import React from 'react';
import { MessageList, Message } from './MessageList';
import { InputBox } from './InputBox';
import { useChat } from '@/hooks/useChat';
import { FileUploadItem } from './upload/FileUploadZone';

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

  const handleFilesUploaded = React.useCallback(
    async (files: FileUploadItem[]) => {
      // Filter successfully uploaded files
      const successfulFiles = files.filter(f => f.status === 'success');

      if (successfulFiles.length === 0) return;

      // Create a message about the uploaded files
      const fileNames = successfulFiles.map(f => f.file.name).join(', ');
      const fileMessage = `I've uploaded the following files: ${fileNames}. They should now be available for search and analysis.`;

      try {
        await sendMessage(fileMessage);
      } catch (error) {
        console.error('Failed to send file upload message:', error);
      }
    },
    [sendMessage]
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
          onFilesUploaded={handleFilesUploaded}
          disabled={sending || isStreaming}
          aria-label="Type and send your message"
          error={error || streamingError}
          onClearError={clearError}
          showFileUpload={true}
        />
      </div>
    </div>
  );
}
