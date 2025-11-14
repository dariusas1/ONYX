import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MessageList, Message } from '@/components/MessageList';

// Mock scrollIntoView as it's not implemented in jsdom
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});

describe('MessageList', () => {
  const mockMessages: Message[] = [
    {
      id: '1',
      role: 'user',
      content: 'Hello, ONYX!',
      timestamp: new Date('2025-11-14T10:00:00'),
    },
    {
      id: '2',
      role: 'assistant',
      content: 'Hello! How can I help you today?',
      timestamp: new Date('2025-11-14T10:00:05'),
    },
  ];

  it('renders without crashing', () => {
    render(<MessageList messages={[]} />);
    // Empty state doesn't have role="log", so check for empty state message instead
    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
  });

  it('displays empty state when no messages', () => {
    render(<MessageList messages={[]} />);

    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
    expect(
      screen.getByText(/Ask me anything. I'm here to help you think strategically/i)
    ).toBeInTheDocument();
  });

  it('renders empty state with bot icon', () => {
    render(<MessageList messages={[]} />);

    // Check for Bot icon (SVG element)
    const emptyStateContainer = screen.getByText('Start a conversation').closest('div');
    const svg = emptyStateContainer?.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders messages correctly', () => {
    render(<MessageList messages={mockMessages} />);

    expect(screen.getByText('Hello, ONYX!')).toBeInTheDocument();
    expect(screen.getByText('Hello! How can I help you today?')).toBeInTheDocument();
  });

  it('displays user messages on the right side', () => {
    render(<MessageList messages={mockMessages} />);

    const userMessageContent = screen.getByText('Hello, ONYX!');
    const messageContainer = userMessageContent.closest('.flex');

    expect(messageContainer).toHaveClass('justify-end');
  });

  it('displays assistant messages on the left side', () => {
    render(<MessageList messages={mockMessages} />);

    const assistantMessageContent = screen.getByText('Hello! How can I help you today?');
    const messageContainer = assistantMessageContent.closest('.flex');

    expect(messageContainer).toHaveClass('justify-start');
  });

  it('shows timestamp for each message', () => {
    render(<MessageList messages={mockMessages} />);

    // Timestamps should be formatted as HH:MM
    const timestamps = screen.getAllByText(/\d{1,2}:\d{2}/);
    expect(timestamps.length).toBeGreaterThanOrEqual(2);
  });

  it('displays user avatar icon', () => {
    render(<MessageList messages={mockMessages} />);

    // User messages should have User icon
    const messageElements = screen.getByText('Hello, ONYX!').closest('.flex');
    const userIcon = messageElements?.querySelector('svg');
    expect(userIcon).toBeInTheDocument();
  });

  it('displays assistant avatar icon', () => {
    render(<MessageList messages={mockMessages} />);

    // Assistant messages should have Bot icon
    const messageElements = screen.getByText('Hello! How can I help you today?').closest('.flex');
    const botIcon = messageElements?.querySelector('svg');
    expect(botIcon).toBeInTheDocument();
  });

  it('displays streaming indicator when isStreaming is true', () => {
    render(<MessageList messages={mockMessages} isStreaming={true} />);

    // Streaming indicator should have three animated dots
    const streamingIndicator = screen.getByText('Hello! How can I help you today?')
      .closest('div[role="log"]');

    // Check for animated dots (spans with animate-bounce class)
    const animatedDots = streamingIndicator?.querySelectorAll('.animate-bounce');
    expect(animatedDots?.length).toBe(3);
  });

  it('does not display streaming indicator when isStreaming is false', () => {
    render(<MessageList messages={mockMessages} isStreaming={false} />);

    const container = screen.getByRole('log');
    const animatedDots = container.querySelectorAll('.animate-bounce');

    // Should not have streaming indicator
    expect(animatedDots.length).toBe(0);
  });

  it('applies custom className prop', () => {
    const customClass = 'custom-message-list-class';
    render(<MessageList messages={mockMessages} className={customClass} />);

    const container = screen.getByRole('log');
    expect(container).toHaveClass(customClass);
  });

  it('has proper ARIA attributes for accessibility', () => {
    render(<MessageList messages={mockMessages} />);

    const container = screen.getByRole('log');
    expect(container).toHaveAttribute('aria-live', 'polite');
    expect(container).toHaveAttribute('aria-label', 'Chat messages');
  });

  it('has scrollable container', () => {
    render(<MessageList messages={mockMessages} />);

    const container = screen.getByRole('log');
    expect(container).toHaveClass('overflow-y-auto');
  });

  it('handles multiple messages of different roles', () => {
    const multipleMessages: Message[] = [
      {
        id: '1',
        role: 'user',
        content: 'First user message',
        timestamp: new Date('2025-11-14T10:00:00'),
      },
      {
        id: '2',
        role: 'assistant',
        content: 'First assistant response',
        timestamp: new Date('2025-11-14T10:00:05'),
      },
      {
        id: '3',
        role: 'user',
        content: 'Second user message',
        timestamp: new Date('2025-11-14T10:00:10'),
      },
      {
        id: '4',
        role: 'assistant',
        content: 'Second assistant response',
        timestamp: new Date('2025-11-14T10:00:15'),
      },
    ];

    render(<MessageList messages={multipleMessages} />);

    expect(screen.getByText('First user message')).toBeInTheDocument();
    expect(screen.getByText('First assistant response')).toBeInTheDocument();
    expect(screen.getByText('Second user message')).toBeInTheDocument();
    expect(screen.getByText('Second assistant response')).toBeInTheDocument();
  });

  it('handles long message content', () => {
    const longMessage: Message = {
      id: '1',
      role: 'user',
      content: 'This is a very long message that should wrap properly. '.repeat(10),
      timestamp: new Date('2025-11-14T10:00:00'),
    };

    render(<MessageList messages={[longMessage]} />);

    const messageContent = screen.getByText(/This is a very long message/);
    expect(messageContent).toBeInTheDocument();

    // Check for break-words class to handle long content
    const messageElement = messageContent.closest('p');
    expect(messageElement).toHaveClass('break-words');
  });

  it('preserves whitespace in messages with whitespace-pre-wrap', () => {
    const messageWithWhitespace: Message = {
      id: '1',
      role: 'user',
      content: 'Line 1\nLine 2\nLine 3',
      timestamp: new Date('2025-11-14T10:00:00'),
    };

    render(<MessageList messages={[messageWithWhitespace]} />);

    // Use a function matcher to handle multiline text
    const messageElement = screen.getByText((content, element) => {
      return element?.tagName === 'P' && content.includes('Line 1') && content.includes('Line 2') && content.includes('Line 3');
    });
    expect(messageElement).toHaveClass('whitespace-pre-wrap');
  });

  it('auto-scrolls to latest message on mount', () => {
    const scrollIntoViewMock = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

    render(<MessageList messages={mockMessages} />);

    // scrollIntoView should be called for auto-scroll
    waitFor(() => {
      expect(scrollIntoViewMock).toHaveBeenCalledWith({ behavior: 'smooth' });
    });
  });

  it('auto-scrolls when new messages are added', () => {
    const scrollIntoViewMock = jest.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

    const { rerender } = render(<MessageList messages={mockMessages} />);

    // Add a new message
    const newMessages: Message[] = [
      ...mockMessages,
      {
        id: '3',
        role: 'user' as const,
        content: 'New message',
        timestamp: new Date('2025-11-14T10:00:10'),
      },
    ];

    rerender(<MessageList messages={newMessages} />);

    // scrollIntoView should be called again
    waitFor(() => {
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });
  });

  it('applies responsive max-width classes to messages', () => {
    render(<MessageList messages={mockMessages} />);

    const userMessage = screen.getByText('Hello, ONYX!').closest('.message');
    expect(userMessage).toHaveClass('max-w-[80%]', 'md:max-w-[70%]');
  });

  it('has proper styling for user messages', () => {
    render(<MessageList messages={mockMessages} />);

    const userMessage = screen.getByText('Hello, ONYX!').closest('.message');
    expect(userMessage).toHaveClass('message-user');
  });

  it('has proper styling for assistant messages', () => {
    render(<MessageList messages={mockMessages} />);

    const assistantMessage = screen.getByText('Hello! How can I help you today?').closest('.message');
    expect(assistantMessage).toHaveClass('message-assistant');
  });
});
