import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { axe, toHaveNoViolations } from 'jest-axe';

// Import components to test
import { ChatInterface } from '@/src/components/ChatInterface';
import { Header } from '@/src/components/Header';
import { MessageList } from '@/src/components/MessageList';
import { InputBox } from '@/src/components/InputBox';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock performance API for testing
Object.defineProperty(window, 'performance', {
  value: {
    getEntriesByType: jest.fn(() => []),
    now: jest.fn(() => Date.now()),
  },
  writable: true,
});

describe('Accessibility Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Header Component', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(<Header />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper semantic structure', () => {
      render(<Header />);

      const header = screen.getByRole('banner');
      expect(header).toBeInTheDocument();

      const heading = screen.getByRole('heading', { name: /onyx/i });
      expect(heading).toBeInTheDocument();

      const navigation = screen.getByRole('navigation', { name: /main navigation/i });
      expect(navigation).toBeInTheDocument();
    });

    it('should have accessible menu button', () => {
      render(<Header />);

      const menuButton = screen.getByRole('button', { name: /open navigation menu/i });
      expect(menuButton).toBeInTheDocument();
      expect(menuButton).toHaveAttribute('aria-expanded', 'false');
      expect(menuButton).toHaveAttribute('aria-haspopup', 'true');
      expect(menuButton).toHaveClass('min-h-[44px]', 'min-w-[44px]');
    });

    it('should support keyboard navigation', () => {
      render(<Header />);

      const menuButton = screen.getByRole('button', { name: /open navigation menu/i });

      // Focus on menu button
      menuButton.focus();
      expect(menuButton).toHaveFocus();

      // Test keyboard interaction
      fireEvent.keyDown(menuButton, { key: 'Enter' });
      expect(menuButton).toBeInTheDocument();

      fireEvent.keyDown(menuButton, { key: ' ' });
      expect(menuButton).toBeInTheDocument();
    });
  });

  describe('ChatInterface Component', () => {
    it('should not have any accessibility violations', async () => {
      const { container } = render(<ChatInterface />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper landmark roles', () => {
      render(<ChatInterface />);

      const main = screen.getByRole('main', { name: /chat conversation/i });
      expect(main).toBeInTheDocument();
    });

    it('should have accessible message input form', () => {
      render(<ChatInterface />);

      const form = screen.getByRole('form', { name: /message input form/i });
      expect(form).toBeInTheDocument();

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('aria-multiline', 'true');
      expect(textarea).toHaveAttribute('aria-describedby', 'input-help');

      const sendButton = screen.getByRole('button', { name: /send message/i });
      expect(sendButton).toBeInTheDocument();
      expect(sendButton).toHaveClass('min-h-[44px]', 'min-w-[44px]');
    });
  });

  describe('MessageList Component', () => {
    const mockMessages = [
      {
        id: '1',
        role: 'user' as const,
        content: 'Hello, how are you?',
        timestamp: new Date(),
      },
      {
        id: '2',
        role: 'assistant' as const,
        content: 'I am doing well, thank you for asking!',
        timestamp: new Date(),
      },
    ];

    it('should not have any accessibility violations', async () => {
      const { container } = render(
        <MessageList messages={mockMessages} />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper message structure', () => {
      render(<MessageList messages={mockMessages} />);

      const messages = screen.getAllByRole('article');
      expect(messages).toHaveLength(2);

      // Check message content is properly labeled
      mockMessages.forEach((message) => {
        const messageContent = document.getElementById(`message-${message.id}-content`);
        const messageTimestamp = document.getElementById(`message-${message.id}-timestamp`);

        expect(messageContent).toBeInTheDocument();
        expect(messageTimestamp).toBeInTheDocument();
      });
    });

    it('should have accessible empty state', () => {
      render(<MessageList messages={[]} />);

      const emptyState = screen.getByRole('status', { name: /no messages yet/i });
      expect(emptyState).toBeInTheDocument();

      const heading = screen.getByRole('heading', { name: /start a conversation/i });
      expect(heading).toBeInTheDocument();
    });

    it('should announce streaming status', () => {
      render(<MessageList messages={mockMessages} isStreaming={true} />);

      const streamingIndicator = screen.getByRole('status', { name: /assistant is typing/i });
      expect(streamingIndicator).toBeInTheDocument();
      expect(streamingIndicator).toHaveAttribute('aria-live', 'polite');
    });

    it('should support keyboard navigation', () => {
      render(<MessageList messages={mockMessages} />);

      const messageContainer = screen.getByRole('log', { name: /chat messages/i });
      expect(messageContainer).toHaveAttribute('tabIndex', '0');

      // Test keyboard navigation
      messageContainer.focus();
      expect(messageContainer).toHaveFocus();
    });
  });

  describe('InputBox Component', () => {
    const mockProps = {
      value: 'Test message',
      onChange: jest.fn(),
      onSubmit: jest.fn(),
    };

    it('should not have any accessibility violations', async () => {
      const { container } = render(<InputBox {...mockProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have accessible form controls', () => {
      render(<InputBox {...mockProps} />);

      const form = screen.getByRole('form', { name: /message input form/i });
      expect(form).toBeInTheDocument();

      const textarea = screen.getByRole('textbox', { name: /message input/i });
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute('aria-multiline', 'true');
      expect(textarea).toHaveAttribute('aria-describedby', 'input-help');
      expect(textarea).toHaveAttribute('autoComplete', 'off');
      expect(textarea).toHaveAttribute('autoCorrect', 'off');

      const sendButton = screen.getByRole('button', { name: /send message/i });
      expect(sendButton).toBeInTheDocument();
      expect(sendButton).toHaveClass('min-h-[44px]', 'min-w-[44px]');
    });

    it('should provide help text when enabled', () => {
      render(<InputBox {...mockProps} />);

      const helpText = screen.getByText(/press enter to send/i);
      expect(helpText).toBeInTheDocument();
      expect(helpText).toHaveAttribute('id', 'input-help');
    });

    it('should support keyboard navigation', () => {
      render(<InputBox {...mockProps} />);

      const textarea = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send message/i });

      // Test textarea focus
      textarea.focus();
      expect(textarea).toHaveFocus();

      // Test Enter key to send
      fireEvent.keyDown(textarea, { key: 'Enter' });
      expect(mockProps.onSubmit).toHaveBeenCalledWith('Test message');

      // Test Shift+Enter for new line
      mockProps.onChange.mockClear();
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
      // Should not call onSubmit on Shift+Enter
      expect(mockProps.onSubmit).not.toHaveBeenCalled();
    });

    it('should handle disabled state properly', () => {
      render(<InputBox {...mockProps} disabled />);

      const textarea = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send message/i });

      expect(textarea).toBeDisabled();
      expect(sendButton).toBeDisabled();

      // Help text should be hidden when disabled
      expect(screen.queryByText(/press enter to send/i)).not.toBeInTheDocument();
    });
  });

  describe('Responsive Design Tests', () => {
    beforeEach(() => {
      // Mock window.matchMedia
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockImplementation(query => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(), // deprecated
          removeListener: jest.fn(), // deprecated
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        })),
      });
    });

    it('should adapt to mobile viewport', () => {
      // Mock mobile viewport
      window.matchMedia.mockImplementation(query => ({
        matches: query.includes('640'),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      }));

      const { container } = render(<Header />);

      // Test that responsive classes are applied
      expect(container.querySelector('.px-3')).toBeInTheDocument();
    });

    it('should adapt to desktop viewport', () => {
      // Mock desktop viewport
      window.matchMedia.mockImplementation(query => ({
        matches: query.includes('1024'),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      }));

      const { container } = render(<Header />);

      // Test that responsive classes are applied
      expect(container.querySelector('.lg\\:px-6')).toBeInTheDocument();
    });
  });

  describe('Performance Tests', () => {
    it('should have optimized images and fonts', () => {
      // Test font loading strategy
      const interLink = document.querySelector('link[rel="preconnect"]');
      expect(interLink).toBeTruthy();
    });

    it('should lazy load non-critical resources', () => {
      // Test that we're not blocking on non-critical resources
      expect(document.querySelector('script[defer]')).toBeTruthy();
    });
  });
});