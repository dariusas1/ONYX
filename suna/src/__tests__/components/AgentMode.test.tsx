import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModeToggle } from '@/components/ModeToggle';
import { AgentModeProvider, useAgentModeContext } from '@/components/AgentModeProvider';
import { AgentModeWarning } from '@/components/AgentModeWarning';
import { InputBox } from '@/components/InputBox';
import type { AgentMode } from '@/components/ModeToggle';

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AgentModeProvider>
    {children}
  </AgentModeProvider>
);

describe('Agent Mode Components', () => {
  beforeEach(() => {
    localStorage.clear();
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
      },
      writable: true,
    });
  });

  describe('ModeToggle', () => {
    it('renders mode toggle with chat mode as default', () => {
      render(
        <TestWrapper>
          <ModeToggle />
        </TestWrapper>
      );

      expect(screen.getByText('Chat Mode')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /toggle agent mode/i })).toBeInTheDocument();
    });

    it('shows agent mode when enabled', () => {
      render(
        <TestWrapper>
          <ModeToggle agentMode="agent" modeDisabled={false} />
        </TestWrapper>
      );

      expect(screen.getByText('Agent Mode')).toBeInTheDocument();
    });

    it('shows disabled state when agent mode is disabled', () => {
      render(
        <TestWrapper>
          <ModeToggle agentMode="agent" modeDisabled={true} />
        </TestWrapper>
      );

      expect(screen.getByText('Agent Mode (Disabled)')).toBeInTheDocument();
    });
  });

  describe('AgentModeProvider', () => {
    it('provides agent mode context', () => {
      let contextValue: any = null;

      const TestComponent = () => {
        contextValue = useAgentModeContext();
        return <div>Test</div>;
      };

      render(
        <TestWrapper>
          <TestComponent />
        </TestWrapper>
      );

      expect(contextValue).toBeTruthy();
      expect(contextValue.mode).toBe('chat');
      expect(typeof contextValue.changeMode).toBe('function');
      expect(typeof contextValue.enableAgentMode).toBe('function');
      expect(typeof contextValue.disableAgentMode).toBe('function');
    });

    it('persists mode changes to localStorage', () => {
      const TestComponent = () => {
        const { enableAgentMode } = useAgentModeContext();

        React.useEffect(() => {
          enableAgentMode();
        }, [enableAgentMode]);

        return <div>Test</div>;
      };

      render(
        <TestWrapper>
          <TestComponent />
        </TestWrapper>
      );

      expect(localStorage.setItem).toHaveBeenCalledWith(
        'agentMode',
        JSON.stringify({ mode: 'agent', isEnabled: true, hasAcceptedWarning: false })
      );
    });
  });

  describe('AgentModeWarning', () => {
    it('renders warning modal when open', () => {
      const mockOnClose = jest.fn();
      const mockOnAccept = jest.fn();
      const mockOnReject = jest.fn();

      render(
        <AgentModeWarning
          isOpen={true}
          onClose={mockOnClose}
          onAccept={mockOnAccept}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByText(/Enable Agent Mode/i)).toBeInTheDocument();
      expect(screen.getByText(/autonomous execution capabilities/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /accept/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /decline/i })).toBeInTheDocument();
    });

    it('does not render when closed', () => {
      const mockOnClose = jest.fn();
      const mockOnAccept = jest.fn();
      const mockOnReject = jest.fn();

      render(
        <AgentModeWarning
          isOpen={false}
          onClose={mockOnClose}
          onAccept={mockOnAccept}
          onReject={mockOnReject}
        />
      );

      expect(screen.queryByText(/Enable Agent Mode/i)).not.toBeInTheDocument();
    });
  });

  describe('InputBox', () => {
    it('shows mode-aware placeholder text', () => {
      const mockOnSubmit = jest.fn();

      render(
        <TestWrapper>
          <InputBox
            agentMode="chat"
            onSubmit={mockOnSubmit}
          />
        </TestWrapper>
      );

      expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    });

    it('shows agent mode placeholder', () => {
      const mockOnSubmit = jest.fn();

      render(
        <TestWrapper>
          <InputBox
            agentMode="agent"
            onSubmit={mockOnSubmit}
          />
        </TestWrapper>
      );

      expect(screen.getByPlaceholderText('Enable Agent Mode to use autonomous execution...')).toBeInTheDocument();
    });

    it('displays mode indicator when enabled', () => {
      const mockOnSubmit = jest.fn();

      render(
        <TestWrapper>
          <InputBox
            agentMode="agent"
            showModeIndicator={true}
            onSubmit={mockOnSubmit}
          />
        </TestWrapper>
      );

      expect(screen.getByText('Agent Mode (Disabled)')).toBeInTheDocument();
    });

    it('submits message when enter is pressed', async () => {
      const mockOnSubmit = jest.fn();

      render(
        <TestWrapper>
          <InputBox
            agentMode="chat"
            onSubmit={mockOnSubmit}
          />
        </TestWrapper>
      );

      const textarea = screen.getByPlaceholderText('Type your message...');
      fireEvent.change(textarea, { target: { value: 'Test message' } });
      fireEvent.keyDown(textarea, { key: 'Enter' });

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith('Test message');
      });
    });
  });

  describe('Integration Tests', () => {
    it('handles complete agent mode flow', async () => {
      let contextValue: any = null;

      const TestComponent = () => {
        contextValue = useAgentModeContext();
        const { mode, changeMode, canUseAgentMode } = contextValue;

        return (
          <div>
            <ModeToggle />
            <InputBox
              agentMode={mode}
              onSubmit={jest.fn()}
            />
          </div>
        );
      };

      render(
        <TestWrapper>
          <TestComponent />
        </TestWrapper>
      );

      // Initially in chat mode
      expect(screen.getByText('Chat Mode')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();

      // Click the mode toggle button
      const toggleButton = screen.getByRole('button', { name: /toggle agent mode/i });
      fireEvent.click(toggleButton);

      // Should show agent mode after enabling
      await waitFor(() => {
        expect(contextValue.mode).toBe('agent');
      });
    });
  });
});