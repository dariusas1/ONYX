import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WorkspaceProvider } from '../../../contexts/WorkspaceContext';
import { WorkspacePanel } from '../WorkspacePanel';

// Mock VNCViewer component
jest.mock('../../VNCViewer/VNCViewer', () => {
  return function MockVNCViewer({ onConnect, onDisconnect, onError }) {
    React.useEffect(() => {
      // Simulate successful connection after component mount
      setTimeout(onConnect, 100);
    }, [onConnect]);

    return (
      <div data-testid="vnc-viewer">
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
});