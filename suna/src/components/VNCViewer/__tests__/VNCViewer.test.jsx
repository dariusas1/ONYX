import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import VNCViewer from '../VNCViewer';

describe('VNCViewer Component', () => {
  const defaultProps = {
    url: 'ws://localhost:6080',
    onConnect: jest.fn(),
    onDisconnect: jest.fn(),
    onError: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock canvas methods
    HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
      fillStyle: '',
      fillRect: jest.fn(),
      createLinearGradient: jest.fn(() => ({
        addColorStop: jest.fn(),
        fillRect: jest.fn()
      })),
      font: '',
      textAlign: '',
      fillText: jest.fn()
    }));

    // Mock getBoundingClientRect
    Element.prototype.getBoundingClientRect = jest.fn(() => ({
      width: 800,
      height: 600,
      left: 0,
      top: 0,
      right: 800,
      bottom: 600,
      x: 0,
      y: 0
    }));

    // Mock resize observer
    global.ResizeObserver = jest.fn().mockImplementation(() => ({
      observe: jest.fn(),
      unobserve: jest.fn(),
      disconnect: jest.fn()
    }));
  });

  it('renders without crashing', () => {
    render(<VNCViewer {...defaultProps} />);

    // Should show connection status overlay initially
    expect(screen.getByText('Connecting to workspace...')).toBeInTheDocument();
  });

  it('shows connecting state initially', () => {
    render(<VNCViewer {...defaultProps} />);

    expect(screen.getByText('Connecting to workspace...')).toBeInTheDocument();
    expect(screen.getByText('VNC Server: ws://localhost:6080')).toBeInTheDocument();
  });

  it('shows disconnected state when connection fails', async () => {
    render(<VNCViewer {...defaultProps} />);

    // Wait for connection state to become error (simulated timeout)
    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  it('calls retry connection when retry button is clicked', async () => {
    const mockRFB = require('@novnc/novnc/core/rfb');
    let connectCallCount = 0;
    mockRFB.mockImplementation(() => {
      connectCallCount++;
      const instance = {
        addEventListener: jest.fn(),
        disconnect: jest.fn(),
        resize: jest.fn(),
        sendMouseButton: jest.fn(),
        sendMouseMove: jest.fn(),
        sendMouseWheel: jest.fn(),
        keyboardEvents: {
          push: jest.fn()
        }
      };

      // Simulate initial connection failure
      if (connectCallCount === 1) {
        setTimeout(() => {
          const errorListeners = instance.addEventListener.mock.calls
            .find(call => call[0] === 'failure');
          if (errorListeners) {
            const [_, handler] = errorListeners;
            handler({ detail: { reason: 'Initial failure' } });
          }
        }, 100);
      }

      return instance;
    });

    render(<VNCViewer {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    // Click retry button
    fireEvent.click(screen.getByText('Retry'));

    // Should trigger another connection attempt
    expect(mockRFB).toHaveBeenCalledTimes(2);
  });

  it('shows connected state when connection succeeds', async () => {
    const mockRFB = require('@novnc/novnc/core/rfb');
    mockRFB.mockImplementation(() => {
      const instance = {
        addEventListener: jest.fn(),
        disconnect: jest.fn(),
        resize: jest.fn(),
        sendMouseButton: jest.fn(),
        sendMouseMove: jest.fn(),
        sendMouseWheel: jest.fn(),
        keyboardEvents: {
          push: jest.fn()
        }
      };

      // Simulate successful connection
      setTimeout(() => {
        const connectListeners = instance.addEventListener.mock.calls
          .find(call => call[0] === 'connect');
        if (connectListeners) {
          const [_, handler] = connectListeners;
          handler();
        }
      }, 100);

      return instance;
    });

    render(<VNCViewer {...defaultProps} />);

    await waitFor(() => {
      expect(defaultProps.onConnect).toHaveBeenCalled();
    });
  });

  it('handles keyboard events when connected', async () => {
    const mockRFB = require('@novnc/novnc/core/rfb');
    mockRFB.mockImplementation(() => {
      const instance = {
        addEventListener: jest.fn(),
        disconnect: jest.fn(),
        resize: jest.fn(),
        sendMouseButton: jest.fn(),
        sendMouseMove: jest.fn(),
        sendMouseWheel: jest.fn(),
        keyboardEvents: {
          push: jest.fn()
        }
      };

      setTimeout(() => {
        const connectListeners = instance.addEventListener.mock.calls
          .find(call => call[0] === 'connect');
        if (connectListeners) {
          const [_, handler] = connectListeners;
          handler();
        }
      }, 100);

      return instance;
    });

    render(<VNCViewer {...defaultProps} />);

    await waitFor(() => {
      expect(defaultProps.onConnect).toHaveBeenCalled();
    });

    // Find the container element
    const container = screen.getByRole('main');

    // Simulate keyboard event
    fireEvent.keyDown(container, { key: 'a', keyCode: 65 });

    await waitFor(() => {
      expect(mockRFB.keyboardEvents.push).toHaveBeenCalled();
    });
  });

  it('handles mouse events when connected', async () => {
    const mockRFB = require('@novnc/novnc/core/rfb');
    const mockSendMouseButton = jest.fn();
    const mockSendMouseMove = jest.fn();

    mockRFB.mockImplementation(() => {
      const instance = {
        addEventListener: jest.fn(),
        disconnect: jest.fn(),
        resize: jest.fn(),
        sendMouseButton: mockSendMouseButton,
        sendMouseMove: mockSendMouseMove,
        sendMouseWheel: jest.fn(),
        keyboardEvents: {
          push: jest.fn()
        }
      };

      setTimeout(() => {
        const connectListeners = instance.addEventListener.mock.calls
          .find(call => call[0] === 'connect');
        if (connectListeners) {
          const [_, handler] = connectListeners;
          handler();
        }
      }, 100);

      return instance;
    });

    render(<VNCViewer {...defaultProps} />);

    await waitFor(() => {
      expect(defaultProps.onConnect).toHaveBeenCalled();
    });

    // Find the canvas element
    const canvas = screen.getByRole('img') || screen.getByText('') || document.querySelector('canvas');

    // Simulate mouse events
    fireEvent.mouseDown(canvas, { button: 0, clientX: 100, clientY: 100 });
    fireEvent.mouseMove(canvas, { clientX: 110, clientY: 110 });
    fireEvent.mouseUp(canvas, { button: 0, clientX: 110, clientY: 110 });

    await waitFor(() => {
      expect(mockSendMouseButton).toHaveBeenCalledWith(100, 100, 0, true);
      expect(mockSendMouseMove).toHaveBeenCalledWith(110, 110);
      expect(mockSendMouseButton).toHaveBeenCalledWith(110, 110, 0, false);
    });
  });

  it('shows stats when settings button is clicked', () => {
    render(<VNCViewer {...defaultProps} />);

    // Find and click settings button
    const settingsButton = screen.getByTitle('Toggle Stats');
    fireEvent.click(settingsButton);

    // Should show stats panel
    expect(screen.getByText('FPS:')).toBeInTheDocument();
    expect(screen.getByText('Quality: 6/9')).toBeInTheDocument();
    expect(screen.getByText('Compression: 1/9')).toBeInTheDocument();
    expect(screen.getByText('Scale: On')).toBeInTheDocument();
  });

  it('toggles fullscreen functionality', () => {
    render(<VNCViewer {...defaultProps} />);

    // Mock fullscreen API
    Object.defineProperty(document, 'fullscreenElement', {
      writable: true,
      value: null
    });

    const mockRequestFullscreen = jest.fn();
    const mockExitFullscreen = jest.fn();

    global.Element.prototype.requestFullscreen = mockRequestFullscreen;
    document.exitFullscreen = mockExitFullscreen;

    // Find and click fullscreen button
    const fullscreenButton = screen.getByTitle('Enter Fullscreen');
    fireEvent.click(fullscreenButton);

    expect(mockRequestFullscreen).toHaveBeenCalled();
  });

  it('displays connection status indicator', () => {
    render(<VNCViewer {...defaultProps} />);

    // Should show connecting status initially
    expect(screen.getByText('connecting')).toBeInTheDocument();
  });

  it('passes custom settings to VNC connection', () => {
    const customProps = {
      ...defaultProps,
      scale: false,
      quality: 8,
      compression: 5
    };

    const mockRFB = require('@novnc/novnc/core/rfb');
    mockRFB.mockImplementation(() => ({
      addEventListener: jest.fn(),
      disconnect: jest.fn(),
      resize: jest.fn(),
      sendMouseButton: jest.fn(),
      sendMouseMove: jest.fn(),
      sendMouseWheel: jest.fn(),
      keyboardEvents: {
        push: jest.fn()
      }
    }));

    render(<VNCViewer {...customProps} />);

    expect(mockRFB).toHaveBeenCalledWith(expect.any(HTMLCanvasElement), 'ws://localhost:6080', expect.objectContaining({
      scaleViewport: false,
      quality: 8,
      compression: 5
    }));
  });
});