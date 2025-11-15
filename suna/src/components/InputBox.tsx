'use client';

import React, { useRef, useEffect, KeyboardEvent, ChangeEvent, useState } from 'react';
import { Send, Bot, MessageSquare, Paperclip } from 'lucide-react';
import { useAgentModeContext } from '@/components/AgentModeProvider';
import type { AgentMode } from '@/components/ModeToggle';
import { FileUploadZone, FileUploadItem } from './upload/FileUploadZone';

export interface InputBoxProps {
  value?: string;
  onChange?: (value: string) => void;
  onSubmit: (message: string) => void;
  onFilesUploaded?: (files: FileUploadItem[]) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  error?: string;
  onClearError?: () => void;
  agentMode?: AgentMode;
  showModeIndicator?: boolean;
  showFileUpload?: boolean;
}

export function InputBox({
  value: externalValue,
  onChange: externalOnChange,
  onSubmit,
  onFilesUploaded,
  disabled = false,
  placeholder,
  className = '',
  error,
  onClearError,
  agentMode,
  showModeIndicator = true,
  showFileUpload = true
}: InputBoxProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [internalValue, setInternalValue] = React.useState('');
  const [showFileUploadZone, setShowFileUploadZone] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadItem[]>([]);

  const agentModeContext = useAgentModeContext();

  // Use provided agentMode or get from context
  const currentMode = agentMode || agentModeContext.mode;
  const canUseAgent = agentModeContext.canUseAgentMode;

  // Use external value if provided, otherwise use internal state
  const value = externalValue ?? internalValue;
  const onChange = externalOnChange ?? setInternalValue;

  // Mode-aware placeholders and styling
  const getModePlaceholder = () => {
    if (placeholder) return placeholder;

    if (currentMode === 'agent' && canUseAgent) {
      return 'Describe what you want the agent to accomplish...';
    } else if (currentMode === 'agent') {
      return 'Enable Agent Mode to use autonomous execution...';
    } else {
      return 'Type your message...';
    }
  };

  const getModeHelpText = () => {
    if (currentMode === 'agent' && canUseAgent) {
      return 'Agent will execute your request autonomously. Press Enter to send, Shift+Enter for new line';
    } else if (currentMode === 'agent') {
      return 'Enable Agent Mode first. Press Enter to send, Shift+Enter for new line';
    } else {
      return 'Press Enter to send, Shift+Enter for new line';
    }
  };

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';
    // Set height to scrollHeight, with max of 200px
    const newHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = `${newHeight}px`;
  }, [value]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    const trimmedValue = value.trim();
    if (!trimmedValue || disabled) return;

    onSubmit(trimmedValue);
    onChange('');

    // Reset textarea height after submission
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    // Shift+Enter for new line (default behavior)
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const handleFilesUploaded = (files: FileUploadItem[]) => {
    setUploadedFiles(files);
    if (onFilesUploaded) {
      onFilesUploaded(files);
    }
    // Hide file upload zone after successful upload
    const successfulFiles = files.filter(f => f.status === 'success');
    if (successfulFiles.length > 0) {
      setShowFileUploadZone(false);
    }
  };

  const toggleFileUpload = () => {
    setShowFileUploadZone(!showFileUploadZone);
  };

  return (
    <div
      className={`border-t border-manus-border bg-manus-surface ${className}`}
      role="form"
      aria-label="Message input form"
    >
      <div className="max-w-chat mx-auto px-3 sm:px-4 py-3 sm:py-4">
        {/* File upload zone */}
        {showFileUpload && showFileUploadZone && (
          <div className="mb-4">
            <FileUploadZone
              onFilesUploaded={handleFilesUploaded}
              maxFiles={10}
              maxSize={50 * 1024 * 1024} // 50MB
              disabled={disabled}
            />
          </div>
        )}

        {/* Mode indicator */}
        {showModeIndicator && (
          <div className="flex items-center gap-2 mb-3 px-1">
            {currentMode === 'agent' ? (
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
                canUseAgent
                  ? 'bg-purple-100 text-purple-700 border border-purple-200'
                  : 'bg-gray-100 text-gray-600 border border-gray-200'
              }`}>
                <Bot className="w-4 h-4" />
                <span className="font-medium">
                  {canUseAgent ? 'Agent Mode Active' : 'Agent Mode (Disabled)'}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-blue-100 text-blue-700 border border-blue-200">
                <MessageSquare className="w-4 h-4" />
                <span className="font-medium">Chat Mode</span>
              </div>
            )}
          </div>
        )}

        {/* Uploaded files summary */}
        {uploadedFiles.length > 0 && (
          <div className="mb-3 px-1">
            <div className="flex items-center gap-2 text-sm text-manus-muted">
              <Paperclip className="w-4 h-4" />
              <span>
                {uploadedFiles.filter(f => f.status === 'success').length} of {uploadedFiles.length} files uploaded successfully
              </span>
              <button
                type="button"
                onClick={() => setUploadedFiles([])}
                className="text-xs hover:text-manus-foreground transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        <div className="flex gap-2 sm:gap-3 items-end">
          {/* File upload button */}
          {showFileUpload && (
            <button
              type="button"
              onClick={toggleFileUpload}
              disabled={disabled}
              className={`flex items-center justify-center h-10 sm:h-11 w-10 sm:w-11 flex-shrink-0 min-w-[44px] min-h-[44px] rounded-lg border transition-colors ${
                showFileUploadZone
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-manus-surface border-manus-border text-manus-muted hover:text-manus-foreground hover:border-manus-border-hover'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-label={showFileUploadZone ? 'Hide file upload' : 'Show file upload'}
              title={showFileUploadZone ? 'Hide file upload' : 'Attach files'}
            >
              <Paperclip className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
              <span className="sr-only">Attach files</span>
            </button>
          )}

          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={getModePlaceholder()}
              className={`input w-full resize-none min-h-[44px] max-h-[200px] py-3 text-sm sm:text-base ${
                currentMode === 'agent' && canUseAgent
                  ? 'border-purple-200 focus:border-purple-400'
                  : currentMode === 'agent'
                  ? 'border-gray-200 focus:border-gray-400'
                  : ''
              }`}
              rows={1}
              aria-label="Message input"
              aria-describedby={disabled ? undefined : "input-help"}
              aria-invalid={false}
              aria-multiline="true"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck="false"
            />
            {!disabled && (
              <div
                id="input-help"
                className="absolute -bottom-5 sm:-bottom-4 left-0 text-xs text-manus-muted sr-only sm:not-sr-only"
              >
                {getModeHelpText()}
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            className={`btn h-10 sm:h-11 w-10 sm:w-11 flex items-center justify-center flex-shrink-0 min-w-[44px] min-h-[44px] ${
              currentMode === 'agent' && canUseAgent
                ? 'btn-purple'
                : 'btn-primary'
            }`}
            aria-label="Send message"
            title="Send message (Enter)"
            aria-describedby="input-help"
          >
            <Send className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
            <span className="sr-only">Send</span>
          </button>
        </div>

        {/* Error display */}
        {error && (
          <div className="mt-2 flex items-start gap-2 text-sm text-red-400 bg-red-900/20 border border-red-500/20 rounded-md p-2">
            <span className="flex-shrink-0 mt-0.5">⚠️</span>
            <div className="flex-1">
              <span className="font-medium">Error:</span> {error}
            </div>
            {onClearError && (
              <button
                type="button"
                onClick={onClearError}
                className="flex-shrink-0 text-red-400 hover:text-red-300 transition-colors p-1 rounded hover:bg-red-900/30"
                aria-label="Clear error"
                title="Clear error"
              >
                ×
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
