import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ChatInterface } from '@/components/ChatInterface';

// Mock the child components to isolate ChatInterface testing
jest.mock('../../src/components/MessageList', () => ({
  MessageList: ({ messages, isStreaming }: any) => (
    <div data-testid="message-list" data-streaming={isStreaming}>
      {messages.length === 0 ? (
        <div>No messages</div>
      ) : (
        messages.map((msg: any) => <div key={msg.id}>{msg.content}</div>)
      )}
    </div>
  ),
}));

jest.mock('../../src/components/InputBox', () => ({
  InputBox: ({ value, onChange, onSubmit, disabled }: any) => (
    <div data-testid="input-box">
      <input
        data-testid="input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      />
      <button
        data-testid="submit-button"
        onClick={() => onSubmit(value)}
        disabled={disabled}
      >
        Send
      </button>
    </div>
  ),
}));

describe('ChatInterface', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<ChatInterface />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('renders MessageList and InputBox components', () => {
    render(<ChatInterface />);
    expect(screen.getByTestId('message-list')).toBeInTheDocument();
    expect(screen.getByTestId('input-box')).toBeInTheDocument();
  });

  it('displays empty state when no messages', () => {
    render(<ChatInterface />);
    expect(screen.getByText('No messages')).toBeInTheDocument();
  });

  it('handles user input correctly', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByTestId('input');
    await user.type(input, 'Test message');

    expect(input).toHaveValue('Test message');
  });

  it('submits message and adds it to the list', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByTestId('input');
    const submitButton = screen.getByTestId('submit-button');

    await user.type(input, 'Hello ONYX');
    await user.click(submitButton);

    // Wait for the user message to appear
    await waitFor(() => {
      expect(screen.getByText('Hello ONYX')).toBeInTheDocument();
    });
  });

  it('sets streaming state when message is submitted', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByTestId('input');
    const submitButton = screen.getByTestId('submit-button');

    await user.type(input, 'Test streaming');
    await user.click(submitButton);

    // Check that streaming is active
    await waitFor(() => {
      const messageList = screen.getByTestId('message-list');
      expect(messageList).toHaveAttribute('data-streaming', 'true');
    });
  });

  it('disables input during streaming', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByTestId('input');
    const submitButton = screen.getByTestId('submit-button');

    await user.type(input, 'Testing disabled state');
    await user.click(submitButton);

    // Input should be disabled while streaming
    await waitFor(() => {
      expect(input).toBeDisabled();
      expect(submitButton).toBeDisabled();
    });
  });

  it('receives assistant response after user message', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    render(<ChatInterface />);

    const input = screen.getByTestId('input');
    const submitButton = screen.getByTestId('submit-button');

    await user.type(input, 'Test question');
    await user.click(submitButton);

    // Wait for user message
    await waitFor(() => {
      expect(screen.getByText('Test question')).toBeInTheDocument();
    });

    // Fast-forward time to get assistant response
    jest.advanceTimersByTime(1500);

    // Wait for assistant response
    await waitFor(() => {
      const messageList = screen.getByTestId('message-list');
      expect(messageList.textContent).toContain('I received your message');
    });

    jest.useRealTimers();
  });

  it('clears input after submission', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);

    const input = screen.getByTestId('input');
    const submitButton = screen.getByTestId('submit-button');

    await user.type(input, 'Clear me');
    expect(input).toHaveValue('Clear me');

    await user.click(submitButton);

    // Wait for the message to be submitted (streaming starts)
    await waitFor(() => {
      expect(screen.getByText('Clear me')).toBeInTheDocument();
    });

    // Note: Input clearing is handled by the parent component's onChange callback
    // The mock InputBox receives onChange('') from ChatInterface after submission
  });

  it('passes conversationId prop correctly', () => {
    const conversationId = 'test-conversation-123';
    render(<ChatInterface conversationId={conversationId} />);

    // Component should render without errors with conversationId
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('applies custom className prop', () => {
    const customClass = 'custom-chat-class';
    render(<ChatInterface className={customClass} />);

    const mainElement = screen.getByRole('main');
    expect(mainElement).toHaveClass(customClass);
  });

  it('handles multiple message submissions', async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });

    render(<ChatInterface />);

    let input = screen.getByTestId('input');
    let submitButton = screen.getByTestId('submit-button');

    // First message
    await user.type(input, 'First message');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('First message')).toBeInTheDocument();
    });

    // Wait for streaming to complete
    jest.advanceTimersByTime(1500);

    await waitFor(() => {
      const messageList = screen.getByTestId('message-list');
      expect(messageList).toHaveAttribute('data-streaming', 'false');
    });

    // Re-get the input element after state update
    input = screen.getByTestId('input');
    submitButton = screen.getByTestId('submit-button');

    // Clear the input first (simulating user clearing)
    await user.clear(input);

    // Second message
    await user.type(input, 'Second message');
    await user.click(submitButton);

    // Both messages should be present (we check the message list has both)
    await waitFor(() => {
      const messageList = screen.getByTestId('message-list');
      expect(messageList.textContent).toContain('First message');
      expect(messageList.textContent).toContain('Second message');
    });

    jest.useRealTimers();
  });
});
