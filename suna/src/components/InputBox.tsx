'use client';

import React, { useRef, useEffect, KeyboardEvent, ChangeEvent } from 'react';
import { Send } from 'lucide-react';

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
  placeholder = 'Type your message...',
  className = '',
}: InputBoxProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
      role="form"
      aria-label="Message input form"
    >
      <div className="max-w-chat mx-auto px-3 sm:px-4 py-3 sm:py-4">
        <div className="flex gap-2 sm:gap-3 items-end">
          {/* Textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={placeholder}
              className="input w-full resize-none min-h-[44px] max-h-[200px] py-3 text-sm sm:text-base"
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
                Press Enter to send, Shift+Enter for new line
              </div>
            )}
          </div>

          {/* Send button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            className="btn btn-primary h-10 sm:h-11 w-10 sm:w-11 flex items-center justify-center flex-shrink-0 min-w-[44px] min-h-[44px]"
            aria-label="Send message"
            title="Send message (Enter)"
            aria-describedby="input-help"
          >
            <Send className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
            <span className="sr-only">Send</span>
          </button>
        </div>
      </div>
    </div>
  );
}
