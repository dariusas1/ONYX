'use client';

import React, { useRef, useEffect, KeyboardEvent, ChangeEvent } from 'react';
import { Send, Play } from 'lucide-react';
import { useMode } from '../contexts/ModeContext';

export interface InputBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function InputBox({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder: _placeholder, // Use the mode-specific placeholder
  className = '',
}: InputBoxProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Mode operations for dynamic UI changes
  const { isAgentMode, isLoading } = useMode();

  // Mode-specific placeholders and text
  const getButtonText = () => isAgentMode ? 'Execute Task' : 'Send';
  const getInputPlaceholder = () => isAgentMode
    ? 'Describe the task you want the agent to execute...'
    : 'Type your message...';

  // Use mode-specific placeholder
  const placeholder = getInputPlaceholder();

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

  return (
    <div
      className={`border-t border-manus-border bg-manus-surface ${className}`}
    >
      <div className="max-w-chat mx-auto px-4 py-4">
        <div className="flex gap-3 items-end">
          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={placeholder}
              className="input w-full resize-none min-h-[44px] max-h-[200px] py-3"
              rows={1}
              aria-label="Message input"
              aria-describedby="input-help"
            />
            <div
              id="input-help"
              className="absolute -bottom-5 left-0 text-xs text-manus-muted"
            >
              Press Enter to send, Shift+Enter for new line
            </div>
          </div>

          {/* Mode-specific button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            className={`
              h-11 w-11 flex items-center justify-center flex-shrink-0
              transition-all duration-300 ease-in-out
              ${isAgentMode
                ? 'bg-orange-500 hover:bg-orange-600 text-white'
                : 'btn btn-primary'
              }
              ${disabled || !value.trim()
                ? 'opacity-50 cursor-not-allowed'
                : 'hover:opacity-80'
              }
              ${isTransitioning ? 'scale-95' : 'scale-100'}
            `}
            aria-label={isAgentMode ? 'Execute task' : 'Send message'}
            title={isAgentMode ? 'Execute task (Enter)' : 'Send message (Enter)'}
          >
            {isAgentMode ? (
              <Play className="w-5 h-5" aria-hidden="true" />
            ) : (
              <Send className="w-5 h-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
