import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import WorkspacePanel from '../WorkspacePanel';

// Mock VNCViewer
jest.mock('../VNCViewer/VNCViewer', () => {
  return function MockVNCViewer({ onConnect, onDisconnect, onError }) {
    // Mock successful connection after a short delay
    React.useEffect(() => {
      const timer = setTimeout(() => {
        onConnect?.();
      }, 100);
      return () => clearTimeout(timer);
    }, [onConnect]);

    return (
      <div data-testid="vnc-viewer">
        Mock VNC Viewer
        <button onClick={() => onDisconnect?.('test disconnect')}>
          Disconnect
        </button>
        <button onClick={() => onError?.('test error')}>
          Error
        </button>
      </div>
    );
  };
});

describe('WorkspacePanel Component', () => {
  const defaultProps = {
    isOpen: true,
    onToggle: jest.fn(),
    vncUrl: 'ws://localhost:6080'
  };

  beforeEach(() => {
    jest.clearAllMocks();

    // Mock window dimensions for responsive testing
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024
    });
  });

  it('renders when open', () => {
    render(<WorkspacePanel {...defaultProps} />);

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByTestId('vnc-viewer')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<WorkspacePanel {...defaultProps} isOpen={false} />);

    expect(screen.queryByText('Workspace')).not.toBeInTheDocument();
    expect(screen.queryByTestId('vnc-viewer')).not.toBeInTheDocument();
  });

  it('shows show workspace button when closed', () => {
    render(<WorkspacePanel {...defaultProps} isOpen={false} />);

    expect(screen.getByText('Show Workspace')).toBeInTheDocument();
  });

  it('calls onToggle when show/hide button is clicked', () => {
    const { rerender } = render(<WorkspacePanel {...defaultProps} isOpen={false} />);

    // Click show workspace button
    fireEvent.click(screen.getByText('Show Workspace'));
    expect(defaultProps.onToggle).toHaveBeenCalledTimes(1);

    // Rerender with panel open
    rerender(<WorkspacePanel {...defaultProps} isOpen={true} />);

    // Click close button
    const closeButton = screen.getByTitle('Hide Workspace');
    fireEvent.click(closeButton);
    expect(defaultProps.onToggle).toHaveBeenCalledTimes(2);
  });

  it('opens settings panel when settings button is clicked', () => {
    render(<WorkspacePanel {...defaultProps} />);

    const settingsButton = screen.getByTitle('Workspace Settings');
    fireEvent.click(settingsButton);

    expect(screen.getByText('VNC Settings')).toBeInTheDocument();
    expect(screen.getByText('Scale to Fit')).toBeInTheDocument();
    expect(screen.getByText('Quality: 6')).toBeInTheDocument();
    expect(screen.getByText('Compression: 1')).toBeInTheDocument();
  });

  it('toggles settings when setting buttons are clicked', () => {
    render(<WorkspacePanel {...defaultProps} />);

    // Open settings
    const settingsButton = screen.getByTitle('Workspace Settings');
    fireEvent.click(settingsButton);

    // Toggle scale setting
    const scaleToggle = screen.getByText('Scale to Fit');
    fireEvent.click(scaleToggle);

    expect(screen.getByText('Compression: 1')).toBeInTheDocument();
  });

  it('handles range slider interactions', () => {
    render(<WorkspacePanel {...defaultProps} />);

    // Open settings
    const settingsButton = screen.getByTitle('Workspace Settings');
    fireEvent.click(settingsButton);

    // Adjust quality slider
    const qualitySlider = screen.getByDisplayValue('6');
    fireEvent.change(qualitySlider, { target: { value: '8' } });

    // Adjust compression slider
    const compressionSlider = screen.getByDisplayValue('1');
    fireEvent.change(compressionSlider, { target: { value: '5' } });
  });

  it('expands panel when expand button is clicked (desktop only)', () => {
    // Mock desktop dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200
    });

    render(<WorkspacePanel {...defaultProps} />);

    const expandButton = screen.getByTitle('Expand Panel');
    fireEvent.click(expandButton);

    // Should now show collapse button
    expect(screen.getByTitle('Collapse Panel')).toBeInTheDocument();
  });

  it('shows mobile device indicator on mobile screens', () => {
    // Mock mobile dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Should show mobile indicator
    expect(screen.getByText('Mobile')).toBeInTheDocument();
  });

  it('shows tablet device indicator on tablet screens', () => {
    // Mock tablet dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Should show tablet indicator
    expect(screen.getByText('Tablet')).toBeInTheDocument();
  });

  it('shows touch controls note on mobile', () => {
    // Mock mobile dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Open settings
    const settingsButton = screen.getByTitle('Workspace Settings');
    fireEvent.click(settingsButton);

    expect(screen.getByText(/Touch Controls:/)).toBeInTheDocument();
    expect(screen.getByText(/Use the button below to minimize/)).toBeInTheDocument();
  });

  it('shows touch controls note on tablet', () => {
    // Mock tablet dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Open settings
    const settingsButton = screen.getByTitle('Workspace Settings');
    fireEvent.click(settingsButton);

    expect(screen.getByText(/Touch Controls:/)).toBeInTheDocument();
  });

  it('shows mobile footer controls on mobile', () => {
    // Mock mobile dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375
    });

    render(<WorkspacePanel {...defaultProps} />);

    expect(screen.getByText('Touch gestures enabled')).toBeInTheDocument();
    expect(screen.getByText('Maximize')).toBeInTheDocument();
  });

  it('shows resize handle on desktop when not expanded', () => {
    // Mock desktop dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Should show resize handle (though it might be styled differently)
    expect(screen.getByTitle('Drag to resize panel')).toBeInTheDocument();
  });

  it('handles VNC connection events', async () => {
    const mockOnConnect = jest.fn();
    const mockOnDisconnect = jest.fn();
    const mockOnError = jest.fn();

    render(
      <WorkspacePanel
        {...defaultProps}
        onConnect={mockOnConnect}
        onDisconnect={mockOnDisconnect}
        onError={mockOnError}
      />
    );

    // Wait for VNC to connect
    await waitFor(() => {
      expect(mockOnConnect).toHaveBeenCalled();
    });

    // Simulate VNC disconnect
    fireEvent.click(screen.getByText('Disconnect'));
    expect(mockOnDisconnect).toHaveBeenCalledWith('test disconnect');

    // Simulate VNC error
    fireEvent.click(screen.getByText('Error'));
    expect(mockOnError).toHaveBeenCalledWith('test error');
  });

  it('auto-expands on mobile when VNC connects', async () => {
    const mockOnConnect = jest.fn();

    // Mock mobile dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375
    });

    render(
      <WorkspacePanel
        {...defaultProps}
        onConnect={mockOnConnect}
      />
    );

    // Wait for VNC to connect
    await waitFor(() => {
      expect(mockOnConnect).toHaveBeenCalled();
    });

    // Should show mobile footer with maximize/minimize controls
    expect(screen.getByText('Touch gestures enabled')).toBeInTheDocument();
  });

  it('renders overlay on mobile and tablet when open', () => {
    // Mock mobile dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Should render overlay (it would be invisible but present in DOM)
    expect(document.querySelector('.fixed.inset-0.bg-black\\/50')).toBeInTheDocument();
  });

  it('does not render overlay on desktop', () => {
    // Mock desktop dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200
    });

    render(<WorkspacePanel {...defaultProps} />);

    // Should not render overlay
    expect(document.querySelector('.fixed.inset-0.bg-black\\/50')).not.toBeInTheDocument();
  });
});