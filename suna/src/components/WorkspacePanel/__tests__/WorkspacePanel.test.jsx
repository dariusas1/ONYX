import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { WorkspaceProvider } from '../../../contexts/WorkspaceContext';
import { WorkspacePanel } from '../WorkspacePanel';

// Mock VNCViewer component
jest.mock('../../VNCViewer/VNCViewer', () => {
  return function MockVNCViewer({
    onConnect,
    onDisconnect,
    onError,
    url,
    scale,
    quality,
    compression,
    className
  }) {
    React.useEffect(() => {
      // Simulate successful connection after component mount
      const timer = setTimeout(onConnect, 100);
      return () => clearTimeout(timer);
    }, [onConnect]);

    return (
      <div
        data-testid="vnc-viewer"
        data-url={url}
        data-scale={scale}
        data-quality={quality}
        data-compression={compression}
        className={className}
      >
        <div data-testid="vnc-canvas" />
        Mock VNC Viewer
      </div>
    );
  };
});

describe('WorkspacePanel Component', () => {
  const defaultProps = {
    isOpen: false,
    onToggle: jest.fn(),
    vncUrl: 'ws://localhost:6080'
  };

  const renderWithWorkspaceProvider = (component) => {
    return render(
      <WorkspaceProvider>
        {component}
      </WorkspaceProvider>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock window.innerWidth for responsive design tests
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200, // Desktop default
    });
  });

  test('renders workspace toggle button when closed', () => {
    renderWithWorkspaceProvider(<WorkspacePanel {...defaultProps} />);

    const toggleButton = screen.getByText('Show Workspace');
    expect(toggleButton).toBeInTheDocument();
    expect(screen.getByTestId('vnc-viewer')).not.toBeInTheDocument();
  });

  test('calls onToggle when toggle button is clicked', () => {
    const mockOnToggle = jest.fn();
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} onToggle={mockOnToggle} />
    );

    const toggleButton = screen.getByText('Show Workspace');
    fireEvent.click(toggleButton);

    expect(mockOnToggle).toHaveBeenCalledTimes(1);
  });

  test('renders workspace panel when open', () => {
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} />
    );

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByTestId('vnc-viewer')).toBeInTheDocument();
    expect(screen.queryByText('Show Workspace')).not.toBeInTheDocument();
  });

  test('renders workspace header with controls', () => {
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} />
    );

    expect(screen.getByText('Workspace')).toBeInTheDocument();
    expect(screen.getByTitle('Workspace Settings')).toBeInTheDocument();
    expect(screen.getByTitle('Expand Panel')).toBeInTheDocument();
    expect(screen.getByTitle('Hide Workspace')).toBeInTheDocument();
  });

  test('toggles settings panel when settings button is clicked', async () => {
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} />
    );

    const settingsButton = screen.getByTitle('Workspace Settings');
    expect(screen.queryByText('VNC Settings')).not.toBeInTheDocument();

    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('VNC Settings')).toBeInTheDocument();
    });
  });

  test('renders VNC settings controls', async () => {
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} />
    );

    // Open settings panel
    const settingsButton = screen.getByTitle('Workspace Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('Scale to Fit')).toBeInTheDocument();
      expect(screen.getByText('Quality:')).toBeInTheDocument();
      expect(screen.getByText('Compression:')).toBeInTheDocument();
    });
  });

  test('calls onToggle when close button is clicked', () => {
    const mockOnToggle = jest.fn();
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} onToggle={mockOnToggle} />
    );

    const closeButton = screen.getByTitle('Hide Workspace');
    fireEvent.click(closeButton);

    expect(mockOnToggle).toHaveBeenCalledTimes(1);
  });

  test('renders connection status indicator', () => {
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} />
    );

    // Connection indicator should be visible with green dot
    const greenDot = document.querySelector('.bg-green-400.rounded-full');
    expect(greenDot).toBeInTheDocument();
  });

  test('applies correct CSS classes for panel state', () => {
    const { container } = renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} />
    );

    const panel = container.querySelector('.fixed.top-0.right-0');
    expect(panel).toHaveClass('translate-x-0');
  });

  test('applies correct CSS classes when closed', () => {
    const { container } = renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={false} />
    );

    const panel = container.querySelector('.fixed.top-0.right-0');
    expect(panel).toHaveClass('translate-x-full');
  });

  test('handles custom vncUrl prop', () => {
    renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} vncUrl="ws://custom:8080" />
    );

    expect(screen.getByTestId('vnc-viewer')).toBeInTheDocument();
  });

  test('applies custom className', () => {
    const { container } = renderWithWorkspaceProvider(
      <WorkspacePanel {...defaultProps} isOpen={true} className="custom-class" />
    );

    const panel = container.querySelector('.custom-class');
    expect(panel).toBeInTheDocument();
  });

  // Enhanced Tests for New Functionality

  describe('Enhanced VNC Settings', () => {
    test('passes correct props to VNC viewer', async () => {
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      await waitFor(() => {
        const vncViewer = screen.getByTestId('vnc-viewer');
        expect(vncViewer).toHaveAttribute('data-url', 'ws://localhost:6080');
        expect(vncViewer).toHaveAttribute('data-scale', 'true');
        expect(vncViewer).toHaveAttribute('data-quality', '6');
        expect(vncViewer).toHaveAttribute('data-compression', '1');
      });
    });

    test('renders enhanced settings panel with descriptions', async () => {
      const user = userEvent.setup();
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const settingsButton = screen.getByTitle('Workspace Settings');
      await user.click(settingsButton);

      await waitFor(() => {
        expect(screen.getByText('Higher quality = more bandwidth')).toBeInTheDocument();
        expect(screen.getByText('Higher compression = less bandwidth')).toBeInTheDocument();
        expect(screen.getByText('Better for desktop viewing')).toBeInTheDocument();
      });
    });

    test('shows quality slider labels', async () => {
      const user = userEvent.setup();
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const settingsButton = screen.getByTitle('Workspace Settings');
      await user.click(settingsButton);

      await waitFor(() => {
        expect(screen.getByText('Fast')).toBeInTheDocument();
        expect(screen.getByText('Balanced')).toBeInTheDocument();
        expect(screen.getByText('High')).toBeInTheDocument();
      });
    });

    test('shows compression slider labels', async () => {
      const user = userEvent.setup();
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const settingsButton = screen.getByTitle('Workspace Settings');
      await user.click(settingsButton);

      await waitFor(() => {
        expect(screen.getByText('None')).toBeInTheDocument();
        expect(screen.getByText('Medium')).toBeInTheDocument();
        expect(screen.getByText('Max')).toBeInTheDocument();
      });
    });
  });

  describe('Connection Status Integration', () => {
    test('displays connection status quick indicator when connected', async () => {
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      await waitFor(() => {
        // After VNC connects, status should be visible
        const statusIndicator = screen.getByText('Connected');
        expect(statusIndicator).toBeInTheDocument();
      });
    });

    test('shows connection info in settings when connected', async () => {
      const user = userEvent.setup();
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument();
      });

      const settingsButton = screen.getByTitle('Workspace Settings');
      await user.click(settingsButton);

      expect(screen.getByText('ws://localhost:6080')).toBeInTheDocument();
      expect(screen.getAllByText('Connected').length).toBeGreaterThan(0);
    });
  });

  describe('Responsive Design', () => {
    test('adapts UI for tablet viewport', async () => {
      // Mock tablet viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      });

      const user = userEvent.setup();
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      // Check tablet-specific adjustments
      await waitFor(() => {
        expect(screen.getByText('Better for tablet viewing')).toBeInTheDocument();
      });

      const settingsButton = screen.getByTitle('Workspace Settings');
      await user.click(settingsButton);

      expect(screen.getByText('Better for tablet viewing')).toBeInTheDocument();
    });

    test('hides expand button on tablet', async () => {
      // Mock tablet viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      });

      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      // Expand button should not be present on tablet
      expect(screen.queryByTitle('Expand Panel')).not.toBeInTheDocument();
    });

    test('shows ESC hint in tablet mode', async () => {
      // Mock tablet viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      });

      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const closeButton = screen.getByTitle('Hide Workspace (ESC)');
      expect(closeButton).toBeInTheDocument();
    });

    test('uses correct panel width for desktop expanded', () => {
      // Mock desktop viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1200,
      });

      const { container } = renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      // Check for desktop panel width class when expanded
      const panel = container.querySelector('.w-1\\/2, .w-\\[30\\%\\]');
      expect(panel).toBeInTheDocument();
    });
  });

  describe('Keyboard Interactions', () => {
    test('closes panel on Escape key press (desktop)', async () => {
      const user = userEvent.setup();
      const mockOnToggle = jest.fn();

      // Mock desktop viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1200,
      });

      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} onToggle={mockOnToggle} />
      );

      await user.keyboard('{Escape}');
      expect(mockOnToggle).toHaveBeenCalledTimes(1);
    });

    test('does not close panel on Escape key press (tablet)', async () => {
      const user = userEvent.setup();
      const mockOnToggle = jest.fn();

      // Mock tablet viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      });

      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} onToggle={mockOnToggle} />
      );

      await user.keyboard('{Escape}');
      expect(mockOnToggle).not.toHaveBeenCalled();
    });
  });

  describe('Enhanced UI States', () => {
    test('shows enhanced connection status with color coding', async () => {
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      await waitFor(() => {
        // Should show connected status
        const statusDot = document.querySelector('.bg-green-400.rounded-full');
        expect(statusDot).toBeInTheDocument();
      });
    });

    test('highlights active settings button', async () => {
      const user = userEvent.setup();
      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const settingsButton = screen.getByTitle('Workspace Settings');
      expect(settingsButton).not.toHaveClass('bg-blue-600');

      await user.click(settingsButton);

      expect(settingsButton).toHaveClass('bg-blue-600');
    });

    test('shows responsive overlay on tablets', async () => {
      // Mock tablet viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      });

      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const overlay = document.querySelector('.fixed.inset-0.z-20');
      expect(overlay).toBeInTheDocument();
      expect(overlay).toHaveClass('bg-black/50');
    });

    test('hides resize handle on tablets', async () => {
      // Mock tablet viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 800,
      });

      renderWithWorkspaceProvider(
        <WorkspacePanel {...defaultProps} isOpen={true} />
      );

      const resizeHandle = document.querySelector('.cursor-ew-resize');
      expect(resizeHandle).not.toBeInTheDocument();
    });
  });

  describe('VNC Viewer Integration', () => {
    test('handles VNC connection events', async () => {
      const mockOnConnect = jest.fn();
      const mockOnDisconnect = jest.fn();
      const mockOnError = jest.fn();

      renderWithWorkspaceProvider(
        <WorkspacePanel
          {...defaultProps}
          isOpen={true}
          onConnect={mockOnConnect}
          onDisconnect={mockOnDisconnect}
          onError={mockOnError}
        />
      );

      await waitFor(() => {
        expect(mockOnConnect).toHaveBeenCalled();
      });

      const vncViewer = screen.getByTestId('vnc-viewer');
      expect(vncViewer).toBeInTheDocument();
      expect(vncViewer).toHaveAttribute('data-url', 'ws://localhost:6080');
    });

    test('passes updated VNC settings to viewer', async () => {
      renderWithWorkspaceProvider(
        <WorkspacePanel
          {...defaultProps}
          isOpen={true}
          vncUrl="ws://custom:8080"
        />
      );

      await waitFor(() => {
        const vncViewer = screen.getByTestId('vnc-viewer');
        expect(vncViewer).toHaveAttribute('data-url', 'ws://custom:8080');
      });
    });
  });
});