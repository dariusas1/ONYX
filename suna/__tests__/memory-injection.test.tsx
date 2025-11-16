/**
 * Memory Injection Component Tests
 * Story 4-2: Memory Injection & Agent Integration
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryInjectionNotification, useMemoryInjectionNotification } from '../src/components/MemoryInjectionNotification';

// Mock Lucide icons
jest.mock('lucide-react', () => ({
  Brain: ({ className }: { className: string }) => <div data-testid="brain-icon" className={className} />,
  Clock: ({ className }: { className: string }) => <div data-testid="clock-icon" className={className} />,
  TrendingUp: ({ className }: { className: string }) => <div data-testid="trending-icon" className={className} />,
  AlertCircle: ({ className }: { className: string }) => <div data-testid="alert-icon" className={className} />,
  X: ({ className }: { className: string }) => <div data-testid="x-icon" className={className} />,
  ChevronDown: ({ className }: { className: string }) => <div data-testid="chevron-down-icon" className={className} />,
  ChevronUp: ({ className }: { className: string }) => <div data-testid="chevron-up-icon" className={className} />,
}));

// Mock timer functions
jest.useFakeTimers();

describe('MemoryInjectionNotification', () => {
  const mockInjection = {
    memories_count: 3,
    instructions_count: 2,
    injection_time_ms: 45,
    performance_stats: {
      cache_hit: true,
      memories: [
        {
          fact: 'User prefers TypeScript over JavaScript',
          category: 'preference',
          confidence: 0.9,
        },
        {
          fact: 'Working on Q4 financial planning',
          category: 'goal',
          confidence: 0.85,
        },
        {
          fact: 'Recent decision to migrate to React 18',
          category: 'decision',
          confidence: 0.95,
        },
      ],
      instructions: [
        {
          instruction_text: 'Always provide code examples with TypeScript types',
          category: 'workflow',
          priority: 8,
        },
        {
          instruction_text: 'Consider security implications in all recommendations',
          category: 'security',
          priority: 9,
        },
      ],
    },
  };

  beforeEach(() => {
    jest.clearAllTimers();
  });

  it('renders notification with injection data', () => {
    render(
      <MemoryInjectionNotification
        injection={mockInjection}
        onDismiss={jest.fn()}
      />
    );

    expect(screen.getByText('Memory Recall Active')).toBeInTheDocument();
    expect(screen.getByText('5 context items loaded')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // memories count
    expect(screen.getByText('2')).toBeInTheDocument(); // instructions count
    expect(screen.getByText('45ms')).toBeInTheDocument(); // load time
  });

  it('shows performance rating based on injection time', () => {
    const fastInjection = { ...mockInjection, injection_time_ms: 25 };
    const { rerender } = render(
      <MemoryInjectionNotification
        injection={fastInjection}
        onDismiss={jest.fn()}
      />
    );

    expect(screen.getByText('Excellent')).toBeInTheDocument();

    const slowInjection = { ...mockInjection, injection_time_ms: 250 };
    rerender(
      <MemoryInjectionNotification
        injection={slowInjection}
        onDismiss={jest.fn()}
      />
    );

    expect(screen.getByText('Slow')).toBeInTheDocument();
  });

  it('displays cache hit indicator', () => {
    render(
      <MemoryInjectionNotification
        injection={mockInjection}
        onDismiss={jest.fn()}
      />
    );

    expect(screen.getByTitle('Cache hit - loaded from memory')).toBeInTheDocument();
  });

  it('expands and collapses details when clicked', async () => {
    render(
      <MemoryInjectionNotification
        injection={mockInjection}
        onDismiss={jest.fn()}
      />
    );

    // Initially should not show detailed memories
    expect(screen.queryByText('Key Memories Retrieved')).not.toBeInTheDocument();

    // Click expand button
    const expandButton = screen.getByLabelText('Expand details');
    fireEvent.click(expandButton);

    // Should show expanded details
    await waitFor(() => {
      expect(screen.getByText('Key Memories Retrieved')).toBeInTheDocument();
      expect(screen.getByText('Standing Instructions Applied')).toBeInTheDocument();
      expect(screen.getByText('User prefers TypeScript over JavaScript')).toBeInTheDocument();
      expect(screen.getByText('Always provide code examples with TypeScript types')).toBeInTheDocument();
    });

    // Click collapse button
    const collapseButton = screen.getByLabelText('Collapse details');
    fireEvent.click(collapseButton);

    await waitFor(() => {
      expect(screen.queryByText('Key Memories Retrieved')).not.toBeInTheDocument();
    });
  });

  it('calls onDismiss when close button is clicked', () => {
    const mockOnDismiss = jest.fn();
    render(
      <MemoryInjectionNotification
        injection={mockInjection}
        onDismiss={mockOnDismiss}
      />
    );

    const closeButton = screen.getByLabelText('Dismiss notification');
    fireEvent.click(closeButton);

    // Should call onDismiss after animation (mocked with immediate)
    expect(mockOnDismiss).toHaveBeenCalled();
  });

  it('auto-dismisses after 8 seconds', () => {
    const mockOnDismiss = jest.fn();
    render(
      <MemoryInjectionNotification
        injection={mockInjection}
        onDismiss={mockOnDismiss}
      />
    );

    // Fast forward 8 seconds
    jest.advanceTimersByTime(8000);

    // Should have called onDismiss
    expect(mockOnDismiss).toHaveBeenCalled();
  });

  it('does not render when injection is null or has no items', () => {
    const { rerender } = render(
      <MemoryInjectionNotification
        injection={null}
        onDismiss={jest.fn()}
      />
    );

    expect(screen.queryByText('Memory Recall Active')).not.toBeInTheDocument();

    rerender(
      <MemoryInjectionNotification
        injection={{ ...mockInjection, memories_count: 0, instructions_count: 0 }}
        onDismiss={jest.fn()}
      />
    );

    expect(screen.queryByText('Memory Recall Active')).not.toBeInTheDocument();
  });

  it('shows truncated results when there are more items than display limit', async () => {
    const injectionWithManyItems = {
      ...mockInjection,
      performance_stats: {
        ...mockInjection.performance_stats,
        memories: Array.from({ length: 8 }, (_, i) => ({
          fact: `Memory fact ${i + 1}`,
          category: 'general',
          confidence: 0.8,
        })),
        instructions: Array.from({ length: 5 }, (_, i) => ({
          instruction_text: `Instruction ${i + 1}`,
          category: 'general',
          priority: 5,
        })),
      },
    };

    render(
      <MemoryInjectionNotification
        injection={injectionWithManyItems}
        onDismiss={jest.fn()}
      />
    );

    // Expand details
    const expandButton = screen.getByLabelText('Expand details');
    fireEvent.click(expandButton);

    await waitFor(() => {
      // Should show first 3 memories and "and 5 more"
      expect(screen.getByText('Memory fact 1')).toBeInTheDocument();
      expect(screen.getByText('... and 5 more memories')).toBeInTheDocument();

      // Should show first 3 instructions and "and 2 more"
      expect(screen.getByText('Instruction 1')).toBeInTheDocument();
      expect(screen.getByText('... and 2 more instructions')).toBeInTheDocument();
    });
  });
});

describe('useMemoryInjectionNotification hook', () => {
  it('manages notification state correctly', () => {
    const TestComponent = () => {
      const { injection, isVisible, showNotification, hideNotification } = useMemoryInjectionNotification();

      return (
        <div>
          <button onClick={() => showNotification({
            memories_count: 1,
            instructions_count: 1,
            injection_time_ms: 50,
            performance_stats: {},
          })}>
            Show
          </button>
          <button onClick={hideNotification}>Hide</button>
          <div data-testid="injection-visible">{injection ? 'visible' : 'hidden'}</div>
          <div data-testid="is-visible">{isVisible ? 'true' : 'false'}</div>
        </div>
      );
    };

    render(<TestComponent />);

    // Initially hidden
    expect(screen.getByTestId('injection-visible')).toHaveTextContent('hidden');
    expect(screen.getByTestId('is-visible')).toHaveTextContent('false');

    // Show notification
    fireEvent.click(screen.getByText('Show'));
    expect(screen.getByTestId('injection-visible')).toHaveTextContent('visible');
    expect(screen.getByTestId('is-visible')).toHaveTextContent('true');

    // Hide notification
    fireEvent.click(screen.getByText('Hide'));
    // Note: Due to setTimeout in hideNotification, we need to advance timers
    jest.advanceTimersByTime(300);
    expect(screen.getByTestId('injection-visible')).toHaveTextContent('hidden');
    expect(screen.getByTestId('is-visible')).toHaveTextContent('false');
  });
});