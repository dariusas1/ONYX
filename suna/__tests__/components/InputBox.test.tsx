import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { InputBox } from '@/components/InputBox';

// Mock HTMLTextAreaElement methods not available in jsdom
beforeAll(() => {
  Object.defineProperty(HTMLTextAreaElement.prototype, 'scrollHeight', {
    configurable: true,
    get: function () {
      return this._scrollHeight || 0;
    },
    set: function (value) {
      this._scrollHeight = value;
    },
  });
});

describe('InputBox', () => {
  const mockOnChange = jest.fn();
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('displays the input value', () => {
    render(
      <InputBox value="Test message" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue('Test message');
  });

  it('calls onChange when user types', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello');

    expect(mockOnChange).toHaveBeenCalled();
    expect(mockOnChange).toHaveBeenCalledWith('H');
  });

  it('calls onSubmit when send button is clicked', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="Test message" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    await user.click(sendButton);

    expect(mockOnSubmit).toHaveBeenCalledWith('Test message');
  });

  it('calls onSubmit when Enter key is pressed', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="Test message" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    await user.click(textarea);
    await user.keyboard('{Enter}');

    expect(mockOnSubmit).toHaveBeenCalledWith('Test message');
  });

  it('does not call onSubmit when Shift+Enter is pressed (new line)', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="Test message" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    await user.click(textarea);
    await user.keyboard('{Shift>}{Enter}{/Shift}');

    // Should NOT submit on Shift+Enter
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('disables input when disabled prop is true', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} disabled={true} />
    );

    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('does not submit when disabled', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="Test message" onChange={mockOnChange} onSubmit={mockOnSubmit} disabled={true} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    await user.click(sendButton);

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('disables send button when input is empty', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it('disables send button when input contains only whitespace', () => {
    render(
      <InputBox value="   " onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it('enables send button when input has content', () => {
    render(
      <InputBox value="Hello" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).not.toBeDisabled();
  });

  it('displays custom placeholder', () => {
    const customPlaceholder = 'Ask me anything...';
    render(
      <InputBox
        value=""
        onChange={mockOnChange}
        onSubmit={mockOnSubmit}
        placeholder={customPlaceholder}
      />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('placeholder', customPlaceholder);
  });

  it('displays default placeholder when not provided', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('placeholder', 'Type your message...');
  });

  it('has proper ARIA labels', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    expect(textarea).toHaveAttribute('aria-label', 'Message input');
    expect(textarea).toHaveAttribute('aria-describedby', 'input-help');
    expect(sendButton).toHaveAttribute('aria-label', 'Send message');
  });

  it('displays help text for keyboard shortcuts', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    expect(
      screen.getByText('Press Enter to send, Shift+Enter for new line')
    ).toBeInTheDocument();
  });

  it('applies custom className prop', () => {
    const customClass = 'custom-input-class';
    render(
      <InputBox
        value=""
        onChange={mockOnChange}
        onSubmit={mockOnSubmit}
        className={customClass}
      />
    );

    const container = screen.getByRole('textbox').closest('div.border-t');
    expect(container).toHaveClass(customClass);
  });

  it('trims whitespace before submitting', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="  Test message  " onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    await user.click(sendButton);

    // Should submit trimmed value
    expect(mockOnSubmit).toHaveBeenCalledWith('Test message');
  });

  it('does not submit empty message', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    await user.click(textarea);
    await user.keyboard('{Enter}');

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('focuses textarea on mount', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');

    waitFor(() => {
      expect(textarea).toHaveFocus();
    });
  });

  it('has Send icon in button', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });

    // Check for SVG icon (lucide-react Send component)
    const icon = sendButton.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('has proper styling for input area', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveClass('input', 'w-full', 'resize-none', 'min-h-[44px]');
  });

  it('has proper styling for send button', () => {
    render(
      <InputBox value="Test" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toHaveClass('btn', 'btn-primary', 'h-11', 'w-11');
  });

  it('handles rapid key presses correctly', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    await user.click(textarea);

    // Type quickly
    await user.keyboard('Hello{Enter}');

    // Should handle Enter key after typing
    expect(mockOnChange).toHaveBeenCalled();
  });

  it('updates value prop correctly on re-render', () => {
    const { rerender } = render(
      <InputBox value="Initial" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    let textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue('Initial');

    // Re-render with new value
    rerender(
      <InputBox value="Updated" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue('Updated');
  });

  it('has accessible button title', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toHaveAttribute('title', 'Send message (Enter)');
  });

  it('prevents form submission on Enter when empty', async () => {
    const user = userEvent.setup();
    render(
      <InputBox value="   " onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    await user.click(textarea);
    await user.keyboard('{Enter}');

    // Should not submit whitespace-only content
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('has maximum height constraint', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveClass('max-h-[200px]');
  });

  it('has Manus theme styling', () => {
    render(
      <InputBox value="" onChange={mockOnChange} onSubmit={mockOnSubmit} />
    );

    const container = screen.getByRole('textbox').closest('div.border-t');
    expect(container).toHaveClass('border-manus-border', 'bg-manus-surface');
  });
});
